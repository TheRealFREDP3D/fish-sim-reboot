"""Soil grid system with multiple distinct soil types and organic rendering"""

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

# ── Soil Type Definitions ─────────────────────────────────────────────────────
# Each type: (base_color, fertile_tint, depleted_tint, nutrient_bias, grain_size, grain_count)
SOIL_TYPES = {
    "sand": {
        "base": (210, 195, 155),
        "fertile": (200, 185, 130),
        "depleted": (225, 215, 185),
        "nutrient_bias": 0.55,  # Sandy soil drains nutrients fast
        "grain_size": (1.5, 3.0),
        "grain_count": 5,
        "diffusion_rate": 0.04,  # Fast lateral diffusion
        "description": "Coarse, pale, fast-draining",
    },
    "silt": {
        "base": (160, 140, 110),
        "fertile": (140, 120, 80),
        "depleted": (180, 165, 140),
        "nutrient_bias": 0.90,
        "grain_size": (1.0, 2.0),
        "grain_count": 4,
        "diffusion_rate": 0.025,
        "description": "Fine, brownish, moderately fertile",
    },
    "clay": {
        "base": (130, 90, 70),
        "fertile": (110, 75, 50),
        "depleted": (155, 120, 100),
        "nutrient_bias": 1.10,  # Clay retains nutrients well
        "grain_size": (0.8, 1.5),
        "grain_count": 3,
        "diffusion_rate": 0.01,  # Slow diffusion — nutrients stay put
        "description": "Dense, reddish-brown, nutrient-retaining",
    },
    "organic": {
        "base": (70, 60, 45),
        "fertile": (55, 48, 30),
        "depleted": (100, 85, 65),
        "nutrient_bias": 1.30,  # Rich dark organic matter
        "grain_size": (1.5, 2.5),
        "grain_count": 4,
        "diffusion_rate": 0.02,
        "description": "Dark, nutrient-rich humus",
    },
    "rocky": {
        "base": (100, 95, 90),
        "fertile": (90, 88, 80),
        "depleted": (120, 115, 110),
        "nutrient_bias": 0.35,  # Rocks hold little nutrition
        "grain_size": (2.0, 4.5),
        "grain_count": 3,
        "diffusion_rate": 0.005,
        "description": "Hard, grey, poor in nutrients",
    },
    "peat": {
        "base": (55, 50, 38),
        "fertile": (42, 38, 22),
        "depleted": (80, 72, 58),
        "nutrient_bias": 1.20,
        "grain_size": (1.2, 2.2),
        "grain_count": 5,
        "diffusion_rate": 0.015,
        "description": "Very dark, fibrous, highly fertile",
    },
}

# Depth-based soil type probability weights
# (depth_ratio_min, depth_ratio_max, {type: weight})
DEPTH_SOIL_WEIGHTS = [
    (0.00, 0.15, {"sand": 70, "silt": 20, "rocky": 10}),  # shallow
    (0.15, 0.35, {"sand": 30, "silt": 40, "clay": 20, "organic": 10}),  # mid-shallow
    (
        0.35,
        0.60,
        {"silt": 25, "clay": 35, "organic": 25, "peat": 10, "rocky": 5},
    ),  # mid-deep
    (0.60, 1.00, {"clay": 20, "organic": 30, "peat": 20, "rocky": 30}),  # deep
]


def _get_soil_type_for_depth(depth_ratio, noise_val):
    """Pick a soil type based on depth and a noise value for patchiness."""
    for d_min, d_max, weights in DEPTH_SOIL_WEIGHTS:
        if d_min <= depth_ratio <= d_max:
            # Add noise-based perturbation to make patches
            keys = list(weights.keys())
            wts = list(weights.values())
            # Slightly bias toward a secondary type based on noise
            if noise_val > 0.7 and len(keys) > 1:
                secondary_idx = int(noise_val * len(keys)) % len(keys)
                wts[secondary_idx] = int(wts[secondary_idx] * 1.8)
            total = sum(wts)
            r = random.uniform(0, total)
            cumulative = 0
            for k, w in zip(keys, wts):
                cumulative += w
                if r <= cumulative:
                    return k
            return keys[-1]
    return "silt"


class SoilCell:
    def __init__(self, x, y, initial_nutrient, start_as_water=False, soil_type=None):
        self.x, self.y = x, y
        self.nutrient = initial_nutrient
        self.is_water = start_as_water
        self.depletion_timer = 0.0

        self.soil_type = soil_type or "silt"
        self._type_data = SOIL_TYPES[self.soil_type]

        # Per-cell variation for organic look
        self.noise_offset = random.uniform(0, 100)
        self.jitter_x = random.uniform(-1.5, 1.5)
        self.jitter_y = random.uniform(-1.5, 1.5)

        # Pre-calculate grain offsets
        gc = self._type_data["grain_count"]
        g_min, g_max = self._type_data["grain_size"]
        self.grains = []
        for _ in range(gc):
            self.grains.append(
                {
                    "ox": random.uniform(1, SOIL_CELL_SIZE - 1),
                    "oy": random.uniform(1, SOIL_CELL_SIZE - 1),
                    "size": random.uniform(g_min, g_max),
                    "color_mod": random.uniform(0.75, 1.25),
                }
            )

        # Special detail for rocky soil: crack lines
        self.cracks = []
        if self.soil_type == "rocky" and random.random() < 0.4:
            for _ in range(random.randint(1, 2)):
                ox = random.uniform(0, SOIL_CELL_SIZE)
                oy = random.uniform(0, SOIL_CELL_SIZE)
                dx = random.uniform(-SOIL_CELL_SIZE * 0.6, SOIL_CELL_SIZE * 0.6)
                dy = random.uniform(-SOIL_CELL_SIZE * 0.6, SOIL_CELL_SIZE * 0.6)
                self.cracks.append((ox, oy, ox + dx, oy + dy))

        # Organic/peat: small dark flecks
        self.flecks = []
        if self.soil_type in ("organic", "peat"):
            for _ in range(random.randint(2, 4)):
                self.flecks.append(
                    (
                        random.uniform(1, SOIL_CELL_SIZE - 1),
                        random.uniform(1, SOIL_CELL_SIZE - 1),
                        random.uniform(0.8, 1.5),
                    )
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
        t = min(1.0, self.nutrient / max(0.1, self._type_data["nutrient_bias"]))
        t = max(0.0, t)
        fertile = self._type_data["fertile"]
        depleted = self._type_data["depleted"]
        base = tuple(
            int(depleted[i] + (fertile[i] - depleted[i]) * t) for i in range(3)
        )
        noise = math.sin(self.x * 0.5 + self.noise_offset + time * 0.15) * 0.5 + 0.5
        shade = tuple(int(c * (0.88 + 0.12 * noise)) for c in base)
        return shade


class SoilGrid:
    def __init__(self, world):
        self.world = world
        self.cell_size = SOIL_CELL_SIZE
        self.cells = {}
        self._cell_list = []
        self._neighbours = {}
        self._update_slice = 0
        self.DIFFUSION_SLICES = 4
        self.generate_soil()

    def generate_soil(self):
        cols = WORLD_WIDTH // self.cell_size + 1
        rows = WORLD_HEIGHT // self.cell_size + 1

        # Build a smooth noise field for soil type patchiness
        noise_field = {}
        for cx in range(cols):
            nv = (
                math.sin(cx * 0.07) * 0.4
                + math.sin(cx * 0.19) * 0.3
                + math.sin(cx * 0.41) * 0.2
                + random.uniform(0, 0.1)
            )
            noise_field[cx] = (nv + 1.0) / 2.0  # normalise to [0,1]

        for cx in range(cols):
            for cy in range(rows):
                px = cx * self.cell_size
                py = cy * self.cell_size
                if py < WATER_LINE_Y:
                    continue
                ty = self.world.get_initial_terrain_height(px)
                depth_ratio = max(
                    0.0,
                    min(1.0, (ty - WATER_LINE_Y) / max(1, WORLD_HEIGHT - WATER_LINE_Y)),
                )
                if py >= ty:
                    noise_val = noise_field.get(cx, 0.5)
                    # Add vertical noise variation
                    noise_val = (
                        noise_val + math.sin(cy * 0.13 + cx * 0.05) * 0.25
                    ) % 1.0
                    soil_type = _get_soil_type_for_depth(depth_ratio, noise_val)
                    type_data = SOIL_TYPES[soil_type]
                    base_n = SOIL_BASE_NUTRIENT * type_data["nutrient_bias"]
                    initial = max(
                        0.1,
                        min(SOIL_MAX_NUTRIENT, base_n + random.uniform(-0.12, 0.12)),
                    )
                    self.cells[(cx, cy)] = SoilCell(cx, cy, initial, False, soil_type)
                else:
                    self.cells[(cx, cy)] = SoilCell(cx, cy, 0.0, True, "silt")

        self._rebuild_cell_list()

    def get_cell(self, cx, cy):
        return self.cells.get((cx, cy))

    def get_cell_at_pixel(self, px, py):
        return self.get_cell(int(px // self.cell_size), int(py // self.cell_size))

    def pixel_to_cell(self, px, py):
        return (int(px // self.cell_size), int(py // self.cell_size))

    def get_neighbors(self, cx, cy):
        return self._neighbours.get((cx, cy), [])

    def update(self, dt):
        slice_size = len(self._cell_list) // self.DIFFUSION_SLICES
        start_idx = self._update_slice * slice_size
        end_idx = (
            start_idx + slice_size
            if self._update_slice < self.DIFFUSION_SLICES - 1
            else len(self._cell_list)
        )

        effective_dt = dt * self.DIFFUSION_SLICES
        diffusion_deltas = {}

        for cx, cy, cell in self._cell_list[start_idx:end_idx]:
            cell.update(effective_dt)

            if cell.is_water and cell.nutrient < 0.01:
                continue

            # Use per-type diffusion rate
            diff_rate = SOIL_TYPES[cell.soil_type]["diffusion_rate"]

            cached_neighbours = self.get_neighbors(cx, cy)
            for nb_cell, (dx, dy) in cached_neighbours:
                if (dx, dy) in [(0, 1), (1, 0)]:
                    if not (nb_cell.is_water and nb_cell.nutrient < 0.01):
                        diff = (cell.nutrient - nb_cell.nutrient) * diff_rate

                        if (cx, cy) not in diffusion_deltas:
                            diffusion_deltas[(cx, cy)] = 0.0
                        diffusion_deltas[(cx, cy)] -= diff

                        if (cx + dx, cy + dy) not in diffusion_deltas:
                            diffusion_deltas[(cx + dx, cy + dy)] = 0.0
                        diffusion_deltas[(cx + dx, cy + dy)] += diff

        for (cx, cy), delta in diffusion_deltas.items():
            cell = self.get_cell(cx, cy)
            if cell:
                cell.nutrient = max(0.0, min(SOIL_MAX_NUTRIENT, cell.nutrient + delta))

        self._update_slice = (self._update_slice + 1) % self.DIFFUSION_SLICES

    def draw(self, screen, camera, time=0):
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

                    # Main cell body
                    rect = pygame.Rect(
                        px - 1, py - 1, self.cell_size + 2, self.cell_size + 2
                    )
                    pygame.draw.rect(screen, color, rect, border_radius=2)

                    # Soil-type specific detail rendering
                    if cell.soil_type == "rocky":
                        # Flat grey highlight on upper edge
                        hl = tuple(min(255, c + 30) for c in color)
                        pygame.draw.line(
                            screen, hl, (px, py), (px + self.cell_size, py), 1
                        )
                        # Crack details
                        dark = tuple(max(0, c - 40) for c in color)
                        for x0, y0, x1, y1 in cell.cracks:
                            pygame.draw.line(
                                screen,
                                dark,
                                (int(px + x0), int(py + y0)),
                                (int(px + x1), int(py + y1)),
                                1,
                            )

                    elif cell.soil_type in ("organic", "peat"):
                        # Dark flecks of decomposed matter
                        fleck_col = tuple(max(0, c - 35) for c in color)
                        for fx, fy, fs in cell.flecks:
                            pygame.draw.circle(
                                screen, fleck_col, (int(px + fx), int(py + fy)), int(fs)
                            )

                    elif cell.soil_type == "sand":
                        # Brighter sparkle grains
                        for grain in cell.grains:
                            g_col = tuple(
                                max(0, min(255, int(c * grain["color_mod"])))
                                for c in color
                            )
                            gx = px + grain["ox"]
                            gy = py + grain["oy"]
                            pygame.draw.circle(
                                screen, g_col, (int(gx), int(gy)), int(grain["size"])
                            )

                    elif cell.soil_type == "clay":
                        # Slight horizontal lamination lines
                        if cy % 2 == 0:
                            lam = tuple(max(0, c - 18) for c in color)
                            pygame.draw.line(
                                screen,
                                lam,
                                (px, py + self.cell_size // 2),
                                (px + self.cell_size, py + self.cell_size // 2),
                                1,
                            )

                    else:
                        # silt / default: subtle grains
                        for grain in cell.grains:
                            g_col = tuple(
                                max(0, min(255, int(c * grain["color_mod"])))
                                for c in color
                            )
                            gx = px + grain["ox"]
                            gy = py + grain["oy"]
                            pygame.draw.circle(
                                screen, g_col, (int(gx), int(gy)), int(grain["size"])
                            )

                    # Nutrient sparkle for very fertile cells (all types)
                    if cell.nutrient > 1.1:
                        sparkle_intensity = int(
                            80 + 120 * (math.sin(time * 3 + cell.noise_offset) + 1) / 2
                        )
                        s_color = (180, 240, sparkle_intensity)
                        sx = px + self.cell_size // 2
                        sy = py + self.cell_size // 2
                        pygame.draw.circle(screen, s_color, (int(sx), int(sy)), 2)

    def _rebuild_cell_list(self):
        self._cell_list = [(cx, cy, cell) for (cx, cy), cell in self.cells.items()]
        self._neighbours = {}
        for (cx, cy), cell in self.cells.items():
            neighbours = []
            for dx, dy in [(0, 1), (-1, 1), (1, 1), (-1, 0), (1, 0), (0, -1), (-1, -1), (1, -1)]:
                nb = self.get_cell(cx + dx, cy + dy)
                if nb:
                    neighbours.append((nb, (dx, dy)))
            self._neighbours[(cx, cy)] = neighbours
