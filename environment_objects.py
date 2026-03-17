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
        self.nutrition = 0.8  # Added for CleanerFish consumption logic

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


class HeartParticle:
    """Floating heart for mating display."""

    def __init__(self, x, y):
        self.x = x + random.uniform(-20, 20)
        self.y = y + random.uniform(-10, 5)
        self.vy = random.uniform(-0.6, -0.2)
        self.vx = random.uniform(-0.3, 0.3)
        self.life = random.uniform(1.2, 2.2)
        self.max_life = self.life
        self.size = random.uniform(5, 10)

    def update(self, dt):
        self.x += self.vx * 40 * dt
        self.y += self.vy * 40 * dt
        self.vy -= 0.01 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, screen, camera):
        pos = camera.apply((self.x, self.y))
        t = self.life / self.max_life
        alpha = int(255 * t * t)
        size = self.size * (0.6 + 0.4 * t)
        self._draw_heart(screen, int(pos[0]), int(pos[1]), size, alpha)

    @staticmethod
    def _draw_heart(screen, cx, cy, size, alpha):
        surf = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
        r = int(size)
        pygame.draw.circle(surf, (255, 80, 120, alpha), (r, r), r)
        pygame.draw.circle(surf, (255, 80, 120, alpha), (r * 3, r), r)
        pts = [(0, r), (r * 4, r), (r * 2, r * 4)]
        pygame.draw.polygon(surf, (255, 80, 120, alpha), pts)
        screen.blit(surf, (cx - r * 2, cy - r * 2))


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
        self.parent1, self.parent2 = parent1, parent2
        self.is_cleaner, self.is_predator = is_cleaner, is_predator
        self.brain = brain
        self.timer = FISH_EGG_HATCH_TIME
        self.pulse_offset = random.uniform(0, math.pi * 2)
        self.x += random.uniform(-18, 18)
        self.y += random.uniform(-8, 8)

    def update(self, dt, world):
        self.timer -= dt
        ty = world.get_terrain_height(self.x)
        if self.y < ty - 4:
            self.y += 15 * dt
        return self.timer <= 0

    def draw(self, screen, camera):
        time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(time * 3 + self.pulse_offset) + 1) * 0.5
        if self.is_predator:
            base_color, glow_color = (255, 80, 80), (255, 160, 160)
        elif self.is_cleaner:
            base_color, glow_color = (100, 200, 255), (180, 230, 255)
        else:
            base_color, glow_color = (255, 210, 80), (255, 240, 160)

        egg_r = 9 + pulse * 3
        surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        cx, cy = 25, 25
        pygame.draw.circle(surf, (*glow_color, 60), (cx, cy), int(egg_r + 8))
        pygame.draw.circle(surf, (*glow_color, 120), (cx, cy), int(egg_r + 4))
        pygame.draw.circle(surf, (*base_color, 220), (cx, cy), int(egg_r))
        pygame.draw.circle(surf, (255, 255, 255, 180), (cx, cy), int(egg_r), 2)

        hatch_progress = 1.0 - (self.timer / FISH_EGG_HATCH_TIME)
        embryo_r = max(2, int(egg_r * 0.35 * (0.5 + hatch_progress * 0.5)))
        embryo_color = tuple(max(0, c - 60) for c in base_color)
        pygame.draw.circle(surf, (*embryo_color, 200), (cx, cy), embryo_r)

        pos = camera.apply((self.x, self.y))
        screen.blit(surf, (int(pos[0]) - cx, int(pos[1]) - cy))
