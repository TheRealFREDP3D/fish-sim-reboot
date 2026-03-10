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
    PARTICLE_ALPHA,
    SEDIMENT_COUNT,
    PLANKTON_COUNT,
)


class Particle:
    """Single floating particle (sediment or plankton)"""

    def __init__(self, is_plankton=False):
        self.is_plankton = is_plankton
        self.reset()

    def reset(self):
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
        base_color = PLANKTON_COLOR if self.is_plankton else SEDIMENT_COLOR
        color_var = random.randint(-30, 30)
        self.color = tuple(max(0, min(255, c + color_var)) for c in base_color)

    def update(self, time):
        drift_x = math.sin(time * 0.5 + self.phase) * 0.4
        drift_y = math.cos(time * 0.3 + self.phase) * 0.2
        self.x += self.speed_x + drift_x
        self.y += self.speed_y + drift_y

        if self.x < 0:
            self.x = WORLD_WIDTH
        elif self.x > WORLD_WIDTH:
            self.x = 0

        if self.y < WATER_LINE_Y + 5 or self.y > WORLD_HEIGHT - 5:
            self.reset()


class ParticleSystem:
    def __init__(self):
        self.particles = []
        # Increase counts for larger world
        for _ in range(SEDIMENT_COUNT * 3):
            self.particles.append(Particle(is_plankton=False))
        for _ in range(PLANKTON_COUNT * 3):
            self.particles.append(Particle(is_plankton=True))
        # Batch rendering surface
        self.particle_surface = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )

    def update(self, time):
        for particle in self.particles:
            particle.update(time)

    def draw(self, screen, camera):
        # Clear batch surface
        self.particle_surface.fill((0, 0, 0, 0))

        # Batch draw all particles
        view = camera.get_view_rect()
        margin = 50
        for particle in self.particles:
            # Simple culling
            if view.left - margin < particle.x < view.right + margin:
                if view.top - margin < particle.y < view.bottom + margin:
                    alpha = PARTICLE_ALPHA + random.randint(-20, 20)
                    color_with_alpha = (*particle.color, max(0, min(255, alpha)))
                    # Render relative to camera on the batch surface
                    screen_pos = camera.apply((particle.x, particle.y))
                    pygame.draw.circle(
                        self.particle_surface,
                        color_with_alpha,
                        (int(screen_pos[0]), int(screen_pos[1])),
                        particle.size,
                    )

        # Single blit for all particles
        screen.blit(self.particle_surface, (0, 0))
