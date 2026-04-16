"""Heritable traits for fish - expanded to include physical performance and appearance"""

import random
from ..config import MUTATION_RATE, MUTATION_STRENGTH


# ── Appearance Trait Enums ─────────────────────────────────────────────────────

# Body shapes: affects fish silhouette
BODY_SHAPE_STREAMLINED = 0  # Long, thin body
BODY_SHAPE_STANDARD = 1     # Balanced proportions
BODY_SHAPE_ROUNDED = 2      # Short, round body

# Fin styles
FIN_STYLE_MINIMAL = 0       # Small, subtle fins
FIN_STYLE_STANDARD = 1      # Normal fins
FIN_STYLE_ELEGANT = 2       # Long, flowing fins
FIN_STYLE_DRAMATIC = 3      # Large, showy fins

# Tail shapes
TAIL_POINTED = 0            # Sharp, angular tail
TAIL_FORKED = 1             # Split tail (like tuna)
TAIL_ROUNDED = 2            # Soft, rounded tail
TAIL_LYRE = 3               # Elegant curved tail

# Pattern types
PATTERN_SOLID = 0           # Single color
PATTERN_STRIPES = 1         # Horizontal stripes
PATTERN_SPOTS = 2           # Polka dot pattern
PATTERN_GRADIENT = 3        # Color fade from head to tail
PATTERN_BANDS = 4           # Vertical bands
PATTERN_MARBLED = 5         # Swirly, organic pattern


class FishTraits:
    """Heritable traits container including color, physical attributes, and appearance"""

    def __init__(self, color_offset=None, physical_traits=None, appearance_traits=None):
        if color_offset is None:
            # Random initial variation around base species color
            self.color_offset = (
                random.uniform(-60, 80),  # R: can be darker or brighter
                random.uniform(-50, 50),  # G: variation in yellow/orange tone
                random.uniform(-80, 40),  # B: usually less blue, but some variation
            )
        else:
            self.color_offset = color_offset

        if physical_traits is None:
            # Baseline performance traits (1.0 is species average)
            self.physical_traits = {
                "max_speed_mult": random.uniform(0.9, 1.1),
                "stamina_mult": random.uniform(0.9, 1.1),
                "turn_rate_mult": random.uniform(0.9, 1.1),
                "metabolism_mult": random.uniform(
                    0.9, 1.1
                ),  # High metabolism = faster but hungrier
                "size_mult": random.uniform(0.9, 1.1),
                "lifespan_mult": random.uniform(0.9, 1.1),
            }
        else:
            self.physical_traits = physical_traits

        # ── NEW: Appearance Traits ──────────────────────────────────────────
        if appearance_traits is None:
            self.appearance_traits = self._random_appearance()
        else:
            self.appearance_traits = appearance_traits

    def _random_appearance(self):
        """Generate random appearance traits for a new fish"""
        return {
            # Body shape: 0=streamlined, 1=standard, 2=rounded
            "body_shape": random.choice([BODY_SHAPE_STREAMLINED, BODY_SHAPE_STANDARD, BODY_SHAPE_ROUNDED]),
            
            # Body proportions
            "body_length_mult": random.uniform(0.85, 1.25),  # How elongated the body is
            "body_width_mult": random.uniform(0.75, 1.30),   # How wide/flat the body is
            "head_size_mult": random.uniform(0.80, 1.20),    # Head proportional size
            
            # Fin configuration
            "fin_style": random.choice([FIN_STYLE_MINIMAL, FIN_STYLE_STANDARD, FIN_STYLE_ELEGANT, FIN_STYLE_DRAMATIC]),
            "dorsal_fin_size": random.uniform(0.5, 1.5),      # Size of top fin
            "pectoral_fin_size": random.uniform(0.6, 1.4),    # Size of side fins
            "anal_fin_size": random.uniform(0.4, 1.3),        # Size of bottom fin
            
            # Tail configuration  
            "tail_shape": random.choice([TAIL_POINTED, TAIL_FORKED, TAIL_ROUNDED, TAIL_LYRE]),
            "tail_size_mult": random.uniform(0.7, 1.4),       # Overall tail size
            "tail_spread": random.uniform(0.6, 1.3),          # How wide the tail spreads
            
            # Pattern and coloration
            "pattern_type": random.choice([PATTERN_SOLID, PATTERN_STRIPES, PATTERN_SPOTS, 
                                           PATTERN_GRADIENT, PATTERN_BANDS, PATTERN_MARBLED]),
            "pattern_intensity": random.uniform(0.3, 1.0),    # How visible the pattern is
            "pattern_scale": random.uniform(0.5, 1.5),        # Size of pattern elements
            "pattern_density": random.uniform(0.3, 0.8),      # How many pattern elements
            
            # Secondary color (for patterns)
            "secondary_color_offset": (
                random.uniform(-80, 80),
                random.uniform(-60, 60),
                random.uniform(-60, 80),
            ),
            
            # Eye variation
            "eye_size_mult": random.uniform(0.8, 1.3),
            "eye_position": random.uniform(-0.1, 0.1),        # Slight forward/back variation
            
            # Scale/shine effects
            "scale_shine": random.uniform(0.0, 0.8),          # How glossy the fish appears
            "iridescence": random.uniform(0.0, 0.5),          # Color-shifting effect
            
            # Additional fins
            "has_barbels": random.random() < 0.15,            # Whisker-like appendages
            "barbel_length": random.uniform(0.3, 0.8),
            
            # Body features
            "belly_curve": random.uniform(-0.2, 0.3),         # Convex/concave belly
            "snout_length": random.uniform(0.8, 1.2),         # Pointed vs blunt face
        }

    @staticmethod
    def blend(parent1_traits, parent2_traits):
        """Blend traits from two parents with slight mutation"""
        # Blend Color
        p1_c = parent1_traits.color_offset
        p2_c = parent2_traits.color_offset
        blend_factor = random.uniform(0.3, 0.7)

        child_offset = tuple(
            p1_c[i] * blend_factor + p2_c[i] * (1 - blend_factor) for i in range(3)
        )

        # Apply color mutation
        mutated_color = []
        for val in child_offset:
            if random.random() < MUTATION_RATE:
                change = random.uniform(-MUTATION_STRENGTH * 40, MUTATION_STRENGTH * 40)
                val = max(-100, min(100, val + change))
            mutated_color.append(val)

        # Blend Physical Traits
        p1_p = parent1_traits.physical_traits
        p2_p = parent2_traits.physical_traits
        child_phys = {}

        for key in p1_p:
            # Random inheritance from either parent
            val = p1_p[key] if random.random() < 0.5 else p2_p[key]

            # Mutation
            if random.random() < MUTATION_RATE:
                change = random.uniform(
                    -MUTATION_STRENGTH * 0.2, MUTATION_STRENGTH * 0.2
                )
                val = max(0.5, min(1.8, val + change))
            child_phys[key] = val

        # ── NEW: Blend Appearance Traits ───────────────────────────────────
        p1_a = parent1_traits.appearance_traits
        p2_a = parent2_traits.appearance_traits
        child_appearance = {}

        # Discrete traits: pick from one parent or mutate
        discrete_traits = ["body_shape", "fin_style", "tail_shape", "pattern_type"]
        for key in discrete_traits:
            if random.random() < MUTATION_RATE * 0.5:
                # Mutation: pick random value
                if key == "body_shape":
                    child_appearance[key] = random.choice([BODY_SHAPE_STREAMLINED, BODY_SHAPE_STANDARD, BODY_SHAPE_ROUNDED])
                elif key == "fin_style":
                    child_appearance[key] = random.choice([FIN_STYLE_MINIMAL, FIN_STYLE_STANDARD, FIN_STYLE_ELEGANT, FIN_STYLE_DRAMATIC])
                elif key == "tail_shape":
                    child_appearance[key] = random.choice([TAIL_POINTED, TAIL_FORKED, TAIL_ROUNDED, TAIL_LYRE])
                elif key == "pattern_type":
                    child_appearance[key] = random.choice([PATTERN_SOLID, PATTERN_STRIPES, PATTERN_SPOTS, 
                                                           PATTERN_GRADIENT, PATTERN_BANDS, PATTERN_MARBLED])
            else:
                # Inherit from one parent
                child_appearance[key] = p1_a[key] if random.random() < 0.5 else p2_a[key]

        # Continuous traits: blend with potential mutation
        continuous_traits = [
            "body_length_mult", "body_width_mult", "head_size_mult",
            "dorsal_fin_size", "pectoral_fin_size", "anal_fin_size",
            "tail_size_mult", "tail_spread",
            "pattern_intensity", "pattern_scale", "pattern_density",
            "eye_size_mult", "eye_position",
            "scale_shine", "iridescence",
            "belly_curve", "snout_length", "barbel_length"
        ]
        
        for key in continuous_traits:
            blend = random.uniform(0.3, 0.7)
            val = p1_a[key] * blend + p2_a[key] * (1 - blend)
            
            # Apply mutation
            if random.random() < MUTATION_RATE:
                change = random.uniform(-MUTATION_STRENGTH * 0.15, MUTATION_STRENGTH * 0.15)
                val = max(0.3, min(1.8, val + change))
            
            child_appearance[key] = val

        # Secondary color: special blending
        sec_color = tuple(
            p1_a["secondary_color_offset"][i] * 0.5 + p2_a["secondary_color_offset"][i] * 0.5
            for i in range(3)
        )
        if random.random() < MUTATION_RATE:
            sec_color = tuple(
                max(-100, min(100, sec_color[i] + random.uniform(-30, 30)))
                for i in range(3)
            )
        child_appearance["secondary_color_offset"] = sec_color

        # Boolean traits
        if random.random() < MUTATION_RATE * 0.3:
            child_appearance["has_barbels"] = random.random() < 0.15
        else:
            child_appearance["has_barbels"] = p1_a["has_barbels"] if random.random() < 0.5 else p2_a["has_barbels"]

        return FishTraits(tuple(mutated_color), child_phys, child_appearance)

    def mutate(self):
        """Returns a mutated version of these traits (for asexual or single-parent legacy logic)"""
        return FishTraits.blend(self, self)

    # ── Appearance accessor methods ─────────────────────────────────────────

    def get_body_proportions(self):
        """Return body width/height ratio based on body shape"""
        base = {
            BODY_SHAPE_STREAMLINED: (1.4, 0.7),   # Long and thin
            BODY_SHAPE_STANDARD: (1.0, 1.0),      # Balanced
            BODY_SHAPE_ROUNDED: (0.7, 1.3),       # Short and round
        }
        w, h = base.get(self.appearance_traits["body_shape"], (1.0, 1.0))
        return (
            w * self.appearance_traits["body_length_mult"],
            h * self.appearance_traits["body_width_mult"]
        )

    def get_fin_config(self):
        """Return fin sizes adjusted by fin style"""
        style_mult = {
            FIN_STYLE_MINIMAL: 0.5,
            FIN_STYLE_STANDARD: 1.0,
            FIN_STYLE_ELEGANT: 1.3,
            FIN_STYLE_DRAMATIC: 1.6,
        }
        mult = style_mult.get(self.appearance_traits["fin_style"], 1.0)
        
        return {
            "dorsal": self.appearance_traits["dorsal_fin_size"] * mult,
            "pectoral": self.appearance_traits["pectoral_fin_size"] * mult,
            "anal": self.appearance_traits["anal_fin_size"] * mult,
        }

    def get_tail_config(self):
        """Return tail configuration"""
        return {
            "shape": self.appearance_traits["tail_shape"],
            "size": self.appearance_traits["tail_size_mult"],
            "spread": self.appearance_traits["tail_spread"],
        }

    def get_pattern_config(self):
        """Return pattern configuration"""
        return {
            "type": self.appearance_traits["pattern_type"],
            "intensity": self.appearance_traits["pattern_intensity"],
            "scale": self.appearance_traits["pattern_scale"],
            "density": self.appearance_traits["pattern_density"],
        }
