"""
Cleaner Fish — Mutualistic symbiont with improved neural network integration.

Three behavioral pillars:
  1. Cleaning Mutualism (primary):   Approach client fish and clean them.
  2. Scavenging (secondary):          Opportunistically eat poop AND plankton.
  3. Cleaning Station Affinity:       Drift toward coral / anemone / sponge.

Improvements:
- Uses NN's clean_drive output (output 2) for behavior control
- Reduced hard-coded behavior in favor of learned responses
- Temporal context helps cleaners remember recent cleaning opportunities
"""

import math
import random
from fish_base import NeuralFish
from config import (
    CLEANER_FISH_SPEED_MULT,
    CLEANER_CLEANING_RANGE,
    CLEANER_CLEANING_DURATION,
    CLEANER_CLEANING_COOLDOWN,
    CLEANER_CLEANING_ENERGY_GAIN,
    CLIENT_STAMINA_GAIN,
    CLIENT_ENERGY_GAIN,
    CLEANER_IMMUNITY_CHANCE,
    CLEANER_STATION_PLANT_TYPES,
    CLEANER_STATION_RADIUS,
    CLEANER_STATION_SEEK_WEIGHT,
    CLEANER_POOP_SEEK_WEIGHT,
    CLEANER_CLIENT_SEEK_WEIGHT,
    FISH_MAX_ENERGY,
)


class CleanerFish(NeuralFish):
    """Cleaner fish with mutualistic cleaning behavior controlled by NN."""

    def __init__(self, world, traits=None, brain=None, start_x=None, start_y=None):
        super().__init__(
            world,
            traits=traits,
            brain=brain,
            is_cleaner=True,
            start_x=start_x,
            start_y=start_y,
        )
        self.physics.max_speed *= CLEANER_FISH_SPEED_MULT

        # Cleaning state
        self._cleaning_cooldown = random.uniform(0.0, CLEANER_CLEANING_COOLDOWN)
        self._is_actively_cleaning = False
        self._cleaning_target = None
        self._cleaning_timer = 0.0
        self._times_cleaned = 0

    def _find_best_client(self, all_fish):
        """Return the nearby non-predator fish that most needs cleaning."""
        best_client = None
        best_score = -1.0
        my_pos = self.physics.pos

        for fish in all_fish:
            if fish is self:
                continue
            if fish.is_predator or not fish.is_mature:
                continue
            if fish.is_cleaner:
                continue

            dist = my_pos.distance_to(fish.physics.pos)
            if dist > CLEANER_CLEANING_RANGE:
                continue

            need = getattr(fish, "needs_cleaning", 0.0)
            if need < 0.15:
                continue

            proximity_bonus = 1.0 - (dist / CLEANER_CLEANING_RANGE)
            score = need * 2.0 + proximity_bonus

            if score > best_score:
                best_score = score
                best_client = fish

        return best_client

    def _find_nearest_station(self, plant_manager):
        """Find the closest plant that serves as a cleaning station."""
        best_plant = None
        best_dist = CLEANER_STATION_RADIUS

        for plant in plant_manager.plants:
            if plant.plant_type not in CLEANER_STATION_PLANT_TYPES:
                continue
            dist = self.physics.pos.distance_to((plant.x, plant.base_y))
            if dist < best_dist:
                best_dist = dist
                best_plant = plant

        return best_plant

    def _find_nearest_poop(self, poops):
        """Find the nearest poop particle for scavenging."""
        best_poop = None
        best_dist = 200.0

        for poop in poops:
            dist = self.physics.pos.distance_to((poop.x, poop.y))
            if dist < best_dist:
                best_dist = dist
                best_poop = poop

        return best_poop

    def _execute_cleaning(self, client, particle_system):
        """Clean the client fish: gain energy, boost client stats."""
        self.energy = min(FISH_MAX_ENERGY, self.energy + CLEANER_CLEANING_ENERGY_GAIN)
        self._times_cleaned += 1
        self._cleaning_cooldown = CLEANER_CLEANING_COOLDOWN
        self._is_actively_cleaning = False
        self._cleaning_target = None

        client.stamina = min(100.0, client.stamina + CLIENT_STAMINA_GAIN)
        client.energy = min(FISH_MAX_ENERGY, client.energy + CLIENT_ENERGY_GAIN)
        client.needs_cleaning = max(0.0, client.needs_cleaning - 0.5)
        client.last_cleaned_time = 0.0

        # Spawn sparkle effect
        mid_x = (self.physics.pos.x + client.physics.pos.x) / 2
        mid_y = (self.physics.pos.y + client.physics.pos.y) / 2
        if hasattr(particle_system, "spawn_cleaning_effect"):
            particle_system.spawn_cleaning_effect(mid_x, mid_y)

    def on_food_consumed(self, food):
        """Override to remove consumed poop from the fish system's poop list."""
        if hasattr(self.world, "fish_system"):
            poops = self.world.fish_system.poops
            if food in poops:
                poops.remove(food)

    def _update_cleaning(self, dt, all_fish, particle_system):
        """Pillar 1: Cleaning mutualism behavior."""
        if self._is_actively_cleaning and self._cleaning_target:
            client = self._cleaning_target
            alive_fish = self.world.fish_system.fish if hasattr(self.world, "fish_system") else []

            if client not in alive_fish:
                self._is_actively_cleaning = False
                self._cleaning_target = None
            else:
                seek = self.physics.seek(
                    client.physics.pos.x,
                    client.physics.pos.y,
                    weight=0.5,
                )
                self.physics.apply_force(seek)

                self._cleaning_timer -= dt
                if self._cleaning_timer <= 0:
                    self._execute_cleaning(client, particle_system)

        elif self._cleaning_cooldown <= 0:
            best_client = self._find_best_client(all_fish)
            if best_client:
                self._is_actively_cleaning = True
                self._cleaning_target = best_client
                self._cleaning_timer = CLEANER_CLEANING_DURATION * 0.5

                seek = self.physics.seek(
                    best_client.physics.pos.x,
                    best_client.physics.pos.y,
                    weight=CLEANER_CLIENT_SEEK_WEIGHT,
                )
                self.physics.apply_force(seek)

    def _update_scavenging(self, dt, poops):
        """Pillar 2: Scavenging behavior using NN's clean_drive output."""
        if not self._is_actively_cleaning:
            clean_drive = self.last_outputs[2] if len(self.last_outputs) > 2 else 0.5
            nearest_poop = self._find_nearest_poop(poops)
            if nearest_poop and clean_drive > 0.3:
                seek = self.physics.seek(
                    nearest_poop.x,
                    nearest_poop.y,
                    weight=CLEANER_POOP_SEEK_WEIGHT * clean_drive,
                )
                self.physics.apply_force(seek)

    def _update_station_affinity(self, plant_manager):
        """Pillar 3: Cleaning station affinity behavior."""
        if not self._is_actively_cleaning and random.random() < 0.3:
            station = self._find_nearest_station(plant_manager)
            if station:
                seek = self.physics.seek(
                    station.x,
                    station.base_y,
                    weight=CLEANER_STATION_SEEK_WEIGHT,
                )
                self.physics.apply_force(seek)

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        self._cleaning_cooldown = max(0.0, self._cleaning_cooldown - dt)

        # Separate poop from plankton
        poops = [t for t in targets if hasattr(t, "nutrition") and not getattr(t, "is_plankton", False)]

        # Behavioral pillars orchestrated through helper methods
        self._update_cleaning(dt, all_fish, particle_system)
        self._update_scavenging(dt, poops)
        self._update_station_affinity(plant_manager)

        # Parent update (NN, state machine, physics, food collision)
        result = super().update(
            dt,
            all_fish,
            targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )

        return result