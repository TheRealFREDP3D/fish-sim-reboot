import pygame
import math
import random
import collections
from neural_net import NeuralNet
from fish_traits import FishTraits, BODY_SHAPE_STREAMLINED, BODY_SHAPE_STANDARD, BODY_SHAPE_ROUNDED, FIN_STYLE_MINIMAL, FIN_STYLE_STANDARD, FIN_STYLE_ELEGANT, FIN_STYLE_DRAMATIC, TAIL_POINTED, TAIL_FORKED, TAIL_ROUNDED, TAIL_LYRE, PATTERN_SOLID, PATTERN_STRIPES, PATTERN_SPOTS, PATTERN_GRADIENT, PATTERN_BANDS, PATTERN_MARBLED
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
    INPUT_COUNT = 18
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

        # Animation state for appearance
        self._fin_phase = random.uniform(0, math.pi * 2)
        self._pattern_seed = random.randint(0, 10000)  # For consistent pattern rendering

        # ── Anti-clustering: track how long fish has been near a plant ─
        self._plant_linger_timer = 0.0
        # ── Exploration: a slowly-changing wander direction ─
        self._wander_angle = random.uniform(0, math.pi * 2)
        self._wander_timer = 0.0

        # ── Cleaning mutualism state ─────────────────────────────────────
        # All fish can be "clients" that benefit from cleaner fish attention.
        # needs_cleaning rises with stress/damage and decays when cleaned.
        self.needs_cleaning = random.uniform(0.0, 0.3)  # start with mild need
        self.last_cleaned_time = 0.0  # seconds since last cleaning event

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
            min_d = FISH_SENSOR_RANGE
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
                    if dist < min_d:
                        min_d = dist
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
            return min_d

        fill_radar(targets, 0)
        fill_radar(
            [f for f in all_fish if getattr(f, "is_predator", False)],
            3,
            is_threat_radar=True,
        )
        min_mate_dist = fill_radar(
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

        # ── Ambush Alert (is a predator near my plant?) ──────────────────
        ambush_alert = 0.0
        if self.closest_plant:
            for f in all_fish:
                if getattr(f, "is_predator", False):
                    p_dist = f.physics.pos.distance_to(
                        (self.closest_plant.x, self.closest_plant.base_y)
                    )
                    if p_dist < PLANT_COVER_RADIUS:
                        ambush_alert = 1.0
                        break

        stats = [
            self.energy / FISH_MAX_ENERGY,
            self.stamina / 100.0,
            (self.physics.pos.y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y),
            self.physics.vel.length() / self.physics.max_speed,
            cover_quality,
            sum(plant_food) / 3.0,
            # 15: Normalized distance to closest plant
            min(1.0, min_plant_dist / FISH_SENSOR_RANGE),
            # 16: Ambush Alert
            ambush_alert,
            # 17: Closest Mate Distance
            min(1.0, min_mate_dist / FISH_SENSOR_RANGE),
        ]
        return radar + stats

    # ── Soft state selection ───────────────────────────────────────────────

    def _pick_state(
        self,
        raw_state_probs,
        threat_level,
        night_rest_factor,
        mating_drive,
        activity_mod=1.0,
    ):
        """
        Apply physiological biases to the NN's raw softmax state probabilities.

        activity_mod parameter allows predator seasonal suppression.
        """
        if self.is_pregnant:
            return FishState.NESTING

        # Convert probabilities back to log-space for bias addition
        logits = [math.log(max(p, 1e-9)) for p in raw_state_probs]

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

        # ── Predator-specific seasonal suppression ───────────────────────
        if self.is_predator and activity_mod < 0.8:
            logits[1] -= (1.0 - activity_mod) * 3.0  # Suppress HUNTING
            logits[0] += (1.0 - activity_mod) * 2.0  # Encourage RESTING

        # ── Predator soft NN bias — discourage MATING when prey scarce ────
        if self.is_predator and hasattr(self.world, "fish_system"):
            prey_count = len(self.world.fish_system.fish)
            pred_count = len(self.world.fish_system.predators)
            if pred_count > 0 and (prey_count / pred_count) < PREDATOR_PREY_RATIO_MIN:
                logits[3] -= 5.0  # Strongly discourage MATING
            if pred_count >= PREDATOR_MAX_POPULATION:
                logits[3] = -1e9  # Hard block at population cap

        if not self.is_mature:
            logits[1] = -1e9  # Block HUNTING for immature fish
            logits[3] = -1e9  # Block MATING for immature fish

        # Predators never enter MATING state
        if self.is_predator:
            logits[3] = -1e9  # Block MATING state completely

        best_idx = logits.index(max(logits))
        return FISH_STATE_ORDER[best_idx]

    # ── Update ─────────────────────────────────────────────────────────────

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        self.age += dt
        self.last_cleaned_time += dt

        # Update fin animation phase
        self._fin_phase += dt * 8.0

        # ── needs_cleaning: rises with age and low energy, decays when cleaned ─
        if self.last_cleaned_time > 5.0:
            # Fish gradually "need cleaning" as they swim around
            age_pressure = min(1.0, self.age / FISH_MAX_AGE)
            energy_pressure = max(0.0, 1.0 - self.energy / FISH_MAX_ENERGY)
            self.needs_cleaning = min(
                1.0,
                self.needs_cleaning
                + (0.02 * age_pressure + 0.03 * energy_pressure) * dt,
            )
        # When recently cleaned, needs_cleaning is reset to near-zero by the cleaner

        metabolism_mod = time_system.metabolism_modifier if time_system else 1.0
        metabolism_rate = (
            0.1
            * self.traits.physical_traits.get("metabolism_mult", 1.0)
            * metabolism_mod
        )
        self.energy -= metabolism_rate * dt
        self.mating_cooldown = max(0.0, self.mating_cooldown - dt)
        self.is_mature = self.age > (FISH_LARVA_DURATION + FISH_JUVENILE_DURATION)

        night_rest_factor = 0.5 if (time_system and time_system.is_night) else 1.0

        # ── Skip speed-based stamina drain while predator is dashing ──────
        speed_ratio = self.physics.vel.length() / max(1.0, self.physics.max_speed)
        if speed_ratio > 0.8 and not getattr(self, "is_dashing", False):
            self.stamina = max(0.0, self.stamina - 15.0 * speed_ratio * dt)
        elif speed_ratio < 0.3:
            recovery = 8.0 * self.traits.physical_traits.get("stamina_mult", 1.0) * dt
            self.stamina = min(100.0, self.stamina + recovery)

        full_inputs = self.get_radar_inputs(all_fish, targets, plant_manager)
        threat_level = sum(full_inputs[3:6])
        cover_quality = full_inputs[13]
        ambush_alert = full_inputs[16]

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

        # ═══════════════════════════════════════════════════════════════════
        # FIX: Cover stamina — reduced bonus, predators get less
        # ═══════════════════════════════════════════════════════════════════
        if cover_quality > 0.3:
            bonus = FISH_COVER_STAMINA_PREDATOR if self.is_predator else FISH_COVER_STAMINA_BONUS
            self.stamina = min(100.0, self.stamina + bonus * cover_quality * dt)

        # ── Neural net forward pass ──────────────────────────────────────
        mating_drive = time_system.mating_drive_modifier if time_system else 1.0
        activity_mod = (
            time_system.predator_activity_modifier
            if (time_system and self.is_predator)
            else 1.0
        )

        self.last_inputs = full_inputs
        outputs, hidden1, hidden2 = self.brain.forward(self.last_inputs)
        self.last_hidden1 = hidden1
        self.last_hidden = hidden2
        self.last_outputs = outputs
        self.output_history.append(list(outputs[:4]))

        steer_out = outputs[0]
        thrust_out = outputs[1]
        hide_drive = outputs[2]
        sprint_drive = outputs[3]
        raw_state_probs = outputs[4:9]
        self.last_state_probs = raw_state_probs

        # ── Soft state selection (now receives activity_mod) ─────────────
        self.state = self._pick_state(
            raw_state_probs, threat_level, night_rest_factor, mating_drive, activity_mod
        )

        # ═══════════════════════════════════════════════════════════════════
        # FIX: Hide Drive — now GATED behind actual threats
        # Only seek plant cover when predators are nearby (threat_level > threshold)
        # This prevents the NN from learning "always hide near plant" as the
        # dominant strategy, which caused fish to cluster and orbit plants.
        # ═══════════════════════════════════════════════════════════════════
        if self.closest_plant:
            should_hide = (
                threat_level > FISH_HIDE_THREAT_THRESHOLD
                or ambush_alert > 0.5
            )

            if should_hide:
                # Active threat — seek plant cover
                if self.is_predator:
                    ambush_weight = hide_drive * 0.3
                    ambush_force = self.physics.seek(
                        self.closest_plant.x,
                        self.closest_plant.base_y,
                        weight=ambush_weight,
                    )
                    self.physics.apply_force(ambush_force)
                else:
                    hide_weight = hide_drive * FISH_HIDE_WEIGHT
                    hide_force = self.physics.seek(
                        self.closest_plant.x,
                        self.closest_plant.base_y,
                        weight=hide_weight,
                    )
                    self.physics.apply_force(hide_force)
                    self._plant_linger_timer = 0.0  # reset since hiding is valid

            # ═══════════════════════════════════════════════════════════════
            # FIX: Plant Restlessness — push away from plants when safe
            # If no threats nearby and fish has been lingering near a plant,
            # apply a gentle force AWAY to prevent orbiting.
            # ═══════════════════════════════════════════════════════════════
            elif self.closest_plant and not self.is_predator:
                dist_to_plant = self.physics.pos.distance_to(
                    (self.closest_plant.x, self.closest_plant.base_y)
                )
                if dist_to_plant < PLANT_COVER_RADIUS:
                    self._plant_linger_timer += dt
                    if self._plant_linger_timer > FISH_PLANT_LINGER_MAX:
                        # Push AWAY from the plant — gentle anti-clustering
                        away_force = self.physics.seek(
                            self.closest_plant.x,
                            self.closest_plant.base_y,
                            weight=-FISH_PLANT_RESTLESSNESS,
                        )
                        self.physics.apply_force(away_force)

                    # Also dampen lingering near plants even before the timer
                    # by reducing the linger timer slowly when safe
                    if self._plant_linger_timer > FISH_PLANT_LINGER_MAX * 0.5:
                        self._plant_linger_timer -= dt * 0.1

        # ═══════════════════════════════════════════════════════════════════
        # FIX: Exploration / Wanderlust — random wander when safe and fed
        # This gives fish a natural tendency to explore the environment
        # instead of huddling near plants.
        # ═══════════════════════════════════════════════════════════════════
        is_safe = threat_level < FISH_HIDE_THREAT_THRESHOLD
        is_well_fed = self.energy > FISH_MAX_ENERGY * 0.5
        if is_safe and is_well_fed and not self.is_hidden:
            # Slowly evolve a wander direction
            self._wander_timer += dt
            if self._wander_timer > 2.0:
                self._wander_angle += random.uniform(-1.2, 1.2)
                self._wander_timer = 0.0

            wander_fx = math.cos(self._wander_angle) * FISH_EXPLORATION_FORCE
            wander_fy = math.sin(self._wander_angle) * FISH_EXPLORATION_FORCE
            self.physics.apply_force((wander_fx, wander_fy))

        # ═══════════════════════════════════════════════════════════════════
        # FIX: Fish Separation — prevent tight clustering
        # Fish that are too close together push apart, breaking up the
        # circular orbit pattern around plants.
        # ═══════════════════════════════════════════════════════════════════
        for other in all_fish:
            if other is self or other.is_predator != self.is_predator:
                continue
            sep_dist = self.physics.pos.distance_to(other.physics.pos)
            if 0 < sep_dist < FISH_SEPARATION_RADIUS:
                # Stronger push the closer they are
                strength = FISH_SEPARATION_FORCE * (1.0 - sep_dist / FISH_SEPARATION_RADIUS)
                # Direction: away from the other fish
                dx = self.physics.pos.x - other.physics.pos.x
                dy = self.physics.pos.y - other.physics.pos.y
                if sep_dist > 0:
                    self.physics.apply_force(
                        (dx / sep_dist * strength, dy / sep_dist * strength)
                    )

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
        speed_ceiling *= 1.0 + sprint_drive * 0.5
        speed_ceiling = min(speed_ceiling, self.physics.max_speed * 1.8)

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

    # ── Drawing with Heritable Appearance ────────────────────────────────────

    def draw(self, screen, camera, time, selected, biolum_alpha=0):
        pos = self.physics.pos
        if not camera.is_visible(pos, margin=60):
            return

        angle = self.physics.heading
        size = self.get_current_size_mult() * 4
        color = self.get_color()
        screen_pos = camera.apply(pos)

        app = self.traits.appearance_traits

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

        # ═══════════════════════════════════════════════════════════════════
        # HERITABLE APPEARANCE RENDERING
        # ═══════════════════════════════════════════════════════════════════

        # Get body proportions based on appearance traits
        body_len, body_wid = self.traits.get_body_proportions()
        body_len *= size
        body_wid *= size

        # Get fin configuration
        fin_config = self.traits.get_fin_config()
        
        # Get tail configuration  
        tail_config = self.traits.get_tail_config()
        
        # Get pattern configuration
        pattern_config = self.traits.get_pattern_config()
        
        # Calculate secondary color
        sec_color_offset = app["secondary_color_offset"]
        base = self._get_base_species_color()
        sec_color = tuple(
            max(0, min(255, base[i] + sec_color_offset[i])) for i in range(3)
        )

        # ── Draw Tail ────────────────────────────────────────────────────────
        self._draw_tail(
            screen, screen_pos, angle, size, color, sec_color, tail_config, time
        )

        # ── Draw Fins ─────────────────────────────────────────────────────────
        self._draw_fins(
            screen, screen_pos, angle, size, color, sec_color, fin_config, app, time
        )

        # ── Draw Body ─────────────────────────────────────────────────────────
        self._draw_body(
            screen, screen_pos, angle, body_len, body_wid, color, sec_color, 
            pattern_config, app, time
        )

        # ── Draw Pattern Overlay ─────────────────────────────────────────────
        if pattern_config["type"] != PATTERN_SOLID:
            self._draw_pattern(
                screen, screen_pos, angle, body_len, body_wid, sec_color, 
                pattern_config, app, time
            )

        # ── Draw Scale Shine ─────────────────────────────────────────────────
        if app["scale_shine"] > 0.2:
            self._draw_shine(screen, screen_pos, angle, body_len, body_wid, app, time)

        # ── Draw Eye ─────────────────────────────────────────────────────────
        eye_size = max(1, int(2 * app["eye_size_mult"]))
        eye_offset = 1.3 + app["eye_position"]
        eye_x = screen_pos[0] + math.cos(angle + 0.35) * size * eye_offset
        eye_y = screen_pos[1] + math.sin(angle + 0.35) * size * eye_offset
        pygame.draw.circle(screen, (255, 255, 255), (int(eye_x), int(eye_y)), eye_size + 1)
        pygame.draw.circle(screen, (0, 0, 0), (int(eye_x), int(eye_y)), eye_size)

        # ── Draw Barbels (whiskers) ──────────────────────────────────────────
        if app["has_barbels"]:
            self._draw_barbels(screen, screen_pos, angle, size, app, time)

        # ── Pregnancy indicator ──────────────────────────────────────────────
        if self.is_pregnant:
            pygame.draw.circle(
                screen,
                (255, 200, 200, 150),
                (int(screen_pos[0]), int(screen_pos[1])),
                int(size * 1.2),
            )

        # ── Selection ring ───────────────────────────────────────────────────
        if selected:
            pygame.draw.circle(
                screen,
                (255, 255, 200),
                (int(screen_pos[0]), int(screen_pos[1])),
                int(size) + 15,
                2,
            )

        # ── Mating state ♥ label ─────────────────────────────────────────────
        if self.state == FishState.MATING and self._mating_glow_timer > 0.3:
            heart_y = int(screen_pos[1]) - int(size * 4) - 8
            sym_font = pygame.font.Font(None, 18)
            sym = sym_font.render("♥", True, (255, 100, 150))
            screen.blit(sym, (int(screen_pos[0]) - sym.get_width() // 2, heart_y))

    def _draw_tail(self, screen, pos, angle, size, color, sec_color, tail_config, time):
        """Draw the fish tail based on tail_shape trait"""
        tail_angle = angle + math.pi + math.sin(time * 10) * 0.4
        tail_size = size * tail_config["size"] * 2.5
        tail_spread = tail_config["spread"]
        tail_shape = tail_config["shape"]

        if tail_shape == TAIL_POINTED:
            pts = [
                (pos[0], pos[1]),
                (pos[0] + math.cos(tail_angle - 0.5) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle - 0.5) * tail_size * tail_spread),
                (pos[0] + math.cos(tail_angle) * tail_size * 1.2,
                 pos[1] + math.sin(tail_angle) * tail_size * 1.2),
                (pos[0] + math.cos(tail_angle + 0.5) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle + 0.5) * tail_size * tail_spread),
            ]
            pygame.draw.polygon(screen, color, pts)
            
        elif tail_shape == TAIL_FORKED:
            fork_depth = 0.6
            pts_left = [
                (pos[0], pos[1]),
                (pos[0] + math.cos(tail_angle - 0.7) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle - 0.7) * tail_size * tail_spread),
                (pos[0] + math.cos(tail_angle - 0.3) * tail_size * fork_depth,
                 pos[1] + math.sin(tail_angle - 0.3) * tail_size * fork_depth),
            ]
            pts_right = [
                (pos[0], pos[1]),
                (pos[0] + math.cos(tail_angle + 0.3) * tail_size * fork_depth,
                 pos[1] + math.sin(tail_angle + 0.3) * tail_size * fork_depth),
                (pos[0] + math.cos(tail_angle + 0.7) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle + 0.7) * tail_size * tail_spread),
            ]
            pygame.draw.polygon(screen, color, pts_left)
            pygame.draw.polygon(screen, color, pts_right)
            
        elif tail_shape == TAIL_ROUNDED:
            pts = [
                (pos[0], pos[1]),
                (pos[0] + math.cos(tail_angle - 0.6) * tail_size * tail_spread * 0.8,
                 pos[1] + math.sin(tail_angle - 0.6) * tail_size * tail_spread * 0.8),
                (pos[0] + math.cos(tail_angle - 0.3) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle - 0.3) * tail_size * tail_spread),
                (pos[0] + math.cos(tail_angle) * tail_size * 0.9,
                 pos[1] + math.sin(tail_angle) * tail_size * 0.9),
                (pos[0] + math.cos(tail_angle + 0.3) * tail_size * tail_spread,
                 pos[1] + math.sin(tail_angle + 0.3) * tail_size * tail_spread),
                (pos[0] + math.cos(tail_angle + 0.6) * tail_size * tail_spread * 0.8,
                 pos[1] + math.sin(tail_angle + 0.6) * tail_size * tail_spread * 0.8),
            ]
            pygame.draw.polygon(screen, color, pts)
            
        elif tail_shape == TAIL_LYRE:
            wave = math.sin(time * 6) * 0.2
            pts = [
                (pos[0], pos[1]),
                (pos[0] + math.cos(tail_angle - 0.8 + wave) * tail_size * tail_spread * 1.1,
                 pos[1] + math.sin(tail_angle - 0.8 + wave) * tail_size * tail_spread * 1.1),
                (pos[0] + math.cos(tail_angle - 0.4) * tail_size * 0.7,
                 pos[1] + math.sin(tail_angle - 0.4) * tail_size * 0.7),
                (pos[0] + math.cos(tail_angle) * tail_size * 0.5,
                 pos[1] + math.sin(tail_angle) * tail_size * 0.5),
                (pos[0] + math.cos(tail_angle + 0.4) * tail_size * 0.7,
                 pos[1] + math.sin(tail_angle + 0.4) * tail_size * 0.7),
                (pos[0] + math.cos(tail_angle + 0.8 - wave) * tail_size * tail_spread * 1.1,
                 pos[1] + math.sin(tail_angle + 0.8 - wave) * tail_size * tail_spread * 1.1),
            ]
            pygame.draw.polygon(screen, color, pts)

    def _draw_fins(self, screen, pos, angle, size, color, sec_color, fin_config, app, time):
        """Draw dorsal, pectoral, and anal fins"""
        fin_anim = math.sin(self._fin_phase) * 0.3
        
        # Dorsal fin (top)
        dorsal_size = size * fin_config["dorsal"] * 1.5
        if dorsal_size > 1:
            dorsal_x = pos[0] + math.cos(angle - math.pi/2) * size * 0.3
            dorsal_y = pos[1] + math.sin(angle - math.pi/2) * size * 0.3
            
            fin_style = app["fin_style"]
            if fin_style == FIN_STYLE_ELEGANT or fin_style == FIN_STYLE_DRAMATIC:
                # Longer, flowing fin
                pts = [
                    (dorsal_x, dorsal_y),
                    (dorsal_x + math.cos(angle - math.pi/2 - 0.3 + fin_anim) * dorsal_size * 1.2,
                     dorsal_y + math.sin(angle - math.pi/2 - 0.3 + fin_anim) * dorsal_size * 1.2),
                    (dorsal_x + math.cos(angle - math.pi/2 + 0.3 + fin_anim) * dorsal_size * 1.2,
                     dorsal_y + math.sin(angle - math.pi/2 + 0.3 + fin_anim) * dorsal_size * 1.2),
                    (dorsal_x + math.cos(angle) * size * 0.5,
                     dorsal_y + math.sin(angle) * size * 0.5),
                ]
            else:
                # Standard triangular fin
                pts = [
                    (dorsal_x, dorsal_y),
                    (dorsal_x + math.cos(angle - math.pi/2) * dorsal_size,
                     dorsal_y + math.sin(angle - math.pi/2) * dorsal_size),
                    (dorsal_x + math.cos(angle) * size * 0.3,
                     dorsal_y + math.sin(angle) * size * 0.3),
                ]
            
            # Draw with slight transparency
            fin_surf = pygame.Surface((int(dorsal_size * 3), int(dorsal_size * 3)), pygame.SRCALPHA)
            fin_color = (*color, 180)
            # Translate points for the surface
            offset_pts = [(p[0] - dorsal_x + dorsal_size * 1.5, p[1] - dorsal_y + dorsal_size * 1.5) for p in pts]
            if len(offset_pts) >= 3:
                pygame.draw.polygon(fin_surf, fin_color, offset_pts)
                screen.blit(fin_surf, (int(dorsal_x - dorsal_size * 1.5), int(dorsal_y - dorsal_size * 1.5)))

        # Pectoral fins (sides) - draw on both sides
        pectoral_size = size * fin_config["pectoral"] * 0.8
        if pectoral_size > 1:
            for side in [-1, 1]:
                pec_angle = angle + side * 0.8
                pec_x = pos[0] + math.cos(angle) * size * 0.3 + math.cos(pec_angle) * size * 0.2
                pec_y = pos[1] + math.sin(angle) * size * 0.3 + math.sin(pec_angle) * size * 0.2
                
                wave = math.sin(self._fin_phase + side) * 0.4
                pts = [
                    (pec_x, pec_y),
                    (pec_x + math.cos(pec_angle + wave) * pectoral_size,
                     pec_y + math.sin(pec_angle + wave) * pectoral_size),
                    (pec_x + math.cos(pec_angle + 0.5 + wave) * pectoral_size * 0.6,
                     pec_y + math.sin(pec_angle + 0.5 + wave) * pectoral_size * 0.6),
                ]
                pygame.draw.polygon(screen, color, pts)

        # Anal fin (bottom)
        anal_size = size * fin_config["anal"] * 1.0
        if anal_size > 1:
            anal_x = pos[0] + math.cos(angle + math.pi/2) * size * 0.2 - math.cos(angle) * size * 0.3
            anal_y = pos[1] + math.sin(angle + math.pi/2) * size * 0.2 - math.sin(angle) * size * 0.3
            
            pts = [
                (anal_x, anal_y),
                (anal_x + math.cos(angle + math.pi/2 - 0.3 + fin_anim) * anal_size,
                 anal_y + math.sin(angle + math.pi/2 - 0.3 + fin_anim) * anal_size),
                (anal_x + math.cos(angle + math.pi/2 + 0.3 + fin_anim) * anal_size,
                 anal_y + math.sin(angle + math.pi/2 + 0.3 + fin_anim) * anal_size),
            ]
            pygame.draw.polygon(screen, color, pts)

    def _draw_body(self, screen, pos, angle, body_len, body_wid, color, sec_color, pattern_config, app, time):
        """Draw the fish body with proper proportions"""
        # Create body surface
        surf_w = int(body_len * 6) + 4
        surf_h = int(body_wid * 4) + 4
        body_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        
        cx, cy = surf_w // 2, surf_h // 2
        
        # Draw body based on shape
        body_shape = app["body_shape"]
        snout_len = app["snout_length"]
        belly_curve = app["belly_curve"]
        
        if body_shape == BODY_SHAPE_STREAMLINED:
            # Long, pointed body
            # Generate bezier-like curve for streamlined shape
            pts = []
            for i in range(20):
                t = i / 19
                # Parametric curve for streamlined body
                x = cx - body_len * 2 + t * body_len * 4
                y_offset = body_wid * 1.5 * math.sin(t * math.pi) * (1 - abs(t - 0.5) * 0.4)
                # Add snout elongation at front
                if t < 0.2:
                    y_offset *= 0.5 + t * 2.5
                pts.append((x, cy - y_offset))
            for i in range(19, -1, -1):
                t = i / 19
                x = cx - body_len * 2 + t * body_len * 4
                y_offset = body_wid * 1.5 * math.sin(t * math.pi) * (1 - abs(t - 0.5) * 0.4)
                if t < 0.2:
                    y_offset *= 0.5 + t * 2.5
                # Apply belly curve
                if t > 0.3 and t < 0.8:
                    y_offset *= (1 + belly_curve * (1 - abs(t - 0.55) * 4))
                pts.append((x, cy + y_offset))
            pygame.draw.polygon(body_surf, (*color, 255), pts)
            
        elif body_shape == BODY_SHAPE_ROUNDED:
            # Short, round body
            pts = []
            for i in range(20):
                t = i / 19
                x = cx - body_len * 1.5 + t * body_len * 3
                y_offset = body_wid * 2 * math.sin(t * math.pi) * (0.8 + t * 0.2 if t > 0.5 else 0.8 + (1-t) * 0.2)
                pts.append((x, cy - y_offset))
            for i in range(19, -1, -1):
                t = i / 19
                x = cx - body_len * 1.5 + t * body_len * 3
                y_offset = body_wid * 2 * math.sin(t * math.pi) * (0.8 + t * 0.2 if t > 0.5 else 0.8 + (1-t) * 0.2)
                y_offset *= (1 + belly_curve)
                pts.append((x, cy + y_offset))
            pygame.draw.polygon(body_surf, (*color, 255), pts)
            
        else:  # BODY_SHAPE_STANDARD
            # Balanced ellipse
            pygame.draw.ellipse(body_surf, (*color, 255), 
                              (cx - body_len * 2, cy - body_wid * 1.5, 
                               body_len * 4, body_wid * 3))

        # Rotate and blit
        rotated_body = pygame.transform.rotate(body_surf, -math.degrees(angle))
        screen.blit(
            rotated_body,
            rotated_body.get_rect(center=(int(pos[0]), int(pos[1]))),
        )

    def _draw_pattern(self, screen, pos, angle, body_len, body_wid, sec_color, pattern_config, app, time):
        """Draw pattern overlay based on pattern_type"""
        pattern_type = pattern_config["type"]
        intensity = pattern_config["intensity"]
        scale = pattern_config["scale"]
        density = pattern_config["density"]
        
        # Create pattern surface
        surf_w = int(body_len * 6) + 4
        surf_h = int(body_wid * 4) + 4
        pattern_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2
        
        pattern_color = (*sec_color, int(200 * intensity))
        
        if pattern_type == PATTERN_STRIPES:
            # Horizontal stripes
            stripe_count = int(5 * density * scale)
            stripe_width = int(body_wid * 0.4 / max(1, stripe_count))
            for i in range(stripe_count):
                y = cy - body_wid * 1.2 + i * (body_wid * 2.4 / stripe_count)
                pygame.draw.line(pattern_surf, pattern_color,
                               (cx - body_len * 1.5, y),
                               (cx + body_len * 1.5, y), max(1, stripe_width))
                               
        elif pattern_type == PATTERN_SPOTS:
            # Polka dot pattern
            random.seed(self._pattern_seed)
            spot_count = int(15 * density)
            for _ in range(spot_count):
                sx = cx + random.uniform(-body_len * 1.5, body_len * 1.5)
                sy = cy + random.uniform(-body_wid * 1.2, body_wid * 1.2)
                # Check if inside body ellipse
                if ((sx - cx) / (body_len * 1.8)) ** 2 + ((sy - cy) / (body_wid * 1.3)) ** 2 < 1:
                    spot_r = int(random.uniform(1, 3) * scale)
                    pygame.draw.circle(pattern_surf, pattern_color, (int(sx), int(sy)), max(1, spot_r))
                    
        elif pattern_type == PATTERN_GRADIENT:
            # Color fade from head to tail
            for i in range(int(body_len * 3)):
                x = cx - body_len * 1.5 + i
                alpha = int(200 * intensity * (i / (body_len * 3)))
                grad_color = (*sec_color, alpha)
                pygame.draw.line(pattern_surf, grad_color,
                               (x, cy - body_wid * 1.3),
                               (x, cy + body_wid * 1.3), 1)
                               
        elif pattern_type == PATTERN_BANDS:
            # Vertical bands
            band_count = int(4 * density)
            band_width = int(body_len * 0.3 * scale)
            for i in range(band_count):
                x = cx - body_len * 1.2 + i * (body_len * 2.4 / band_count)
                pygame.draw.line(pattern_surf, pattern_color,
                               (x, cy - body_wid * 1.3),
                               (x, cy + body_wid * 1.3), max(1, band_width))
                               
        elif pattern_type == PATTERN_MARBLED:
            # Swirly, organic pattern
            random.seed(self._pattern_seed)
            for _ in range(int(8 * density)):
                start_x = cx + random.uniform(-body_len * 1.3, body_len * 1.3)
                start_y = cy + random.uniform(-body_wid * 1.0, body_wid * 1.0)
                # Draw curved line
                pts = [(start_x, start_y)]
                for j in range(5):
                    pts.append((
                        pts[-1][0] + random.uniform(-body_len * 0.4, body_len * 0.4) * scale,
                        pts[-1][1] + random.uniform(-body_wid * 0.3, body_wid * 0.3) * scale
                    ))
                if len(pts) >= 2:
                    pygame.draw.lines(pattern_surf, pattern_color, False, pts, max(1, int(2 * scale)))

        # Rotate and blit pattern
        rotated_pattern = pygame.transform.rotate(pattern_surf, -math.degrees(angle))
        screen.blit(
            rotated_pattern,
            rotated_pattern.get_rect(center=(int(pos[0]), int(pos[1]))),
        )

    def _draw_shine(self, screen, pos, angle, body_len, body_wid, app, time):
        """Draw scale shine/iridescence effect"""
        shine = app["scale_shine"]
        iridescence = app["iridescence"]
        
        # Create shine surface
        surf_w = int(body_len * 3) + 4
        surf_h = int(body_wid * 2) + 4
        shine_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        cx, cy = surf_w // 2, surf_h // 2
        
        # Animate iridescence
        hue_shift = math.sin(time * 2 + self._pattern_seed) * iridescence * 30
        
        # Draw highlight arc
        for i in range(int(body_len * 1.5)):
            x = cx - body_len * 0.5 + i * 0.5
            alpha = int(60 * shine * (1 - i / (body_len * 1.5)))
            # Iridescent color shift
            shine_color = (
                min(255, 200 + int(hue_shift)),
                min(255, 220 + int(hue_shift * 0.5)),
                min(255, 255)
            )
            pygame.draw.line(shine_surf, (*shine_color, alpha),
                           (x, cy - body_wid * 0.8 + i * 0.2),
                           (x, cy - body_wid * 0.3), 1)

        # Rotate and blit
        rotated_shine = pygame.transform.rotate(shine_surf, -math.degrees(angle))
        screen.blit(
            rotated_shine,
            rotated_shine.get_rect(center=(int(pos[0]) - body_len * 0.3, int(pos[1]) - body_wid * 0.2)),
        )

    def _draw_barbels(self, screen, pos, angle, size, app, time):
        """Draw whisker-like barbels"""
        barbel_len = size * app["barbel_length"] * 3
        wave = math.sin(time * 5) * 0.3
        
        for side in [-1, 1]:
            start_x = pos[0] + math.cos(angle) * size * 0.8
            start_y = pos[1] + math.sin(angle) * size * 0.8
            
            end_x = start_x + math.cos(angle + side * 0.4 + wave * side) * barbel_len
            end_y = start_y + math.sin(angle + side * 0.4 + wave * side) * barbel_len
            
            pygame.draw.line(screen, (60, 50, 40), 
                           (int(start_x), int(start_y)), 
                           (int(end_x), int(end_y)), 1)

    def _get_base_species_color(self):
        """Get the base color for this fish's species"""
        if self.is_predator:
            base = [220, 60, 60]
        elif self.is_cleaner:
            base = [100, 180, 220]
        else:
            base = [255, 160, 60]
        return base

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
