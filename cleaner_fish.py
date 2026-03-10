import pygame
import math
from fish import NeuralFish, FishState
from config import CLEANER_FISH_SPEED_MULT


class CleanerFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None):
        # Initialize as a cleaner fish (affects base color and radar)
        super().__init__(world, traits=traits, brain=brain, is_cleaner=True)
        # Apply speed modifier from config
        self.physics.max_speed *= CLEANER_FISH_SPEED_MULT

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        """
        Specialized update:
        1. Inherits standard neural steering.
        2. Adds a specific 'cleaning' drive towards poop particles.
        3. Benefits from 'is_hidden' logic when near plants.
        """
        # 1. Sensory Check: Find the nearest poop (target)
        closest_poop = None
        min_dist = 200  # Cleaning detection range

        for poop in targets:
            dist = math.hypot(self.physics.pos.x - poop.x, self.physics.pos.y - poop.y)
            if dist < min_dist:
                min_dist = dist
                closest_poop = poop

        # 2. Apply "Cleaning" Steering Force
        if closest_poop and self.energy < 45:  # Only clean if not totally full
            # Seek the poop particle with high priority
            seek_force = self.physics.seek(closest_poop.x, closest_poop.y, weight=1.5)
            self.physics.apply_force(seek_force)

        # 3. Base Neural Logic
        # This handles energy decay, age, fleeing from predators, and neural steering
        res = super().update(dt, all_fish, targets, particle_system, plant_manager)

        # 4. Hiding Mechanic (Passive)
        # The base NeuralFish already sets self.is_hidden = True if near a plant.
        # This reduces their detection range for predators in NeuralFish.get_radar_inputs.

        return res
