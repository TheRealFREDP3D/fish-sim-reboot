"""Seed system - floating seeds that settle and grow into plants"""

import pygame
import random
import math
from config import *

class Seed:
    """A floating seed that drifts and can settle on suitable terrain"""

    def __init__(self, plant_type, traits=None):
        self.plant_type = plant_type
        if traits is None:
            self.traits = {
                "max_height_factor": random.uniform(0.85, 1.15),
                "growth_rate_mult": random.uniform(0.9, 1.1),
                "root_aggression": random.uniform(0.8, 1.2),
                "seed_efficiency": random.uniform(0.9, 1.1),
                "glow_intensity": random.uniform(0.8, 1.2),
                "spread_factor": random.uniform(0.8, 1.2),
                "filter_efficiency": random.uniform(0.9, 1.1),
                "branch_density": random.uniform(0.8, 1.2),
                "pulse_speed": random.uniform(0.9, 1.1),
            }
        else:
            self.traits = traits.copy()

        self.x = random.uniform(0, WORLD_WIDTH)
        self.y = random.uniform(WATER_LINE_Y + 20, WORLD_HEIGHT - 100)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(0.5, 1.2)
        self.phase = random.uniform(0, math.pi * 2)
        self.age = 0

    def mutate(self, parent_traits):
        new_traits = {}
        for key, value in parent_traits.items():
            if random.random() < MUTATION_RATE:
                change = random.uniform(-MUTATION_STRENGTH, MUTATION_STRENGTH)
                new_traits[key] = max(0.4, min(2.5, value * (1 + change)))
            else:
                new_traits[key] = value
        return new_traits

    def update(self, dt, world, time_system=None):
        self.age += dt
        if time_system and time_system.season_index == 3:
            return False 

        drift = math.sin(self.age * 1.5 + self.phase) * 0.4
        self.x += (self.vx + drift) * 60 * dt
        self.y += self.vy * 40 * dt
        self.vx *= 0.97
        if self.vy < 0.8: self.vy += dt * 0.5

        if self.x < 0: self.x = WORLD_WIDTH
        elif self.x > WORLD_WIDTH: self.x = 0

        terrain_y = world.get_terrain_height(self.x)
        if self.y >= terrain_y - 3:
            depth_ratio = world.get_depth_ratio(terrain_y)
            
            # Consistently check depth using the centralized plant logic
            from plants import is_valid_depth
            if is_valid_depth(self.plant_type, depth_ratio):
                return True

            self.vy = -0.3
            self.vx = random.uniform(-1.0, 1.0)
            self.y = terrain_y - 8

        return False

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), 10):
            return

        base_color = {
            "kelp": (60, 150, 60), "seagrass": (100, 220, 100), "algae": (40, 110, 40),
            "red_seaweed": (160, 50, 50), "lily_pad": (50, 140, 50), "tube_sponge": (180, 160, 120),
            "fan_coral": (220, 120, 170), "anemone": (140, 80, 200),
        }[self.plant_type]

        brightness = 0.8 + 0.4 * (self.traits["max_height_factor"] - 0.8)
        color = tuple(max(0, min(255, int(c * brightness))) for c in base_color)
        pulse = (math.sin(self.age * 4) + 1) * 0.5
        draw_radius = 3 + pulse * 1.5
        screen_pos = camera.apply((self.x, self.y))

        pygame.draw.circle(screen, color, (int(screen_pos[0]), int(screen_pos[1])), int(draw_radius))
        glow_color = tuple(min(255, c + 70) for c in color)
        pygame.draw.circle(screen, glow_color, (int(screen_pos[0]), int(screen_pos[1])), int(draw_radius + 2), 1)