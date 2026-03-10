from config import *
from fish_base import NeuralFish
from environment_objects import PoopParticle, FishEgg
from fish_traits import FishTraits
from family import Family
from brain_visualizer import BrainVisualizer


class FishSystem:
    def __init__(self, particle_system, plant_manager, world):
        self.world, self.particle_system, self.plant_manager = (
            world,
            particle_system,
            plant_manager,
        )
        # Link world to system so predators can find mates in population lists
        self.world.fish_system = self

        self.fish = [NeuralFish(world) for _ in range(FISH_MAX_POPULATION // 2)]
        from cleaner_fish import CleanerFish
        from predator_fish import PredatorFish

        self.cleaner_fish = [
            CleanerFish(world) for _ in range(CLEANER_FISH_MAX_POPULATION // 2)
        ]
        self.predators = [PredatorFish(world) for _ in range(PREDATOR_MAX_POPULATION)]
        self.poops, self.eggs = [], []
        self.selected_fish = None
        self.families = []
        
        # Initialize brain visualizer
        self.brain_visualizer = BrainVisualizer(SCREEN_WIDTH, SCREEN_HEIGHT)

    def handle_click(self, pos, camera):
        # Convert screen click to world coordinates
        world_x = pos[0] + camera.x
        world_y = pos[1] + camera.y

        all_f = self.fish + self.cleaner_fish + self.predators
        if not all_f:
            return
        clicked = min(
            all_f,
            key=lambda f: f.physics.pos.distance_to((world_x, world_y)),
        )
        if clicked.physics.pos.distance_to((world_x, world_y)) < 40:
            self.selected_fish = clicked
        else:
            self.selected_fish = None

    def update(self, dt):
        all_fish = self.fish + self.cleaner_fish + self.predators

        # 1. Predator Reproduction Cycle
        for predator in self.predators:
            if (
                hasattr(predator, "try_reproduce")
                and predator.try_reproduce()
                and len(self.predators) < PREDATOR_MAX_POPULATION
            ):
                egg = FishEgg(
                    predator.physics.pos.x,
                    predator.physics.pos.y,
                    predator.traits.mutate(),
                    parent1=predator,
                    parent2=predator.mate,
                    is_predator=True,
                )
                self.eggs.append(egg)

        # Update eggs
        for egg in self.eggs[:]:
            if egg.update(dt, self.world):
                self.eggs.remove(egg)
                self.spawn_from_egg(egg)

        # 3. Handle Family Units
        for family in self.families[:]:
            family.update(dt)
            if not family.active:
                self.families.remove(family)

        # 4. Handle Sediment/Fertilizer
        for p in self.poops[:]:
            if not p.update(dt, self.world):
                self.poops.remove(p)

        # 5. Core Simulation Loop
        plankton = [p for p in self.particle_system.particles if p.is_plankton]

        # Mapping populations to their targets and reproductive capability
        sim_groups = [
            (self.fish, plankton, True),
            (self.cleaner_fish, self.poops, True),
            (self.predators, self.fish + self.cleaner_fish, False),
        ]

        for f_list, targets, can_mate in sim_groups:
            for f in f_list[:]:
                res = f.update(
                    dt, all_fish, targets, self.particle_system, self.plant_manager
                )

                # Handle physical results (Poop or Eggs)
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
                        )
                    )

                # Handle death
                lifespan = FISH_MAX_AGE * f.traits.physical_traits.get(
                    "lifespan_mult", 1.0
                )
                if f.energy <= 0 or f.age > lifespan:
                    if f == self.selected_fish:
                        self.selected_fish = None
                    f_list.remove(f)
                    continue

                # Handle mating attempts (within subspecies)
                if can_mate and f.state == FishState.MATING:
                    self.try_mate(f, f_list)

        # Maintain base population
        if len(self.fish) < 6:
            self.fish.append(NeuralFish(self.world))

    def try_mate(self, f, f_list):
        if f.is_pregnant:
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
                    mother = f if f.sex == "F" else partner
                    father = partner if f.sex == "F" else f
                    mother.is_pregnant = True
                    mother.pregnancy_traits, mother.pregnancy_partner = (
                        child_traits,
                        father,
                    )
                    break

    def spawn_from_egg(self, egg):
        if egg.is_cleaner:
            from cleaner_fish import CleanerFish

            child = CleanerFish(self.world, traits=egg.traits)
            self.cleaner_fish.append(child)
        elif egg.is_predator:
            from predator_fish import PredatorFish

            child = PredatorFish(self.world, traits=egg.traits)
            self.predators.append(child)
        else:
            child = NeuralFish(self.world, traits=egg.traits)
            self.fish.append(child)

        p1, p2 = egg.parent1, egg.parent2
        all_f = self.fish + self.cleaner_fish + self.predators
        if p1 in all_f and p2 in all_f:
            family = Family(p1, p2, [child], self)
            self.families.append(family)
            p1.family, p2.family, child.family = family, family, family

    def draw(self, screen, camera, time, dt=0.0):
        # Update brain visualizer
        self.brain_visualizer.update(dt, self.selected_fish)
        
        for e in self.eggs:
            e.draw(screen, camera)
        for p in self.poops:
            p.draw(screen, camera)
        for f in self.fish + self.cleaner_fish + self.predators:
            f.draw(screen, camera, time, f == self.selected_fish)
        if self.selected_fish:
            self.brain_visualizer.draw(screen, self.selected_fish, time)
