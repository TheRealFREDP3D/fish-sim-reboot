"""
Plant development system — staged lifecycle with seasonal behaviour.

Season index:  0=Spring  1=Summer  2=Autumn  3=Winter

Lifecycle (linear, one-way):
  germinating → seedling → mature → flowering → dying → decomposing

Key seasonal rules
──────────────────
  Spring  – good germination, moderate growth, light seeding begins
  Summer  – peak growth and height, very little new seeding
  Autumn  – seed dispersal peaks; plants begin to age faster
  Winter  – dormancy: no new seeds, reduced photosynthesis, accelerated aging
"""

import random
from config import (
    SEED_GROWTH_ENERGY, MATURE_ENERGY_THRESHOLD, PLANT_BASE_MAINTENANCE,
    PLANT_SIZE_MAINTENANCE_FACTOR, PLANT_MAX_AGE, FLOWERING_ENERGY_THRESHOLD,
    FLOWERING_DURATION, DECOMPOSITION_DURATION, DECOMPOSITION_NUTRIENT_RETURN,
    WINTER_SURVIVAL_CHANCE, SPRING_GERMINATION_BOOST,
    WINTER_PHOTOSYNTHESIS_BASE, FLOWERING_SEASON_PREFERENCE,
    _SEASON_AGE_RATE, _SEASON_PHOTO_MOD, _SEASON_CAN_SEED, _SEASON_SEED_COOLDOWN,
)

# ── Seasonal modifiers are now in config.py ───────────────────────────────────


class PlantDevelopment:
    """Handles staged development for one plant instance."""

    def __init__(self, plant_type, seed_traits=None):
        self.plant_type   = plant_type
        self.traits       = seed_traits or {}
        self.age          = 0.0
        self.energy       = 1.5   # start with some energy so germination isn't instant
        self.stage        = "seed"          # ← changed: start as dormant seed
        self.is_mature    = False
        self.is_flowering = False
        self.time_in_stage = 0.0
        self._has_flowered = False   # each plant flowers at most once
        self._winter_roll_made = False      # one-time survival roll

        self._init_species_params()

        # Physical dimensions — updated each frame by _update_dimensions()
        self.current_height   = 3.0
        self.current_segments = 1.0
        self.target_height    = 3.0
        self.target_segments  = 1.0

        self.visible_blades = 0.0

        if plant_type == "seagrass":
            self.total_blades   = random.randint(4, 6)

        # Stagger seed cooldowns so plants don't all fire at once
        self.seed_cooldown = random.uniform(5.0, 25.0)

        self.season_index = 0

    # ── Species parameters ────────────────────────────────────────────────

    def _init_species_params(self):
        self.germination_energy = SEED_GROWTH_ENERGY
        self.maturity_energy    = MATURE_ENERGY_THRESHOLD
        self.flowering_energy   = FLOWERING_ENERGY_THRESHOLD
        self.max_age            = PLANT_MAX_AGE

        overrides = {
            "lily_pad":    dict(germ=0.7, mat=0.8, flow=0.9, age=0.8),
            "tube_sponge": dict(germ=1.3, mat=1.2, flow=1.3, age=1.5),
            "red_seaweed": dict(germ=0.8, mat=0.9, flow=0.85, age=1.0),
            "anemone":     dict(germ=0.6, mat=0.7, flow=0.8,  age=0.9),
            "fan_coral":   dict(germ=1.1, mat=1.1, flow=1.2,  age=1.3),
        }
        if self.plant_type in overrides:
            o = overrides[self.plant_type]
            self.germination_energy *= o["germ"]
            self.maturity_energy    *= o["mat"]
            self.flowering_energy   *= o["flow"]
            self.max_age            *= o["age"]

        segs = {
            "kelp": 14, "seagrass": 10, "algae": 6,
            "red_seaweed": 12, "tube_sponge": 8,
            "fan_coral": 16, "anemone": 6, "lily_pad": 1,
        }
        self._max_segments = segs.get(self.plant_type, 8)

    # ── Root-growth multiplier ────────────────────────────────────────────

    def get_root_growth_multiplier(self, energy, height):
        energy_factor = min(energy / 10.0, 2.0)
        height_factor = max(0.1, 1.0 - (height / 100.0))
        return energy_factor * height_factor

    # ── Main update ───────────────────────────────────────────────────────

    def update(self, dt, growth_nutrients, height_unused,
               photosynthesis_rate=0.0, season_index=0):
        """
        dt                  – seconds since last frame
        growth_nutrients    – nutrients harvested from roots this frame
        photosynthesis_rate – from TimeSystem (0..~1.2)
        season_index        – 0=Spring 1=Summer 2=Autumn 3=Winter
        """
        self.season_index = season_index
        self.time_in_stage += dt
        self.seed_cooldown  = max(0.0, self.seed_cooldown - dt)

        # ── Age rate ───────────────────────────────────────────────────────
        age_mult = _SEASON_AGE_RATE.get(season_index, 1.0)
        if self.stage == "dormant":
            age_mult *= 0.4               # age very slowly while dormant
        self.age += dt * age_mult

        # ── Photosynthesis & energy gain ───────────────────────────────────
        photo = photosynthesis_rate
        if season_index == 3:  # winter
            base_winter = WINTER_PHOTOSYNTHESIS_BASE
            hardy_bonus = WINTER_SURVIVAL_CHANCE.get(self.plant_type, 0.1)
            photo = base_winter * (0.5 + hardy_bonus * 1.5)
        photo *= _SEASON_PHOTO_MOD.get(season_index, 1.0)
        self.energy += photo * 1.2 * dt
        self.energy += growth_nutrients * 8.0 * dt

        # Maintenance
        maintenance = (PLANT_BASE_MAINTENANCE +
                       self.current_height * PLANT_SIZE_MAINTENANCE_FACTOR * 0.005)
        if season_index == 3:
            maintenance *= 1.6   # winter stress
        self.energy = max(0.0, self.energy - maintenance * dt)

        self._update_dimensions(dt, season_index)

        # ── Stage logic ────────────────────────────────────────────────────
        self._handle_seasonal_transitions(season_index)

        if self.stage == "seed":
            self._update_as_seed(dt)
        elif self.stage == "dormant":
            self._update_dormant(dt)
        elif self.stage == "germinating":
            if self.energy >= SEED_GROWTH_ENERGY * 0.9:
                self._transition("seedling")
        elif self.stage == "seedling":
            if self.energy >= MATURE_ENERGY_THRESHOLD:
                self._transition("mature")
            elif self.energy <= 0 and self.time_in_stage > 25:
                self._transition("dying")
        elif self.stage == "mature":
            self._try_enter_flowering(season_index)
            if self.age > PLANT_MAX_AGE * 0.95 or self.energy <= 0:
                self._transition("dying")
        elif self.stage == "flowering":
            if self.time_in_stage >= FLOWERING_DURATION or self.energy < 1.0:
                self._transition("dying")
        elif self.stage == "dying":
            if self.time_in_stage >= DECOMPOSITION_DURATION:
                self._transition("decomposing")

        return self.stage != "decomposing"

    def _handle_seasonal_transitions(self, season):
        if season == 3:  # Winter
            if self.stage in ("mature", "flowering") and not self._winter_roll_made:
                self._winter_roll_made = True
                if random.random() > WINTER_SURVIVAL_CHANCE.get(self.plant_type, 0.1):
                    self._transition("dying")
                else:
                    self._transition("dormant")
        elif season == 0 and self.stage == "dormant":  # Spring awakening
            if random.random() < 0.12 + 0.25 * self.traits.get("growth_rate_mult", 1.0):
                self._transition("germinating")

    def _update_as_seed(self, dt):
        # Seeds are dormant in winter
        season = self.season_index
        if season == 3:
            return
        # Spring boost
        germ_chance = 0.008
        if season == 0:
            germ_chance *= SPRING_GERMINATION_BOOST
        if self.energy > 0.8 and random.random() < germ_chance * 60 * dt:
            self._transition("germinating")

    def _update_dormant(self, dt):
        # Very slow energy drain + tiny photosynthesis
        self.energy = max(0.1, self.energy - 0.008 * dt)

    def _try_enter_flowering(self, season):
        if self._has_flowered:
            return
        pref = FLOWERING_SEASON_PREFERENCE.get(season, 0.0)
        if pref <= 0:
            return
        if (self.energy >= FLOWERING_ENERGY_THRESHOLD and
            random.random() < 0.007 * pref):
            self._transition("flowering")

    def _transition(self, new_stage):
        self.stage         = new_stage
        self.time_in_stage = 0.0
        self.is_mature     = self.stage in ("mature", "flowering")
        self.is_flowering  = self.stage == "flowering"
        if new_stage == "flowering":
            self._has_flowered = True

    # ── Physical dimensions ───────────────────────────────────────────────

    def _update_dimensions(self, dt, season_index):
        stage_frac = {
            "germinating": 0.05,
            "seedling":    0.30,
            "mature":      1.00,
            "flowering":   1.00,
            "dying":       0.70,
            "decomposing": 0.40,
        }.get(self.stage, 1.0)

        if season_index == 3:   # winter stunts growth
            stage_frac *= 0.75

        height_factor        = self.traits.get("max_height_factor", 1.0)
        max_h                = getattr(self, "_max_height_ref", 80.0) * height_factor
        self.target_height   = max(3.0, max_h * stage_frac)
        self.target_segments = max(1.0, self._max_segments * min(1.0, stage_frac * 1.2))

        grow_speed = 12.0 * dt
        if self.current_height < self.target_height:
            self.current_height = min(self.target_height,
                                      self.current_height + grow_speed)
        else:
            self.current_height = max(self.target_height,
                                      self.current_height - grow_speed * 0.3)

        seg_speed = 2.0 * dt
        if self.current_segments < self.target_segments:
            self.current_segments = min(self.target_segments,
                                        self.current_segments + seg_speed)
        else:
            self.current_segments = max(self.target_segments,
                                        self.current_segments - seg_speed * 0.5)

        if self.plant_type == "seagrass":
            target_blades = self.total_blades * stage_frac
            if self.current_height > 5:
                self.visible_blades = min(target_blades,
                                          self.visible_blades + seg_speed * 0.5)
            else:
                self.visible_blades = max(0.0,
                                          self.visible_blades - seg_speed * 0.3)

    # ── Seed production ───────────────────────────────────────────────────

    def can_produce_seed(self, seed_dispersal_modifier, season_index):
        """
        Returns True (and consumes energy + resets cooldown) if a seed should
        be released right now.

        Called once per frame per plant from PlantManager.
        Very low base probability ensures seeds are rare events, not a spam.
        """
        if not _SEASON_CAN_SEED.get(season_index, True):
            return False
        if self.stage not in ("mature", "flowering"):
            return False
        if self.seed_cooldown > 0:
            return False

        # Base per-frame probability
        # ~0.0015/frame * 60fps ≈ once per ~11 s before modifiers
        base_p = 0.0015
        if self.stage == "flowering":
            base_p *= 4.0   # flowering is peak seeding time

        if random.random() > base_p * seed_dispersal_modifier:
            return False

        # Energy gate — seeding is expensive
        energy_cost = 2.5
        if self.energy < energy_cost:
            return False

        self.energy       -= energy_cost
        self.seed_cooldown = _SEASON_SEED_COOLDOWN.get(season_index, 20.0)
        return True

    # ── Decomposition ─────────────────────────────────────────────────────

    def get_decomposition_return(self):
        return DECOMPOSITION_NUTRIENT_RETURN if self.stage == "decomposing" else 0.0
