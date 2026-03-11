import pygame
import math
import random
import collections
from neural_net import NeuralNet
from fish_traits import FishTraits
from fish_physics import SteeringPhysics
from config import *
from family import Family
from environment_objects import PoopParticle


class NeuralFish:
    INPUT_COUNT = 14
    OUTPUT_COUNT = 2

    def __init__(self, world, traits=None, brain=None, is_cleaner=False):
        self.world = world
        self.is_cleaner = is_cleaner
        self.is_predator = False
        self.traits = traits if traits else FishTraits()
        self.brain = (
            brain if brain else NeuralNet(self.INPUT_COUNT, 12, self.OUTPUT_COUNT)
        )
        start_x = random.uniform(100, WORLD_WIDTH - 100)
        start_y = random.uniform(WATER_LINE_Y + 100, WORLD_HEIGHT - 200)
        self.physics = SteeringPhysics(start_x, start_y, FISH_MAX_SPEED, FISH_MAX_FORCE)

        # Apply physical trait multipliers
        self.physics.max_speed *= self.traits.physical_traits.get("max_speed_mult", 1.0)
        self.physics.max_force *= self.traits.physical_traits.get("turn_rate_mult", 1.0)
        self.age = 0.0
        self.energy = FISH_MAX_ENERGY * 0.8
        self.stamina = 100.0
        self.state = FishState.RESTING
        self.sex = random.choice(["M", "F"])
        self.mating_cooldown = 20.0
        self.is_mature = False
        self.is_hidden = False
        self.is_pregnant = False
        self.pregnancy_traits = None
        self.pregnancy_partner = None
        self.security_level = 0.0
        self.family = None

        # Store last neural activity for visualization
        self.last_inputs = [0.0] * self.INPUT_COUNT
        self.last_hidden = [0.0] * self.brain.hidden2_size
        self.last_hidden1 = [0.0] * self.brain.hidden_size
        self.last_outputs = [0.0] * self.OUTPUT_COUNT
        self.output_history = collections.deque(maxlen=60)

        # Lifetime counters
        self.food_eaten = 0
        self.distance_traveled = 0.0
        self.offspring_count = 0

    @property
    def pos(self):
        return self.physics.pos

    def get_radar_inputs(self, all_fish, targets, plant_manager):
        radar = [0.0] * 9
        self.is_hidden = False
        min_plant_dist = 9999
        self.closest_plant = None
        for plant in plant_manager.plants:
            dist_to_base = self.physics.pos.distance_to((plant.x, plant.base_y))
            if dist_to_base < min_plant_dist:
                min_plant_dist = dist_to_base
                self.closest_plant = plant
            if dist_to_base < 60:
                self.is_hidden = True
                self.security_level = max(0, 1.0 - (min_plant_dist / 160.0))

        def fill_radar(objects, offset, is_threat_radar=False, bias_multiplier=1.0):
            for obj in objects:
                if is_threat_radar and getattr(obj, "is_hidden", False):
                    continue
                ox = getattr(
                    obj, "x", obj.physics.pos.x if hasattr(obj, "physics") else 0
                )
                oy = getattr(
                    obj, "y", obj.physics.pos.y if hasattr(obj, "physics") else 0
                )
                dist = self.physics.pos.distance_to((ox, oy))
                detection_range = FISH_SENSOR_RANGE
                if is_threat_radar and self.is_hidden:
                    detection_range *= 0.5
                if dist < detection_range and dist > 0:
                    angle = math.atan2(oy - self.physics.pos.y, ox - self.physics.pos.x) - self.physics.heading
                    angle = (angle + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle) < FISH_SENSOR_ARC:
                        sector = int(
                            (angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3
                        )
                        sector = max(0, min(2, sector))
                        radar[offset + sector] += (1.0 - (dist / detection_range)) * bias_multiplier

        # State biasing: amplify the radar signals relevant to current state
        # so the neural net receives a clearer gradient toward the right behavior.
        food_bias = 1.0
        threat_bias = 1.0
        mate_bias = 1.0

        if self.state == FishState.HUNTING:
            food_bias = 2.5
        elif self.state == FishState.MATING:
            mate_bias = 2.5
        elif self.state == FishState.FLEEING:
            threat_bias = 3.0
        elif self.state == FishState.NESTING:
            # Virtual "food" signal pointing toward closest plant for nesting
            if self.closest_plant and min_plant_dist < 300:
                dx = self.closest_plant.x - self.physics.pos.x
                dy = self.closest_plant.base_y - self.physics.pos.y
                dist = max(1, min_plant_dist)
                angle = math.atan2(dy, dx) - self.physics.heading
                angle = (angle + math.pi) % (2 * math.pi) - math.pi
                if abs(angle) < FISH_SENSOR_ARC:
                    sector = int((angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3)
                    sector = max(0, min(2, sector))
                    radar[6 + sector] += (1.0 - (dist / 300)) * 2.0
        elif self.state == FishState.RESTING:
            food_bias = 0.4
            threat_bias = 0.6
            mate_bias = 0.4

        fill_radar(targets, 0, bias_multiplier=food_bias)
        threats = [f for f in all_fish if getattr(f, "is_predator", False)]
        fill_radar(threats, 3, is_threat_radar=True, bias_multiplier=threat_bias)
        mates = [
            f
            for f in all_fish
            if f.is_cleaner == self.is_cleaner
            and f.is_predator == self.is_predator
            and f.sex != self.sex
            and f.is_mature
        ]
        fill_radar(mates, 6, bias_multiplier=mate_bias)
        return [min(1.0, v) for v in radar]

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        self.age += dt
        metabolism_rate = 0.1 * self.traits.physical_traits.get("metabolism_mult", 1.0)
        self.energy -= metabolism_rate * dt
        self.mating_cooldown = max(0, self.mating_cooldown - dt)
        self.is_mature = self.age > (FISH_LARVA_DURATION + FISH_JUVENILE_DURATION)

        # Stamina: drains at high speed, recovers at rest
        speed_ratio = self.physics.vel.length() / max(1.0, self.physics.max_speed)
        if speed_ratio > 0.8:
            self.stamina = max(0.0, self.stamina - 15.0 * speed_ratio * dt)
        elif speed_ratio < 0.3:
            recovery = 8.0 * self.traits.physical_traits.get("stamina_mult", 1.0) * dt
            self.stamina = min(100.0, self.stamina + recovery)

        radar = self.get_radar_inputs(all_fish, targets, plant_manager)

        # ── State determination ────────────────────────────────────────────────
        # State sets input biases (see get_radar_inputs) and speed ceiling, but
        # the NEURAL NET decides the actual heading and throttle.
        threat_level = sum(radar[3:6])
        if threat_level > 0.3:
            self.state = FishState.FLEEING
        elif self.is_pregnant:
            self.state = FishState.NESTING
        elif self.energy < FISH_HUNGER_THRESHOLD:
            self.state = FishState.HUNTING
        elif (
            self.is_mature
            and self.energy > FISH_MATING_THRESHOLD
            and self.mating_cooldown <= 0
        ):
            self.state = FishState.MATING
        else:
            self.state = FishState.RESTING

        # ── Neural forward pass ───────────────────────────────────────────────
        stats = [
            self.energy / FISH_MAX_ENERGY,          # 9:  energy level
            self.stamina / 100.0,                   # 10: stamina level
            (self.physics.pos.y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y),  # 11: depth
            self.physics.vel.length() / self.physics.max_speed,  # 12: current speed ratio
            self.security_level,                    # 13: plant cover
        ]

        self.last_inputs = radar + stats
        outputs, hidden1, hidden2 = self.brain.forward(self.last_inputs)
        self.last_hidden1 = hidden1
        self.last_hidden = hidden2
        self.last_outputs = outputs
        self.output_history.append(list(outputs))

        steer_out = outputs[0]   # tanh → [-1, 1]: negative=left, positive=right
        thrust_out = outputs[1]  # tanh → [-1, 1]: negative=brake/reverse, positive=forward

        # ── Speed ceiling per state ────────────────────────────────────────────
        # The neural net still controls exact throttle within this ceiling.
        stamina_factor = max(0.3, self.stamina / 100.0)
        if self.state == FishState.FLEEING:
            speed_ceiling = self.physics.max_speed * 1.3 * stamina_factor
        elif self.state == FishState.HUNTING:
            speed_ceiling = self.physics.max_speed * 1.0
        elif self.state == FishState.MATING:
            speed_ceiling = self.physics.max_speed * 0.85
        elif self.state == FishState.NESTING:
            speed_ceiling = self.physics.max_speed * 0.6
        else:  # RESTING
            speed_ceiling = self.physics.max_speed * 0.35

        # ── Neural steering: heading delta driven directly by steer output ─────
        # Turn rate scales with agility trait; full output = ~90°/s turn
        turn_rate = 2.5 * self.traits.physical_traits.get("turn_rate_mult", 1.0)
        heading_delta = steer_out * turn_rate * dt
        new_heading = self.physics.heading + heading_delta

        # ── Thrust: neural thrust_out maps to [0, speed_ceiling] ─────────────
        # thrust_out in [-1,1]: negative values reduce speed (braking),
        # positive values accelerate. We normalise to [0, 1] for force magnitude.
        normalised_thrust = (thrust_out + 1.0) / 2.0   # now [0, 1]
        target_speed = normalised_thrust * speed_ceiling

        # Apply a steering force toward (new_heading, target_speed)
        desired_vx = math.cos(new_heading) * target_speed
        desired_vy = math.sin(new_heading) * target_speed
        steer_force_x = (desired_vx - self.physics.vel.x) * 0.35
        steer_force_y = (desired_vy - self.physics.vel.y) * 0.35

        # Clamp to max_force so the fish can't teleport
        steer_len = math.hypot(steer_force_x, steer_force_y)
        if steer_len > self.physics.max_force:
            scale = self.physics.max_force / steer_len
            steer_force_x *= scale
            steer_force_y *= scale

        self.physics.apply_force((steer_force_x, steer_force_y))

        # ── Nesting: lay egg when close to plant ─────────────────────────────
        if self.is_pregnant and self.closest_plant:
            dist_to_plant = self.physics.pos.distance_to(
                (self.closest_plant.x, self.closest_plant.base_y)
            )
            if dist_to_plant < 40:
                self.is_pregnant = False
                self.offspring_count += 1
                partner = self.pregnancy_partner
                self.pregnancy_partner = None
                return (
                    "egg",
                    self.physics.pos[0],
                    self.physics.pos[1],
                    self.pregnancy_traits,
                    self,
                    partner,
                    getattr(self, 'pregnancy_brain', None),
                )

        # ── Family cohesion ───────────────────────────────────────────────────
        if self.family and self.family.active:
            if self.is_mature and not self.is_pregnant:
                child_positions = [
                    (c.physics.pos.x, c.physics.pos.y)
                    for c in self.family.children
                    if not c.is_mature
                ]
                if child_positions:
                    avg_x = sum(p[0] for p in child_positions) / len(child_positions)
                    avg_y = sum(p[1] for p in child_positions) / len(child_positions)
                    # Gentle pull — doesn't override neural steering, just nudges
                    family_force = self.physics.seek(avg_x, avg_y, weight=0.4)
                    self.physics.apply_force(family_force)

        # ── Bounds + physics integration ──────────────────────────────────────
        self.physics.bounce_bounds(
            0,
            WATER_LINE_Y + 20,
            WORLD_WIDTH,
            self.world.get_terrain_height(self.physics.pos.x),
        )
        self.physics.update(dt, FISH_DRAG)
        self.distance_traveled += self.physics.vel.length() * dt

        # ── Food collision ────────────────────────────────────────────────────
        for t in targets[:]:
            if self.is_predator:
                break
            tx = getattr(t, "x", t.physics.pos.x if hasattr(t, "physics") else 0)
            ty = getattr(t, "y", t.physics.pos.y if hasattr(t, "physics") else 0)
            collision_radius = 25 * self.traits.physical_traits.get("size_mult", 1.0)
            if self.physics.pos.distance_to((tx, ty)) < collision_radius:
                self.energy = min(FISH_MAX_ENERGY, self.energy + 12.0)
                self.food_eaten += 1
                if hasattr(t, "reset"):
                    t.reset()
                elif t in targets:
                    targets.remove(t)
                break

        if random.random() < 0.001 * (self.energy / FISH_MAX_ENERGY):
            return PoopParticle(self.physics.pos.x, self.physics.pos.y)
        return None

    def draw(self, screen, camera, time, selected):
        pos = self.physics.pos
        if not camera.is_visible(pos, margin=60):
            return

        angle = self.physics.heading
        size = self.traits.physical_traits.get("size_mult", 1.0) * 4
        color = self.get_color()
        tail_angle = angle + math.pi + math.sin(time * 10) * 0.4
        screen_pos = camera.apply(pos)
        tail_pts = [
            (screen_pos[0], screen_pos[1]),
            (
                screen_pos[0] + math.cos(tail_angle - 0.6) * size * 2.5,
                screen_pos[1] + math.sin(tail_angle - 0.6) * size * 2.5,
            ),
            (
                screen_pos[0] + math.cos(tail_angle + 0.6) * size * 2.5,
                screen_pos[1] + math.sin(tail_angle + 0.6) * size * 2.5,
            ),
        ]
        pygame.draw.polygon(screen, color, tail_pts)

        body_surf = pygame.Surface((size * 6, size * 4), pygame.SRCALPHA)
        pygame.draw.ellipse(body_surf, (*color, 255), (size, size, size * 4, size * 2))
        if self.is_pregnant:
            pygame.draw.circle(
                body_surf, (255, 200, 200, 150), (size * 2.5, size * 2), size * 1.2
            )
        rotated_body = pygame.transform.rotate(body_surf, -math.degrees(angle))
        screen.blit(
            rotated_body,
            rotated_body.get_rect(center=(int(screen_pos[0]), int(screen_pos[1]))),
        )

        eye_x, eye_y = (
            screen_pos[0] + math.cos(angle + 0.35) * size * 1.3,
            screen_pos[1] + math.sin(angle + 0.35) * size * 1.3,
        )
        pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), 2)
        pygame.draw.circle(screen, (0, 0, 0), (int(eye_x), int(eye_y)), 1)

        if selected:
            pygame.draw.circle(
                screen,
                (255, 255, 200),
                (int(screen_pos[0]), int(screen_pos[1])),
                size + 15,
                2,
            )

    def draw_brain(self, screen, time):
        pass

    def _get_activation_color(self, value):
        def lerp_color(c1, c2, t):
            return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

        NEUTRAL_COLOR = (100, 100, 100)
        POSITIVE_COLOR = (50, 255, 50)
        NEGATIVE_COLOR = (255, 50, 255)

        t = min(1.0, abs(value))
        if value > 0:
            return lerp_color(NEUTRAL_COLOR, POSITIVE_COLOR, t)
        else:
            return lerp_color(NEUTRAL_COLOR, NEGATIVE_COLOR, t)

    def _get_gradient_color(self, ratio):
        ratio = max(0, min(1, ratio))
        if ratio < 0.5:
            return (255, int(255 * ratio * 2), 50)
        return (int(255 * (1 - (ratio - 0.5) * 2)), 255, 50)

    def get_color(self):
        if self.is_predator:
            base = [220, 60, 60]
        elif self.is_cleaner:
            base = [100, 180, 220]
        else:
            base = [255, 160, 60]
        color = [
            max(0, min(255, base[i] + self.traits.color_offset[i])) for i in range(3)
        ]
        factor = 1.0 - (self.age / FISH_MAX_AGE) * 0.4
        return tuple(max(0, min(255, int(c * factor))) for c in color)