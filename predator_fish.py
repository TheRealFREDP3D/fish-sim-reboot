"""Predator Fish - High-speed hunters with improved neural network integration.

Improvements:
- Uses NN's ambush_drive and dash_drive outputs for behavior control
- Reduced hard-coded behavior in favor of learned responses
- Temporal context helps predators learn hunting patterns
- Damage-based bite system with blood effects
- Seasonal activity affects behavior through NN inputs

AGGRESSION OVERHAUL:
- Always scans for prey (not just when hungry)
- Always pursues detected prey at high intensity
- Much larger dash trigger range with lower stamina threshold
- Faster bite rate and higher damage
- Proactive patrol behavior to find prey
"""

import math
import random
from fish_base import NeuralFish
from config import (
    PREDATOR_SPEED_MULT,
    PREDATOR_DASH_DURATION,
    PREDATOR_DASH_COOLDOWN,
    PREDATOR_DASH_STAMINA_THRESHOLD,
    PREDATOR_DASH_STAMINA_DRAIN,
    PREDATOR_DASH_FORCE_MULT,
    PREDATOR_SIZE_ADVANTAGE_MULTIPLIER,
    PREDATOR_CANNIBAL_SIZE_RATIO,
    PREDATOR_DAMAGE_PER_BITE,
    PREDATOR_BACKSTAB_MULTIPLIER,
    PREDATOR_BITE_COOLDOWN,
    PREDATOR_SCAVENGE_THRESHOLD,
    PREDATOR_SCAVENGE_ENERGY_GAIN,
    PREDATOR_MAX_POPULATION,
    PREDATOR_PREY_RATIO_MIN,
    PREDATOR_DASH_TRIGGER_RANGE,
    PREDATOR_DASH_MIN_STAMINA_RATIO,
    PREDATOR_DASH_MIN_ACTIVITY,
    PREDATOR_DASH_DRIVE_THRESHOLD,
    PREDATOR_DASH_CLOSE_RANGE,
    CLEANER_IMMUNITY_CHANCE,
    PREY_PREDATOR_MIN_DISTANCE,
    FISH_HUNGER_THRESHOLD,
    FISH_MAX_ENERGY,
    FISH_MAX_AGE,
    FISH_MATING_THRESHOLD,
    FISH_REPRODUCTION_COST,
    FishState,
    FISH_EXPLORATION_FORCE,
)


class PredatorFish(NeuralFish):
    """Predator fish with aggressive hunting behavior controlled by improved NN."""

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

        # Bite-based hunting
        self._bite_cooldown = 0.0
        
        # Patrol hunting state
        self._wander_angle = random.uniform(0, math.pi * 2)
        self._wander_timer = 0.0

    def _get_viable_prey(self, all_fish):
        """Return prey fish that are smaller than this predator.
        
        Includes cannibalism for much larger predators.
        Cleaner fish have 90% immunity.
        """
        my_size = self.get_current_size_mult()
        prey = []
        
        for f in all_fish:
            if f is self:
                continue

            # Cleaner fish immunity
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

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        # Seasonal activity scaling
        activity_mod = time_system.predator_activity_modifier if time_system else 1.0

        # Dash stamina drain
        effective_dash_drain = PREDATOR_DASH_STAMINA_DRAIN * (0.8 + 0.2 * activity_mod)

        # ALWAYS scan for prey — predators are opportunistic apex hunters
        prey_targets = self._get_viable_prey(all_fish)
        is_hungry = self.energy < FISH_HUNGER_THRESHOLD

        closest_prey = None
        min_dist = PREY_PREDATOR_MIN_DISTANCE
        for prey in prey_targets:
            dist = self.physics.pos.distance_to(prey.physics.pos)
            if dist < min_dist:
                min_dist = dist
                closest_prey = prey

        # Parent update (NN forward pass happens here)
        res = super().update(
            dt,
            all_fish,
            prey_targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )

        # ═══════════════════════════════════════════════════════════════════
        # IMPROVED: Use NN outputs for hunting behavior
        # ambush_drive = output[2], dash_drive = output[3]
        # ═══════════════════════════════════════════════════════════════════
        
        # Get behavior drives from NN
        ambush_drive = self.last_outputs[2] if len(self.last_outputs) > 2 else 0.5
        dash_drive = self.last_outputs[3] if len(self.last_outputs) > 3 else 0.5

        # ── Hunting seek — predators ALWAYS pursue detected prey ───────────
        if closest_prey:
            # Always hunt — hungrier = more aggressive pursuit
            hunger_boost = 1.8 if is_hungry else 0.9
            base_hunt_weight = 0.9 * activity_mod * hunger_boost
            
            # NN enhancement when in HUNTING state
            if self.state == FishState.HUNTING:
                hunt_weight = base_hunt_weight * (1.0 + ambush_drive * 0.6)
            else:
                hunt_weight = base_hunt_weight * 0.5  # Still pursue even outside HUNTING state
                
            seek_force = self.physics.seek(
                closest_prey.physics.pos.x,
                closest_prey.physics.pos.y,
                weight=hunt_weight,
            )
            self.physics.apply_force(seek_force)

            # Initiate dash when close and ready — highly aggressive
            if (
                min_dist < PREDATOR_DASH_TRIGGER_RANGE
                and self.dash_cooldown <= 0
                and not self.is_dashing
                and self.stamina > PREDATOR_DASH_STAMINA_THRESHOLD * PREDATOR_DASH_MIN_STAMINA_RATIO
                and activity_mod > PREDATOR_DASH_MIN_ACTIVITY
                and (dash_drive > PREDATOR_DASH_DRIVE_THRESHOLD or min_dist < PREDATOR_DASH_CLOSE_RANGE)
            ):
                self.is_dashing = True
                self.dash_timer = PREDATOR_DASH_DURATION
                self.dash_cooldown = PREDATOR_DASH_COOLDOWN

        # ── Independent dash stamina (skip parent's speed-based drain) ──────
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

        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self._bite_cooldown = max(0.0, self._bite_cooldown - dt)

        # ═══════════════════════════════════════════════════════════════════
        # Damage-based hunting — always attempt to bite nearby prey
        # ═══════════════════════════════════════════════════════════════════
        for prey in prey_targets:
            collision_radius = 20 * self.get_current_size_mult()
            dist = math.hypot(
                self.physics.pos.x - prey.physics.pos.x,
                self.physics.pos.y - prey.physics.pos.y,
            )
            if dist < collision_radius and self._bite_cooldown <= 0:
                # Base bite damage scales with predator size — highly lethal
                base_damage = PREDATOR_DAMAGE_PER_BITE * self.get_current_size_mult()
                
                # Hunger bonus — predators deal more damage when desperate
                hunger_multiplier = 1.0 + (1.0 - self.energy / FISH_MAX_ENERGY) * 0.5
                damage = base_damage * hunger_multiplier

                # Backstab bonus
                heading_diff = self.physics.heading - prey.physics.heading
                heading_diff = abs(
                    math.atan2(math.sin(heading_diff), math.cos(heading_diff))
                )
                if heading_diff < math.pi * 0.4:
                    damage *= PREDATOR_BACKSTAB_MULTIPLIER

                prey.energy -= damage
                
                # Energy gain from biting — hunting is always worthwhile
                energy_gain = damage * 0.6
                self.energy = min(FISH_MAX_ENERGY, self.energy + energy_gain)
                self._bite_cooldown = PREDATOR_BITE_COOLDOWN
                
                # Kill prey if damage is lethal
                if prey.energy <= 0:
                    prey.energy = 0
                    # Big bonus energy for successful kill
                    kill_bonus = 20.0 * prey.get_current_size_mult()
                    self.energy = min(FISH_MAX_ENERGY, self.energy + kill_bonus)
                    self.food_eaten += 1

                # Blood effect
                bite_x = prey.physics.pos.x
                bite_y = prey.physics.pos.y
                blood = self._create_blood_effect(bite_x, bite_y, self.physics.heading)
                fish_system = getattr(self.world, "fish_system", None)
                if fish_system and blood:
                    fish_system.blood_effects.append(blood)

                break

        # ═══════════════════════════════════════════════════════════════════
        # Active prey pursuit — predators always actively seek food
        # ═══════════════════════════════════════════════════════════════════
        
        # Always patrol when no prey nearby — predators actively seek food
        if not closest_prey and activity_mod > 0.3:
            # Patrol hunting behavior - swim in patterns to find prey
            self._wander_timer += dt
            if self._wander_timer > 2.5:  # Change direction more frequently
                self._wander_angle += random.uniform(-math.pi/2, math.pi/2)
                self._wander_timer = 0.0
            
            # Patrol movement — faster and wider search patterns
            patrol_fx = math.cos(self._wander_angle) * FISH_EXPLORATION_FORCE * 1.5
            patrol_fy = math.sin(self._wander_angle) * FISH_EXPLORATION_FORCE * 1.5
            self.physics.apply_force((patrol_fx, patrol_fy))
        
        # ═══════════════════════════════════════════════════════════════════
        # Scavenging fallback — eat eggs when desperate
        # ═══════════════════════════════════════════════════════════════════
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
                        # Small blood effect for egg (only if brain exists)
                        if hasattr(egg, 'brain') and egg.brain is not None:
                            blood = self._create_blood_effect(egg.x, egg.y, self.physics.heading)
                            if blood:
                                fish_system.blood_effects.append(blood)
                        break

        return res

    def _create_blood_effect(self, x, y, heading):
        """Create a blood effect at the given position."""
        try:
            from environment_objects import BloodEffect
            return BloodEffect(x, y, heading)
        except ImportError:
            return None

    def try_reproduce(self):
        """Check if predator can reproduce (population control)."""
        # Use boosted threshold if prey is scarce
        effective_mating_threshold = getattr(self, 'mating_threshold_boost', FISH_MATING_THRESHOLD)
        
        if (
            not self.is_mature
            or self.energy < effective_mating_threshold
            or self.mating_cooldown > 0
        ):
            return False

        if not hasattr(self.world, "fish_system"):
            return False

        system = self.world.fish_system
        prey_count = len(system.fish)
        pred_count = len(system.predators)

        # Need minimum prey-to-predator ratio
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
