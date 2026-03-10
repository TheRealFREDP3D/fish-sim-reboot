"""Soil grid system with improved organic sediment rendering"""

import pygame
import random
import math
from config import (
    SOIL_CELL_SIZE,
    SOIL_DEPLETED_COLOR,
    SOIL_FERTILE_COLOR,
    SOIL_BASE_NUTRIENT,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WATER_LINE_Y,
    SOIL_SOLIDIFY_THRESHOLD,
    SOIL_MAX_NUTRIENT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
)


class SoilCell:
    def __init__(self, x, y, initial_nutrient, start_as_water=False):
        self.x, self.y = x, y
        self.nutrient = initial_nutrient
        self.is_water = start_as_water
        self.depletion_timer = 0.0
        # Per-cell variation for organic look
        self.noise_offset = random.uniform(0, 100)
        self.jitter_x = random.uniform(-2, 2)
        self.jitter_y = random.uniform(-2, 2)
        # Pre-calculate some grain offsets for performance
        self.grains = []
        for _ in range(3):
            self.grains.append(
                {
                    "ox": random.uniform(0, SOIL_CELL_SIZE),
                    "oy": random.uniform(0, SOIL_CELL_SIZE),
                    "size": random.uniform(1, 2.5),
                    "color_mod": random.uniform(0.8, 1.2),
                }
            )

    def deplete(self, amount):
        if self.is_water:
            return 0.0
        actual = min(self.nutrient, amount)
        self.nutrient -= actual
        return actual

    def update(self, dt):
        if self.is_water:
            if self.nutrient >= SOIL_SOLIDIFY_THRESHOLD:
                self.is_water = False
        else:
            if self.nutrient <= 0.01:
                self.depletion_timer += dt
                if self.depletion_timer >= 5.0:
                    self.is_water = True
            else:
                self.depletion_timer = 0.0

    def get_color(self, time):
        # Calculate color based on nutrient level
        t = min(1.0, self.nutrient)
        base = tuple(
            int(
                SOIL_DEPLETED_COLOR[i]
                + (SOIL_FERTILE_COLOR[i] - SOIL_DEPLETED_COLOR[i]) * t
            )
            for i in range(3)
        )
        # Organic shading based on position and time
        noise = math.sin(self.x * 0.5 + self.noise_offset + time * 0.2) * 0.5 + 0.5
        shade = tuple(int(c * (0.9 + 0.1 * noise)) for c in base)
        return shade


class SoilGrid:
    def __init__(self, world):
        self.world = world
        self.cell_size = SOIL_CELL_SIZE
        self.cells = {}
        self.generate_soil()

    def generate_soil(self):
        cols = WORLD_WIDTH // self.cell_size + 1
        rows = WORLD_HEIGHT // self.cell_size + 1
        for cx in range(cols):
            for cy in range(rows):
                px = cx * self.cell_size
                py = cy * self.cell_size
                if py < WATER_LINE_Y:
                    continue
                ty = self.world.get_initial_terrain_height(px)
                if py >= ty:
                    initial = max(
                        0.2, min(1.0, SOIL_BASE_NUTRIENT + random.uniform(-0.1, 0.1))
                    )
                    self.cells[(cx, cy)] = SoilCell(cx, cy, initial, False)
                else:
                    self.cells[(cx, cy)] = SoilCell(cx, cy, 0.0, True)

    def get_cell(self, cx, cy):
        return self.cells.get((cx, cy))

    def get_cell_at_pixel(self, px, py):
        return self.get_cell(int(px // self.cell_size), int(py // self.cell_size))

    def pixel_to_cell(self, px, py):
        return (int(px // self.cell_size), int(py // self.cell_size))

    def get_neighbors(self, cx, cy):
        res = []
        for dx, dy in [(0, 1), (-1, 0), (1, 0), (0, -1)]:
            c = self.get_cell(cx + dx, cy + dy)
            if c:
                res.append((c, (dx, dy)))
        return res

    def update(self, dt):
        for cell in self.cells.values():
            cell.update(dt)

        # Soil Nutrient Diffusion
        transfers = {}
        for (cx, cy), c in self.cells.items():
            if c.is_water and c.nutrient < 0.01:
                continue
            for dx, dy in [(0, 1), (1, 0)]:
                nb = self.get_cell(cx + dx, cy + dy)
                if nb:
                    diff = (c.nutrient - nb.nutrient) * 0.02
                    transfers[(cx, cy, dx, dy)] = diff

        for (cx, cy, dx, dy), amt in transfers.items():
            s = self.get_cell(cx, cy)
            t = self.get_cell(cx + dx, cy + dy)
            if s and t:
                s.nutrient = max(0.0, min(SOIL_MAX_NUTRIENT, s.nutrient - amt))
                t.nutrient = max(0.0, min(SOIL_MAX_NUTRIENT, t.nutrient + amt))

    def draw(self, screen, camera, time=0):
        # Only iterate over visible cells
        view = camera.get_view_rect()
        start_cx = max(0, int(view.left // self.cell_size))
        end_cx = min(
            WORLD_WIDTH // self.cell_size, int(view.right // self.cell_size) + 1
        )
        start_cy = max(0, int(view.top // self.cell_size))
        end_cy = min(
            WORLD_HEIGHT // self.cell_size, int(view.bottom // self.cell_size) + 1
        )

        for cx in range(start_cx, end_cx + 1):
            for cy in range(start_cy, end_cy + 1):
                cell = self.get_cell(cx, cy)
                if cell and not cell.is_water:
                    px, py = camera.apply(
                        (
                            cx * self.cell_size + cell.jitter_x,
                            cy * self.cell_size + cell.jitter_y,
                        )
                    )
                    px, py = int(px), int(py)
                    color = cell.get_color(time)

                    # Main organic body
                    rect = pygame.Rect(
                        px - 1, py - 1, self.cell_size + 2, self.cell_size + 2
                    )
                    pygame.draw.rect(screen, color, rect, border_radius=3)

                    # Grain details
                    for grain in cell.grains:
                        g_color = tuple(
                            max(0, min(255, int(c * grain["color_mod"]))) for c in color
                        )
                        gx = px + grain["ox"]
                        gy = py + grain["oy"]
                        pygame.draw.circle(
                            screen, g_color, (int(gx), int(gy)), int(grain["size"])
                        )

                    # Nutrient sparkle for very fertile soil
                    if cell.nutrient > 1.0:
                        sparkle_intensity = int(
                            100 + 155 * (math.sin(time * 3 + cell.noise_offset) + 1) / 2
                        )
                        s_color = (200, 255, sparkle_intensity)
                        sx = px + self.cell_size // 2
                        sy = py + self.cell_size // 2
                        pygame.draw.circle(screen, s_color, (int(sx), int(sy)), 2)
