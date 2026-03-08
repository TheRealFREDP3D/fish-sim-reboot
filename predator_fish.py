"""Predator Fish - Hunts others with size restrictions and high-speed dash mechanic"""
import pygame
import math
import random
from fish import NeuralFish, FishState
from config import (
    PREDATOR_SPEED_MULT,
    PREDATOR_DASH_SPEED_MULT,
    PREDATOR_DASH_DURATION,
    PREDATOR_DASH_COOLDOWN,
    FISH_MAX_SPEED,
    FISH_HUNGER_THRESHOLD,
    FISH_MATING_THRESHOLD,
    WATER_LINE_Y,
    FISH_MAX_AGE
)


class PredatorFish(NeuralFish):
    def __init__(self, world, traits=None, brain=None):
        super().__init__(world, traits=traits, brain=brain)
        self.is_predator = True
        self.physics.max_speed *= PREDATOR_SPEED_MULT * 1.2
        self.energy = 80.0
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.is_dashing = False
        self.successful_hunts = 0
        self.has_reproduced = False
        self.mate_found = False
        self.mate = None

    def update(self, dt, all_fish, targets, particle_system, plant_manager):
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.physics.max_speed /= PREDATOR_DASH_SPEED_MULT

        threat_level = sum(self.get_radar_inputs(all_fish, targets, plant_manager)[3:6])
        
        # Use trait-based lifespan
        max_age = FISH_MAX_AGE * self.traits.physical_traits.get("lifespan_mult", 1.0)
        life_remaining = (max_age - self.age) / max_age
        
        if threat_level > 0.3:
            self.state = FishState.FLEEING
        elif not self.has_reproduced and life_remaining < 0.2:
            if self.mate_found and self.mate and self.mate in self.world.fish_system.predators:
                self.state = FishState.MATING
                self.mate.state = FishState.MATING
            else:
                self.state = FishState.MATING
                self.find_mate(self.world.fish_system.predators)
        elif self.energy < FISH_HUNGER_THRESHOLD * 0.8:
            self.state = FishState.HUNTING
        else:
            self.state = FishState.RESTING

        if self.state == FishState.RESTING:
            target_y = WATER_LINE_Y + 80
            self.physics.apply_force(self.physics.seek(self.physics.pos[0], target_y, weight=0.8))
        elif self.state == FishState.HUNTING:
            my_size = self.traits.physical_traits['size_mult'] * (1.0 if self.is_mature else 0.7)
            best_prey, best_dist = None, 180
            for t in targets:
                protected = False
                if hasattr(t, 'family') and t.family and t.family.active:
                    for member in t.family.get_family_members(exclude_self=t):
                        if member.is_mature and math.hypot(member.physics.pos[0] - t.physics.pos[0],
                                                          member.physics.pos[1] - t.physics.pos[1]) < 80:
                            protected = True
                            break
                if protected or getattr(t, 'is_hidden', False): continue
                dist = math.hypot(self.physics.pos[0] - t.physics.pos[0], self.physics.pos[1] - t.physics.pos[1])
                if dist < best_dist:
                    prey_size = t.traits.physical_traits['size_mult'] * (1.0 if t.is_mature else 0.7)
                    if my_size > prey_size * 0.8:
                        best_prey, best_dist = t, dist

            if best_prey and not self.is_dashing and self.dash_cooldown <= 0 and best_dist < 160:
                self.is_dashing = True
                self.dash_timer = PREDATOR_DASH_DURATION
                self.dash_cooldown = PREDATOR_DASH_COOLDOWN + random.uniform(0, 1.5)
                self.physics.max_speed *= PREDATOR_DASH_SPEED_MULT
                self.energy -= 4.0

            if best_prey:
                self.physics.apply_force(self.physics.seek(best_prey.physics.pos[0], best_prey.physics.pos[1], weight=1.8))

        if self.is_dashing:
            for t in targets[:]:
                dist = math.hypot(self.physics.pos[0] - t.physics.pos[0], self.physics.pos[1] - t.physics.pos[1])
                if dist < 25:
                    prey_size = t.traits.physical_traits['size_mult'] * (1.0 if t.is_mature else 0.7)
                    my_size = self.traits.physical_traits['size_mult'] * (1.0 if self.is_mature else 0.7)
                    if my_size > prey_size * 0.7:
                        self.energy = min(100.0, self.energy + 35.0)
                        self.successful_hunts += 1
                        t.energy = -10
                        break

        return super().update(dt, all_fish, targets, particle_system, plant_manager)

    def find_mate(self, all_predators):
        if self.mate_found or self.sex != 'M': return
        closest_mate, min_dist = None, float('inf')
        max_age = FISH_MAX_AGE * self.traits.physical_traits.get("lifespan_mult", 1.0)
        
        for predator in all_predators:
            if (predator != self and not predator.has_reproduced and predator.sex != self.sex and 
                (max_age - predator.age) / max_age < 0.3):
                dist = math.hypot(self.physics.pos[0] - predator.physics.pos[0], self.physics.pos[1] - predator.physics.pos[1])
                if dist < min_dist and dist < 200:
                    min_dist, closest_mate = dist, predator
        
        if closest_mate:
            self.mate = closest_mate
            closest_mate.mate = self
            self.mate_found = True
            closest_mate.mate_found = True
            
    def try_reproduce(self):
        if (self.has_reproduced or not self.mate_found or not self.mate or 
            self.mate not in self.world.fish_system.predators):
            return False
        if self.successful_hunts > 2 and self.mate.successful_hunts > 2:
            self.has_reproduced = True
            self.mate.has_reproduced = True
            return True
        return False
            
    def draw(self, screen, time, selected=False):
        if self.is_dashing:
            speed = math.hypot(*self.physics.vel)
            for i in range(1, 5):
                offset = (self.physics.vel[0] * 0.02 * i, self.physics.vel[1] * 0.02 * i)
                old_pos = (int(self.physics.pos[0] - offset[0]), int(self.physics.pos[1] - offset[1]))
                pygame.draw.circle(screen, (255, 80, 80, 100 - i * 15), old_pos, 12 - i * 2)

        super().draw(screen, time, selected)
        
        max_age = FISH_MAX_AGE * self.traits.physical_traits.get("lifespan_mult", 1.0)
        if not self.has_reproduced and (max_age - self.age) / max_age < 0.3:
            pulse = (math.sin(time * 3) + 1) * 0.5 * 30 + 20
            color = (0, 255, 0, 100) if self.mate_found else (255, 200, 0, 100)
            surf = pygame.Surface((pulse*2, pulse*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (pulse, pulse), pulse, 2)
            screen.blit(surf, (int(self.physics.pos[0] - pulse), int(self.physics.pos[1] - pulse)))

        if selected:
            bar_w, bar_h, y_offset = 50, 6, 30
            pygame.draw.rect(screen, (40, 40, 40), (self.physics.pos[0] - bar_w//2, self.physics.pos[1] + y_offset, bar_w, bar_h))
            pygame.draw.rect(screen, (255, 80, 80), (self.physics.pos[0] - bar_w//2, self.physics.pos[1] + y_offset, bar_w * (self.energy / 100.0), bar_h))
            if self.dash_cooldown > 0:
                y_offset += 8
                pygame.draw.rect(screen, (40, 40, 40), (self.physics.pos[0] - bar_w//2, self.physics.pos[1] + y_offset, bar_w, bar_h))
                progress = 1.0 - (self.dash_cooldown / (PREDATOR_DASH_COOLDOWN + 1.5))
                pygame.draw.rect(screen, (80, 150, 255), (self.physics.pos[0] - bar_w//2, self.physics.pos[1] + y_offset, bar_w * progress, bar_h))
