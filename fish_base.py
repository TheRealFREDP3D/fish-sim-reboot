import pygame
import math
import random
import collections
from neural_net import NeuralNet
from fish_traits import FishTraits
from fish_physics import SteeringPhysics
from config import *
from environment_objects import PoopParticle

_GLOW_SURF_SIZE = 60
_glow_surf = None


def _get_glow_surf():
    global _glow_surf
    if _glow_surf is None:
        _glow_surf = pygame.Surface(
            (_GLOW_SURF_SIZE * 2, _GLOW_SURF_SIZE * 2), pygame.SRCALPHA
        )
    return _glow_surf


def get_life_stage_size_mult(age):
    larva_end = FISH_LARVA_DURATION
    juv_end = larva_end + max(0.1, FISH_JUVENILE_DURATION)
    adult_end = juv_end + max(0.1, FISH_ADULT_DURATION)

    if age < larva_end:
        return 0.35
    elif age < juv_end:
        juv_duration = max(0.1, FISH_JUVENILE_DURATION)
        t = (age - larva_end) / juv_duration
        return 0.35 + t * 0.40
    elif age < adult_end:
        adult_duration = max(0.1, FISH_ADULT_DURATION)
        t = (age - juv_end) / adult_duration
        return 0.75 + t * 0.25
    else:
        return 1.0


class NeuralFish:
    INPUT_COUNT = 15
    OUTPUT_COUNT = 9  # 2 movement + 2 behavior + 5 state logits

    def __init__(
        self,
        world,
        traits=None,
        brain=None,
        is_cleaner=False,
        start_x=None,
        start_y=None,
    ):
        self.world = world
        self.is_cleaner = is_cleaner
        self.is_predator = False
        self.traits = traits if traits else FishTraits()
        self.brain = (
            brain if brain else NeuralNet(self.INPUT_COUNT, 12, self.OUTPUT_COUNT)
        )

        start_x = start_x or random.uniform(100, WORLD_WIDTH - 100)
        start_y = start_y or random.uniform(WATER_LINE_Y + 100, WORLD_HEIGHT - 200)

        self.physics = SteeringPhysics(start_x, start_y, FISH_MAX_SPEED, FISH_MAX_FORCE)

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
        self.family = None

        self.closest_plant = None
        self.grazing_cooldown = 0.0

        self.last_inputs = [0.0] * self.INPUT_COUNT
        self.last_hidden = [0.0] * self.brain.hidden2_size
        self.last_hidden1 = [0.0] * self.brain.hidden_size
        self.last_outputs = [0.0] * self.OUTPUT_COUNT
        # State probabilities exposed for the brain visualizer
        self.last_state_probs = [0.2] * 5
        self.output_history = collections.deque(maxlen=60)

        self.food_eaten = 0
        self.distance_traveled = 0.0
        self.offspring_count = 0

        self._mating_glow_timer = 0.0
        self._heart_timer = 0.0

    @property
    def pos(self):
        return self.physics.pos

    def get_current_size_mult(self):
        return get_life_stage_size_mult(self.age) * self.traits.physical_traits.get(
            "size_mult", 1.0
        )

    # ── Radar / sensory inputs ─────────────────────────────────────────────

    def get_radar_inputs(self, all_fish, targets, plant_manager):
        radar = [0.0] * 9
        self.is_hidden = False
        min_plant_dist = 9999
        self.closest_plant = None

        plant_food = [0.0, 0.0, 0.0]
        cover_quality = 0.0
        closest_cover_dist = 9999

        for plant in plant_manager.plants:
            if plant.biomass < 1.0:
                continue
            dist = self.physics.pos.distance_to((plant.x, plant.base_y))
            if dist < PLANT_COVER_RADIUS * 2:
                angle = (
                    math.atan2(
                        plant.base_y - self.physics.pos.y, plant.x - self.physics.pos.x
                    )
                    - self.physics.heading
                )
                angle = (angle + math.pi) % (2 * math.pi) - math.pi
                if abs(angle) < FISH_SENSOR_ARC * 1.5:
                    sector = int(
                        (angle + FISH_SENSOR_ARC * 1.5) / (3 * FISH_SENSOR_ARC) * 3
                    )
                    sector = max(0, min(2, sector))
                    plant_food[sector] += (plant.biomass / 20.0) * (
                        1.0 - dist / (PLANT_COVER_RADIUS * 2)
                    )

                if dist < closest_cover_dist:
                    closest_cover_dist = dist
                    cover_quality = PLANT_COVER_STRENGTH.get(plant.plant_type, 1.0) * (
                        1.0 - dist / PLANT_COVER_RADIUS
                    )

            if dist < min_plant_dist:
                min_plant_dist = dist
                self.closest_plant = plant
            if dist < 60:
                self.is_hidden = True

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
                    angle = (
                        math.atan2(oy - self.physics.pos.y, ox - self.physics.pos.x)
                        - self.physics.heading
                    )
                    angle = (angle + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle) < FISH_SENSOR_ARC:
                        sector = int(
                            (angle + FISH_SENSOR_ARC) / (2 * FISH_SENSOR_ARC) * 3
                        )
                        sector = max(0, min(2, sector))
                        radar[offset + sector] += (
                            1.0 - (dist / detection_range)
                        ) * bias_multiplier

        fill_radar(targets, 0)
        fill_radar(
            [f for f in all_fish if getattr(f, "is_predator", False)],
            3,
            is_threat_radar=True,
        )
        fill_radar(
            [
                f
                for f in all_fish
                if f.is_cleaner == self.is_cleaner
                and f.is_predator == self.is_predator
                and f.sex != self.sex
                and f.is_mature
            ],
            6,
        )

        stats = [
            self.energy / FISH_MAX_ENERGY,
            self.stamina / 100.0,
            (self.physics.pos.y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y),
            self.physics.vel.length() / self.physics.max_speed,
            cover_quality,
            sum(plant_food) / 3.0,
        ]
        return radar + stats

    # ── Soft state selection ───────────────────────────────────────────────

    def _pick_state(self, raw_state_probs, threat_level, night_rest_factor,
                    mating_drive):
        """
        Apply physiological biases to the NN's raw softmax state probabilities.
        """
        if self.is_pregnant:
            return FishState.NESTING

        # Convert probabilities back to log-space for bias addition
        import math as _math
        logits = [_math.log(max(p, 1e-9)) for p in raw_state_probs]

        # Threat → nudge FLEE
        logits[2] += threat_level * STATE_BIAS_FLEE_THREAT

        # Hunger → nudge HUNT
        hunger_signal = max(0.0, 1.0 - self.energy / FISH_MAX_ENERGY)
        logits[1] += hunger_signal * STATE_BIAS_HUNT_HUNGER

        # Mating readiness → nudge MATE
        if (
            self.is_mature
            and self.energy > FISH_MATING_THRESHOLD / mating_drive
            and self.mating_cooldown <= 0
        ):
            logits[3] += STATE_BIAS_MATE_DRIVE * mating_drive

        # Night → nudge REST
        logits[0] += (1.0 - night_rest_factor) * STATE_BIAS_REST_NIGHT

        if not self.is_mature:
            logits[3] = -1e9

        best_idx = logits.index(max(logits))
        return FISH_STATE_ORDER[best_idx]

    # ── Update ─────────────────────────────────────────────────────────────

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        self.age += dt

        metabolism_mod = time_system.metabolism_modifier if time_system else 1.0
        metabolism_rate = (
            0.1
            * self.traits.physical_traits.get("metabolism_mult", 1.0)
            * metabolism_mod
        )
        self.energy -= metabolism_rate * dt
        self.mating_cooldown = max(0, self.mating_cooldown - dt)
        self.is_mature = self.age > (FISH_LARVA_DURATION + FISH_JUVENILE_DURATION)

        night_rest_factor = 0.5 if (time_system and time_system.is_night) else 1.0

        speed_ratio = self.physics.vel.length() / max(1.0, self.physics.max_speed)
        if speed_ratio > 0.8:
            self.stamina = max(0.0, self.stamina - 15.0 * speed_ratio * dt)
        elif speed_ratio < 0.3:
            recovery = 8.0 * self.traits.physical_traits.get("stamina_mult", 1.0) * dt
            self.stamina = min(100.0, self.stamina + recovery)

        full_inputs = self.get_radar_inputs(all_fish, targets, plant_manager)
        threat_level = sum(full_inputs[3:6])
        cover_quality = full_inputs[13]

        self.grazing_cooldown = max(0.0, self.grazing_cooldown - dt)

        if (
            not self.is_predator
            and self.energy < FISH_HUNGER_THRESHOLD * 0.7
            and self.grazing_cooldown <= 0
        ):
            for plant in plant_manager.plants:
                if (
                    plant.biomass > 2.0
                    and self.physics.pos.distance_to((plant.x, plant.base_y))
                    < PLANT_GRAZE_RANGE
                ):
                    energy_gained = plant.graze(1.8)
                    if energy_gained > 0:
                        self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gained)
                        self.grazing_cooldown = GRAZING_COOLDOWN
                        for _ in range(3):
                            particle_system.add_bubble(
                                self.physics.pos.x + random.uniform(-10, 10),
                                self.physics.pos.y - 8,
                            )
                        break

        if cover_quality > 0.3:
            self.stamina = min(100.0, self.stamina + 18.0 * cover_quality * dt)

        # ── Neural net forward pass ──────────────────────────────────────
        mating_drive = time_system.mating_drive_modifier if time_system else 1.0

        self.last_inputs = full_inputs
        outputs, hidden1, hidden2 = self.brain.forward(self.last_inputs)
        self.last_hidden1 = hidden1
        self.last_hidden = hidden2
        self.last_outputs = outputs
        self.output_history.append(list(outputs[:4]))  # Store movement + behaviors

        steer_out = outputs[0]
        thrust_out = outputs[1]
        hide_drive = outputs[2]
        sprint_drive = outputs[3]
        raw_state_probs = outputs[4:9]
        self.last_state_probs = raw_state_probs

        # ── Soft state selection ─────────────────────────────────────────
        self.state = self._pick_state(
            raw_state_probs, threat_level, night_rest_factor, mating_drive
        )

        # ── Behavioral Lever: Hide Drive ──────────────────────────────────
        if self.closest_plant:
            # High hide_drive pushes the fish to stay near plant cover
            hide_weight = hide_drive * 1.6
            hide_force = self.physics.seek(
                self.closest_plant.x, self.closest_plant.base_y, weight=hide_weight
            )
            self.physics.apply_force(hide_force)

        # ── Mating display timers ─────────────────────────────────────────
        if self.state == FishState.MATING:
            self._mating_glow_timer += dt
            self._heart_timer = max(0.0, self._heart_timer - dt)
            if self._heart_timer <= 0 and hasattr(particle_system, "spawn_heart"):
                particle_system.spawn_heart(self.physics.pos.x, self.physics.pos.y)
                self._heart_timer = MATING_HEART_SPAWN_INTERVAL + random.uniform(
                    0, MATING_HEART_RANDOM_RANGE
                )
        else:
            self._mating_glow_timer = max(
                0.0, self._mating_glow_timer - dt * MATING_GLOW_DECAY_RATE
            )

        # ── Speed ceiling ─────────────────────────────────────────────────
        stamina_factor = max(0.3, self.stamina / 100.0)
        if self.state == FishState.FLEEING:
            speed_ceiling = (
                self.physics.max_speed * 1.3 * stamina_factor * night_rest_factor
            )
        elif self.state == FishState.HUNTING:
            speed_ceiling = self.physics.max_speed * 1.0 * night_rest_factor
        elif self.state == FishState.MATING:
            speed_ceiling = self.physics.max_speed * 0.85 * night_rest_factor
        elif self.state == FishState.NESTING:
            speed_ceiling = self.physics.max_speed * 0.6
        else:
            speed_ceiling = self.physics.max_speed * 0.35 * night_rest_factor

        # ── Behavioral Lever: Sprint Drive ────────────────────────────────
        # Evolution can temporarily boost speed by up to 50%
        speed_ceiling *= (1.0 + sprint_drive * 0.5)

        turn_rate = FISH_TURN_RATE_SCALAR * self.traits.physical_traits.get(
            "turn_rate_mult", 1.0
        )
        heading_delta = steer_out * turn_rate * dt
        new_heading = self.physics.heading + heading_delta

        normalised_thrust = (thrust_out + 1.0) / 2.0
        target_speed = normalised_thrust * speed_ceiling

        desired_vx = math.cos(new_heading) * target_speed
        desired_vy = math.sin(new_heading) * target_speed
        steer_force_x = (desired_vx - self.physics.vel.x) * FISH_STEERING_FORCE_FACTOR
        steer_force_y = (desired_vy - self.physics.vel.y) * FISH_STEERING_FORCE_FACTOR

        steer_len = math.hypot(steer_force_x, steer_force_y)
        if steer_len > self.physics.max_force:
            scale = self.physics.max_force / steer_len
            steer_force_x *= scale
            steer_force_y *= scale

        self.physics.apply_force((steer_force_x, steer_force_y))

        # Egg laying 
        if self.is_pregnant and self.closest_plant:
            dist_to_plant = self.physics.pos.distance_to(
                (self.closest_plant.x, self.closest_plant.base_y)
            )
            if dist_to_plant < 40:
                self.is_pregnant = False
                self.offspring_count += 1
                partner = self.pregnancy_partner
                self.pregnancy_partner = None
                if hasattr(particle_system, "spawn_mating_burst"):
                    particle_system.spawn_mating_burst(
                        self.physics.pos.x, self.physics.pos.y
                    )
                return (
                    "egg",
                    self.physics.pos[0],
                    self.physics.pos[1],
                    self.pregnancy_traits,
                    self,
                    partner,
                    getattr(self, "pregnancy_brain", None),
                )

        # ── Family cohesion ───────────────────────────────────────────────
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
                    dist_to_kids = self.physics.pos.distance_to((avg_x, avg_y))
                    cohesion_weight = min(1.8, 0.5 + dist_to_kids / 120.0)
                    self.physics.apply_force(
                        self.physics.seek(avg_x, avg_y, weight=cohesion_weight)
                    )
            else:
                parent_positions = [
                    (p.physics.pos.x, p.physics.pos.y) for p in self.family.parents
                ]
                if parent_positions and not self.is_mature:
                    avg_x = sum(p[0] for p in parent_positions) / len(parent_positions)
                    avg_y = sum(p[1] for p in parent_positions) / len(parent_positions)
                    dist_to_parent = self.physics.pos.distance_to((avg_x, avg_y))
                    child_weight = min(2.5, 0.8 + dist_to_parent / 80.0)
                    self.physics.apply_force(
                        self.physics.seek(avg_x, avg_y, weight=child_weight)
                    )

        self.physics.bounce_bounds(
            0,
            WATER_LINE_Y + 20,
            WORLD_WIDTH,
            self.world.get_terrain_height(self.physics.pos.x),
        )
        self.physics.update(dt, FISH_DRAG, speed_ceiling)
        self.distance_traveled += self.physics.vel.length() * dt

        # ── Food collision ────────────────────────────────────────────────
        for t in targets[:]:
            if self.is_predator:
                break
            tx = getattr(t, "x", t.physics.pos.x if hasattr(t, "physics") else 0)
            ty = getattr(t, "y", t.physics.pos.y if hasattr(t, "physics") else 0)
            collision_radius = 30 * self.traits.physical_traits.get("size_mult", 1.0)
            if self.physics.pos.distance_to((tx, ty)) < collision_radius:
                energy_gain = 12.0 * getattr(t, "nutrition", 1.0)
                self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gain)
                self.food_eaten += 1

                eat_color = (
                    (
                        min(255, int(t.color[0] + 80)) if hasattr(t, "color") else 120,
                        min(255, int(t.color[1] + 80)) if hasattr(t, "color") else 230,
                        min(255, int(t.color[2] + 60)) if hasattr(t, "color") else 160,
                    )
                    if hasattr(t, "color")
                    else (120, 230, 160)
                )
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

        angle = self.physics.heading
        size = self.get_current_size_mult() * 4
        color = self.get_color()
        tail_angle = angle + math.pi + math.sin(time * 10) * 0.4
        screen_pos = camera.apply(pos)

        # ── Mating glow ──────────────────────────────────────────────────
        if self._mating_glow_timer > 0:
            pulse = (math.sin(time * 6.0) + 1) * 0.5
            glow_intensity = min(1.0, self._mating_glow_timer / 0.5) * (
                0.6 + 0.4 * pulse
            )
            glow_r = int(size * 4 + 10 * pulse)
            glow_r = min(glow_r, _GLOW_SURF_SIZE - 1)
            gs = _get_glow_surf()
            gs.fill((0, 0, 0, 0))
            glow_alpha = int(glow_intensity * 140)
            pygame.draw.circle(
                gs,
                (255, 100, 160, glow_alpha),
                (_GLOW_SURF_SIZE, _GLOW_SURF_SIZE),
                glow_r,
            )
            pygame.draw.circle(
                gs,
                (255, 180, 210, glow_alpha // 2),
                (_GLOW_SURF_SIZE, _GLOW_SURF_SIZE),
                glow_r + 6,
            )
            screen.blit(
                gs,
                (
                    int(screen_pos[0]) - _GLOW_SURF_SIZE,
                    int(screen_pos[1]) - _GLOW_SURF_SIZE,
                ),
            )

        # ── Bioluminescence glow ─────────────────────────────────────────
        if biolum_alpha > 10:
            if self.is_predator:
                glow_col = BIOLUM_COLORS["predator"]
            elif self.is_cleaner:
                glow_col = BIOLUM_COLORS["cleaner"]
            else:
                glow_col = BIOLUM_COLORS["common"]

            glow_r = int(size * 3 + 6)
            glow_r = min(glow_r, _GLOW_SURF_SIZE - 1)
            gs = _get_glow_surf()
            gs.fill((0, 0, 0, 0))
            pygame.draw.circle(
                gs,
                (*glow_col, biolum_alpha // 3),
                (_GLOW_SURF_SIZE, _GLOW_SURF_SIZE),
                glow_r,
            )
            screen.blit(
                gs,
                (
                    int(screen_pos[0]) - _GLOW_SURF_SIZE,
                    int(screen_pos[1]) - _GLOW_SURF_SIZE,
                ),
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
        pygame.draw.ellipse(body_surf, (*color, 255), (size, size, size * 4, size * 2))
        if self.is_pregnant:
            pygame.draw.circle(
                body_surf,
                (255, 200, 200, 150),
                (int(size * 2.5), int(size * 2)),
                int(size * 1.2),
            )
        rotated_body = pygame.transform.rotate(body_surf, -math.degrees(angle))
        screen.blit(
            rotated_body,
            rotated_body.get_rect(center=(int(screen_pos[0]), int(screen_pos[1]))),
        )

        # Eye
        eye_x = screen_pos[0] + math.cos(angle + 0.35) * size * 1.3
        eye_y = screen_pos[1] + math.sin(angle + 0.35) * size * 1.3
        pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), 2)
        pygame.draw.circle(screen, (0, 0, 0), (int(eye_x), int(eye_y)), 1)

        # Selection ring
        if selected:
            pygame.draw.circle(
                screen,
                (255, 255, 200),
                (int(screen_pos[0]), int(screen_pos[1])),
                int(size) + 15,
                2,
            )

        # ── Mating state ♥ label ─────────────────────────────────────────
        if self.state == FishState.MATING and self._mating_glow_timer > 0.3:
            heart_y = int(screen_pos[1]) - int(size * 4) - 8
            sym_font = pygame.font.Font(None, 18)
            sym = sym_font.render("♥", True, (255, 100, 150))
            screen.blit(sym, (int(screen_pos[0]) - sym.get_width() // 2, heart_y))

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