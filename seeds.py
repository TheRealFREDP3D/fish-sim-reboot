"""Seed system - floating seeds that settle and grow into plants"""

import pygame
import random
import math
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    WATER_LINE_Y,
    MUTATION_RATE,
    MUTATION_STRENGTH,
    KELP_DEPTH_MAX,
    SEAGRASS_DEPTH_MIN,
    SEAGRASS_DEPTH_MAX,
    ALGAE_DEPTH_MIN,
)


class Seed:
    """A floating seed that drifts and can settle on suitable terrain"""

    def __init__(self, plant_type, traits=None):
        self.plant_type = plant_type
        # Heritable traits - if None, generate random starting variation
        if traits is None:
            self.traits = {
                "max_height_factor": random.uniform(0.85, 1.15),
                "growth_rate_mult": random.uniform(0.9, 1.1),
                "root_aggression": random.uniform(0.8, 1.2),
                "seed_efficiency": random.uniform(0.9, 1.1),
            }
        else:
            self.traits = traits.copy()

        self.x = random.uniform(0, WORLD_WIDTH)
        self.y = random.uniform(WATER_LINE_Y + 20, WORLD_HEIGHT - 100)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(0.5, 1.2)  # Downward drift
        self.phase = random.uniform(0, math.pi * 2)
        self.age = 0

    def mutate(self, parent_traits):
        """Create a slightly mutated copy of traits for offspring"""
        new_traits = {}
        for key, value in parent_traits.items():
            if random.random() < MUTATION_RATE:
                change = random.uniform(-MUTATION_STRENGTH, MUTATION_STRENGTH)
                new_traits[key] = max(0.4, min(2.5, value * (1 + change)))
            else:
                new_traits[key] = value
        return new_traits

    def update(self, dt, world):
        """Update position with gentle drifting and water resistance"""
        self.age += dt

        # Horizontal drift
        drift = math.sin(self.age * 1.5 + self.phase) * 0.4
        self.x += (self.vx + drift) * 60 * dt

        # Vertical descent
        self.y += self.vy * 40 * dt

        # Slow down initial "ejection" velocity
        self.vx *= 0.97
        if self.vy < 0.8:
            self.vy += dt * 0.5

        # Wrap horizontally
        if self.x < 0:
            self.x = WORLD_WIDTH
        elif self.x > WORLD_WIDTH:
            self.x = 0

        # Check if settled on terrain
        terrain_y = world.get_terrain_height(self.x)
        if self.y >= terrain_y - 3:
            depth_ratio = world.get_depth_ratio(terrain_y)
            # Conditions for settling
            if self.plant_type == "kelp" and depth_ratio <= KELP_DEPTH_MAX:
                return True
            elif (
                self.plant_type == "seagrass"
                and SEAGRASS_DEPTH_MIN <= depth_ratio <= SEAGRASS_DEPTH_MAX
            ):
                return True
            elif self.plant_type == "algae" and depth_ratio >= ALGAE_DEPTH_MIN:
                return True

            # Wrong depth or habitat - bounce and keep drifting
            self.vy = -0.3
            self.vx = random.uniform(-1.0, 1.0)
            self.y = terrain_y - 8

        return False

    def draw(self, screen, camera):
        """Draw seed as small dot with slight trait-based color variation"""
        # Culling
        if not camera.is_visible((self.x, self.y), 10):
            return

        base_color = {
            "kelp": (60, 150, 60),
            "seagrass": (100, 220, 100),
            "algae": (40, 110, 40),
        }[self.plant_type]

        # Slight tint based on max_height_factor
        brightness = 0.8 + 0.4 * (self.traits["max_height_factor"] - 0.8)
        color = tuple(max(0, min(255, int(c * brightness))) for c in base_color)

        # Pulsing core
        pulse = (math.sin(self.age * 4) + 1) * 0.5
        draw_radius = 3 + pulse * 1.5

        # Apply camera transformation
        screen_pos = camera.apply((self.x, self.y))

        pygame.draw.circle(
            screen, color, (int(screen_pos[0]), int(screen_pos[1])), int(draw_radius)
        )
        # Add subtle glow
        glow_color = tuple(min(255, c + 70) for c in color)
        pygame.draw.circle(
            screen,
            glow_color,
            (int(screen_pos[0]), int(screen_pos[1])),
            int(draw_radius + 2),
            1,
        )
