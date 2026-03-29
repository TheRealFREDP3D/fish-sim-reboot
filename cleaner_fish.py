"""
Cleaner Fish — Mutualistic symbiont with three behavioral pillars:

  1. Cleaning Mutualism (primary):   Approach client fish and clean them.
     Cleaners gain energy; clients gain stamina + small energy boost.
  2. Scavenging (secondary):          Opportunistically eat poop AND plankton.
     No hunger gate — cleaners forage constantly.
  3. Cleaning Station Affinity:       Drift toward coral / anemone / sponge
     plants as preferred loitering zones.

Ecological role:
  • Positive feedback loop: cleaning improves client health → clients survive
    longer → more cleaning opportunities.
  • Predators largely ignore cleaners (90% immunity) mimicking real-world
    cleaner–predator recognition.
"""

import math
import random
from fish_base import NeuralFish
from config import (
    CLEANER_FISH_SPEED_MULT,
    CLEANER_FISH_CLEANING_ENERGY_THRESHOLD,
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
    CLEANER_PLANKTON_EAT_CHANCE,
    CLEANER_POOP_SEEK_WEIGHT,
    CLEANER_CLIENT_SEEK_WEIGHT,
    FISH_MAX_ENERGY,
    FISH_MAX_SPEED,
    FISH_SENSOR_RANGE,
    FISH_MAX_FORCE,
)


class CleanerFish(NeuralFish):
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

        # ── Cleaning state ────────────────────────────────────────────────
        self._cleaning_cooldown = random.uniform(0.0, CLEANER_CLEANING_COOLDOWN)
        self._is_actively_cleaning = False
        self._cleaning_target = None
        self._cleaning_timer = 0.0
        self._times_cleaned = 0  # lifetime counter (fitness signal)

    # ── Find viable clients ───────────────────────────────────────────────

    def _find_best_client(self, all_fish):
        """Return the nearby non-predator fish that most needs cleaning."""
        best_client = None
        best_score = -1.0
        my_pos = self.physics.pos

        for fish in all_fish:
            if fish is self:
                continue
            # Don't clean predators or immature fish
            if fish.is_predator or not fish.is_mature:
                continue
            # Don't clean other cleaner fish
            if fish.is_cleaner:
                continue

            dist = my_pos.distance_to(fish.physics.pos)
            if dist > CLEANER_CLEANING_RANGE:
                continue

            # Score: prioritize fish with high needs_cleaning that are close
            need = getattr(fish, "needs_cleaning", 0.0)
            if need < 0.15:
                continue  # skip fish that don't really need cleaning yet

            proximity_bonus = 1.0 - (dist / CLEANER_CLEANING_RANGE)
            score = need * 2.0 + proximity_bonus

            if score > best_score:
                best_score = score
                best_client = fish

        return best_client

    # ── Find nearest cleaning station plant ───────────────────────────────

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

    # ── Find nearest poop ─────────────────────────────────────────────────

    def _find_nearest_poop(self, poops):
        best_poop = None
        best_dist = 200.0

        for poop in poops:
            dist = self.physics.pos.distance_to((poop.x, poop.y))
            if dist < best_dist:
                best_dist = dist
                best_poop = poop

        return best_poop

    # ── Execute a cleaning event on a client ──────────────────────────────

    def _execute_cleaning(self, client, particle_system):
        """Clean the client fish: gain energy, boost client's stamina and energy."""
        self.energy = min(FISH_MAX_ENERGY, self.energy + CLEANER_CLEANING_ENERGY_GAIN)
        self._times_cleaned += 1
        self._cleaning_cooldown = CLEANER_CLEANING_COOLDOWN
        self._is_actively_cleaning = False
        self._cleaning_target = None

        # Client benefits
        client.stamina = min(100.0, client.stamina + CLIENT_STAMINA_GAIN)
        client.energy = min(FISH_MAX_ENERGY, client.energy + CLIENT_ENERGY_GAIN)
        client.needs_cleaning = max(0.0, client.needs_cleaning - 0.5)
        client.last_cleaned_time = 0.0

        # Spawn teal sparkle effect at midpoint between cleaner and client
        mid_x = (self.physics.pos.x + client.physics.pos.x) / 2
        mid_y = (self.physics.pos.y + client.physics.pos.y) / 2
        if hasattr(particle_system, "spawn_cleaning_effect"):
            particle_system.spawn_cleaning_effect(mid_x, mid_y)

    # ── Main update ───────────────────────────────────────────────────────

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        self._cleaning_cooldown = max(0.0, self._cleaning_cooldown - dt)

        # Separate poop targets from plankton targets if both were passed
        # (fish_system now passes poops+plankton combined for cleaners)
        poops = [t for t in targets if hasattr(t, "nutrition") and not getattr(t, "is_plankton", False)]
        plankton = [t for t in targets if getattr(t, "is_plankton", False)]

        # ═══════════════════════════════════════════════════════════════════
        # PILLAR 1 — Cleaning Mutualism (highest priority when available)
        # ═══════════════════════════════════════════════════════════════════
        if self._is_actively_cleaning and self._cleaning_target:
            # Stay close to the client and count down the cleaning duration
            client = self._cleaning_target
            # Verify client is still alive and nearby
            alive_fish = self.world.fish_system.fish if hasattr(self.world, "fish_system") else []
            if client not in alive_fish:
                self._is_actively_cleaning = False
                self._cleaning_target = None
            else:
                # Gently follow the client
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
            # Look for a client to clean
            best_client = self._find_best_client(all_fish)
            if best_client:
                self._is_actively_cleaning = True
                self._cleaning_target = best_client
                self._cleaning_timer = CLEANER_CLEANING_DURATION * 0.5  # quick initial clean

                # Also seek toward the client to close distance faster
                seek = self.physics.seek(
                    best_client.physics.pos.x,
                    best_client.physics.pos.y,
                    weight=CLEANER_CLIENT_SEEK_WEIGHT,
                )
                self.physics.apply_force(seek)

        # ═══════════════════════════════════════════════════════════════════
        # PILLAR 2 — Scavenging (always active, no hunger gate)
        # ═══════════════════════════════════════════════════════════════════
        # Seek nearest poop opportunistically
        if not self._is_actively_cleaning:
            nearest_poop = self._find_nearest_poop(poops)
            if nearest_poop:
                seek = self.physics.seek(
                    nearest_poop.x,
                    nearest_poop.y,
                    weight=CLEANER_POOP_SEEK_WEIGHT,
                )
                self.physics.apply_force(seek)

        # ═══════════════════════════════════════════════════════════════════
        # PILLAR 3 — Cleaning Station Affinity (gentle pull toward stations)
        # ═══════════════════════════════════════════════════════════════════
        if not self._is_actively_cleaning and random.random() < 0.3:
            station = self._find_nearest_station(plant_manager)
            if station:
                seek = self.physics.seek(
                    station.x,
                    station.base_y,
                    weight=CLEANER_STATION_SEEK_WEIGHT,
                )
                self.physics.apply_force(seek)

        # ── Parent update (NN, state machine, physics, food collision) ────
        return super().update(
            dt,
            all_fish,
            targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )
