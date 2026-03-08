"""Plant system with organic visual rendering, tapered blades, and visible seed production"""
import pygame
import math
import random
from config import (
    SCREEN_HEIGHT, WATER_LINE_Y,
    KELP_HEIGHT_MIN, KELP_HEIGHT_MAX, KELP_SWAY_SPEED, KELP_SWAY_AMPLITUDE,
    KELP_COLOR, KELP_HIGHLIGHT, KELP_WIDTH, KELP_DEPTH_MAX,
    SEAGRASS_HEIGHT_MIN, SEAGRASS_HEIGHT_MAX, SEAGRASS_SWAY_SPEED,
    SEAGRASS_SWAY_AMPLITUDE, SEAGRASS_COLOR, SEAGRASS_HIGHLIGHT, SEAGRASS_WIDTH,
    SEAGRASS_DEPTH_MIN, SEAGRASS_DEPTH_MAX,
    ALGAE_HEIGHT_MIN, ALGAE_HEIGHT_MAX, ALGAE_SWAY_SPEED, ALGAE_SWAY_AMPLITUDE,
    ALGAE_COLOR, ALGAE_HIGHLIGHT, ALGAE_WIDTH, ALGAE_DEPTH_MIN,
    ROOT_BASE_GROWTH_RATE, SEED_PRODUCTION_ENERGY, SEED_PRODUCTION_COST,
    BUBBLE_CHANCE, BUBBLE_COLOR, SOIL_MAX_NUTRIENT
)
from roots import RootSystem
from seeds import Seed
from plant_development import PlantDevelopment

class Plant:
    def __init__(self, x, base_y, plant_type, soil_grid, seed_traits):
        self.x = x
        self.base_y = base_y
        self.plant_type = plant_type
        self.traits = seed_traits
        self.development = PlantDevelopment(plant_type)

        height_min_max = {
            "kelp": (KELP_HEIGHT_MIN, KELP_HEIGHT_MAX),
            "seagrass": (SEAGRASS_HEIGHT_MIN, SEAGRASS_HEIGHT_MAX),
            "algae": (ALGAE_HEIGHT_MIN, ALGAE_HEIGHT_MAX),
        }[plant_type]
        base_min, base_max = height_min_max
        self.max_height = int(base_min + (base_max - base_min) * self.traits["max_height_factor"])

        self.sway_speed = {
            "kelp": KELP_SWAY_SPEED,
            "seagrass": SEAGRASS_SWAY_SPEED,
            "algae": ALGAE_SWAY_SPEED
        }[plant_type]
        self.sway_amplitude = {
            "kelp": KELP_SWAY_AMPLITUDE,
            "seagrass": SEAGRASS_SWAY_AMPLITUDE,
            "algae": ALGAE_SWAY_AMPLITUDE
        }[plant_type]
        self.base_color = {
            "kelp": KELP_COLOR,
            "seagrass": SEAGRASS_COLOR,
            "algae": ALGAE_COLOR
        }[plant_type]
        self.highlight_color = {
            "kelp": KELP_HIGHLIGHT,
            "seagrass": SEAGRASS_HIGHLIGHT,
            "algae": ALGAE_HIGHLIGHT
        }[plant_type]
        self.width = {
            "kelp": KELP_WIDTH,
            "seagrass": SEAGRASS_WIDTH,
            "algae": ALGAE_WIDTH
        }[plant_type]

        self.phase_offset = random.uniform(0, math.pi * 2)
        self.wind_phase = 0.0
        self.root_system = RootSystem(self.x, self.base_y, soil_grid)

        if plant_type == "seagrass":
            self.blade_count = random.randint(4, 7)
            self.blade_data = []
            for _ in range(self.blade_count):
                self.blade_data.append({
                    'offset': random.uniform(-12, 12),
                    'h_mult': random.uniform(0.7, 1.1),
                    'phase': random.uniform(0, math.pi * 2),
                    'speed': random.uniform(0.8, 1.2)
                })

        self.floating_leaves = []
        self.decomposition_particles = []
        self.seed_release_cooldown = 0.0

    def update(self, dt, soil_grid):
        self.wind_phase += dt * 0.4
        self.seed_release_cooldown = max(0, self.seed_release_cooldown - dt)

        base_mult = self.traits["root_aggression"]
        need_mult = self.development.get_root_growth_multiplier(self.development.energy, self.development.current_height)
        self.root_system.adjust_growth_rate(ROOT_BASE_GROWTH_RATE * base_mult * need_mult)

        self.root_system.update(dt, self.development.current_height)
        nutrients = self.root_system.harvest_nutrients()

        alive = self.development.update(dt, nutrients * self.traits["growth_rate_mult"], self.development.current_height)

        # Kelp Leaf Detachment
        if self.plant_type == "kelp" and self.development.is_mature and random.random() < 0.0005:
            self.floating_leaves.append({
                "x": self.x,
                "y": self.base_y - self.development.current_height * 0.7,
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-0.8, -0.4),
                "life": random.uniform(6, 12),
                "rot": 0,
                "spin": random.uniform(-5, 5)
            })

        for leaf in self.floating_leaves[:]:
            leaf["x"] += leaf["vx"]
            leaf["y"] += leaf["vy"]
            leaf["life"] -= dt
            leaf["rot"] += leaf["spin"] * dt
            if leaf["life"] <= 0:
                self.floating_leaves.remove(leaf)

        # Decomposition visual feedback
        if self.development.stage == "decomposing" and random.random() < 0.1:
            self.decomposition_particles.append({
                "x": self.x + random.uniform(-10, 10),
                "y": self.base_y - random.uniform(0, self.development.current_height),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.2, 0.2),
                "life": 2.0
            })

        for p in self.decomposition_particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= dt
            if p["life"] <= 0:
                self.decomposition_particles.remove(p)

        return alive

    def produce_seed(self, time):
        """Attempt to produce a seed if flowering and energy permits"""
        can_seed = self.development.stage == "flowering" or (self.development.stage == "mature" and random.random() < 0.05)
        
        if can_seed and self.seed_release_cooldown <= 0:
            if self.development.energy >= SEED_PRODUCTION_ENERGY * self.traits["seed_efficiency"]:
                self.development.energy -= SEED_PRODUCTION_COST * self.traits["seed_efficiency"]
                self.seed_release_cooldown = 3.0 # Wait between seeds
                
                child_seed = Seed(self.plant_type)
                child_seed.traits = child_seed.mutate(self.traits)
                
                # Position seed at the tip
                tip_x, tip_y = self.get_tip_position(time)
                child_seed.x = tip_x
                child_seed.y = tip_y
                # Give it some initial "ejection" velocity
                child_seed.vx = random.uniform(-1.5, 1.5)
                child_seed.vy = random.uniform(-2.0, -0.5)
                
                return child_seed
        return None

    def draw(self, screen, time, soil_grid):
        color = self.get_organic_color()
        height = self.development.current_height

        if self.plant_type == "seagrass":
            self.draw_seagrass(screen, time, color, height)
        elif self.plant_type == "kelp":
            self.draw_kelp(screen, time, color, height)
        else:
            self.draw_algae(screen, time, color, height)

        # Draw flowering effect with pulse
        if self.development.is_flowering:
            top_pos = self.get_tip_position(time)
            pulse = (math.sin(time * 5) + 1) * 0.5
            radius = 6 + pulse * 4
            pygame.draw.circle(screen, (255, 255, 150), (int(top_pos[0]), int(top_pos[1])), int(radius))
            pygame.draw.circle(screen, (255, 255, 255), (int(top_pos[0]), int(top_pos[1])), int(radius + 2), 1)

        # Draw decomp particles
        for p in self.decomposition_particles:
            alpha = max(0, min(255, int(150 * (p["life"] / 2.0))))
            surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (100, 80, 50, alpha), (2, 2), 2)
            screen.blit(surf, (int(p["x"]) - 2, int(p["y"]) - 2))

    def get_organic_color(self):
        depth_ratio = (self.base_y - WATER_LINE_Y) / (SCREEN_HEIGHT - WATER_LINE_Y)
        energy_ratio = min(1.0, max(0.2, self.development.energy / 10.0))

        r = int(self.base_color[0] * (0.6 + 0.4 * energy_ratio) * (1.0 - 0.3 * depth_ratio))
        g = int(self.base_color[1] * (0.6 + 0.4 * energy_ratio) * (1.0 - 0.3 * depth_ratio))
        b = int(self.base_color[2] * (0.6 + 0.4 * energy_ratio) * (1.0 - 0.3 * depth_ratio))

        if self.development.stage == "decomposing":
            return (80, 70, 50)
        elif self.development.stage == "dying":
            return (int(r * 0.7), int(g * 0.8), int(b * 0.5))

        return (r, g, b)

    def draw_seagrass(self, screen, time, color, height):
        visible_blades = getattr(self.development, "visible_blades", self.blade_count)
        for i in range(int(visible_blades)):
            if i >= len(self.blade_data):
                break
            data = self.blade_data[i]
            points = []
            blade_h = height * data['h_mult']
            segments = 8
            for s in range(segments + 1):
                prog = s / segments
                sway = math.sin(time * self.sway_speed * data['speed'] + self.phase_offset + data['phase'] + s * 0.2)
                sway *= self.sway_amplitude * (prog ** 1.8)
                px = self.x + data['offset'] + sway
                py = self.base_y - (blade_h * prog)
                points.append((px, py))

            if len(points) > 1:
                for s in range(len(points) - 1):
                    w = max(1, int(self.width * (1.0 - (s / len(points)))))
                    pygame.draw.line(screen, color, points[s], points[s+1], w)

    def draw_kelp(self, screen, time, color, height):
        segments = int(self.development.current_segments)
        points = [(self.x, self.base_y)]
        seg_h = height / max(1, segments)
        for i in range(1, segments + 1):
            prog = i / segments
            sway = math.sin(time * self.sway_speed + self.phase_offset + i * 0.3) * self.sway_amplitude * (prog ** 1.5)
            px = self.x + sway
            py = self.base_y - (seg_h * i)
            points.append((px, py))

            # Larger leaves for kelp
            if i > 2 and i % 3 == 0:
                leaf_dir = 1 if i % 6 == 0 else -1
                leaf_surf = pygame.Surface((24, 12), pygame.SRCALPHA)
                leaf_color = color[:3] if len(color) >= 3 else color
                pygame.draw.ellipse(leaf_surf, (*leaf_color, 180), (0, 0, 24, 12))
                rotated_leaf = pygame.transform.rotate(leaf_surf, leaf_dir * 45)
                screen.blit(rotated_leaf, (px + leaf_dir * 12 - 12, py - 6))

        if len(points) > 1:
            for i in range(len(points) - 1):
                thickness = max(1, int(self.width * (1.1 - (i / len(points)))))
                pygame.draw.line(screen, color, points[i], points[i+1], thickness)

    def draw_algae(self, screen, time, color, height):
        points = [(self.x, self.base_y)]
        segments = 6
        seg_h = height / segments
        for i in range(1, segments + 1):
            prog = i / segments
            sway = math.sin(time * self.sway_speed + self.phase_offset + i * 0.5) * self.sway_amplitude * prog
            points.append((self.x + sway, self.base_y - seg_h * i))

        if len(points) > 1:
            for i in range(len(points) - 1):
                thickness = max(2, int((self.width + 2) * (1.0 - (i / len(points)) * 0.5)))
                pygame.draw.line(screen, color, points[i], points[i+1], thickness)

        # Bulbous tip for algae
        tip = points[-1]
        pygame.draw.circle(screen, color, (int(tip[0]), int(tip[1])), self.width + 2)

    def get_tip_position(self, time):
        sway = math.sin(time * self.sway_speed + self.phase_offset + 3.0) * self.sway_amplitude
        return (self.x + sway, self.base_y - self.development.current_height)

    def draw_roots(self, screen, time=0):
        self.root_system.draw(screen, time)

class PlantManager:
    def __init__(self, world):
        self.world = world
        self.plants = []
        self.seeds = []
        self.bubbles = []
        self.renewal_timer = 0.0

    def spawn_initial_seeds(self):
        for _ in range(50):
            plant_type = random.choice(["kelp", "seagrass", "algae"])
            seed = Seed(plant_type)
            self.seeds.append(seed)

    def update(self, dt):
        soil_grid = self.world.soil_grid
        time = pygame.time.get_ticks() / 1000.0

        # Maintain minimum seed population if ecology is sparse
        if len(self.plants) < 15:
            self.renewal_timer += dt
            if self.renewal_timer > 3.0:
                self.seeds.append(Seed(random.choice(["kelp", "seagrass", "algae"])))
                self.renewal_timer = 0

        # Seed Updates
        for seed in self.seeds[:]:
            settled = seed.update(dt, self.world)
            if settled:
                self.seeds.remove(seed)
                terrain_y = self.world.get_terrain_height(seed.x)
                depth_ratio = self.world.get_depth_ratio(terrain_y)

                # Check if specific plant type can grow here
                if seed.plant_type == 'kelp' and depth_ratio <= KELP_DEPTH_MAX:
                    self.plants.append(Plant(seed.x, terrain_y, "kelp", soil_grid, seed.traits))
                elif seed.plant_type == 'seagrass' and SEAGRASS_DEPTH_MIN <= depth_ratio <= SEAGRASS_DEPTH_MAX:
                    self.plants.append(Plant(seed.x, terrain_y, "seagrass", soil_grid, seed.traits))
                elif seed.plant_type == 'algae' and depth_ratio >= ALGAE_DEPTH_MIN:
                    self.plants.append(Plant(seed.x, terrain_y, "algae", soil_grid, seed.traits))

        # Plant Updates
        for plant in self.plants[:]:
            alive = plant.update(dt, soil_grid)
            
            if not alive:
                # Return nutrients to soil on death
                nutrients = plant.development.get_decomposition_return()
                cell = soil_grid.get_cell_at_pixel(plant.x, plant.base_y)
                if cell:
                    cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + nutrients)
                    # Spread to neighbors
                    for nb, _ in soil_grid.get_neighbors(cell.x, cell.y):
                        nb.nutrient = min(SOIL_MAX_NUTRIENT, nb.nutrient + nutrients * 0.3)
                
                self.plants.remove(plant)
                continue

            # Visible Seed Production
            new_seed = plant.produce_seed(time)
            if new_seed:
                self.seeds.append(new_seed)

            # Bubbles
            if plant.development.is_mature and random.random() < BUBBLE_CHANCE:
                self.bubbles.append({
                    "x": plant.x + random.uniform(-10, 10),
                    "y": plant.base_y - plant.development.current_height * 0.9,
                    "vy": random.uniform(-1.0, -0.5),
                    "life": random.uniform(2.0, 4.0),
                    "size": random.randint(2, 5),
                })

        for bubble in self.bubbles[:]:
            bubble["y"] += bubble["vy"] * 60 * dt
            bubble["life"] -= dt
            if bubble["life"] <= 0 or bubble["y"] < WATER_LINE_Y:
                self.bubbles.remove(bubble)

    def draw(self, screen, time):
        # Draw seeds first so they appear behind plant bodies
        for seed in self.seeds:
            seed.draw(screen)
            
        for plant in self.plants:
            plant.draw_roots(screen, time)

        for plant in self.plants:
            plant.draw(screen, time, self.world.soil_grid)

        for bubble in self.bubbles:
            alpha = max(0, min(255, int(255 * (bubble["life"] / 4.0))))
            pygame.draw.circle(screen, (*BUBBLE_COLOR, alpha), (int(bubble["x"]), int(bubble["y"])), bubble["size"])
