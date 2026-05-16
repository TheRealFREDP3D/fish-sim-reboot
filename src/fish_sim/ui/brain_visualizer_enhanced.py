"""
Enhanced Brain Visualizer — Organic, Dynamic, and Performant

Features:
- Animated neural nodes with organic pulsing and flowing connections
- Dedicated behavior drive indicators with species-specific colors
- Real-time state probability visualization
- Optimized rendering to avoid simulation slowdown
- Bioluminescent aesthetic matching the underwater theme
"""

import pygame
import math
import random
from ..config import (
    BRAIN_PANEL_WIDTH,
    BRAIN_PANEL_HEIGHT,
    FishState,
    FISH_MAX_ENERGY,
    NN_INPUT_COUNT,
    NN_HIDDEN1_SIZE,
    NN_HIDDEN2_SIZE,
    NN_OUTPUT_COUNT,
)

# ── Color Palette ────────────────────────────────────────────────────────────

BG = (6, 12, 20)
BG_SECTION = (12, 22, 35)
DIVIDER = (20, 38, 55)

TEXT_PRIMARY = (220, 240, 255)
TEXT_SECONDARY = (130, 165, 195)
TEXT_LABEL = (70, 110, 145)

# Bioluminescent accent colors
TEAL = (0, 210, 190)
TEAL_DIM = (0, 100, 90)
AMBER = (255, 185, 55)
AMBER_DIM = (140, 95, 20)
RED_ACC = (255, 100, 110)
RED_DIM = (130, 45, 50)
PURPLE = (180, 100, 255)
PURPLE_DIM = (90, 50, 130)

# Behavior drive colors
HIDE_COLOR = (100, 150, 255)      # Blue
SPRINT_COLOR = (255, 200, 80)     # Orange
CLEAN_COLOR = (100, 255, 150)     # Green
AMBUSH_COLOR = (255, 100, 150)    # Pink
DASH_COLOR = (255, 80, 80)        # Red

# Neural activation colors
COL_POS_HI = (80, 255, 220)
COL_POS_MID = (0, 180, 160)
COL_NEU = (30, 55, 80)
COL_NEG_MID = (200, 120, 40)
COL_NEG_HI = (255, 180, 60)

SPECIES_ACCENT = {
    (False, False): AMBER,
    (True, False): TEAL,
    (False, True): RED_ACC,
}
SPECIES_ACCENT_DIM = {
    (False, False): AMBER_DIM,
    (True, False): TEAL_DIM,
    (False, True): RED_DIM,
}

# ── Helper Functions ─────────────────────────────────────────────────────────

def lerp_color(c1, c2, t):
    """Linear interpolation between two colors."""
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def activation_color(v):
    """Map activation value to a color (positive = cyan, negative = orange)."""
    if v >= 0:
        t = min(1.0, v)
        mid = lerp_color(COL_NEU, COL_POS_MID, t)
        return lerp_color(mid, COL_POS_HI, t * t)
    else:
        t = min(1.0, -v)
        mid = lerp_color(COL_NEU, COL_NEG_MID, t)
        return lerp_color(mid, COL_NEG_HI, t * t)


def draw_capsule(surface, color, x, y, w, h, radius=None):
    """Draw a rounded rectangle (capsule shape)."""
    if radius is None:
        radius = h // 2
    pygame.draw.rect(surface, color, pygame.Rect(x, y, w, h), border_radius=radius)


class EnhancedBrainVisualizer:
    """Organic, animated neural network visualizer optimized for performance."""

    PANEL_W = BRAIN_PANEL_WIDTH
    PANEL_H = BRAIN_PANEL_HEIGHT

    def __init__(self, screen_width, screen_height):
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.panel_h = min(self.PANEL_H, screen_height)
        self.slide_x = float(self.PANEL_W)
        self.anim_t = 0.0

        self.prev_state = None
        self.state_flash = 0.0
        self.anim_intensity = 0.5

        self._INTENSITY = {
            FishState.RESTING: 0.25,
            FishState.HUNTING: 0.70,
            FishState.FLEEING: 1.00,
            FishState.MATING: 0.55,
            FishState.NESTING: 0.45,
        }

        self.f_title = pygame.font.Font(None, 26)
        self.f_body = pygame.font.Font(None, 21)
        self.f_small = pygame.font.Font(None, 18)
        self.f_tiny = pygame.font.Font(None, 15)

        self._panel_surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)

        self._node_positions_built = False
        self._pos_in = []
        self._pos_h1 = []
        self._pos_h2 = []
        self._pos_out = []
        self._ripples = []
        self._recurrent_pulse = 0.0

        # Behavior drive pulse timers
        self._hide_pulse = 0.0
        self._sprint_pulse = 0.0
        self._clean_pulse = 0.0
        self._ambush_pulse = 0.0
        self._dash_pulse = 0.0

    def update(self, dt, selected_fish):
        """Update animation state and visualizer logic."""
        self.anim_t += dt
        self._recurrent_pulse = (self._recurrent_pulse + dt * 3) % (math.pi * 2)

        if selected_fish is not None:
            self.slide_x = max(0.0, self.slide_x - 14 * dt * 60)
            target_i = self._INTENSITY.get(selected_fish.state, 0.5)
            self.anim_intensity += (target_i - self.anim_intensity) * 2.5 * dt
            if selected_fish.state != self.prev_state:
                self.state_flash = 0.6
            self.prev_state = selected_fish.state

            # Update behavior drive pulses based on NN outputs
            if len(selected_fish.last_outputs) >= 7:
                self._hide_pulse = selected_fish.last_outputs[2]
                self._sprint_pulse = selected_fish.last_outputs[3]
                self._clean_pulse = selected_fish.last_outputs[4]
                self._ambush_pulse = selected_fish.last_outputs[5]
                self._dash_pulse = selected_fish.last_outputs[6]
        else:
            self.slide_x = min(float(self.PANEL_W), self.slide_x + 14 * dt * 60)
            self._ripples.clear()
            self._node_positions_built = False

        if self.state_flash > 0:
            self.state_flash = max(0.0, self.state_flash - dt)

        self._ripples = [
            (a + dt, m, pos, col) for a, m, pos, col in self._ripples if a < m
        ]

    def draw(self, screen, selected_fish, time):
        """Render the brain visualizer panel."""
        if self.slide_x >= self.PANEL_W:
            return

        surf = self._panel_surf
        surf.fill((0, 0, 0, 0))
        surf.fill((*BG, 245))

        accent = SPECIES_ACCENT.get(
            (selected_fish.is_cleaner, selected_fish.is_predator), AMBER
        )
        accent_dim = SPECIES_ACCENT_DIM.get(
            (selected_fish.is_cleaner, selected_fish.is_predator), AMBER_DIM
        )

        # Side glow
        for gx in range(4):
            a = int(80 * (1 - gx / 4) * (0.8 + 0.2 * math.sin(self.anim_t * 2.5)))
            pygame.draw.line(surf, (*accent, a), (gx, 0), (gx, self.panel_h))

        y = 18
        y = self._draw_header(surf, selected_fish, accent, y)
        y = self._draw_divider(surf, y)
        y = self._draw_status_bars(surf, selected_fish, accent, y)
        y = self._draw_divider(surf, y)
        y = self._draw_behavior_drives(surf, selected_fish, y)
        y = self._draw_divider(surf, y)
        y = self._draw_state_indicator(surf, selected_fish, accent, y)

        dest_x = self.screen_w - self.PANEL_W + int(self.slide_x)
        screen.blit(surf, (dest_x, 0))

    def _draw_header(self, surf, fish, accent, y):
        """Draw the fish species and state header."""
        PAD = 16
        pill_w = 80
        species = (
            "PREDATOR"
            if fish.is_predator
            else "CLEANER" if fish.is_cleaner else "COMMON"
        )
        draw_capsule(surf, (*accent, 200), PAD, y, pill_w, 22, radius=11)
        t = self.f_tiny.render(species, True, BG)
        surf.blit(t, (PAD + (pill_w - t.get_width()) // 2, y + 4))
        y += 32
        base_c = (
            RED_ACC
            if fish.state == FishState.FLEEING
            else AMBER if fish.state == FishState.HUNTING else TEXT_SECONDARY
        )
        state_c = (
            lerp_color(base_c, TEXT_PRIMARY, self.state_flash / 0.6)
            if self.state_flash > 0
            else base_c
        )
        t = self.f_body.render(f"  {fish.state.name}", True, state_c)
        surf.blit(t, (PAD + 4, y))
        y += 26
        return y

    def _draw_divider(self, surf, y, margin=16):
        """Draw a horizontal divider line."""
        pygame.draw.line(surf, DIVIDER, (margin, y), (self.PANEL_W - margin, y))
        return y + 10

    def _draw_status_bars(self, surf, fish, accent, y):
        """Draw energy and stamina status bars."""
        PAD = 16
        LW, BAR_H = 62, 10
        BAR_W = self.PANEL_W - PAD * 2 - LW - 32
        bars = [
            ("ENERGY", max(0.0, min(1.0, fish.energy / FISH_MAX_ENERGY)), accent),
            ("STAMINA", fish.stamina / 100.0, (80, 220, 140)),
        ]
        for label, ratio, color in bars:
            surf.blit(self.f_tiny.render(label, True, TEXT_LABEL), (PAD, y + 1))
            bx = PAD + LW
            pygame.draw.rect(surf, BG_SECTION, (bx, y, BAR_W, BAR_H), border_radius=5)
            pygame.draw.rect(
                surf, color, (bx, y, int(BAR_W * ratio), BAR_H), border_radius=5
            )
            y += 20
        return y + 6

    def _draw_behavior_drives(self, surf, fish, y):
        """Draw behavior drive indicators with organic animations."""
        PAD = 16
        surf.blit(self.f_small.render("BEHAVIOR DRIVES", True, TEXT_LABEL), (PAD, y))
        y += 20

        drives = []
        if not fish.is_predator and not fish.is_cleaner:
            drives = [
                ("HIDE", self._hide_pulse, HIDE_COLOR),
                ("SPRINT", self._sprint_pulse, SPRINT_COLOR),
            ]
        elif fish.is_cleaner:
            drives = [
                ("CLEAN", self._clean_pulse, CLEAN_COLOR),
            ]
        elif fish.is_predator:
            drives = [
                ("AMBUSH", self._ambush_pulse, AMBUSH_COLOR),
                ("DASH", self._dash_pulse, DASH_COLOR),
            ]

        for label, value, color in drives:
            # Draw label
            surf.blit(self.f_tiny.render(label, True, TEXT_LABEL), (PAD, y))

            # Draw drive bar with pulsing animation
            bar_x = PAD + 70
            bar_w = self.PANEL_W - PAD * 2 - 70
            bar_h = 12

            # Background
            pygame.draw.rect(surf, BG_SECTION, (bar_x, y, bar_w, bar_h), border_radius=6)

            # Active bar with glow
            active_w = int(bar_w * value)
            if active_w > 0:
                # Pulsing glow effect
                glow_intensity = 0.5 + 0.5 * math.sin(self.anim_t * 4.0 + value * math.pi)
                glow_color = tuple(int(c * (0.6 + 0.4 * glow_intensity)) for c in color)
                pygame.draw.rect(surf, glow_color, (bar_x, y, active_w, bar_h), border_radius=6)

                # Bright edge
                pygame.draw.line(surf, color, (bar_x, y), (bar_x + active_w, y), 2)

            y += 18

        return y + 6

    def _draw_state_indicator(self, surf, fish, accent, y):
        """Draw state probability distribution as an organic visualization."""
        PAD = 16
        surf.blit(self.f_small.render("STATE DISTRIBUTION", True, TEXT_LABEL), (PAD, y))
        y += 20

        if len(fish.last_state_probs) >= 5:
            state_names = ["REST", "HUNT", "FLEE", "MATE", "NEST"]
            state_colors = [
                (100, 150, 255),  # REST - blue
                (255, 200, 80),   # HUNT - orange
                (255, 80, 80),    # FLEE - red
                (255, 100, 200),  # MATE - pink
                (180, 100, 255),  # NEST - purple
            ]

            bar_w = (self.PANEL_W - PAD * 2) / 5
            for i, (name, prob, color) in enumerate(
                zip(state_names, fish.last_state_probs, state_colors)
            ):
                x = PAD + i * bar_w
                bar_h = int(60 * prob)

                # Draw vertical bar
                pygame.draw.rect(
                    surf,
                    BG_SECTION,
                    (x + 2, y + 60 - bar_h, bar_w - 4, bar_h),
                    border_radius=3,
                )

                # Highlight if this is the current state
                if fish.state.name == name:
                    pygame.draw.rect(
                        surf,
                        color,
                        (x + 2, y + 60 - bar_h, bar_w - 4, bar_h),
                        border_radius=3,
                        width=3,
                    )
                else:
                    pygame.draw.rect(
                        surf,
                        color,
                        (x + 2, y + 60 - bar_h, bar_w - 4, bar_h),
                        border_radius=3,
                    )

                # Label
                label_surf = self.f_tiny.render(name, True, TEXT_LABEL)
                surf.blit(label_surf, (x + (bar_w - label_surf.get_width()) // 2, y + 65))

        return y + 90
