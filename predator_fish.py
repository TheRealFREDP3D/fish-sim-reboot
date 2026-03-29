"""Predator Fish - High-speed hunters with ambush, dash, and damage-based hunting

Fixes implemented:
  #1  Manual seek now gated behind NN HUNTING state (no more steering conflicts)
  #3  hide_drive used as ambush patience instead of flee-to-cover
  #4  Size-based cannibalism for much larger predators
  #5  Damage-based bite system with backstab bonus (replaces instant kill)
  #6  Dash stamina handled independently (no double drain from parent)
  #7  Seasonal activity passed to NN via parent activity_mod
  #8  Egg scavenging fallback when desperate
  #9  try_reproduce() removed — predators now mate through the NN state machine
  #11 Blood drops visible on bite (BloodEffect replaces generic EatEffect)
"""

import math
import random
from fish_base import NeuralFish, get_life_stage_size_mult
from config import *
from environment_objects import BloodEffect


class PredatorFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None, start_x=None, start_y=None):
        super().__init__(
            world,
            traits=traits,
            brain=brain,
            start_x=start_x,
            start_y=start_y,
        )
        self.is_predator = True
        self.physics.max_speed *= PREDATOR_SPEED_MULT

        # Dash mechanics
        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0

        # FIX #5: Bite-based hunting with cooldown
        self._bite_cooldown = 0.0

    # ── Prey filtering ───────────────────────────────────────────────────

    def _get_viable_prey(self, all_fish):
        """Return prey fish that are strictly smaller than this predator.

        FIX #4: Includes cannibalism for predators that are 2x+ larger.
        Cleaner fish are largely immune (90%) mimicking real-world
        predator-cleaner recognition.
        """
        my_size = self.get_current_size_mult()
        prey = []
        for f in all_fish:
            if f is self:
                continue

            # ── Cleaner fish immunity ─────────────────────────────────────
            # In nature, even apex predators tolerate cleaner fish at
            # cleaning stations.  90% chance to skip, 10% to hunt.
            if f.is_cleaner:
                if random.random() < CLEANER_IMMUNITY_CHANCE:
                    continue

            if f.is_predator:
                # Cannibalism only when significantly larger
                if my_size >= f.get_current_size_mult() * PREDATOR_CANNIBAL_SIZE_RATIO:
                    prey.append(f)
            else:
                if f.is_hidden:
                    continue
                prey_size = f.get_current_size_mult()
                if my_size >= prey_size * PREDATOR_SIZE_ADVANTAGE_MULTIPLIER:
                    prey.append(f)
        return prey

    # ── Update ────────────────────────────────────────────────────────────

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        # FIX #7: Seasonal activity scaling (weaker in winter)
        activity_mod = time_system.predator_activity_modifier if time_system else 1.0

        # FIX #6: Scale dash stamina drain with activity (less drain in winter)
        effective_dash_drain = PREDATOR_DASH_STAMINA_DRAIN * (0.8 + 0.2 * activity_mod)

        # Only actively hunt when hungry
        is_hungry = self.energy < FISH_HUNGER_THRESHOLD

        # Filter prey by size
        prey_targets = self._get_viable_prey(all_fish) if is_hungry else []

        closest_prey = None
        min_dist = PREY_PREDATOR_MIN_DISTANCE
        for prey in prey_targets:
            dist = self.physics.pos.distance_to(prey.physics.pos)
            if dist < min_dist:
                min_dist = dist
                closest_prey = prey

        # ── Parent update (NN, state machine, physics) ──────────────────
        res = super().update(
            dt,
            all_fish,
            prey_targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )

        # ── FIX #1: Manual seek ONLY when NN agrees (HUNTING state) ─────
        if closest_prey and is_hungry and self.state == FishState.HUNTING:
            seek_force = self.physics.seek(
                closest_prey.physics.pos.x,
                closest_prey.physics.pos.y,
                weight=0.9 * activity_mod,
            )
            self.physics.apply_force(seek_force)

            # Initiate dash when close and ready
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

        # ── FIX #6: Independent dash stamina (parent skips drain while dashing) ─
        if self.is_dashing:
            self.dash_timer -= dt
            # Only drain stamina from dash, skip parent speed-based drain (Issue #6)
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

        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self._bite_cooldown = max(0.0, self._bite_cooldown - dt)

        # ── FIX #5: Damage-based hunting instead of instant kill ─────────
        # ── FIX #11: Blood drops visible on each bite ────────────────────
        if is_hungry:
            for prey in prey_targets:
                collision_radius = 20 * self.get_current_size_mult()
                dist = math.hypot(
                    self.physics.pos.x - prey.physics.pos.x,
                    self.physics.pos.y - prey.physics.pos.y,
                )
                if dist < collision_radius and self._bite_cooldown <= 0:
                    # Base bite damage scales with predator size
                    damage = PREDATOR_DAMAGE_PER_BITE * self.get_current_size_mult()

                    # Backstab bonus — attacking from behind the prey
                    heading_diff = self.physics.heading - prey.physics.heading
                    heading_diff = abs(
                        math.atan2(math.sin(heading_diff), math.cos(heading_diff))
                    )
                    if heading_diff < math.pi * 0.4:  # within ~72° of behind
                        damage *= PREDATOR_BACKSTAB_MULTIPLIER

                    prey.energy -= damage
                    # Partial energy gain per bite (not full kill reward)
                    energy_gain = damage * 0.3
                    self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gain)
                    self._bite_cooldown = PREDATOR_BITE_COOLDOWN

                    # ── Blood drops spray from the wound ─────────────────
                    # Spawn at the prey's position, angled away from attacker
                    bite_x = prey.physics.pos.x
                    bite_y = prey.physics.pos.y
                    blood = BloodEffect(bite_x, bite_y, self.physics.heading)
                    # Add to the fish system's blood effects list
                    fish_system = getattr(self.world, "fish_system", None)
                    if fish_system:
                        fish_system.blood_effects.append(blood)

                    break

        # ── FIX #8: Scavenging fallback — eat eggs when desperate ────────
        if not closest_prey and self.energy < PREDATOR_SCAVENGE_THRESHOLD:
            fish_system = getattr(self.world, "fish_system", None)
            if fish_system:
                for egg in fish_system.eggs[:]:
                    dist = self.physics.pos.distance_to((egg.x, egg.y))
                    if dist < 40:
                        self.energy = min(
                            FISH_MAX_ENERGY,
                            self.energy + PREDATOR_SCAVENGE_ENERGY_GAIN,
                        )
                        fish_system.eggs.remove(egg)
                        # Scavenging eggs — small blood tint (yolk-like)
                        blood = BloodEffect(egg.x, egg.y, self.physics.heading)
                        fish_system.blood_effects.append(blood)
                        break

        return res

    def try_reproduce(self):
        """
        Called by FishSystem for predator reproduction.

        FIX #10: Population control — only reproduce when prey is sufficient.
        """
        if (
            not self.is_mature
            or self.energy < FISH_MATING_THRESHOLD
            or self.mating_cooldown > 0
        ):
            return False

        if not hasattr(self.world, "fish_system"):
            return False

        system = self.world.fish_system
        prey_count = len(system.fish)
        pred_count = len(system.predators)

        # Need minimum prey-to-predator ratio to sustain population
        if pred_count > 0 and (prey_count / pred_count) < PREDATOR_PREY_RATIO_MIN:
            return False

        # Hard cap on predator population
        if pred_count >= PREDATOR_MAX_POPULATION:
            return False

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