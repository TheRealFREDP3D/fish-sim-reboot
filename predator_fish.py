"""Predator Fish - High-speed hunters with dash capabilities"""

import math
from fish_base import NeuralFish, get_life_stage_size_mult
from config import *
from config import PREDATOR_SIZE_ADVANTAGE_MULTIPLIER, PREY_PREDATOR_MIN_DISTANCE


class PredatorFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None):
        super().__init__(world, traits=traits, brain=brain)
        self.is_predator = True
        self.physics.max_speed *= PREDATOR_SPEED_MULT

        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.mate = None

    def _get_viable_prey(self, all_fish):
        """Return prey fish that are strictly smaller than this predator."""
        my_size = self.get_current_size_mult()
        prey = []
        for f in all_fish:
            if f.is_predator or f.is_hidden:
                continue
            prey_size = f.get_current_size_mult()
            # Predator must be meaningfully larger — at least 20% bigger or same size
            if my_size >= prey_size * PREDATOR_SIZE_ADVANTAGE_MULTIPLIER:
                prey.append(f)
        return prey

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        # Seasonal activity scaling (slower in winter)
        activity_mod = time_system.predator_activity_modifier if time_system else 1.0

        # Only hunt when hungry — same hunger threshold as other fish
        is_hungry = self.energy < FISH_HUNGER_THRESHOLD

        # Only target prey that are smaller than the predator
        prey_targets = self._get_viable_prey(all_fish) if is_hungry else []

        closest_prey = None
        min_dist = PREY_PREDATOR_MIN_DISTANCE
        for prey in prey_targets:
            dist = self.physics.pos.distance_to(prey.physics.pos)
            if dist < min_dist:
                min_dist = dist
                closest_prey = prey

        if closest_prey and is_hungry:
            seek_force = self.physics.seek(
                closest_prey.physics.pos.x,
                closest_prey.physics.pos.y,
                weight=0.9 * activity_mod,
            )
            self.physics.apply_force(seek_force)

            if (
                min_dist < 150
                and self.dash_cooldown <= 0
                and not self.is_dashing
                and self.stamina > PREDATOR_DASH_STAMINA_THRESHOLD
                and activity_mod > 0.5  # no dashing in deep winter
            ):
                self.is_dashing = True
                self.dash_timer = PREDATOR_DASH_DURATION
                self.dash_cooldown = PREDATOR_DASH_COOLDOWN

        if self.is_dashing:
            self.dash_timer -= dt
            self.stamina = max(0.0, self.stamina - PREDATOR_DASH_STAMINA_DRAIN * dt)

            if self.stamina <= 0:
                self.is_dashing = False
            else:
                dash_force = self.physics.max_force * PREDATOR_DASH_FORCE_MULT
                self.physics.apply_force(
                    (
                        math.cos(self.physics.heading) * dash_force,
                        math.sin(self.physics.heading) * dash_force,
                    )
                )

            if self.dash_timer <= 0:
                self.is_dashing = False

        self.dash_cooldown = max(0, self.dash_cooldown - dt)

        res = super().update(
            dt,
            all_fish,
            prey_targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )

        # Eating on collision — only viable (smaller) prey
        if is_hungry:
            for prey in prey_targets:
                collision_radius = 20 * self.get_current_size_mult()
                dist = math.hypot(
                    self.physics.pos.x - prey.physics.pos.x,
                    self.physics.pos.y - prey.physics.pos.y,
                )
                if dist < collision_radius:
                    prey.energy = 0
                    self.energy = min(FISH_MAX_ENERGY, self.energy + 25.0)
                    break

        return res

    def try_reproduce(self):
        """Called by FishSystem.update in its dedicated predator reproduction block."""
        if (
            not self.is_mature
            or self.energy < FISH_MATING_THRESHOLD
            or self.mating_cooldown > 0
        ):
            return False

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
                    self.mate = partner
                    self.energy -= FISH_REPRODUCTION_COST
                    partner.energy -= FISH_REPRODUCTION_COST
                    self.mating_cooldown = 40.0
                    partner.mating_cooldown = 40.0
                    return True

        return False
