"""Predator Fish - High-speed hunters with dash capabilities"""

import pygame
import math
import random
from fish import NeuralFish, FishState
from config import *


class PredatorFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None):
        super().__init__(world, traits=traits, brain=brain)
        self.is_predator = True
        self.physics.max_speed *= PREDATOR_SPEED_MULT

        # Dash mechanics
        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        # 1. Target Selection (Hunt other fish)
        prey_targets = [f for f in all_fish if not f.is_predator and not f.is_hidden]

        closest_prey = None
        min_dist = 400

        for prey in prey_targets:
            dist = math.hypot(
                self.physics.pos.x - prey.physics.pos.x,
                self.physics.pos.y - prey.physics.pos.y,
            )
            if dist < min_dist:
                min_dist = dist
                closest_prey = prey

        # 2. Hunting & Dashing Logic
        if closest_prey:
            # Move toward prey
            seek_force = self.physics.seek(
                closest_prey.physics.pos.x, closest_prey.physics.pos.y, weight=1.2
            )
            self.physics.apply_force(seek_force)

            # Trigger Dash if close enough and off cooldown
            if min_dist < 150 and self.dash_cooldown <= 0 and not self.is_dashing:
                self.is_dashing = True
                self.dash_timer = PREDATOR_DASH_DURATION
                self.dash_cooldown = PREDATOR_DASH_COOLDOWN

        # 3. Handle Dash State
        if self.is_dashing:
            self.dash_timer -= dt
            # Apply dash multiplier
            self.physics.apply_force(
                (
                    math.cos(self.physics.heading) * self.physics.max_force * 2,
                    math.sin(self.physics.heading) * self.physics.max_force * 2,
                )
            )
            if self.dash_timer <= 0:
                self.is_dashing = False

        self.dash_cooldown = max(0, self.dash_cooldown - dt)

        # 4. Standard Update (Energy, Aging, etc.)
        # We pass an empty list for 'targets' because predators don't eat poop
        res = super().update(dt, all_fish, [], particle_system, plant_manager)

        # 5. Eating Logic (Collision with prey)
        for prey in prey_targets:
            dist = math.hypot(
                self.physics.pos.x - prey.physics.pos.x,
                self.physics.pos.y - prey.physics.pos.y,
            )
            if dist < 20:  # Kill distance
                prey.energy = 0
                self.energy = min(FISH_MAX_ENERGY, self.energy + 25.0)
                break

        return res
