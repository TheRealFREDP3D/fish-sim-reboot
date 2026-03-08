"""Plant development system - handles life stages and nutrient recycling"""
import random
from config import *

class PlantDevelopment:
    """Handles staged development: germinating → seedling → mature → flowering → dying → decomposing"""
    def __init__(self, plant_type):
        self.plant_type = plant_type
        self.age = 0.0
        self.energy = 0.0
        self.stage = "germinating"
        self.is_mature = False
        self.is_flowering = False
        self.time_in_stage = 0.0
        params = {
            "kelp": {"max_height": 120, "segments": KELP_SEGMENTS},
            "seagrass": {"max_height": 60, "segments": SEAGRASS_SEGMENTS},
            "algae": {"max_height": 35, "segments": ALGAE_SEGMENTS},
        }[plant_type]
        self.max_height = params["max_height"]
        self.max_segments = params["segments"]
        self.current_height = 3
        self.current_segments = 1
        self.target_height = 3
        self.target_segments = 1
        if plant_type == "seagrass":
            self.total_blades = random.randint(4, 6)
            self.visible_blades = 0
        else:
            self.visible_blades = 0
        self.germination_energy = SEED_GROWTH_ENERGY
        self.maturity_energy = MATURE_ENERGY_THRESHOLD
        self.flowering_energy = FLOWERING_ENERGY_THRESHOLD

    def get_root_growth_multiplier(self, current_energy, current_height):
        multiplier = 1.0
        size_factor = current_height / max(10, self.max_height)
        multiplier += size_factor * 1.2
        if current_energy < 3.0:
            desperation = (3.0 - current_energy) / 3.0
            multiplier += desperation * 2.0
        elif current_energy < ROOT_ENERGY_HUNGRY_THRESHOLD:
            deficit = ROOT_ENERGY_HUNGRY_THRESHOLD - current_energy
            multiplier += deficit * 0.5
        if current_energy > ROOT_HIGH_ENERGY_SLOWDOWN:
            excess = current_energy - ROOT_HIGH_ENERGY_SLOWDOWN
            multiplier = max(0.4, multiplier - excess * 0.06)
        return min(ROOT_MAX_GROWTH_MULTIPLIER, max(0.4, multiplier))

    def update(self, dt, nutrients_received, current_height):
        self.age += dt
        self.time_in_stage += dt
        
        # Maintenance cost scales significantly with size
        size_factor = current_height / max(10, self.max_height)
        maintenance = (PLANT_BASE_MAINTENANCE + PLANT_SIZE_MAINTENANCE_FACTOR * size_factor) * dt
        self.energy += nutrients_received - maintenance

        # Stage progression
        if self.stage == "germinating" and self.energy >= self.germination_energy:
            self.stage = "seedling"
            self.target_height = self.max_height * 0.45
            self.target_segments = max(3, self.max_segments // 2)
            if self.plant_type == "seagrass":
                self.visible_blades = 2
            self.time_in_stage = 0.0
            
        elif self.stage == "seedling" and self.energy >= self.maturity_energy:
            self.stage = "mature"
            self.is_mature = True
            self.target_height = self.max_height
            self.target_segments = self.max_segments
            if self.plant_type == "seagrass":
                self.visible_blades = self.total_blades
            self.time_in_stage = 0.0
            
        elif self.stage == "mature" and self.energy >= self.flowering_energy:
            self.stage = "flowering"
            self.is_flowering = True
            self.time_in_stage = 0.0
            
        elif self.stage == "flowering" and self.time_in_stage >= FLOWERING_DURATION:
            self.stage = "dying"
            self.is_flowering = False
            self.time_in_stage = 0.0
            
        elif self.stage == "dying" and (self.energy < 0 or self.age > PLANT_MAX_AGE):
            self.stage = "decomposing"
            self.time_in_stage = 0.0

        # Slow visual growth
        growth_speed = dt * 1.8
        self.current_height += (self.target_height - self.current_height) * min(1.0, growth_speed)
        if self.current_segments < self.target_segments:
            self.current_segments += dt * 1.5
            self.current_segments = min(self.current_segments, self.target_segments)

        # Alive as long as not fully decomposed
        return self.stage != "decomposing" or self.time_in_stage < DECOMPOSITION_DURATION

    def get_decomposition_return(self):
        """Calculate nutrients returned to soil upon final death"""
        if self.stage == "decomposing":
            # Return energy + biomass bonus
            return (max(0, self.energy) + 5.0) * DECOMPOSITION_NUTRIENT_RETURN
        return 0.0
