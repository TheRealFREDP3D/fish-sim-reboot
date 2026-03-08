""" World system with dynamic terrain derivation and enhanced volumetric lighting """
import pygame
import random
import math
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WATER_LINE_Y, BEACH_SLOPE_END, STEEP_DROP_END,
    TERRAIN_BASE_HEIGHT, SKY_COLOR, BEACH_COLOR, TERRAIN_COLOR, TERRAIN_DARK_COLOR,
    WATER_SURFACE_COLOR, WATER_DEEP_COLOR, LIGHT_RAY_COUNT, LIGHT_RAY_ALPHA,
    SOIL_CELL_SIZE, LIGHT_RAY_COLOR, HAZE_COLOR
)
from soil import SoilGrid

class World:
    def __init__(self):
        self.initial_terrain = []
        self._generate_initial_profile()
        self.soil_grid = SoilGrid(self)
        self.water_gradient_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - WATER_LINE_Y))
        self.render_water_gradient()
        self.haze_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(WATER_LINE_Y, SCREEN_HEIGHT):
            ratio = (y - WATER_LINE_Y) / (SCREEN_HEIGHT - WATER_LINE_Y)
            alpha = int(ratio * 140)
            pygame.draw.line(self.haze_surface, (*HAZE_COLOR, alpha), (0, y), (SCREEN_WIDTH, y))

    def _generate_initial_profile(self):
        for x in range(SCREEN_WIDTH + 1):
            if x < BEACH_SLOPE_END:
                base_y = WATER_LINE_Y + (x / BEACH_SLOPE_END * 150)
            elif x < STEEP_DROP_END:
                progress = (x - BEACH_SLOPE_END) / (STEEP_DROP_END - BEACH_SLOPE_END)
                base_y = (WATER_LINE_Y + 150) + (progress**2 * (TERRAIN_BASE_HEIGHT - 200))
            else:
                base_y = TERRAIN_BASE_HEIGHT - 50
            noise = math.sin(x * 0.02) * 15 + random.uniform(-3, 3)
            self.initial_terrain.append(base_y + noise)

    def get_initial_terrain_height(self, x):
        idx = max(0, min(len(self.initial_terrain)-1, int(x)))
        return self.initial_terrain[idx]

    def get_terrain_height(self, x):
        cell_x = int(x // SOIL_CELL_SIZE)
        start_row = int(WATER_LINE_Y // SOIL_CELL_SIZE)
        max_row = int(SCREEN_HEIGHT // SOIL_CELL_SIZE)
        for cy in range(start_row, max_row):
            cell = self.soil_grid.get_cell(cell_x, cy)
            if cell and not cell.is_water:
                return cy * SOIL_CELL_SIZE
        return SCREEN_HEIGHT - 10

    def get_depth_ratio(self, y):
        return min(max(0, (y - WATER_LINE_Y) / (SCREEN_HEIGHT - WATER_LINE_Y)), 1.0)

    def render_water_gradient(self):
        for y in range(SCREEN_HEIGHT - WATER_LINE_Y):
            ratio = self.get_depth_ratio(WATER_LINE_Y + y)
            color = tuple(int(WATER_SURFACE_COLOR[i] + (WATER_DEEP_COLOR[i] - WATER_SURFACE_COLOR[i]) * ratio) for i in range(3))
            pygame.draw.line(self.water_gradient_surface, color, (0, y), (SCREEN_WIDTH, y))

    def draw(self, screen):
        screen.fill(SKY_COLOR, (0, 0, SCREEN_WIDTH, WATER_LINE_Y))
        screen.blit(self.water_gradient_surface, (0, WATER_LINE_Y))
        points = []
        for x in range(0, SCREEN_WIDTH + 1, 15):
            points.append((x, self.get_terrain_height(x)))
        poly_points = points + [(SCREEN_WIDTH, SCREEN_HEIGHT), (0, SCREEN_HEIGHT)]
        pygame.draw.polygon(screen, TERRAIN_COLOR, poly_points)

        time = pygame.time.get_ticks() * 0.001
        ray_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(LIGHT_RAY_COUNT):
            center_x = (i + 0.5) * (SCREEN_WIDTH / LIGHT_RAY_COUNT)
            offset = math.sin(time * 0.3 + i * 2) * 120
            ray_x = center_x + offset
            width_top = 10 + math.sin(time + i) * 5
            width_bottom = 80 + math.sin(time * 0.7 + i) * 30
            for layer in range(3):
                l_alpha = int((LIGHT_RAY_ALPHA / (layer + 1)) + math.sin(time * 1.5 + i) * 10)
                l_alpha = max(0, min(255, l_alpha))
                l_width_t = width_top + layer * 15
                l_width_b = width_bottom + layer * 40
                pts = [
                    (ray_x - l_width_t, WATER_LINE_Y),
                    (ray_x + l_width_t, WATER_LINE_Y),
                    (ray_x + l_width_b, SCREEN_HEIGHT),
                    (ray_x - l_width_b, SCREEN_HEIGHT)
                ]
                pygame.draw.polygon(ray_surface, (*LIGHT_RAY_COLOR, l_alpha), pts)
        screen.blit(ray_surface, (0, 0))
        screen.blit(self.haze_surface, (0, 0))

        for i in range(0, SCREEN_WIDTH, 20):
            wave = math.sin(time * 2.0 + i * 0.05) * 4
            y_pos = WATER_LINE_Y + wave
            glint_alpha = int(120 + math.sin(time * 3 + i) * 100)
            if glint_alpha > 180:
                glint_size = 2 + (glint_alpha - 180) // 20
                pygame.draw.circle(screen, (255, 255, 255, glint_alpha // 3), (i, int(y_pos)), glint_size)

        self.soil_grid.draw(screen, time)
