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

# Pre-allocated shared glow surface — large enough for any fish glow.
# Allocated once at module load, reused every draw call.
_GLOW_SURF_SIZE = 60
_glow_surf = None  # initialised lazily after pygame.init()


def _get_glow_surf():
    global _glow_surf
    if _glow_surf is None:
        _glow_surf = pygame.Surface((_GLOW_SURF_SIZE * 2, _GLOW_SURF_SIZE * 2),
                                    pygame.SRCALPHA)
    return _glow_surf


class NeuralFish:
    INPUT_COUNT  = 15
    OUTPUT_COUNT = 2

    def __init__(self, world, traits=None, brain=None, is_cleaner=False):
        self.world       = world
        self.is_cleaner  = is_cleaner
        self.is_predator = False
        self.traits      = traits if traits else FishTraits()
        self.brain       = brain  if brain  else NeuralNet(self.INPUT_COUNT, 12, self.OUTPUT_COUNT)

        start_x = random.uniform(100, WORLD_WIDTH - 100)
        start_y = random.uniform(WATER_LINE_Y + 100, WORLD_HEIGHT - 200)
        self.physics = SteeringPhysics(start_x, start_y, FISH_MAX_SPEED, FISH_MAX_FORCE)

        self.physics.max_speed *= self.traits.physical_traits.get("max_speed_mult", 1.0)
        self.physics.max_force *= self.traits.physical_traits.get("turn_rate_mult",  1.0)

        self.age            = 0.0
        self.energy         = FISH_MAX_ENERGY * 0.8
        self.stamina        = 100.0
        self.state          = FishState.RESTING
        self.sex            = random.choice(["M", "F"])
        self.mating_cooldown = 20.0
        self.is_mature      = False
        self.is_hidden      = False
        self.is_pregnant    = False
        self.pregnancy_traits  = None
        self.pregnancy_partner = None
        self.family         = None

        self.last_inputs  = [0.0] * self.INPUT_COUNT
        self.last_hidden  = [0.0] * self.brain.hidden2_size
        self.last_hidden1 = [0.0] * self.brain.hidden_size
        self.last_outputs = [0.0] * self.OUTPUT_COUNT
        self.output_history = collections.deque(maxlen=60)

        self.food_eaten        = 0
        self.distance_traveled = 0.0
        self.offspring_count   = 0

    @property
    def pos(self):
        return self.physics.pos

    # ── Radar / sensory inputs ─────────────────────────────────────────────

    def get_radar_inputs(self, all_fish, targets, plant_manager):
        """
        Returns a 15-element input vector:
          [0-2]  food radar   (L/C/R)
          [3-5]  threat radar (L/C/R)
          [6-8]  mate radar   (L/C/R)
          [9]    energy
          [10]   stamina
          [11]   depth
          [12]   speed
          [13]   cover quality
          [14]   plant food average
        """
        radar = [0.0] * 9
        self.is_hidden = False
        min_plant_dist = 9999
        self.closest_plant = None

        plant_food    = [0.0, 0.0, 0.0]
        cover_quality = 0.0
        closest_cover_dist = 9999

        for plant in plant_manager.plants:
            if plant.biomass < 1.0:
                continue
            dist = self.physics.pos.distance_to((plant.x, plant.base_y))
            if dist < PLANT_COVER_RADIUS * 2:
                angle = (math.atan2(plant.base_y - self.physics.pos.y,
                                  plant.x - self.physics.pos.x) - self.physics.heading)
                angle = (angle + math.pi) % (2 * math.pi) - math.pi
                if abs(angle) < FISH_SENSOR_ARC * 1.5:
                    sector = int((angle + FISH_SENSOR_ARC * 1.5) / (3 * FISH_SENSOR_ARC) * 3)
                    sector = max(0, min(2, sector))
                    plant_food[sector] += (plant.biomass / 20.0) * (1.0 - dist / (PLANT_COVER_RADIUS * 2))

                if dist < closest_cover_dist:
                    closest_cover_dist = dist
                    cover_quality = PLANT_COVER_STRENGTH.get(plant.plant_type, 1.0) * (1.0 - dist / PLANT_COVER_RADIUS)

            if dist < min_plant_dist:
                min_plant_dist = dist
                self.closest_plant = plant
            if dist < 60:
                self.is_hidden = True

        def fill_radar(objects, offset, is_threat_radar=False, bias_multiplier=1.0):
            for obj in objects:
                if is_threat_radar and getattr(obj, "is_hidden", False):
                    continue
                ox = getattr(obj, "x", obj.physics.pos.x if hasattr(obj, "physics") else 0)
                oy = getattr(obj, "y", obj.physics.pos.y if hasattr(obj, "physics") else 0)
                dist = self.physics.pos.distance_to((ox, oy))
                detection_range = FISH_SENSOR_RANGE
                if is_threat_radar and self.is_hidden:
                    detection_range *= 0.5
                if dist < detection_range and dist > 0:
                    angle = (
                        math.atan2(oy - self.physics.pos.y, ox - self.physics.pos.x)
                        - self.physics.heading
                    )
                    angle = (angle + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle) < FISH_SENSOR_ARC:
                        sector = int((angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3)
                        sector = max(0, min(2, sector))
                        radar[offset + sector] += (
                            1.0 - (dist / detection_range)
                        ) * bias_multiplier

        food_bias   = 1.0
        threat_bias = 1.0
        mate_bias   = 1.0

        if self.state == FishState.HUNTING:
            food_bias = 2.5
        elif self.state == FishState.MATING:
            mate_bias = 2.5
        elif self.state == FishState.FLEEING:
            threat_bias = 3.0
        elif self.state == FishState.NESTING:
            if self.closest_plant and min_plant_dist < 300:
                dx   = self.closest_plant.x     - self.physics.pos.x
                dy   = self.closest_plant.base_y - self.physics.pos.y
                dist = max(1, min_plant_dist)
                angle = math.atan2(dy, dx) - self.physics.heading
                angle = (angle + math.pi) % (2 * math.pi) - math.pi
                if abs(angle) < FISH_SENSOR_ARC:
                    sector = int((angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3)
                    sector = max(0, min(2, sector))
                    radar[sector] += (1.0 - (dist / 300)) * 2.0
        elif self.state == FishState.RESTING:
            food_bias   = 0.4
            threat_bias = 0.6
            mate_bias   = 0.4

        fill_radar(targets, 0, bias_multiplier=food_bias)
        fill_radar(
            [f for f in all_fish if getattr(f, "is_predator", False)],
            3, is_threat_radar=True, bias_multiplier=threat_bias,
        )
        fill_radar(
            [f for f in all_fish
             if f.is_cleaner == self.is_cleaner
             and f.is_predator == self.is_predator
             and f.sex != self.sex
             and f.is_mature],
            6, bias_multiplier=mate_bias,
        )

        # Build and return the complete 15-element input vector
        stats = [
            self.energy / FISH_MAX_ENERGY,
            self.stamina / 100.0,
            (self.physics.pos.y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y),
            self.physics.vel.length() / self.physics.max_speed,
            cover_quality,
            sum(plant_food) / 3.0,
        ]
        return radar + stats  # 9 + 6 = 15

    # ── Update ─────────────────────────────────────────────────────────────

    def update(self, dt, all_fish, targets, particle_system, plant_manager,
               time_system=None):
        self.age += dt

        metabolism_mod  = time_system.metabolism_modifier if time_system else 1.0
        metabolism_rate = (
            0.1
            * self.traits.physical_traits.get("metabolism_mult", 1.0)
            * metabolism_mod
        )
        self.energy -= metabolism_rate * dt
        self.mating_cooldown = max(0, self.mating_cooldown - dt)
        self.is_mature       = self.age > (FISH_LARVA_DURATION + FISH_JUVENILE_DURATION)

        night_rest_factor = 0.5 if (time_system and time_system.is_night) else 1.0

        speed_ratio = self.physics.vel.length() / max(1.0, self.physics.max_speed)
        if speed_ratio > 0.8:
            self.stamina = max(0.0, self.stamina - 15.0 * speed_ratio * dt)
        elif speed_ratio < 0.3:
            recovery = 8.0 * self.traits.physical_traits.get("stamina_mult", 1.0) * dt
            self.stamina = min(100.0, self.stamina + recovery)

        # Build the complete 15-element input vector once
        full_inputs = self.get_radar_inputs(all_fish, targets, plant_manager)

        # Extract named slices for state logic (indices match get_radar_inputs layout)
        threat_level  = sum(full_inputs[3:6])
        cover_quality = full_inputs[13]

        # Grazing
        self.grazing_cooldown = getattr(self, "grazing_cooldown", 0.0)
        self.grazing_cooldown = max(0.0, self.grazing_cooldown - dt)

        if (not self.is_predator and
            self.energy < FISH_HUNGER_THRESHOLD * 0.7 and
            self.grazing_cooldown <= 0):

            for plant in plant_manager.plants:
                if plant.biomass > 2.0 and self.physics.pos.distance_to((plant.x, plant.base_y)) < PLANT_GRAZE_RANGE:
                    energy_gained = plant.graze(1.8)
                    if energy_gained > 0:
                        self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gained)
                        self.grazing_cooldown = GRAZING_COOLDOWN
                        for _ in range(3):
                            particle_system.add_bubble(self.physics.pos.x + random.uniform(-10, 10),
                                                       self.physics.pos.y - 8)
                        break

        # Shelter stamina recovery
        if cover_quality > 0.3:
            self.stamina = min(100.0, self.stamina + 18.0 * cover_quality * dt)

        # State machine
        mating_drive  = time_system.mating_drive_modifier if time_system else 1.0
        eff_mating_th = FISH_MATING_THRESHOLD / mating_drive

        if threat_level > 0.3:
            self.state = FishState.FLEEING
        elif self.is_pregnant:
            self.state = FishState.NESTING
        elif self.energy < FISH_HUNGER_THRESHOLD:
            self.state = FishState.HUNTING
        elif (
            self.is_mature
            and self.energy > eff_mating_th
            and self.mating_cooldown <= 0
        ):
            self.state = FishState.MATING
        else:
            self.state = FishState.RESTING

        # Store inputs and run the network
        self.last_inputs = full_inputs
        outputs, hidden1, hidden2 = self.brain.forward(self.last_inputs)
        self.last_hidden1 = hidden1
        self.last_hidden  = hidden2
        self.last_outputs = outputs
        self.output_history.append(list(outputs))

        steer_out  = outputs[0]
        thrust_out = outputs[1]

        stamina_factor = max(0.3, self.stamina / 100.0)
        if self.state == FishState.FLEEING:
            speed_ceiling = self.physics.max_speed * 1.3 * stamina_factor * night_rest_factor
        elif self.state == FishState.HUNTING:
            speed_ceiling = self.physics.max_speed * 1.0 * night_rest_factor
        elif self.state == FishState.MATING:
            speed_ceiling = self.physics.max_speed * 0.85 * night_rest_factor
        elif self.state == FishState.NESTING:
            speed_ceiling = self.physics.max_speed * 0.6
        else:
            speed_ceiling = self.physics.max_speed * 0.35 * night_rest_factor

        turn_rate     = FISH_TURN_RATE_SCALAR * self.traits.physical_traits.get("turn_rate_mult", 1.0)
        heading_delta = steer_out * turn_rate * dt
        new_heading   = self.physics.heading + heading_delta

        normalised_thrust = (thrust_out + 1.0) / 2.0
        target_speed      = normalised_thrust * speed_ceiling

        desired_vx      = math.cos(new_heading) * target_speed
        desired_vy      = math.sin(new_heading) * target_speed
        steer_force_x   = (desired_vx - self.physics.vel.x) * FISH_STEERING_FORCE_FACTOR
        steer_force_y   = (desired_vy - self.physics.vel.y) * FISH_STEERING_FORCE_FACTOR

        steer_len = math.hypot(steer_force_x, steer_force_y)
        if steer_len > self.physics.max_force:
            scale       = self.physics.max_force / steer_len
            steer_force_x *= scale
            steer_force_y *= scale

        self.physics.apply_force((steer_force_x, steer_force_y))

        # Egg laying when near a plant
        if self.is_pregnant and self.closest_plant:
            dist_to_plant = self.physics.pos.distance_to(
                (self.closest_plant.x, self.closest_plant.base_y)
            )
            if dist_to_plant < 40:
                self.is_pregnant       = False
                self.offspring_count  += 1
                partner                = self.pregnancy_partner
                self.pregnancy_partner = None
                return (
                    "egg",
                    self.physics.pos[0],
                    self.physics.pos[1],
                    self.pregnancy_traits,
                    self,
                    partner,
                    getattr(self, "pregnancy_brain", None),
                )

        # Family cohesion
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
                    self.physics.apply_force(self.physics.seek(avg_x, avg_y, weight=0.4))

        self.physics.bounce_bounds(
            0, WATER_LINE_Y + 20, WORLD_WIDTH,
            self.world.get_terrain_height(self.physics.pos.x),
        )
        self.physics.update(dt, FISH_DRAG, speed_ceiling)
        self.distance_traveled += self.physics.vel.length() * dt

        # ── Food collision (plankton eating) ───────────────────────────────
        for t in targets[:]:
            if self.is_predator:
                break
            tx = getattr(t, "x", t.physics.pos.x if hasattr(t, "physics") else 0)
            ty = getattr(t, "y", t.physics.pos.y if hasattr(t, "physics") else 0)
            # Larger collision radius — plankton are now bigger and worth seeking
            collision_radius = 30 * self.traits.physical_traits.get("size_mult", 1.0)
            if self.physics.pos.distance_to((tx, ty)) < collision_radius:
                energy_gain = 12.0
                # Nutrition bonus if plankton has a nutrition attribute
                nutrition = getattr(t, "nutrition", 1.0)
                energy_gain *= nutrition

                self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gain)
                self.food_eaten += 1

                # Spawn eat effect at plankton position
                eat_color = (
                    min(255, int(t.color[0] + 80)) if hasattr(t, "color") else 120,
                    min(255, int(t.color[1] + 80)) if hasattr(t, "color") else 230,
                    min(255, int(t.color[2] + 60)) if hasattr(t, "color") else 160,
                ) if hasattr(t, "color") else (120, 230, 160)
                particle_system.spawn_eat_effect(tx, ty, eat_color)

                if hasattr(t, "reset"):
                    t.reset()
                elif t in targets:
                    targets.remove(t)
                break

        if random.random() < 0.001 * (self.energy / FISH_MAX_ENERGY):
            return PoopParticle(self.physics.pos.x, self.physics.pos.y)
        return None

    # ── Drawing ────────────────────────────────────────────────────────────

    def draw(self, screen, camera, time, selected, biolum_alpha=0):
        pos = self.physics.pos
        if not camera.is_visible(pos, margin=60):
            return

        angle      = self.physics.heading
        size       = self.traits.physical_traits.get("size_mult", 1.0) * 4
        color      = self.get_color()
        tail_angle = angle + math.pi + math.sin(time * 10) * 0.4
        screen_pos = camera.apply(pos)

        # ── Bioluminescence glow (reuses shared surface) ───────────────────
        if biolum_alpha > 10:
            if self.is_predator:
                glow_col = BIOLUM_COLORS["predator"]
            elif self.is_cleaner:
                glow_col = BIOLUM_COLORS["cleaner"]
            else:
                glow_col = BIOLUM_COLORS["common"]

            glow_r = int(size * 3 + 6)
            glow_r = min(glow_r, _GLOW_SURF_SIZE - 1)
            gs     = _get_glow_surf()
            gs.fill((0, 0, 0, 0))
            pygame.draw.circle(
                gs, (*glow_col, biolum_alpha // 3),
                (_GLOW_SURF_SIZE, _GLOW_SURF_SIZE), glow_r,
            )
            screen.blit(
                gs,
                (int(screen_pos[0]) - _GLOW_SURF_SIZE,
                 int(screen_pos[1]) - _GLOW_SURF_SIZE),
            )

        # Tail
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

        # Body
        body_surf = pygame.Surface((int(size * 6), int(size * 4)), pygame.SRCALPHA)
        pygame.draw.ellipse(body_surf, (*color, 255),
                            (size, size, size * 4, size * 2))
        if self.is_pregnant:
            pygame.draw.circle(body_surf, (255, 200, 200, 150),
                               (int(size * 2.5), int(size * 2)), int(size * 1.2))
        rotated_body = pygame.transform.rotate(body_surf, -math.degrees(angle))
        screen.blit(
            rotated_body,
            rotated_body.get_rect(center=(int(screen_pos[0]), int(screen_pos[1]))),
        )

        # Eye
        eye_x = screen_pos[0] + math.cos(angle + 0.35) * size * 1.3
        eye_y = screen_pos[1] + math.sin(angle + 0.35) * size * 1.3
        pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), 2)
        pygame.draw.circle(screen, (0, 0, 0),       (int(eye_x), int(eye_y)), 1)

        # Selection ring
        if selected:
            pygame.draw.circle(
                screen, (255, 255, 200),
                (int(screen_pos[0]), int(screen_pos[1])), int(size) + 15, 2,
            )

    def draw_brain(self, screen, time):
        pass

    # ── Colour helpers ─────────────────────────────────────────────────────

    def _get_activation_color(self, value):
        def lerp_color(c1, c2, t):
            return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
        NEUTRAL  = (100, 100, 100)
        POSITIVE = (50, 255, 50)
        NEGATIVE = (255, 50, 255)
        t = min(1.0, abs(value))
        return lerp_color(NEUTRAL, POSITIVE, t) if value > 0 else lerp_color(NEUTRAL, NEGATIVE, t)

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
        color  = [
            max(0, min(255, base[i] + self.traits.color_offset[i])) for i in range(3)
        ]
        factor = 1.0 - (self.age / FISH_MAX_AGE) * 0.4
        return tuple(max(0, min(255, int(c * factor))) for c in color)
