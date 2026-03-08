"""Heritable traits for fish - expanded to include physical performance"""
import random
from config import MUTATION_RATE, MUTATION_STRENGTH

class FishTraits:
    """Heritable traits container including color and physical attributes"""
    def __init__(self, color_offset=None, physical_traits=None):
        if color_offset is None:
            # Random initial variation around base species color
            self.color_offset = (
                random.uniform(-60, 80),   # R: can be darker or brighter
                random.uniform(-50, 50),   # G: variation in yellow/orange tone
                random.uniform(-80, 40),   # B: usually less blue, but some variation
            )
        else:
            self.color_offset = color_offset
            
        if physical_traits is None:
            # Baseline performance traits (1.0 is species average)
            self.physical_traits = {
                "max_speed_mult": random.uniform(0.9, 1.1),
                "stamina_mult": random.uniform(0.9, 1.1),
                "turn_rate_mult": random.uniform(0.9, 1.1),
                "metabolism_mult": random.uniform(0.9, 1.1), # High metabolism = faster but hungrier
                "size_mult": random.uniform(0.9, 1.1),
                "lifespan_mult": random.uniform(0.9, 1.1)
            }
        else:
            self.physical_traits = physical_traits

    @staticmethod
    def blend(parent1_traits, parent2_traits):
        """Blend traits from two parents with slight mutation"""
        # Blend Color
        p1_c = parent1_traits.color_offset
        p2_c = parent2_traits.color_offset
        blend_factor = random.uniform(0.3, 0.7)
        
        child_offset = tuple(
            p1_c[i] * blend_factor + p2_c[i] * (1 - blend_factor)
            for i in range(3)
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
                change = random.uniform(-MUTATION_STRENGTH * 0.2, MUTATION_STRENGTH * 0.2)
                val = max(0.5, min(1.8, val + change))
            child_phys[key] = val
        
        return FishTraits(tuple(mutated_color), child_phys)
