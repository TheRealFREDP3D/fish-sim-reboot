"""
Revamped Fish Physics - Steering Force Model
"""
import math
import random
from typing import Tuple, List

class SteeringPhysics:
    """Handles steering-based movement and spatial navigation"""
    
    @staticmethod
    def truncate(vector: Tuple[float, float], max_val: float) -> Tuple[float, float]:
        """Limit a vector to a maximum magnitude"""
        mag = math.hypot(vector[0], vector[1])
        if mag > max_val:
            factor = max_val / mag
            return (vector[0] * factor, vector[1] * factor)
        return vector

    def __init__(self, x, y, max_speed, max_force):
        self.pos = [x, y]
        self.vel = [random.uniform(-1, 1), random.uniform(-1, 1)]
        self.acc = [0.0, 0.0]
        self.max_speed = max_speed
        self.max_force = max_force
        self.heading = random.uniform(0, math.pi * 2)

    def apply_force(self, force: Tuple[float, float]):
        """Accumulate forces for this frame"""
        self.acc[0] += force[0]
        self.acc[1] += force[1]

    def seek(self, target_x: float, target_y: float, weight: float = 1.0) -> Tuple[float, float]:
        """Generate a steering force towards a target"""
        desired_x = target_x - self.pos[0]
        desired_y = target_y - self.pos[1]
        dist = math.hypot(desired_x, desired_y)
        
        if dist > 0:
            desired_x = (desired_x / dist) * self.max_speed
            desired_y = (desired_y / dist) * self.max_speed
            
            steer_x = desired_x - self.vel[0]
            steer_y = desired_y - self.vel[1]
            return self.truncate((steer_x * weight, steer_y * weight), self.max_force)
        return (0, 0)

    def update(self, dt: float, drag: float):
        """Standard Euler integration with drag"""
        # Update velocity
        self.vel[0] += self.acc[0] * dt * 60
        self.vel[1] += self.acc[1] * dt * 60
        
        # Apply natural water drag
        self.vel[0] *= drag
        self.vel[1] *= drag
        
        # Speed limit
        self.vel = list(self.truncate(tuple(self.vel), self.max_speed))
        
        # Update position
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        
        # Update heading based on velocity
        if math.hypot(self.vel[0], self.vel[1]) > 1.0:
            self.heading = math.atan2(self.vel[1], self.vel[0])
            
        # Reset acceleration
        self.acc = [0.0, 0.0]

    def bounce_bounds(self, min_x, min_y, max_x, max_y):
        """Gentle force pushing fish back into bounds"""
        buffer = 50
        force_mult = 2.0
        if self.pos[0] < min_x + buffer: self.apply_force((self.max_force * force_mult, 0))
        elif self.pos[0] > max_x - buffer: self.apply_force((-self.max_force * force_mult, 0))
        
        if self.pos[1] < min_y + buffer: self.apply_force((0, self.max_force * force_mult))
        elif self.pos[1] > max_y - buffer: self.apply_force((0, -self.max_force * force_mult))

