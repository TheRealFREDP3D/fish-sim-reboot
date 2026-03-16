from fish_base import NeuralFish
from config import CLEANER_FISH_SPEED_MULT, CLEANER_FISH_CLEANING_ENERGY_THRESHOLD


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

    def update(
        self, dt, all_fish, targets, particle_system, plant_manager, time_system=None
    ):
        closest_poop = None
        min_dist = 200

        for poop in targets:
            dist = self.physics.pos.distance_to((poop.x, poop.y))
            if dist < min_dist:
                min_dist = dist
                closest_poop = poop

        if closest_poop and self.energy < CLEANER_FISH_CLEANING_ENERGY_THRESHOLD:
            seek_force = self.physics.seek(closest_poop.x, closest_poop.y, weight=0.6)
            self.physics.apply_force(seek_force)

        return super().update(
            dt,
            all_fish,
            targets,
            particle_system,
            plant_manager,
            time_system=time_system,
        )
