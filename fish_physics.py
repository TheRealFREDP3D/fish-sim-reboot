import math
import random
import pygame


class SteeringPhysics:
    """Handles steering-based movement and spatial navigation using Vector2"""

    def __init__(self, x, y, max_speed, max_force):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.acc = pygame.Vector2(0.0, 0.0)
        self.max_speed = max_speed
        self.max_force = max_force
        self.heading = random.uniform(0, math.pi * 2)

    def apply_force(self, force):
        """Accumulate forces for this frame"""
        if isinstance(force, (tuple, list)):
            force = pygame.Vector2(force)
        self.acc += force

    def seek(
        self, target_x: float, target_y: float, weight: float = 1.0
    ) -> pygame.Vector2:
        """Generate a steering force towards a target.

        Weight is applied before clamping so that max_force is always
        respected as a true upper bound on the final output vector.
        """
        target = pygame.Vector2(target_x, target_y)
        dist = self.pos.distance_to(target)

        if dist > 0:
            desired = (target - self.pos).normalize() * self.max_speed
            steer = (desired - self.vel) * weight  # apply weight first
            if steer.length() > self.max_force:
                steer.scale_to_length(self.max_force)  # then clamp
            return steer
        return pygame.Vector2(0, 0)

    def update(self, dt: float, drag: float):
        """Standard Euler integration with drag"""
        self.vel += self.acc * dt * 60
        self.vel *= drag

        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        self.pos += self.vel * dt

        if self.vel.length() > 1.0:
            self.heading = math.atan2(self.vel.y, self.vel.x)

        self.acc = pygame.Vector2(0, 0)

    def bounce_bounds(self, min_x, min_y, max_x, max_y):
        """Gentle force pushing fish back into bounds"""
        buffer = 50
        force_mult = 2.0
        if self.pos.x < min_x + buffer:
            self.apply_force((self.max_force * force_mult, 0))
        elif self.pos.x > max_x - buffer:
            self.apply_force((-self.max_force * force_mult, 0))

        if self.pos.y < min_y + buffer:
            self.apply_force((0, self.max_force * force_mult))
        elif self.pos.y > max_y - buffer:
            self.apply_force((0, -self.max_force * force_mult))
