import pygame
import math
import random
from config import *


class PoopParticle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = random.uniform(0.5, 1.2)
        c_var = random.randint(-10, 10)
        self.color = (90 + c_var, 60 + c_var, 30)
        self.size = random.uniform(2, 4)
        self.rot = random.uniform(0, 360)

    def update(self, dt, world):
        self.y += self.vy * 40 * dt
        self.rot += dt * 50
        ty = world.get_terrain_height(self.x)
        if self.y >= ty:
            cell = world.soil_grid.get_cell_at_pixel(self.x, self.y)
            if cell:
                cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + 0.35)
            return False
        return True

    def draw(self, screen, camera):
        pos = camera.apply((self.x, self.y))
        pts = []
        for i in range(5):
            angle = math.radians(self.rot + i * 72)
            dist = self.size * (0.8 + 0.4 * math.sin(i))
            pts.append(
                (pos[0] + math.cos(angle) * dist, pos[1] + math.sin(angle) * dist)
            )
        pygame.draw.polygon(screen, self.color, pts)


class FishEgg:
    def __init__(
        self,
        x,
        y,
        traits,
        parent1=None,
        parent2=None,
        is_cleaner=False,
        is_predator=False,
        brain=None,
    ):
        self.x, self.y = x, y
        self.traits = traits
        self.parent1 = parent1
        self.parent2 = parent2
        self.is_cleaner = is_cleaner
        self.is_predator = is_predator
        self.brain = brain
        self.timer = FISH_EGG_HATCH_TIME
        self.pulse_offset = random.uniform(0, math.pi * 2)

    def update(self, dt, world):
        self.timer -= dt
        ty = world.get_terrain_height(self.x)
        if self.y < ty - 4:
            self.y += 15 * dt
        return self.timer <= 0

    def draw(self, screen, camera):
        time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(time * 3 + self.pulse_offset) + 1) * 0.5
        base_color = (200, 200, 255) if self.is_cleaner else (255, 180, 100)
        if self.is_predator:
            base_color = (255, 100, 100)
        surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*base_color, 80), (10, 10), 6 + pulse * 2)
        pygame.draw.circle(surf, (255, 255, 255, 150), (10, 10), 7 + pulse, 1)
        core_color = tuple(min(255, c + 50) for c in base_color)
        pygame.draw.circle(surf, core_color, (10, 8), 2 + pulse)
        pos = camera.apply((self.x, self.y))
        screen.blit(surf, (int(pos[0] - 10), int(pos[1] - 10)))
