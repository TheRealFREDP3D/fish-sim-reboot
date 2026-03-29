import random
from config import (
    FISH_MAX_POPULATION,
    CLEANER_FISH_MAX_POPULATION,
    PREDATOR_MAX_POPULATION,
    FISH_MAX_AGE,
    FISH_MAX_ENERGY,
    FISH_POPULATION_FLOOR,
    CLEANER_POPULATION_FLOOR,
    PREDATOR_POPULATION_FLOOR,
    FISH_CARRYING_CAPACITY,
    FISH_CARRYING_CAPACITY_STRENGTH,
    WATER_LINE_Y,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SOIL_MAX_NUTRIENT,
    FISH_REPRODUCTION_COST,
    PREDATOR_PREY_RATIO_MIN,
)
from fish_base import NeuralFish, FishState
from environment_objects import PoopParticle, FishEgg, DeadFish, BloodEffect
from fish_traits import FishTraits
from family import Family
from brain_visualizer import BrainVisualizer
from neural_net import NeuralNet
from cleaner_fish import CleanerFish
from predator_fish import PredatorFish


class FishSystem:
    def __init__(self, particle_system, plant_manager, world):
        self.world, self.particle_system, self.plant_manager = (
            world,
            particle_system,
            plant_manager,
        )
        self.world.fish_system = self

        self.fish = [NeuralFish(world) for _ in range(FISH_MAX_POPULATION // 2)]
        self.cleaner_fish = [
            CleanerFish(world) for _ in range(CLEANER_FISH_MAX_POPULATION // 2)
        ]
        self.predators = [PredatorFish(world) for _ in range(PREDATOR_MAX_POPULATION)]
        self.poops, self.eggs = [], []
        self.selected_fish = None
        self.families = []

        # ── NEW: Dead fish and blood effect management ────────────────────
        self.dead_fish: list[DeadFish] = []
        self.blood_effects: list[BloodEffect] = []

        self.brain_visualizer = BrainVisualizer(SCREEN_WIDTH, SCREEN_HEIGHT)

    def handle_click(self, pos, camera):
        world_x = pos[0] + camera.x
        world_y = pos[1] + camera.y
        all_f = self.fish + self.cleaner_fish + self.predators
        if not all_f:
            return
        clicked = min(
            all_f, key=lambda f: f.physics.pos.distance_to((world_x, world_y))
        )
        if clicked.physics.pos.distance_to((world_x, world_y)) < 40:
            self.selected_fish = clicked
        else:
            self.selected_fish = None

    def _kill_fish(self, f, f_list):
        """
        Remove a fish from its population list and spawn a DeadFish corpse
        that sinks to the bottom and decomposes into soil nutrients.
        """
        # Deselect if this fish was selected
        if f == self.selected_fish:
            self.selected_fish = None

        # Remove from family if applicable
        if f.family and f.family.active:
            f.family.active = False

        # Create a DeadFish corpse at the fish's position
        color = f.get_color()
        size = f.get_current_size_mult()
        heading = f.physics.heading
        corpse = DeadFish(f.physics.pos.x, f.physics.pos.y, color, size, heading)
        self.dead_fish.append(corpse)

        # Remove from the living list
        if f in f_list:
            f_list.remove(f)

    def update(self, dt, time_system=None):
        all_fish = self.fish + self.cleaner_fish + self.predators

        # ── 1. Update dead fish (sinking & decomposition) ─────────────────
        for corpse in self.dead_fish[:]:
            if not corpse.update(dt, self.world):
                self.dead_fish.remove(corpse)

        # ── 2. Update blood effects ──────────────────────────────────────
        self.blood_effects = [b for b in self.blood_effects if b.update(dt)]

        # 2. Update eggs — hatch and spawn at egg location
        for egg in self.eggs[:]:
            if egg.update(dt, self.world):
                self.eggs.remove(egg)
                self.spawn_from_egg(egg)

        # 3. Family Units
        for family in self.families[:]:
            family.update(dt)
            if not family.active:
                self.families.remove(family)

        # 4. Sediment/Fertilizer — update poop (some may be eaten by cleaners
        #    before they land, which is fine — cleaner_fish handles removal)
        for p in self.poops[:]:
            if not p.update(dt, self.world):
                self.poops.remove(p)

        # 5. Core Simulation Loop
        # Build the plankton list once for reuse
        plankton = [p for p in self.particle_system.particles if p.is_plankton]

        pred_activity = time_system.predator_activity_modifier if time_system else 1.0

        # ── Simulation groups ─────────────────────────────────────────────
        # Common fish: eat plankton
        sim_groups = [
            (self.fish, plankton, True),
        ]

        # Cleaner fish: eat BOTH poop AND plankton (opportunistic omnivores)
        # The poop list reference is shared — when cleaners eat poop via the
        # base class collision loop, the poop is removed from self.poops.
        # We snapshot plankton separately so cleaners don't consume the same
        # plankton instances that common fish might eat this frame.
        cleaner_targets = list(self.poops) + list(plankton)
        sim_groups.append((self.cleaner_fish, cleaner_targets, True))

        # Predators: hunt common fish + cleaner fish (with immunity check)
        sim_groups.append(
            (self.predators, self.fish + self.cleaner_fish, True)
        )

        for f_list, targets, can_mate in sim_groups:
            for f in f_list[:]:
                res = f.update(
                    dt,
                    all_fish,
                    targets,
                    self.particle_system,
                    self.plant_manager,
                    time_system=time_system,
                )

                if isinstance(res, PoopParticle):
                    self.poops.append(res)
                elif isinstance(res, tuple) and res[0] == "egg":
                    self.eggs.append(
                        FishEgg(
                            res[1],
                            res[2],
                            res[3],
                            res[4],
                            res[5],
                            f.is_cleaner,
                            f.is_predator,
                            res[6] if len(res) > 6 else None,
                        )
                    )

                lifespan = FISH_MAX_AGE * f.traits.physical_traits.get(
                    "lifespan_mult", 1.0
                )
                if f.energy <= 0 or f.age > lifespan:
                    self._kill_fish(f, f_list)
                    continue

                # Handle predator reproduction separately since they can't enter MATING state
                if f.is_predator and hasattr(f, 'try_reproduce'):
                    if f.try_reproduce():
                        # Predator successfully reproduced, create egg
                        egg_data = (
                            "egg",
                            f.physics.pos.x,
                            f.physics.pos.y,
                            f.traits,
                            f.brain,
                            f.is_cleaner,
                            f.is_predator,
                            f.mate.brain if f.mate else None,
                        )
                        self.eggs.append(
                            FishEgg(
                                egg_data[1],
                                egg_data[2],
                                egg_data[3],
                                egg_data[4],
                                egg_data[5],
                                egg_data[6],
                                egg_data[7],
                                egg_data[8] if len(egg_data) > 8 else None,
                            )
                        )
                        f.mate = None  # Clear mate reference

                if can_mate and f.state == FishState.MATING:
                    self.try_mate(f, f_list)

        # 6. Population floors — ensure minimum viable populations
        if len(self.fish) < FISH_POPULATION_FLOOR:
            self.fish.append(NeuralFish(self.world))

        if len(self.cleaner_fish) < CLEANER_POPULATION_FLOOR:
            self.cleaner_fish.append(CleanerFish(self.world))

        if len(self.predators) < PREDATOR_POPULATION_FLOOR:
            self.predators.append(PredatorFish(self.world))

        # 7. Update eat effects with real dt
        self.particle_system.eat_effects = [
            e for e in self.particle_system.eat_effects if e.update(dt)
        ]

    def try_mate(self, f, f_list):
        if f.is_pregnant:
            return

        # ── Carrying capacity pressure on common fish ────────────────────
        total_population = len(self.fish) + len(self.cleaner_fish)
        if not f.is_predator and not f.is_cleaner:
            if total_population >= FISH_CARRYING_CAPACITY:
                return  # hard block at carrying capacity
            # Soft suppression as we approach the cap
            overage_ratio = total_population / FISH_CARRYING_CAPACITY
            if overage_ratio > 0.7 and random.random() > (1.0 - overage_ratio):
                return  # probabilistic suppression near cap

        # Predator reproduction requires healthy prey population
        if f.is_predator:
            prey_count = len(self.fish)
            pred_count = len(self.predators)
            if prey_count / max(1, pred_count) < PREDATOR_PREY_RATIO_MIN:
                return

        for partner in f_list:
            if (
                partner != f
                and partner.state == FishState.MATING
                and partner.sex != f.sex
            ):
                if f.physics.pos.distance_to(partner.physics.pos) < 45:
                    f.energy -= FISH_REPRODUCTION_COST
                    partner.energy -= FISH_REPRODUCTION_COST
                    f.mating_cooldown, partner.mating_cooldown = 40.0, 40.0
                    child_traits = FishTraits.blend(f.traits, partner.traits)
                    blended_brain = NeuralNet.blend(f.brain, partner.brain)
                    child_brain = blended_brain.mutate()
                    mother = f if f.sex == "F" else partner
                    father = partner if f.sex == "F" else f
                    mother.is_pregnant = True
                    mother.pregnancy_traits, mother.pregnancy_partner = (
                        child_traits,
                        father,
                    )
                    mother.pregnancy_brain = child_brain
                    break

    def spawn_from_egg(self, egg):
        """Spawn a juvenile fish at the egg's position."""
        # Clamp spawn position to valid water bounds
        spawn_x = max(50, min(WORLD_WIDTH - 50, egg.x))
        spawn_y = max(WATER_LINE_Y + 30, min(WORLD_HEIGHT - 100, egg.y))

        if egg.is_cleaner:
            child = CleanerFish(
                self.world,
                traits=egg.traits,
                brain=egg.brain,
                start_x=spawn_x,
                start_y=spawn_y,
            )
            self.cleaner_fish.append(child)
        elif egg.is_predator:
            child = PredatorFish(
                self.world,
                traits=egg.traits,
                brain=egg.brain,
                start_x=spawn_x,
                start_y=spawn_y,
            )
            self.predators.append(child)
        else:
            child = NeuralFish(
                self.world,
                traits=egg.traits,
                brain=egg.brain,
                start_x=spawn_x,
                start_y=spawn_y,
            )
            self.fish.append(child)

        p1, p2 = egg.parent1, egg.parent2
        all_f = self.fish + self.cleaner_fish + self.predators
        if p1 in all_f and p2 in all_f:
            family = Family(p1, p2, [child], self)
            self.families.append(family)
            p1.family, p2.family, child.family = family, family, family

    def draw(self, screen, camera, time, dt=0.0, time_system=None):
        self.brain_visualizer.update(dt, self.selected_fish)

        biolum = time_system.get_bioluminescence_alpha() if time_system else 0

        # Draw dead fish corpses (behind living fish)
        for corpse in self.dead_fish:
            corpse.draw(screen, camera)

        # Draw blood effects
        for blood in self.blood_effects:
            blood.draw(screen, camera)

        for e in self.eggs:
            e.draw(screen, camera)
        for p in self.poops:
            p.draw(screen, camera)
        for f in self.fish + self.cleaner_fish + self.predators:
            f.draw(screen, camera, time, f == self.selected_fish, biolum_alpha=biolum)
        if self.selected_fish:
            self.brain_visualizer.draw(screen, self.selected_fish, time)