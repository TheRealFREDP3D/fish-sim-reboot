"""World system with dynamic terrain derivation and time-of-day / season lighting"""

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
    NIGHT_OVERLAY_COLOR,
    STAR_COUNT,
    STAR_MAX_ALPHA,
    SEASONAL_PARTICLE_CHANCE,
    LEAF_COLORS,
    SNOW_COLOR,
)
from soil import SoilGrid


class World:
    def __init__(self):
        self.initial_terrain = []
        self._generate_initial_profile()
        self.soil_grid = SoilGrid(self)
        self.water_gradient_surface = pygame.Surface(
            (SCREEN_WIDTH, WORLD_HEIGHT - WATER_LINE_Y)
        )
        self.haze_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        self.night_overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )

        # Reusable ray surface — allocated once, cleared each frame
        self._ray_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )

        # Star positions (world-space x, screen-space y) – static per session
        rng = random.Random(42)
        self.stars = [
            (
                rng.uniform(0, WORLD_WIDTH),
                rng.uniform(0, WATER_LINE_Y - 10),
                rng.uniform(0.4, 1.0),  # size factor
                rng.uniform(0, math.pi * 2),  # twinkle phase
            )
            for _ in range(STAR_COUNT)
        ]

        # Pre-build star surfaces (one per star) so we don't allocate per frame
        self._star_surfs = []
        for _, _, sfactor, _ in self.stars:
            r = max(1, int(sfactor * 2.5))
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            self._star_surfs.append((r, s))

        # Seasonal surface particles (leaves / snow)
        self.season_particles = []

        self.render_water_gradient()
        self._rebuild_haze()

    def cleanup(self):
        """Release pygame surfaces to prevent memory leaks on world reset."""
        self._star_surfs.clear()  # releases all (r, surface) tuples and their surfaces
        self.season_particles.clear()
        self.water_gradient_surface = None
        self.haze_surface = None
        self.night_overlay = None
        self._ray_surface = None

    # ── Terrain generation ─────────────────────────────────────────────────

    def _generate_initial_profile(self):
        beach_end = BEACH_SLOPE_END + random.uniform(-50, 100)
        drop_end = STEEP_DROP_END + random.uniform(-100, 200)
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
                base_y = TERRAIN_BASE_HEIGHT - 50 + math.sin(x * 0.005) * 40

            noise = math.sin(x * noise_scale) * noise_amp + random.uniform(-5, 5)
            self.initial_terrain.append(base_y + noise)

    def get_initial_terrain_height(self, x):
        idx = max(0, min(len(self.initial_terrain) - 1, int(x)))
        return self.initial_terrain[idx]

    def get_terrain_height(self, x):
        cell_x = int(x // SOIL_CELL_SIZE)
        # Add bounds checking for cell_x
        max_cells = WORLD_WIDTH // SOIL_CELL_SIZE
        if cell_x < 0 or cell_x > max_cells:
            return WORLD_HEIGHT - 10

        start_row = int(WATER_LINE_Y // SOIL_CELL_SIZE)
        max_row = int(WORLD_HEIGHT // SOIL_CELL_SIZE)
        for cy in range(start_row, max_row):
            cell = self.soil_grid.get_cell(cell_x, cy)
            if cell and not cell.is_water:
                return cy * SOIL_CELL_SIZE
        return WORLD_HEIGHT - 10

    def get_depth_ratio(self, y):
        return min(max(0, (y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y)), 1.0)

    # ── Static surface builders ────────────────────────────────────────────

    def render_water_gradient(self):
        gradient_height = WORLD_HEIGHT - WATER_LINE_Y
        for y in range(gradient_height):
            ratio = y / gradient_height
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

    def _rebuild_haze(self):
        self.haze_surface.fill((0, 0, 0, 0))
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            alpha = int(ratio * 160)
            pygame.draw.line(
                self.haze_surface, (*HAZE_COLOR, alpha), (0, y), (SCREEN_WIDTH, y)
            )

    # ── Per-frame update ───────────────────────────────────────────────────

    def update(self, dt, time_system):
        if not time_system:
            return

        season_idx = time_system.season_index
        chance = SEASONAL_PARTICLE_CHANCE.get(season_idx, 0.0)
        if chance > 0 and random.random() < chance * 60 * dt:
            self._spawn_season_particle(season_idx)

        for p in self.season_particles[:]:
            p["x"] += p["vx"] * dt * 60
            p["y"] += p["vy"] * dt * 60
            p["life"] -= dt
            p["rot"] = p.get("rot", 0) + p.get("spin", 0) * dt
            if p["life"] <= 0 or p["y"] > SCREEN_HEIGHT:
                self.season_particles.remove(p)

        upwell = time_system.nutrient_upwelling * dt
        if upwell > 0:
            for _ in range(3):
                cx = random.randint(0, WORLD_WIDTH // SOIL_CELL_SIZE)
                cy = random.randint(
                    int(WATER_LINE_Y // SOIL_CELL_SIZE),
                    int(WORLD_HEIGHT // SOIL_CELL_SIZE) - 1,
                )
                cell = self.soil_grid.get_cell(cx, cy)
                if cell and not cell.is_water:
                    from config import SOIL_MAX_NUTRIENT

                    cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + upwell * 10)

    def _spawn_season_particle(self, season_idx):
        if season_idx == 2:  # Autumn leaf
            color = random.choice(LEAF_COLORS)
            self.season_particles.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),
                    "y": -10,
                    "vx": random.uniform(-0.5, 0.5),
                    "vy": random.uniform(0.4, 1.0),
                    "life": random.uniform(6, 14),
                    "size": random.randint(4, 8),
                    "color": color,
                    "rot": random.uniform(0, 360),
                    "spin": random.uniform(-60, 60),
                    "type": "leaf",
                }
            )
        elif season_idx == 3:  # Winter snow
            self.season_particles.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),
                    "y": -6,
                    "vx": random.uniform(-0.2, 0.2),
                    "vy": random.uniform(0.2, 0.6),
                    "life": random.uniform(8, 20),
                    "size": random.randint(2, 4),
                    "color": SNOW_COLOR,
                    "rot": 0,
                    "spin": 0,
                    "type": "snow",
                }
            )

    # ── Drawing ────────────────────────────────────────────────────────────

    def draw(self, screen, camera, time_system=None):
        sky = time_system.get_sky_color() if time_system else SKY_COLOR
        screen.fill(sky)

        # ── Stars ──────────────────────────────────────────────────────────
        if time_system:
            star_alpha = int(
                max(0, (1.0 - time_system.light_level * 2.5)) * STAR_MAX_ALPHA
            )
            if star_alpha > 5:
                anim_t = pygame.time.get_ticks() * 0.001
                for idx, (sx, sy, sfactor, sphase) in enumerate(self.stars):
                    screen_sx = sx - camera.x
                    if screen_sx < -4 or screen_sx > SCREEN_WIDTH + 4:
                        continue
                    twinkle = 0.7 + 0.3 * math.sin(anim_t * 2.0 + sphase)
                    a = int(star_alpha * twinkle)
                    r, star_surf = self._star_surfs[idx]
                    # Reuse the cached surface — just fill with new alpha
                    star_surf.fill((0, 0, 0, 0))
                    pygame.draw.circle(star_surf, (255, 255, 230, a), (r + 1, r + 1), r)
                    screen.blit(star_surf, (int(screen_sx) - r - 1, int(sy) - r - 1))

        # ── Water body ─────────────────────────────────────────────────────
        water_y = WATER_LINE_Y - camera.y
        if water_y < SCREEN_HEIGHT:
            if time_system:
                ll = time_system.light_level
                tint_surf = pygame.Surface(
                    self.water_gradient_surface.get_size(), pygame.SRCALPHA
                )
                dark_alpha = int((1.0 - ll) * 160)
                tint_surf.fill((*NIGHT_OVERLAY_COLOR, dark_alpha))
                blended = self.water_gradient_surface.copy()
                blended.blit(tint_surf, (0, 0))
                screen.blit(blended, (0, water_y))
            else:
                screen.blit(self.water_gradient_surface, (0, water_y))

        # ── Terrain ────────────────────────────────────────────────────────
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

        # ── Light rays ─────────────────────────────────────────────────────
        ray_alpha = (
            time_system.get_light_ray_alpha() if time_system else LIGHT_RAY_ALPHA
        )
        if ray_alpha > 2:
            anim_t = pygame.time.get_ticks() * 0.001
            # Reuse pre-allocated ray surface
            self._ray_surface.fill((0, 0, 0, 0))
            for i in range(LIGHT_RAY_COUNT):
                world_center_x = (i + 0.5) * (WORLD_WIDTH / LIGHT_RAY_COUNT)
                screen_center_x = world_center_x - camera.x * 0.5
                offset = math.sin(anim_t * 0.3 + i * 2) * 120
                ray_x = screen_center_x + offset

                if ray_x < -200 or ray_x > SCREEN_WIDTH + 200:
                    continue

                width_top = 10 + math.sin(anim_t + i) * 5
                width_bottom = 80 + math.sin(anim_t * 0.7 + i) * 30
                for layer in range(3):
                    l_alpha = int(
                        (ray_alpha / (layer + 1)) + math.sin(anim_t * 1.5 + i) * 10
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
                    pygame.draw.polygon(
                        self._ray_surface, (*LIGHT_RAY_COLOR, l_alpha), pts
                    )
            screen.blit(self._ray_surface, (0, 0))

        screen.blit(self.haze_surface, (0, 0))

        # ── Surface glints ─────────────────────────────────────────────────
        if time_system is None or time_system.light_level > 0.2:
            anim_t = pygame.time.get_ticks() * 0.001
            glint_strength = time_system.light_level if time_system else 1.0
            if water_y > -20 and water_y < SCREEN_HEIGHT:
                for i in range(0, SCREEN_WIDTH, 40):
                    world_i = i + camera.x
                    wave = math.sin(anim_t * 2.0 + world_i * 0.05) * 4
                    y_pos = water_y + wave
                    glint_alpha = int(
                        (120 + math.sin(anim_t * 3 + world_i) * 100) * glint_strength
                    )
                    if glint_alpha > 180:
                        glint_size = 2 + (glint_alpha - 180) // 20
                        pygame.draw.circle(
                            screen,
                            (255, 255, 255, glint_alpha // 3),
                            (i, int(y_pos)),
                            glint_size,
                        )

        # ── Night dark overlay ─────────────────────────────────────────────
        if time_system:
            night_alpha = time_system.get_ambient_light_alpha()
            if night_alpha > 5:
                self.night_overlay.fill((*NIGHT_OVERLAY_COLOR, night_alpha))
                screen.blit(self.night_overlay, (0, 0))

        self.soil_grid.draw(screen, camera, pygame.time.get_ticks() * 0.001)

        self._draw_season_particles(screen)

    def _draw_season_particles(self, screen):
        for p in self.season_particles:
            if p["type"] == "leaf":
                surf = pygame.Surface((p["size"] * 2, p["size"]), pygame.SRCALPHA)
                pygame.draw.ellipse(
                    surf, (*p["color"], 200), (0, 0, p["size"] * 2, p["size"])
                )
                rotated = pygame.transform.rotate(surf, p["rot"])
                screen.blit(
                    rotated,
                    (
                        int(p["x"]) - rotated.get_width() // 2,
                        int(p["y"]) - rotated.get_height() // 2,
                    ),
                )
            else:  # snow
                pygame.draw.circle(
                    screen,
                    (*p["color"], 180),
                    (int(p["x"]), int(p["y"])),
                    p["size"],
                )
