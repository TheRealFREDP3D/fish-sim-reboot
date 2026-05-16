"""Polished Brain Visualizer - A structured, high-tech HUD for neural monitoring."""

import pygame
import math
from ..config import (
    FISH_MAX_AGE,
    FISH_MAX_ENERGY,
    FishState,
    FISH_STATE_ORDER,
)

class BrainVisualizer:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.panel_width = 460
        self.panel_height = screen_height
        self.panel_offset_x = self.panel_width

        # Cyber-Oceanic Palette
        self.col_bg = (10, 15, 25, 235)
        self.col_card = (25, 35, 55, 180)
        self.col_accent = (0, 210, 255)
        self.col_text_main = (220, 235, 255)
        self.col_text_dim = (130, 150, 180)
        
        # Fonts
        self.f_large = pygame.font.Font(None, 36)
        self.f_mid = pygame.font.Font(None, 24)
        self.f_small = pygame.font.Font(None, 18)
        self.f_tiny = pygame.font.Font(None, 14)

        self.anim_phase = 0.0

    def update(self, dt, selected_fish):
        self.anim_phase += dt
        if selected_fish:
            self.panel_offset_x = max(0, self.panel_offset_x - 1200 * dt)
        else:
            self.panel_offset_x = min(self.panel_width, self.panel_offset_x + 1200 * dt)

    def draw(self, screen, fish, time):
        if self.panel_offset_x >= self.panel_width:
            return

        accent = self._get_accent(fish)
        surf = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        surf.fill(self.col_bg)

        # Main Panel Decoration
        pygame.draw.line(surf, accent, (0, 0), (0, self.panel_height), 3)

        y = 30
        y = self._draw_header(surf, fish, accent, y)
        y = self._draw_vitals(surf, fish, accent, y)
        y = self._draw_neural_grid(surf, fish, accent, y)
        y = self._draw_decisions(surf, fish, accent, y)
        y = self._draw_actuators(surf, fish, accent, y)

        screen.blit(surf, (self.screen_width - self.panel_width + int(self.panel_offset_x), 0))

    def _get_accent(self, fish):
        if fish.is_predator: return (255, 70, 90)
        if fish.is_cleaner: return (0, 255, 220)
        return (255, 210, 80)

    def _draw_header(self, surf, fish, accent, y):
        # Species + Sex
        spec = f"{'PREDATOR' if fish.is_predator else 'CLEANER' if fish.is_cleaner else 'COMMON'}"
        title = self.f_large.render(spec, True, accent)
        surf.blit(title, (30, y))
        
        sex_sym = "MALE ♂" if fish.sex == "M" else "FEMALE ♀"
        txt = self.f_small.render(f"{sex_sym}  |  AGE: {fish.age:.1f}s", True, self.col_text_dim)
        surf.blit(txt, (30, y + 32))

        # Big State Indicator
        state_txt = self.f_large.render(fish.state.name, True, self.col_text_main)
        surf.blit(state_txt, (30, y + 65))
        
        return y + 120

    def _draw_vitals(self, surf, fish, accent, y):
        self._draw_module_bg(surf, y, 90)
        
        vitals = [
            ("ENERGY", fish.energy / FISH_MAX_ENERGY, (255, 210, 80)),
            ("STAMINA", fish.stamina / 100.0, (100, 255, 180))
        ]
        
        for i, (label, ratio, col) in enumerate(vitals):
            ly = y + 15 + (i * 35)
            txt = self.f_tiny.render(label, True, self.col_text_dim)
            surf.blit(txt, (45, ly))
            
            # Bar
            bx, bw, bh = 110, 300, 8
            pygame.draw.rect(surf, (15, 20, 35), (bx, ly + 4, bw, bh), border_radius=4)
            fill = int(bw * max(0, min(1, ratio)))
            if fill > 2:
                pygame.draw.rect(surf, col, (bx, ly + 4, fill, bh), border_radius=4)
        
        return y + 110

    def _draw_neural_grid(self, surf, fish, accent, y):
        self._draw_module_bg(surf, y, 220)
        txt = self.f_small.render("NEURAL SENSORY MAPPING", True, accent)
        surf.blit(txt, (30, y - 20))

        # Define grid for inputs (Radar vs Internal)
        # We sample the 27 inputs into a cleaner grid
        input_data = fish.last_inputs if hasattr(fish, 'last_inputs') else [0]*27
        
        # Draw Radar Group (Inputs 0-8)
        r_x, r_y = 50, y + 40
        txt = self.f_tiny.render("RADAR ARRAY", True, self.col_text_dim)
        surf.blit(txt, (r_x, r_y - 20))
        for i in range(9):
            ix, iy = r_x + (i % 3) * 30, r_y + (i // 3) * 30
            val = input_data[i]
            self._draw_node(surf, (ix, iy), val, accent)

        # Draw Stats Group (Inputs 9-26)
        s_x, s_y = 180, y + 40
        txt = self.f_tiny.render("INTERNAL STATE / ENV", True, self.col_text_dim)
        surf.blit(txt, (s_x, s_y - 20))
        for i in range(9, 27):
            idx = i - 9
            ix, iy = s_x + (idx % 6) * 30, s_y + (idx // 6) * 30
            val = input_data[i]
            self._draw_node(surf, (ix, iy), val, accent)

        # Draw Hidden Layers (sampled for visuals)
        h_x, h_y = 400, y + 40
        txt = self.f_tiny.render("HIDDEN", True, self.col_text_dim)
        surf.blit(txt, (h_x, h_y - 20))
        h_data = fish.last_hidden if hasattr(fish, 'last_hidden') else [0]*8
        for i, val in enumerate(h_data):
            self._draw_node(surf, (h_x, h_y + i * 20), val, (150, 150, 255))

        return y + 240

    def _draw_decisions(self, surf, fish, accent, y):
        self._draw_module_bg(surf, y, 130)
        txt = self.f_small.render("BEHAVIOR PROBABILITIES", True, accent)
        surf.blit(txt, (30, y - 20))

        probs = fish.last_state_probs if hasattr(fish, 'last_state_probs') else [0.2]*5
        for i, state in enumerate(FISH_STATE_ORDER):
            ly = y + 15 + (i * 22)
            # Label
            label_col = self.col_text_main if fish.state == state else self.col_text_dim
            txt = self.f_tiny.render(state.name, True, label_col)
            surf.blit(txt, (45, ly))
            
            # Probability mini-bar
            bx, bw, bh = 140, 270, 6
            pygame.draw.rect(surf, (15, 20, 35), (bx, ly + 4, bw, bh), border_radius=3)
            fill = int(bw * probs[i])
            if fill > 1:
                col = accent if fish.state == state else (80, 100, 140)
                pygame.draw.rect(surf, col, (bx, ly + 4, fill, bh), border_radius=3)

        return y + 150

    def _draw_actuators(self, surf, fish, accent, y):
        self._draw_module_bg(surf, y, 80)
        
        steer = fish.last_outputs[0] if fish.last_outputs else 0
        thrust = (fish.last_outputs[1] + 1) / 2 if len(fish.last_outputs) > 1 else 0

        # Steer Vector
        sx, sy = 100, y + 40
        pygame.draw.circle(surf, (20, 30, 50), (sx, sy), 30)
        pygame.draw.arc(surf, self.col_text_dim, (sx-30, sy-30, 60, 60), 0, math.pi*2, 1)
        
        end_x = sx + math.cos(math.pi*1.5 + steer) * 25
        end_y = sy + math.sin(math.pi*1.5 + steer) * 25
        pygame.draw.line(surf, accent, (sx, sy), (end_x, end_y), 3)
        surf.blit(self.f_tiny.render("STEER", True, self.col_text_dim), (sx-15, sy+35))

        # Thrust Force
        tx, ty = 200, y + 35
        pygame.draw.rect(surf, (20, 30, 50), (tx, ty, 200, 12), border_radius=6)
        pygame.draw.rect(surf, accent, (tx, ty, int(200 * thrust), 12), border_radius=6)
        surf.blit(self.f_tiny.render("THRUST FORCE", True, self.col_text_dim), (tx, ty + 20))

        return y + 100

    def _draw_module_bg(self, surf, y, height):
        pygame.draw.rect(surf, self.col_card, (20, y, self.panel_width - 40, height), border_radius=10)

    def _draw_node(self, surf, pos, val, color):
        intensity = abs(val)
        # Background dot
        pygame.draw.circle(surf, (40, 50, 70), pos, 8)
        # Active fill
        if intensity > 0.05:
            r = 2 + (intensity * 6)
            alpha = int(100 + intensity * 155)
            # Draw glow
            glow_r = r + 4
            s = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha // 4), (glow_r, glow_r), glow_r)
            surf.blit(s, (pos[0]-glow_r, pos[1]-glow_r))
            # Draw Core
            pygame.draw.circle(surf, color, pos, int(r))
