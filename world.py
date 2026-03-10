"""World system with dynamic terrain derivation and enhanced volumetric lighting"""

import pygame
import random
import math
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    WATER_LINE_Y,
    BEACH_SLOPE_END,
    STEEP_DROP_END,
    TERRAIN_BASE_HEIGHT,
    SKY_COLOR,
    TERRAIN_COLOR,
    WATER_SURFACE_COLOR,
    WATER_DEEP_COLOR,
    LIGHT_RAY_COUNT,
    LIGHT_RAY_ALPHA,
    SOIL_CELL_SIZE,
    LIGHT_RAY_COLOR,
    HAZE_COLOR,
)
from soil import SoilGrid


class World:
    def __init__(self):
        self.initial_terrain = []
        self._generate_initial_profile()
        self.soil_grid = SoilGrid(self)
        self.water_gradient_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.haze_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        self.render_water_gradient()

    def _generate_initial_profile(self):
        # Randomize key terrain markers
        beach_end = BEACH_SLOPE_END + random.uniform(-50, 100)
        drop_end = STEEP_DROP_END + random.uniform(-100, 200)

        # Noise parameters
        noise_scale = random.uniform(0.01, 0.04)
        noise_amp = random.uniform(10, 30)

        for x in range(WORLD_WIDTH + 1):
            if x < beach_end:
                base_y = WATER_LINE_Y + (x / beach_end * 150)
            elif x < drop_end:
                progress = (x - beach_end) / (drop_end - beach_end)
                base_y = (WATER_LINE_Y + 150) + (
                    progress**2 * (TERRAIN_BASE_HEIGHT - 200)
                )
            else:
                # Add some rolling hills in the deep
                base_y = TERRAIN_BASE_HEIGHT - 50 + math.sin(x * 0.005) * 40

            noise = math.sin(x * noise_scale) * noise_amp + random.uniform(-5, 5)
            self.initial_terrain.append(base_y + noise)

    def get_initial_terrain_height(self, x):
        idx = max(0, min(len(self.initial_terrain) - 1, int(x)))
        return self.initial_terrain[idx]

    def get_terrain_height(self, x):
        cell_x = int(x // SOIL_CELL_SIZE)
        start_row = int(WATER_LINE_Y // SOIL_CELL_SIZE)
        max_row = int(WORLD_HEIGHT // SOIL_CELL_SIZE)
        for cy in range(start_row, max_row):
            cell = self.soil_grid.get_cell(cell_x, cy)
            if cell and not cell.is_water:
                return cy * SOIL_CELL_SIZE
        return WORLD_HEIGHT - 10

    def get_depth_ratio(self, y):
        return min(max(0, (y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y)), 1.0)

    def render_water_gradient(self):
        # Setup static haze surface here instead of init for clarity
        self.haze_surface.fill((0, 0, 0, 0))
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            alpha = int(ratio * 160)
            pygame.draw.line(
                self.haze_surface, (*HAZE_COLOR, alpha), (0, y), (SCREEN_WIDTH, y)
            )

        for y in range(SCREEN_HEIGHT):
            # We use a screen-sized gradient that we'll blit appropriately
            # Or better, we blit it based on camera Y if world height > screen height
            ratio = y / SCREEN_HEIGHT
            color = tuple(
                int(
                    WATER_SURFACE_COLOR[i]
                    + (WATER_DEEP_COLOR[i] - WATER_SURFACE_COLOR[i]) * ratio
                )
                for i in range(3)
            )
            pygame.draw.line(
                self.water_gradient_surface, color, (0, y), (SCREEN_WIDTH, y)
            )

    def draw(self, screen, camera):
        # Draw Sky (static or slightly parallax?)
        screen.fill(SKY_COLOR)

        # Water surface rendering
        water_y = WATER_LINE_Y - camera.y
        if water_y < SCREEN_HEIGHT:
            # Draw water body
            screen.blit(self.water_gradient_surface, (0, max(0, water_y)))

        # Terrain rendering with camera
        points = []
        step = 20
        start_x = int(camera.x // step) * step
        end_x = int((camera.x + SCREEN_WIDTH) // step) * step + step

        for x in range(start_x, end_x + step, step):
            world_x = max(0, min(WORLD_WIDTH, x))
            points.append(camera.apply((world_x, self.get_terrain_height(world_x))))

        if points:
            poly_points = points + [
                (points[-1][0], SCREEN_HEIGHT),
                (points[0][0], SCREEN_HEIGHT),
            ]
            pygame.draw.polygon(screen, TERRAIN_COLOR, poly_points)

        # Light Rays (Parallax effect)
        time = pygame.time.get_ticks() * 0.001
        ray_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(LIGHT_RAY_COUNT):
            # Give rays a world position for parallax
            world_center_x = (i + 0.5) * (WORLD_WIDTH / LIGHT_RAY_COUNT)
            screen_center_x = world_center_x - camera.x * 0.5  # Slight parallax

            offset = math.sin(time * 0.3 + i * 2) * 120
            ray_x = screen_center_x + offset

            # Cull if far off screen
            if ray_x < -200 or ray_x > SCREEN_WIDTH + 200:
                continue

            width_top = 10 + math.sin(time + i) * 5
            width_bottom = 80 + math.sin(time * 0.7 + i) * 30
            for layer in range(3):
                l_alpha = int(
                    (LIGHT_RAY_ALPHA / (layer + 1)) + math.sin(time * 1.5 + i) * 10
                )
                l_alpha = max(0, min(255, l_alpha))
                l_width_t = width_top + layer * 15
                l_width_b = width_bottom + layer * 40
                pts = [
                    (ray_x - l_width_t, water_y),
                    (ray_x + l_width_t, water_y),
                    (ray_x + l_width_b, SCREEN_HEIGHT),
                    (ray_x - l_width_b, SCREEN_HEIGHT),
                ]
                # Filter points to avoid huge polygons when water_y is off-screen
                pygame.draw.polygon(ray_surface, (*LIGHT_RAY_COLOR, l_alpha), pts)
        screen.blit(ray_surface, (0, 0))
        screen.blit(self.haze_surface, (0, 0))

        # Surface glints
        if water_y > -20 and water_y < SCREEN_HEIGHT:
            for i in range(0, SCREEN_WIDTH, 40):
                world_i = i + camera.x  # To keep waves consistent
                wave = math.sin(time * 2.0 + world_i * 0.05) * 4
                y_pos = water_y + wave
                glint_alpha = int(120 + math.sin(time * 3 + world_i) * 100)
                if glint_alpha > 180:
                    glint_size = 2 + (glint_alpha - 180) // 20
                    pygame.draw.circle(
                        screen,
                        (255, 255, 255, glint_alpha // 3),
                        (i, int(y_pos)),
                        glint_size,
                    )

        self.soil_grid.draw(screen, camera, time)
