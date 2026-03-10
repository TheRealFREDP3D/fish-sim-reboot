"""Predator Fish - High-speed hunters with dash capabilities"""

import math
from fish import NeuralFish
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
        self.mate = None  # To satisfy FishSystem.update reproduction block

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        # 1. Target Selection (Hunt other fish)
        prey_targets = [f for f in all_fish if not f.is_predator and not f.is_hidden]

        closest_prey = None
        min_dist = 400

        for prey in prey_targets:
            dist = self.physics.pos.distance_to(prey.physics.pos)
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
        # We pass prey_targets into super().update so that the predator's radar reflects prey
        res = super().update(dt, all_fish, prey_targets, particle_system, plant_manager)

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

    def try_reproduce(self):
        """
        Custom reproduction logic for predators.
        Called by FishSystem.update in its dedicated predator reproduction block.
        """
        if (
            not self.is_mature
            or self.energy < FISH_MATING_THRESHOLD
            or self.mating_cooldown > 0
        ):
            return False

        # Scan world for a partner
        # FishSystem links itself to world.fish_system during init
        if not hasattr(self.world, "fish_system"):
            return False

        system = self.world.fish_system
        for partner in system.predators:
            if (
                partner != self
                and partner.is_mature
                and partner.sex != self.sex
                and partner.mating_cooldown <= 0
                and partner.energy > FISH_MATING_THRESHOLD
            ):
                dist = self.physics.pos.distance_to(partner.physics.pos)
                if dist < 50:
                    # Successful mating
                    self.mate = partner
                    self.energy -= FISH_REPRODUCTION_COST
                    partner.energy -= FISH_REPRODUCTION_COST
                    self.mating_cooldown = 40.0
                    partner.mating_cooldown = 40.0
                    return True

        return False
