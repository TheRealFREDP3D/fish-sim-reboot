"""Configuration settings for the Underwater Plant Ecosystem Simulation"""

from enum import Enum, auto

# Screen settings
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
WORLD_WIDTH = 4000
WORLD_HEIGHT = 1200
FPS = 60
TITLE = "Fish Simulation - Reboot"

# Camera settings
CAMERA_SMOOTHING = 0.1

# Particles
PARTICLE_COUNT = 180
SEDIMENT_COUNT = 120
PLANKTON_COUNT = 60  # reduced — plants now top this up dynamically
PARTICLE_MIN_SIZE = 1
PARTICLE_MAX_SIZE = 4
PARTICLE_MIN_SPEED = 0.1
PARTICLE_MAX_SPEED = 0.5
SEDIMENT_COLOR = (180, 160, 140)
PLANKTON_COLOR = (100, 200, 100)  # fallback only — individual colors set per particle
PARTICLE_ALPHA = 90

# Plankton color palette — varied microorganism hues
PLANKTON_COLORS = [
    (80, 200, 120),   # green algae
    (60, 210, 180),   # cyan diatom
    (160, 220, 80),   # yellow-green
    (100, 180, 220),  # blue phytoplankton
    (200, 160, 80),   # golden dinoflagellate
    (180, 90, 180),   # pink/purple cryptophyte
    (60, 190, 140),   # teal cyanobacteria
    (220, 200, 60),   # yellow diatom
]

# Plankton size (half of previous values)
PLANKTON_BASE_RADIUS_MIN = 1.5  # was ~3
PLANKTON_BASE_RADIUS_MAX = 3.5  # was ~6.5

# Visual effects
LIGHT_RAY_COUNT = 10
LIGHT_RAY_ALPHA = 40
LIGHT_RAY_COLOR = (200, 230, 255)
BUBBLE_CHANCE = 0.003
BUBBLE_COLOR = (200, 230, 255)

# Soil settings
SOIL_CELL_SIZE = 12
SOIL_BASE_NUTRIENT = 0.9
SOIL_SURFACE_BONUS = 0.25
SOIL_DEPLETED_COLOR = (85, 80, 75)
SOIL_FERTILE_COLOR = (110, 70, 45)
SOIL_SOLIDIFY_THRESHOLD = 0.4
SOIL_MAX_NUTRIENT = 1.5

# Terrain zones
WATER_LINE_Y = 150
BEACH_SLOPE_END = 200
STEEP_DROP_END = 400
TERRAIN_BASE_HEIGHT = 700

# Colors - Environment
SKY_COLOR = (152, 219, 249)
BEACH_COLOR = (235, 210, 170)
TERRAIN_COLOR = (60, 50, 45)
TERRAIN_DARK_COLOR = (45, 35, 30)
WATER_SURFACE_COLOR = (80, 170, 210)
WATER_DEEP_COLOR = (15, 40, 80)
HAZE_COLOR = (20, 50, 90)

# ── Plant species — ORIGINAL ──────────────────────────────────────────────────
KELP_HEIGHT_MIN = 100
KELP_HEIGHT_MAX = 200
KELP_SEGMENTS = 14
KELP_SWAY_SPEED = 1.2
KELP_SWAY_AMPLITUDE = 20
KELP_COLOR = (45, 110, 45)
KELP_HIGHLIGHT = (80, 160, 80)
KELP_WIDTH = 6
KELP_DEPTH_MAX = 0.40

SEAGRASS_HEIGHT_MIN = 40
SEAGRASS_HEIGHT_MAX = 90
SEAGRASS_SEGMENTS = 10
SEAGRASS_SWAY_SPEED = 2.2
SEAGRASS_SWAY_AMPLITUDE = 12
SEAGRASS_COLOR = (60, 170, 60)
SEAGRASS_HIGHLIGHT = (120, 220, 120)
SEAGRASS_WIDTH = 3
SEAGRASS_DEPTH_MIN = 0.20
SEAGRASS_DEPTH_MAX = 0.70

ALGAE_HEIGHT_MIN = 15
ALGAE_HEIGHT_MAX = 60
ALGAE_SEGMENTS = 5
ALGAE_SWAY_SPEED = 2.8
ALGAE_SWAY_AMPLITUDE = 6
ALGAE_COLOR = (30, 80, 30)
ALGAE_HIGHLIGHT = (60, 120, 60)
ALGAE_WIDTH = 4
ALGAE_DEPTH_MIN = 0.60

# ── Plant species — NEW ───────────────────────────────────────────────────────
RED_SEAWEED_HEIGHT_MIN = 80
RED_SEAWEED_HEIGHT_MAX = 160
RED_SEAWEED_SEGMENTS = 12
RED_SEAWEED_SWAY_SPEED = 0.8
RED_SEAWEED_SWAY_AMPLITUDE = 15
RED_SEAWEED_COLOR = (140, 40, 40)
RED_SEAWEED_HIGHLIGHT = (200, 80, 80)
RED_SEAWEED_WIDTH = 8
RED_SEAWEED_DEPTH_MIN = 0.50
RED_SEAWEED_DEPTH_MAX = 0.95
RED_SEAWEED_GLOW_INTENSITY = 1.5

LILY_PAD_SIZE_MIN = 30
LILY_PAD_SIZE_MAX = 60
LILY_PAD_COLOR = (50, 120, 50)
LILY_PAD_HIGHLIGHT = (80, 180, 80)
LILY_PAD_FLOWER_COLOR = (255, 200, 220)
LILY_PAD_DEPTH_MAX = 0.15
LILY_PAD_SPREAD_RATE = 0.3
LILY_PAD_ROOT_DEPTH = 3

TUBE_SPONGE_HEIGHT_MIN = 50
TUBE_SPONGE_HEIGHT_MAX = 120
TUBE_SPONGE_SEGMENTS = 8
TUBE_SPONGE_COLOR = (180, 160, 120)
TUBE_SPONGE_HIGHLIGHT = (220, 200, 160)
TUBE_SPONGE_WIDTH = 14
TUBE_SPONGE_DEPTH_MIN = 0.30
TUBE_SPONGE_DEPTH_MAX = 0.80
TUBE_SPONGE_FILTER_RATE = 0.15

FAN_CORAL_HEIGHT_MIN = 40
FAN_CORAL_HEIGHT_MAX = 100
FAN_CORAL_SEGMENTS = 16
FAN_CORAL_SWAY_SPEED = 1.5
FAN_CORAL_SWAY_AMPLITUDE = 25
FAN_CORAL_COLOR = (200, 100, 150)
FAN_CORAL_HIGHLIGHT = (255, 150, 200)
FAN_CORAL_WIDTH = 2
FAN_CORAL_DEPTH_MIN = 0.40
FAN_CORAL_DEPTH_MAX = 0.90
FAN_CORAL_BRANCH_FACTOR = 0.7

ANEMONE_HEIGHT_MIN = 20
ANEMONE_HEIGHT_MAX = 45
ANEMONE_TENTACLES = 12
ANEMONE_SWAY_SPEED = 3.5
ANEMONE_COLOR = (100, 50, 150)
ANEMONE_GLOW_COLOR = (150, 100, 255)
ANEMONE_HIGHLIGHT = (180, 130, 255)
ANEMONE_WIDTH = 3
ANEMONE_DEPTH_MIN = 0.25
ANEMONE_DEPTH_MAX = 0.60
ANEMONE_PULSE_SPEED = 2.0
ANEMONE_ATTRACT_RADIUS = 80

# ── Root system ───────────────────────────────────────────────────────────────
ROOT_BASE_THICKNESS = 5
ROOT_BASE_GROWTH_RATE = 0.6
ROOT_MAX_NODES = 120
ROOT_MAX_DEPTH = 35
ROOT_BRANCH_CHANCE = 0.15
ROOT_UPTAKE_CAPACITY = 0.02
ROOT_TRANSPORT_LOSS = 0.005
ROOT_BASE_COLOR = (130, 100, 80)
ROOT_ACTIVE_COLOR = (210, 170, 110)
ROOT_TIP_COLOR = (255, 220, 150)
ROOT_ENERGY_HUNGRY_THRESHOLD = 5.0
ROOT_HIGH_ENERGY_SLOWDOWN = 15.0
ROOT_MAX_GROWTH_MULTIPLIER = 3.5

# ── Plant lifecycle ───────────────────────────────────────────────────────────
SEED_GROWTH_ENERGY = 1.0
MATURE_ENERGY_THRESHOLD = 3.5
PLANT_BASE_MAINTENANCE = 0.12  # reduced from 0.15 for better longevity
PLANT_SIZE_MAINTENANCE_FACTOR = 0.35
PLANT_MAX_AGE = 70.0  # increased from 60.0
SEED_PRODUCTION_ENERGY = 5.5
SEED_PRODUCTION_COST = 2.0  # reduced from 3.0 — seeding less costly
FLOWERING_ENERGY_THRESHOLD = 6.0  # reduced from 7.0 — easier to flower
FLOWERING_DURATION = 14.0  # slightly longer flowering window
DECOMPOSITION_NUTRIENT_RETURN = 0.8
DECOMPOSITION_DURATION = 8.0

# ── Plant population caps ─────────────────────────────────────────────────────
PLANT_HARD_CAP = 60
SEED_HARD_CAP = 60  # increased from 40 — allow more seeds to accumulate

# ── Plankton spawning from plants ─────────────────────────────────────────────
PLANKTON_PER_PLANT_CHANCE = 0.012   # probability per mature plant per second
PLANKTON_HARD_CAP = 200             # max plankton alive at once
PLANKTON_SPAWN_SPREAD = 30          # px radius around plant tip

# ── Evolution settings ────────────────────────────────────────────────────────
MUTATION_RATE = 0.2
MUTATION_STRENGTH = 0.15

# ── Fish Physics ──────────────────────────────────────────────────────────────
FISH_MAX_FORCE = 4.5
FISH_MAX_SPEED = 140.0
FISH_DRAG = 0.96
FISH_MIN_SPEED = 15.0

FISH_TURN_RATE_SCALAR = 2.5
FISH_STEERING_FORCE_FACTOR = 0.35

FISH_SENSOR_RANGE = 250.0
FISH_SENSOR_ARC = 1.2
FISH_SENSORS_COUNT = 3

FISH_LARVA_DURATION = 12.0
FISH_JUVENILE_DURATION = 20.0
FISH_ADULT_DURATION = 150.0
FISH_ELDER_DURATION = 80.0
FISH_MAX_AGE = (
    FISH_LARVA_DURATION
    + FISH_JUVENILE_DURATION
    + FISH_ADULT_DURATION
    + FISH_ELDER_DURATION
)

CLEANER_FISH_SPEED_MULT = 0.85
CLEANER_FISH_CLEANING_ENERGY_THRESHOLD = 45.0
PREDATOR_SPEED_MULT = 0.95
PREDATOR_DASH_SPEED_MULT = 2.4
PREDATOR_DASH_DURATION = 0.8
PREDATOR_DASH_COOLDOWN = 3.5
PREDATOR_DASH_STAMINA_THRESHOLD = 20.0
PREDATOR_DASH_STAMINA_DRAIN = 30.0
PREDATOR_DASH_FORCE_MULT = 3.5

FISH_MAX_ENERGY = 50.0
FISH_HUNGER_THRESHOLD = 30.0
FISH_MATING_THRESHOLD = 35.0
FISH_REPRODUCTION_COST = 12.0
FISH_EGG_HATCH_TIME = 10.0

FISH_MAX_POPULATION = 40
CLEANER_FISH_MAX_POPULATION = 15
PREDATOR_MAX_POPULATION = 4


class FishState(Enum):
    RESTING = auto()
    HUNTING = auto()
    FLEEING = auto()
    MATING = auto()
    NESTING = auto()


BRAIN_PANEL_WIDTH = 420
BRAIN_PANEL_HEIGHT = 800

# ── Time & Season System ──────────────────────────────────────────────────────
DAY_DURATION = 120.0
SEASON_DURATION = DAY_DURATION * 7

# ── Named constants for magic numbers ────────────────────────────────────────
INFINITE_COOLDOWN = 999.0
GERMINATION_FAILURE_ENERGY_THRESHOLD = 0.5
GERMINATION_FAILURE_TIME = 60.0
SEEDLING_DEATH_TIME = 25.0
DORMANT_ENERGY_MINIMUM = 0.05
DORMANT_DEATH_TIME = 30.0
SPRING_GERMINATION_BASE_CHANCE = 0.015
SUMMER_GERMINATION_BASE_CHANCE = 0.006
SEED_ENERGY_THRESHOLD = 0.6
FLOWERING_BASE_CHANCE = 0.015
AUTUMN_SEED_BASE_PROBABILITY = 0.004
SUMMER_SEED_BASE_PROBABILITY = 0.001
SEED_ENERGY_COST = 2.0
PREDATOR_SIZE_ADVANTAGE_MULTIPLIER = 1.2
PREY_PREDATOR_MIN_DISTANCE = 400

# ── Mating display constants ──────────────────────────────────────────────────
MATING_HEART_SPAWN_INTERVAL = 1.2
MATING_HEART_RANDOM_RANGE = 0.6
MATING_GLOW_DECAY_RATE = 3.0

DAWN_START = 0.18
DAWN_END = 0.27
DUSK_START = 0.73
DUSK_END = 0.82

SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]

SEASON_COLORS = [
    (180, 240, 180),
    (255, 240, 160),
    (220, 160, 80),
    (160, 190, 230),
]

NIGHT_OVERLAY_COLOR = (5, 8, 25)

BIOLUM_COLORS = {
    "common": (180, 230, 255),
    "cleaner": (100, 255, 220),
    "predator": (255, 120, 120),
}

STAR_COUNT = 120
STAR_MAX_ALPHA = 200

# Keys 0 (Spring) and 1 (Summer) intentionally absent — they produce no particles.
# world.py uses .get(season_idx, 0.0) so missing keys safely default to 0.
SEASONAL_PARTICLE_CHANCE = {
    2: 0.004,  # Autumn — falling leaves
    3: 0.003,  # Winter — snow
}
LEAF_COLORS = [(180, 80, 20), (210, 130, 30), (160, 60, 10), (200, 160, 40)]
SNOW_COLOR = (220, 235, 255)

# ── Enhanced seasonal plant behavior ─────────────────────────────────────────
# Significantly raised survival chances so plants persist through winter
WINTER_SURVIVAL_CHANCE = {
    "kelp": 0.30,        # was 0.15
    "seagrass": 0.55,    # was 0.35
    "algae": 0.15,       # was 0.05
    "red_seaweed": 0.25, # was 0.10
    "lily_pad": 0.80,    # was 0.70
    "tube_sponge": 0.60, # was 0.45
    "fan_coral": 0.40,   # was 0.25
    "anemone": 0.70,     # was 0.60
}

SPRING_GERMINATION_BOOST = 4.0
WINTER_PHOTOSYNTHESIS_BASE = 0.08

# Flowering preferences per season (0=Spring, 1=Summer, 2=Autumn, 3=Winter)
# Summer now also has a moderate preference so plants can flower+seed in Summer too
FLOWERING_SEASON_PREFERENCE = {
    0: 0.3,  # Spring: rare flowering
    1: 1.4,  # Summer: good flowering (was 1.8 — still high but allows summer seeding)
    2: 1.0,  # Autumn: solid flowering (was 0.6)
    3: 0.0,  # Winter: none
}

_SEASON_AGE_RATE = {0: 0.8, 1: 0.7, 2: 1.2, 3: 2.0}
_SEASON_PHOTO_MOD = {0: 1.0, 1: 1.1, 2: 0.8, 3: 0.25}
# Allow seeding in Summer (1) and Autumn (2); not Spring (saves energy for growth) or Winter
_SEASON_CAN_SEED = {0: False, 1: True, 2: True, 3: False}
_SEASON_SEED_COOLDOWN = {0: INFINITE_COOLDOWN, 1: 30.0, 2: 10.0, 3: INFINITE_COOLDOWN}

# ── Fish-Plant Interaction Mechanics ─────────────────────────────────────────
PLANT_COVER_RADIUS = 85.0
PLANT_COVER_STRENGTH = {
    "kelp": 1.4,
    "seagrass": 1.1,
    "algae": 0.9,
    "red_seaweed": 1.2,
    "lily_pad": 1.6,
    "tube_sponge": 1.3,
    "fan_coral": 1.5,
    "anemone": 1.7,
}
PLANT_GRAZE_RANGE = 38.0
PLANT_GRAZE_ENERGY_GAIN = 7.5
PLANT_GRAZE_DAMAGE = 1.35
GRAZING_COOLDOWN = 3.8
GRAZING_VISUAL_DURATION = 2.5

FISH_PLANT_PREFERENCE = {
    False: {"seagrass": 1.6, "algae": 1.4, "kelp": 1.1},
    True: {"tube_sponge": 1.8, "anemone": 1.5, "fan_coral": 1.3},
}
