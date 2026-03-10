import pygame
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    CAMERA_SMOOTHING,
)


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        self.target = None

    def follow(self, target):
        self.target = target

    def update(self):
        if self.target:
            # Center on target
            target_x = self.target.pos.x - self.width // 2
            target_y = self.target.pos.y - self.height // 2

            # Smoothly interpolate
            self.x += (target_x - self.x) * CAMERA_SMOOTHING
            self.y += (target_y - self.y) * CAMERA_SMOOTHING

        # Constrain to world bounds
        self.x = max(0, min(self.x, WORLD_WIDTH - self.width))
        self.y = max(0, min(self.y, WORLD_HEIGHT - self.height))

    def apply(self, pos):
        """Transform world position to screen position"""
        if isinstance(pos, pygame.Vector2):
            return pygame.Vector2(pos.x - self.x, pos.y - self.y)
        return (pos[0] - self.x, pos[1] - self.y)

    def is_visible(self, pos, margin=100):
        """Check if a point or rect is within the camera view (with margin)"""
        return (
            self.x - margin < pos[0] < self.x + self.width + margin
            and self.y - margin < pos[1] < self.y + self.height + margin
        )

    def get_view_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
