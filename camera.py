import pygame
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    CAMERA_SMOOTHING,
)

CAMERA_PAN_SPEED = 400  # pixels per second


class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        self.target = None

    def follow(self, target):
        self.target = target

    def update(self, dt=0):
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

    def pan(self, dx, dy, dt):
        """Move camera by a pixel delta, releasing any follow target."""
        if dx != 0 or dy != 0:
            self.target = None
            self.x += dx * CAMERA_PAN_SPEED * dt
            self.y += dy * CAMERA_PAN_SPEED * dt
            # Constrain to world bounds
            self.x = max(0, min(self.x, WORLD_WIDTH - self.width))
            self.y = max(0, min(self.y, WORLD_HEIGHT - self.height))

    def apply(self, pos):
        """Transform world position to screen position"""
        if isinstance(pos, pygame.Vector2):
            return pygame.Vector2(pos.x - self.x, pos.y - self.y)
        return (pos[0] - self.x, pos[1] - self.y)

    def is_visible(self, obj, margin=100):
        """Check if a point or rect is within the camera view (with margin)"""
        view_rect_with_margin = self.get_view_rect().inflate(margin * 2, margin * 2)
        if isinstance(obj, pygame.Rect):
            return view_rect_with_margin.colliderect(obj)
        return view_rect_with_margin.collidepoint(obj)

    def get_view_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
