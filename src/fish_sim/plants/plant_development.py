"""
Plant development system — staged lifecycle with strict seasonal behaviour.

Season index:  0=Spring  1=Summer  2=Autumn  3=Winter

Lifecycle (linear, one-way):
  seed → germinating → seedling → mature → flowering → seeding → dormant/dying → decomposing

FIXED: Plants now return to mature after flowering (if healthy) instead of dying.
This allows sustainable reproduction cycles.

Strict seasonal rules ──────────────────────
  Spring  – seeds germinate, dormant plants wake up, roots/growth begins
  Summer  – peak growth, photosynthesis at max, some seeding allowed
  Autumn  – flowering peaks, seed dispersal, plants prepare for winter
  Winter  – no germination, no growth, plants go dormant or die, decomposition
"""

import random
from ..config import (
    SEED_GROWTH_ENERGY,
    MATURE_ENERGY_THRESHOLD,
    PLANT_BASE_MAINTENANCE,
    PLANT_SIZE_MAINTENANCE_FACTOR,
    PLANT_MAX_AGE,
    FLOWERING_ENERGY_THRESHOLD,
    FLOWERING_DURATION,
    DECOMPOSITION_DURATION,
    DECOMPOSITION_NUTRIENT_RETURN,
    WINTER_SURVIVAL_CHANCE,
    SPRING_GERMINATION_BOOST,
    WINTER_PHOTOSYNTHESIS_BASE,
    FLOWERING_SEASON_PREFERENCE,
    _SEASON_AGE_RATE,
    _SEASON_PHOTO_MOD,
    _SEASON_CAN_SEED,
    _SEASON_SEED_COOLDOWN,
    GERMINATION_FAILURE_ENERGY_THRESHOLD,
    GERMINATION_FAILURE_TIME,
    SEEDLING_DEATH_TIME,
    DORMANT_ENERGY_MINIMUM,
    DORMANT_DEATH_TIME,
    SPRING_GERMINATION_BASE_CHANCE,
    SUMMER_GERMINATION_BASE_CHANCE,
    SEED_ENERGY_THRESHOLD,
    FLOWERING_BASE_CHANCE,
    AUTUMN_SEED_BASE_PROBABILITY,
    SUMMER_SEED_BASE_PROBABILITY,
    SPRING_SEED_BASE_PROBABILITY,
    SEED_ENERGY_COST,
    WINTER_MAINTENANCE_MULT,
)


class PlantDevelopment:
    """Handles staged development for one plant instance."""

    def __init__(self, plant_type, seed_traits=None):
        self.plant_type = plant_type
        self.traits = seed_traits or {}
        self.age = 0.0
        self.energy = 1.5
        self.stage = "seed"
        self.is_mature = False
        self.is_flowering = False
        self.time_in_stage = 0.0
        self._has_flowered = False  # Reset each spring
        self._winter_roll_made = False
        self._dormant_seasons = 0  # how many winters survived dormant
        self._last_season = -1  # track season transitions

        self._init_species_params()

        self.current_height = 3.0
        self.current_segments = 1.0
        self.target_height = 3.0
        self.target_segments = 1.0
        self.visible_blades = 0.0

        if plant_type == "seagrass":
            self.total_blades = random.randint(4, 6)

        # Stagger seed cooldowns so plants don't all fire at once
        self.seed_cooldown = random.uniform(5.0, 20.0)
        self.season_index = 0

    # ── Species parameters ────────────────────────────────────────────────

    def _init_species_params(self):
        self.germination_energy = SEED_GROWTH_ENERGY
        self.maturity_energy = MATURE_ENERGY_THRESHOLD
        self.flowering_energy = FLOWERING_ENERGY_THRESHOLD
        self.max_age = PLANT_MAX_AGE

        overrides = {
            "lily_pad": dict(germ=0.7, mat=0.8, flow=0.9, age=0.8),
            "tube_sponge": dict(germ=1.3, mat=1.2, flow=1.3, age=1.5),
            "red_seaweed": dict(germ=0.8, mat=0.9, flow=0.85, age=1.0),
            "anemone": dict(germ=0.6, mat=0.7, flow=0.8, age=0.9),
            "fan_coral": dict(germ=1.1, mat=1.1, flow=1.2, age=1.3),
        }
        if self.plant_type in overrides:
            o = overrides[self.plant_type]
            self.germination_energy *= o["germ"]
            self.maturity_energy *= o["mat"]
            self.flowering_energy *= o["flow"]
            self.max_age *= o["age"]

        segs = {
            "kelp": 14,
            "seagrass": 10,
            "algae": 6,
            "red_seaweed": 12,
            "tube_sponge": 8,
            "fan_coral": 16,
            "anemone": 6,
            "lily_pad": 1,
        }
        self._max_segments = segs.get(self.plant_type, 8)

    # ── Root-growth multiplier ────────────────────────────────────────────

    def get_root_growth_multiplier(self, energy, height):
        energy_factor = min(energy / 10.0, 2.0)
        height_factor = max(0.1, 1.0 - (height / 100.0))
        return energy_factor * height_factor

    # ── Main update ───────────────────────────────────────────────────────

    def update(
        self,
        dt,
        growth_nutrients,
        height_unused,
        photosynthesis_rate=0.0,
        season_index=0,
    ):
        """
        dt                  – seconds since last frame
        growth_nutrients    – nutrients harvested from roots this frame
        photosynthesis_rate – from TimeSystem (0..~1.2)
        season_index        – 0=Spring 1=Summer 2=Autumn 3=Winter
        """
        self.season_index = season_index
        self.time_in_stage += dt
        self.seed_cooldown = max(0.0, self.seed_cooldown - dt)

        # Detect season change (for one-shot transitions)
        season_changed = season_index != self._last_season
        self._last_season = season_index

        # ── Age rate ───────────────────────────────────────────────────────
        age_mult = _SEASON_AGE_RATE.get(season_index, 1.0)
        if self.stage in ("seed", "dormant"):
            age_mult *= 0.2  # seeds/dormant plants age very slowly
        self.age += dt * age_mult

        # ── Photosynthesis & energy gain ───────────────────────────────────
        # Only growing/mature plants photosynthesise — seeds and dormant plants don't
        if self.stage not in ("seed", "dormant", "decomposing"):
            photo = photosynthesis_rate
            if season_index == 3:  # winter
                base_winter = WINTER_PHOTOSYNTHESIS_BASE
                hardy_bonus = WINTER_SURVIVAL_CHANCE.get(self.plant_type, 0.1)
                photo = base_winter * (0.5 + hardy_bonus * 1.5)
            photo *= _SEASON_PHOTO_MOD.get(season_index, 1.0)
            self.energy += photo * 1.2 * dt
            self.energy += growth_nutrients * 8.0 * dt

            # Maintenance cost - REDUCED for better survival
            maintenance = (
                PLANT_BASE_MAINTENANCE
                + self.current_height * PLANT_SIZE_MAINTENANCE_FACTOR * 0.005
            )
            if season_index == 3:
                maintenance *= WINTER_MAINTENANCE_MULT  # Reduced winter stress
            self.energy = max(0.0, self.energy - maintenance * dt)

        self._update_dimensions(dt, season_index)

        # ── Strict seasonal stage transitions ──────────────────────────────
        self._handle_seasonal_transitions(season_index, season_changed)

        # ── Per-stage logic ────────────────────────────────────────────────
        if self.stage == "seed":
            self._update_as_seed(dt, season_index)

        elif self.stage == "dormant":
            self._update_dormant(dt, season_index)

        elif self.stage == "germinating":
            # Need a bit of energy to push through germination
            if self.energy >= SEED_GROWTH_ENERGY * 0.9:
                self._transition("seedling")
            elif (
                self.time_in_stage > GERMINATION_FAILURE_TIME
                and self.energy < GERMINATION_FAILURE_ENERGY_THRESHOLD
            ):
                # Failed to germinate — die
                self._transition("dying")

        elif self.stage == "seedling":
            # Grow toward maturity
            if self.energy >= MATURE_ENERGY_THRESHOLD:
                self._transition("mature")
            elif self.energy <= 0 and self.time_in_stage > SEEDLING_DEATH_TIME:
                self._transition("dying")

        elif self.stage == "mature":
            # FIX: Spring, Summer AND Autumn: try to flower
            # Previously only (1, 2) — plants in Spring couldn't flower at all
            if season_index in (0, 1, 2):  # Spring, Summer, Autumn
                self._try_enter_flowering(season_index)
            # Check for old age death
            if self.age > PLANT_MAX_AGE * 0.95:
                self._transition("dying")
            # Energy-based death only at very low levels
            elif self.energy <= 0.1:  # Changed from <= 0 to give buffer
                self._transition("dying")

        elif self.stage == "flowering":
            # FIXED: After flowering duration, return to mature if healthy
            if self.time_in_stage >= FLOWERING_DURATION:
                # Check if plant is healthy enough to continue
                if self.energy >= MATURE_ENERGY_THRESHOLD * 0.5:
                    # Return to mature to continue producing seeds
                    self._transition("mature")
                elif self.energy < 0.5:
                    # Only die if critically low energy
                    self._transition("dying")
                else:
                    # Marginal energy - return to mature anyway
                    self._transition("mature")
            # Die during flowering only if critically starved
            elif self.energy < 0.3:
                self._transition("dying")

        elif self.stage == "dying":
            if self.time_in_stage >= DECOMPOSITION_DURATION:
                self._transition("decomposing")

        return self.stage != "decomposing"

    # ── Seasonal transition logic ─────────────────────────────────────────

    def _handle_seasonal_transitions(self, season, season_changed):
        """
        Called every frame. season_changed=True on the first frame of a new season.
        """
        if not season_changed:
            # Mid-season: only handle ongoing winter stress for non-dormant plants
            if season == 3 and self.stage in ("mature", "flowering", "seedling"):
                if self.energy <= 0.05:  # Very low energy threshold
                    self._transition("dying")
            return

        # ── Season just changed ────────────────────────────────────────────

        if season == 3:  # Just entered Winter
            self._winter_roll_made = False  # reset for this winter

            if self.stage in ("mature", "flowering"):
                # Roll for survival: hardy plants go dormant, others die
                survival = WINTER_SURVIVAL_CHANCE.get(self.plant_type, 0.1)
                if random.random() < survival:
                    self._transition("dormant")
                    self._dormant_seasons += 1
                else:
                    self._transition("dying")

            elif self.stage == "seedling":
                # Seedlings have a harder time surviving winter
                survival = WINTER_SURVIVAL_CHANCE.get(self.plant_type, 0.1) * 0.6
                if random.random() < survival:
                    self._transition("dormant")
                else:
                    self._transition("dying")

            elif self.stage == "germinating":
                # Germinating plants always die in winter
                self._transition("dying")

            # Seeds just wait — they don't transition

        elif season == 0:  # Just entered Spring
            self._winter_roll_made = False

            # FIXED: Reset flowering flag so plants can flower again this year
            self._has_flowered = False

            if self.stage == "dormant":
                # Wake up from dormancy in spring
                wake_chance = 0.7 + 0.25 * self.traits.get("growth_rate_mult", 1.0)
                wake_chance = min(0.95, wake_chance)
                if random.random() < wake_chance:
                    self._transition("mature")  # dormant plants resume as mature
                else:
                    # Failed to wake — die
                    self._transition("dying")

        elif season == 2:  # Just entered Autumn
            # Autumn provides another chance for mature plants to flower if they haven't yet
            # Note: _has_flowered is reset in spring, so plants can flower each year
            pass

    def _update_as_seed(self, dt, season):
        """
        Seeds germinate in Spring (primary) and early Summer (fallback).
        They wait patiently through Autumn and Winter.
        """
        if season == 3:  # Winter — stay dormant as seed
            return
        if season == 2:  # Autumn — wait for next spring
            return

        # Spring: high chance to germinate
        if season == 0:
            germ_chance = SPRING_GERMINATION_BASE_CHANCE * SPRING_GERMINATION_BOOST
        else:
            # Summer fallback: moderate chance (late starters)
            germ_chance = SUMMER_GERMINATION_BASE_CHANCE

        if (
            self.energy > SEED_ENERGY_THRESHOLD
            and random.random() < germ_chance * 60 * dt
        ):
            self._transition("germinating")

    def _update_dormant(self, dt, season):
        """
        Dormant plants barely tick over.
        They are woken up by _handle_seasonal_transitions when Spring arrives.
        """
        # Very slow energy drain to simulate basal metabolism
        self.energy = max(
            DORMANT_ENERGY_MINIMUM, self.energy - 0.002 * dt  # Reduced from 0.003
        )

        # If energy runs out mid-dormancy, the plant dies
        if (
            self.energy <= DORMANT_ENERGY_MINIMUM
            and self.time_in_stage > DORMANT_DEATH_TIME
        ):
            self._transition("dying")

    def _try_enter_flowering(self, season_index):
        """Called in Spring, Summer and Autumn. Each plant flowers at most once per YEAR (reset in spring)."""
        if self._has_flowered:
            return
        pref = FLOWERING_SEASON_PREFERENCE.get(season_index, 0.0)
        if pref <= 0:
            return
        if (
            self.energy >= FLOWERING_ENERGY_THRESHOLD
            and random.random() < FLOWERING_BASE_CHANCE * pref
        ):
            self._transition("flowering")

    def _transition(self, new_stage):
        self.stage = new_stage
        self.time_in_stage = 0.0
        self.is_mature = self.stage in ("mature", "flowering")
        self.is_flowering = self.stage == "flowering"
        if new_stage == "flowering":
            self._has_flowered = True

    # ── Physical dimensions ───────────────────────────────────────────────

    def _update_dimensions(self, dt, season_index):
        stage_frac = {
            "germinating": 0.05,
            "seedling": 0.30,
            "mature": 1.00,
            "flowering": 1.00,
            "dying": 0.70,
            "decomposing": 0.40,
            "dormant": 0.60,  # dormant plants shrink a little but don't disappear
        }.get(self.stage, 1.0)

        if season_index == 3 and self.stage not in ("dormant", "seed"):
            stage_frac *= 0.75

        height_factor = self.traits.get("max_height_factor", 1.0)
        max_h = getattr(self, "_max_height_ref", 80.0) * height_factor
        self.target_height = max(3.0, max_h * stage_frac)
        self.target_segments = max(1.0, self._max_segments * min(1.0, stage_frac * 1.2))

        grow_speed = 12.0 * dt
        if self.current_height < self.target_height:
            self.current_height = min(
                self.target_height, self.current_height + grow_speed
            )
        else:
            self.current_height = max(
                self.target_height, self.current_height - grow_speed * 0.3
            )

        seg_speed = 2.0 * dt
        if self.current_segments < self.target_segments:
            self.current_segments = min(
                self.target_segments, self.current_segments + seg_speed
            )
        else:
            self.current_segments = max(
                self.target_segments, self.current_segments - seg_speed * 0.5
            )

        if self.plant_type == "seagrass":
            target_blades = self.total_blades * stage_frac
            if self.current_height > 5:
                self.visible_blades = min(
                    target_blades, self.visible_blades + seg_speed * 0.5
                )
            else:
                self.visible_blades = max(0.0, self.visible_blades - seg_speed * 0.3)

    # ── Seed production ───────────────────────────────────────────────────

    def can_produce_seed(self, seed_dispersal_modifier, season_index):
        """
        Seeds are released primarily in Autumn, with good output in Summer,
        and moderate output in Spring (FIX: Spring was previously blocked).

        Flowering plants release more seeds; mature plants release fewer.
        """
        if not _SEASON_CAN_SEED.get(season_index, True):
            return False
        # FIX: Allow seeding in Spring (0), Summer (1) and Autumn (2)
        if season_index not in (0, 1, 2):
            return False
        if self.stage not in ("mature", "flowering"):
            return False
        if self.seed_cooldown > 0:
            return False

        # Base probability — Autumn is primary seeding window
        if season_index == 2:  # Autumn
            base_p = AUTUMN_SEED_BASE_PROBABILITY
        elif season_index == 0:  # Spring — new: moderate seed output
            base_p = SPRING_SEED_BASE_PROBABILITY
        else:  # Summer
            base_p = SUMMER_SEED_BASE_PROBABILITY

        if self.stage == "flowering":
            base_p *= 5.0  # flowering is peak seeding time

        if random.random() > base_p * seed_dispersal_modifier:
            return False

        energy_cost = SEED_ENERGY_COST  # Reduced in config
        if self.energy < energy_cost:
            return False

        self.energy -= energy_cost
        self.seed_cooldown = _SEASON_SEED_COOLDOWN.get(season_index, 20.0)
        return True

    # ── Decomposition ─────────────────────────────────────────────────────

    def get_decomposition_return(self):
        return DECOMPOSITION_NUTRIENT_RETURN if self.stage == "decomposing" else 0.0
