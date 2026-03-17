"""Particle system for floating sediment and plankton"""

import pygame
import random
import math
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    WATER_LINE_Y,
    PARTICLE_MIN_SIZE,
    PARTICLE_MAX_SIZE,
    PARTICLE_MAX_SPEED,
    SEDIMENT_COLOR,
    PLANKTON_COLOR,
    PLANKTON_COLORS,
    PLANKTON_BASE_RADIUS_MIN,
    PLANKTON_BASE_RADIUS_MAX,
    PARTICLE_ALPHA,
    SEDIMENT_COUNT,
    PLANKTON_COUNT,
)


class EatEffect:
    """Burst effect shown when a fish eats a plankton particle."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.age = 0.0
        self.duration = 0.45
        self.sparks = [
            {
                "angle": random.uniform(0, math.pi * 2),
                "speed": random.uniform(20, 55),
                "size": random.uniform(1.5, 3.5),
            }
            for _ in range(7)
        ]

    def update(self, dt):
        self.age += dt
        return self.age < self.duration

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), 60):
            return
        t = self.age / self.duration
        alpha = int(255 * (1.0 - t) ** 1.5)
        screen_pos = camera.apply((self.x, self.y))
        sx, sy = int(screen_pos[0]), int(screen_pos[1])

        ring_r = int(4 + t * 18)
        ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surf, (*self.color, max(0, alpha)), (ring_r + 2, ring_r + 2), ring_r, 2
        )
        screen.blit(ring_surf, (sx - ring_r - 2, sy - ring_r - 2))

        for spark in self.sparks:
            dist = spark["speed"] * t
            px = sx + math.cos(spark["angle"]) * dist
            py = sy + math.sin(spark["angle"]) * dist
            spark_alpha = max(0, int(alpha * 0.8))
            spark_surf = pygame.Surface(
                (int(spark["size"] * 2 + 2), int(spark["size"] * 2 + 2)),
                pygame.SRCALPHA,
            )
            pygame.draw.circle(
                spark_surf,
                (*self.color, spark_alpha),
                (int(spark["size"] + 1), int(spark["size"] + 1)),
                int(spark["size"]),
            )
            screen.blit(
                spark_surf, (int(px) - int(spark["size"]), int(py) - int(spark["size"]))
            )


class MatingBurstEffect:
    """Pink/red burst when two fish mate and lay eggs."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.age = 0.0
        self.duration = 0.9
        self.sparks = [
            {
                "angle": random.uniform(0, math.pi * 2),
                "speed": random.uniform(30, 80),
                "size": random.uniform(2.0, 5.0),
                "color": random.choice(
                    [
                        (255, 100, 150),
                        (255, 180, 200),
                        (255, 80, 120),
                        (255, 220, 240),
                        (255, 140, 180),
                    ]
                ),
            }
            for _ in range(14)
        ]

    def update(self, dt):
        self.age += dt
        return self.age < self.duration

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), 100):
            return
        t = self.age / self.duration
        alpha = int(255 * (1.0 - t) ** 1.2)
        screen_pos = camera.apply((self.x, self.y))
        sx, sy = int(screen_pos[0]), int(screen_pos[1])

        # Expanding ring
        ring_r = int(8 + t * 40)
        ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surf,
            (255, 120, 180, max(0, alpha // 2)),
            (ring_r + 2, ring_r + 2),
            ring_r,
            3,
        )
        screen.blit(ring_surf, (sx - ring_r - 2, sy - ring_r - 2))

        for spark in self.sparks:
            dist = spark["speed"] * t
            px = sx + math.cos(spark["angle"]) * dist
            py = sy + math.sin(spark["angle"]) * dist
            spark_alpha = max(0, int(alpha * 0.9))
            r = int(spark["size"] * (1.0 - t * 0.5))
            if r < 1:
                continue
            spark_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                spark_surf, (*spark["color"], spark_alpha), (r + 1, r + 1), r
            )
            screen.blit(spark_surf, (int(px) - r, int(py) - r))


class Particle:
    """Single floating particle (sediment or plankton)"""

    def __init__(self, is_plankton=False):
        self.is_plankton = is_plankton
        self.reset()

    def reset(self, spawn_x=None, spawn_y=None):
        """Reset to a random position, or to a specific plant-tip location."""
        if spawn_x is not None and spawn_y is not None:
            self.x = spawn_x + random.uniform(-8, 8)
            self.y = spawn_y + random.uniform(-8, 8)
        else:
            self.x = random.uniform(0, WORLD_WIDTH)
            self.y = random.uniform(WATER_LINE_Y + 10, WORLD_HEIGHT - 20)

        self.size = random.randint(PARTICLE_MIN_SIZE, PARTICLE_MAX_SIZE)
        speed_factor = 0.6 if self.is_plankton else 1.0
        self.speed_x = (
            random.uniform(-PARTICLE_MAX_SPEED, PARTICLE_MAX_SPEED) * speed_factor
        )
        self.speed_y = (
            random.uniform(0.05, 0.2) if self.is_plankton else random.uniform(0.05, 0.3)
        )
        self.phase = random.uniform(0, math.pi * 2)
        self.spin_phase = random.uniform(0, math.pi * 2)
        self.spin_speed = random.uniform(0.5, 1.5)

        if self.is_plankton:
            base = random.choice(PLANKTON_COLORS)
            v = random.randint(-20, 20)
            self.color = tuple(max(0, min(255, c + v)) for c in base)
            self.nutrition = random.uniform(0.6, 1.4)
        else:
            color_var = random.randint(-30, 30)
            self.color = tuple(max(0, min(255, c + color_var)) for c in SEDIMENT_COLOR)
            self.nutrition = 1.0

        self.variant = random.randint(0, 2) if self.is_plankton else 0

    def update(self, time, depth_bias=0.0):
        drift_x = math.sin(time * 0.5 + self.phase) * 0.4
        drift_y = math.cos(time * 0.3 + self.phase) * 0.2

        if self.is_plankton:
            self.spin_phase += 0.016 * self.spin_speed
            water_column = WORLD_HEIGHT - WATER_LINE_Y
            target_ratio = 0.5 - depth_bias * 0.35
            target_y = WATER_LINE_Y + target_ratio * water_column
            dy_migrate = (target_y - self.y) * 0.001
            self.y += (self.speed_y + drift_y + dy_migrate) * 1.0
        else:
            self.y += self.speed_y + drift_y

        self.x += self.speed_x + drift_x

        if self.x < 0:
            self.x = WORLD_WIDTH
        elif self.x > WORLD_WIDTH:
            self.x = 0

        if self.y < WATER_LINE_Y + 5 or self.y > WORLD_HEIGHT - 5:
            self.reset()

    def _draw_plankton_shape(self, surface, color, cx, cy, r, spin):
        """Draw a distinctive plankton organism shape."""
        if self.variant == 0:
            arm = r
            thick = max(1, int(r * 0.55))
            pygame.draw.rect(surface, color, (cx - arm, cy - thick, arm * 2, thick * 2))
            pygame.draw.rect(surface, color, (cx - thick, cy - arm, thick * 2, arm * 2))
            pygame.draw.circle(surface, color, (cx - arm, cy), thick)
            pygame.draw.circle(surface, color, (cx + arm, cy), thick)
            pygame.draw.circle(surface, color, (cx, cy - arm), thick)
            pygame.draw.circle(surface, color, (cx, cy + arm), thick)

        elif self.variant == 1:
            points = []
            for i in range(12):
                a = spin + i * math.pi / 6
                ri = r if i % 2 == 0 else r * 0.45
                points.append((cx + math.cos(a) * ri, cy + math.sin(a) * ri))
            if len(points) >= 3:
                pygame.draw.polygon(surface, color, points)

        else:
            body_w = max(2, int(r * 1.4))
            body_h = max(2, int(r * 0.7))
            tail_len = int(r * 1.2)
            cos_s, sin_s = math.cos(spin), math.sin(spin)
            body_pts = []
            for angle in range(0, 360, 20):
                ra = math.radians(angle)
                bx = math.cos(ra) * body_w
                by = math.sin(ra) * body_h
                rx = cx + bx * cos_s - by * sin_s
                ry = cy + bx * sin_s + by * cos_s
                body_pts.append((rx, ry))
            if len(body_pts) >= 3:
                pygame.draw.polygon(surface, color, body_pts)
            tail_end = (
                cx - math.cos(spin) * (body_w + tail_len),
                cy - math.sin(spin) * (body_w + tail_len),
            )
            tail_base1 = (
                cx - math.cos(spin) * body_w + math.sin(spin) * 2,
                cy - math.sin(spin) * body_w - math.cos(spin) * 2,
            )
            tail_base2 = (
                cx - math.cos(spin) * body_w - math.sin(spin) * 2,
                cy - math.sin(spin) * body_w + math.cos(spin) * 2,
            )
            pygame.draw.polygon(surface, color, [tail_base1, tail_base2, tail_end])


class ParticleSystem:
    def __init__(self):
        self.particles = []
        for _ in range(SEDIMENT_COUNT * 3):
            self.particles.append(Particle(is_plankton=False))
        for _ in range(PLANKTON_COUNT):
            self.particles.append(Particle(is_plankton=True))
        self.particle_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        self.eat_effects: list[EatEffect] = []
        self.mating_effects: list[MatingBurstEffect] = []
        # Hearts are imported lazily to avoid circular imports
        self._heart_particles: list = []

    # ── Public helpers called by other systems ─────────────────────────────

    def spawn_plankton_at(self, x, y, color_hint=None):
        from config import PLANKTON_HARD_CAP

        plankton_count = sum(1 for p in self.particles if p.is_plankton)
        if plankton_count >= PLANKTON_HARD_CAP:
            return

        p = Particle(is_plankton=True)
        p.reset(spawn_x=x, spawn_y=y)
        p.speed_y = random.uniform(-0.6, -0.1)
        p.speed_x = random.uniform(-0.4, 0.4)

        if color_hint is not None:
            base = random.choice(PLANKTON_COLORS)
            blend = 0.35
            blended = tuple(
                max(0, min(255, int(base[i] * (1 - blend) + color_hint[i] * blend)))
                for i in range(3)
            )
            v = random.randint(-15, 15)
            p.color = tuple(max(0, min(255, c + v)) for c in blended)

        self.particles.append(p)

    def spawn_eat_effect(self, x, y, color=None):
        if color is None:
            color = (120, 230, 160)
        self.eat_effects.append(EatEffect(x, y, color))

    def spawn_mating_burst(self, x, y):
        """Call when two fish successfully mate / lay eggs."""
        self.mating_effects.append(MatingBurstEffect(x, y))
        # Spawn a cluster of heart particles
        from environment_objects import HeartParticle

        for _ in range(6):
            self._heart_particles.append(HeartParticle(x, y))

    def spawn_heart(self, x, y):
        """Spawn a single heart for fish currently in MATING state (called per-frame, rarely)."""
        from environment_objects import HeartParticle

        self._heart_particles.append(HeartParticle(x, y))

    def add_bubble(self, x, y):
        p = Particle(is_plankton=False)
        p.x = x
        p.y = y
        p.speed_y = -random.uniform(0.5, 1.2)
        p.speed_x = random.uniform(-0.2, 0.2)
        p.color = (200, 230, 255)
        p.size = random.randint(1, 3)
        self.particles.append(p)

    # ── Update / Draw ──────────────────────────────────────────────────────

    def update_with_dt(self, dt, time_system=None):
        """Preferred update — accepts real dt with optimized particle management."""
        depth_bias = time_system.plankton_depth_bias if time_system else 0.0
        for particle in self.particles:
            particle.update(pygame.time.get_ticks() * 0.001, depth_bias=depth_bias)

        # In-place filtering for better performance
        self.eat_effects = [e for e in self.eat_effects if e.update(dt)]
        self.mating_effects = [e for e in self.mating_effects if e.update(dt)]
        self._heart_particles = [h for h in self._heart_particles if h.update(dt)]

    def draw(self, screen, camera, time_system=None):
        self.particle_surface.fill((0, 0, 0, 0))
        view = camera.get_view_rect()
        margin = 60

        biolumin_alpha = time_system.get_bioluminescence_alpha() if time_system else 0
        time_val = pygame.time.get_ticks() * 0.001

        for particle in self.particles:
            if not (view.left - margin < particle.x < view.right + margin):
                continue
            if not (view.top - margin < particle.y < view.bottom + margin):
                continue

            screen_pos = camera.apply((particle.x, particle.y))
            sx, sy = int(screen_pos[0]), int(screen_pos[1])

            if particle.is_plankton:
                pulse = (math.sin(time_val * 3.0 + particle.phase) + 1) * 0.5
                base_r = PLANKTON_BASE_RADIUS_MIN + particle.nutrition * (
                    PLANKTON_BASE_RADIUS_MAX - PLANKTON_BASE_RADIUS_MIN
                )
                r = max(1, int(base_r + pulse * 0.8))

                brightness = 0.7 + 0.3 * particle.nutrition * (0.8 + 0.2 * pulse)
                col = tuple(min(255, int(c * brightness)) for c in particle.color)

                if biolumin_alpha > 0:
                    glow_r = r + 3 + int(pulse * 2)
                    glow_alpha = min(
                        255, int(biolumin_alpha * 1.4 * particle.nutrition)
                    )
                    glow_col = (
                        min(255, col[0] + 40),
                        min(255, col[1] + 80),
                        min(255, col[2] + 60),
                    )
                    glow_surf = pygame.Surface(
                        (glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA
                    )
                    pygame.draw.circle(
                        glow_surf,
                        (*glow_col, glow_alpha),
                        (glow_r + 1, glow_r + 1),
                        glow_r,
                    )
                    self.particle_surface.blit(
                        glow_surf, (sx - glow_r - 1, sy - glow_r - 1)
                    )

                shape_size = (r + 3) * 2 + 4
                shape_surf = pygame.Surface((shape_size, shape_size), pygame.SRCALPHA)
                cx, cy = shape_size // 2, shape_size // 2
                particle._draw_plankton_shape(
                    shape_surf, (*col, 220), cx, cy, r, particle.spin_phase
                )
                nucleus_r = max(1, r // 3)
                bright_col = tuple(min(255, c + 80) for c in col)
                pygame.draw.circle(shape_surf, (*bright_col, 255), (cx, cy), nucleus_r)
                self.particle_surface.blit(
                    shape_surf, (sx - shape_size // 2, sy - shape_size // 2)
                )

            else:
                alpha = PARTICLE_ALPHA + random.randint(-20, 20)
                pygame.draw.circle(
                    self.particle_surface,
                    (*particle.color, max(0, min(255, alpha))),
                    (sx, sy),
                    particle.size,
                )

        screen.blit(self.particle_surface, (0, 0))

        for effect in self.eat_effects:
            effect.draw(screen, camera)
        for effect in self.mating_effects:
            effect.draw(screen, camera)
        for heart in self._heart_particles:
            heart.draw(screen, camera)
