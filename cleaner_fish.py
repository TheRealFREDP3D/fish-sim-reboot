"""Cleaner Fish - Specialized behavior including hiding near roots"""
import pygame
import math
import random
from fish import NeuralFish, FishState
from config import CLEANER_FISH_SPEED_MULT

class CleanerFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None):
        super().__init__(world, traits=traits, brain=brain, is_cleaner=True)
        self.physics.max_speed *= CLEANER_FISH_SPEED_MULT

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        # Cleaner fish logic: Inherits state logic from NeuralFish
        # but specifically targets poop particles ('targets' here)
        res = super().update(dt, all_fish, targets, particle_system, plant_manager)
        return res
