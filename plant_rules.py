"""Plant rules and validation logic shared between plants and seeds modules."""

from config import (
    KELP_DEPTH_MAX,
    SEAGRASS_DEPTH_MIN,
    SEAGRASS_DEPTH_MAX,
    ALGAE_DEPTH_MIN,
    RED_SEAWEED_DEPTH_MIN,
    RED_SEAWEED_DEPTH_MAX,
    LILY_PAD_DEPTH_MAX,
    TUBE_SPONGE_DEPTH_MIN,
    TUBE_SPONGE_DEPTH_MAX,
    FAN_CORAL_DEPTH_MIN,
    FAN_CORAL_DEPTH_MAX,
    ANEMONE_DEPTH_MIN,
    ANEMONE_DEPTH_MAX,
)


def is_valid_depth(plant_type, depth_ratio):
    """Check if a plant type can grow at the given depth ratio.

    Args:
        plant_type: String identifier for the plant type (e.g., "kelp", "seagrass")
        depth_ratio: Float between 0 and 1 representing depth (0 = surface, 1 = bottom)

    Returns:
        bool: True if the plant can grow at this depth, False otherwise
    """
    rules = {
        "kelp": lambda d: d <= KELP_DEPTH_MAX,
        "seagrass": lambda d: SEAGRASS_DEPTH_MIN <= d <= SEAGRASS_DEPTH_MAX,
        "algae": lambda d: d >= ALGAE_DEPTH_MIN,
        "red_seaweed": lambda d: RED_SEAWEED_DEPTH_MIN <= d <= RED_SEAWEED_DEPTH_MAX,
        "lily_pad": lambda d: d <= LILY_PAD_DEPTH_MAX,
        "tube_sponge": lambda d: TUBE_SPONGE_DEPTH_MIN <= d <= TUBE_SPONGE_DEPTH_MAX,
        "fan_coral": lambda d: FAN_CORAL_DEPTH_MIN <= d <= FAN_CORAL_DEPTH_MAX,
        "anemone": lambda d: ANEMONE_DEPTH_MIN <= d <= ANEMONE_DEPTH_MAX,
    }
    return rules.get(plant_type, lambda d: True)(depth_ratio)
