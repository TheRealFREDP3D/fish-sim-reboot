"""Professional Brain Visualizer - Organic & Portfolio-Ready"""

import pygame
import math
from ..config import (
    BRAIN_PANEL_WIDTH, FISH_MAX_AGE, FISH_MAX_ENERGY,
    FISH_LARVA_DURATION, FISH_JUVENILE_DURATION, FISH_ELDER_DURATION,
    FishState
)


class BrainVisualizer:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Panel settings - wider and more spacious
        self.panel_width = 460
        self.panel_height = screen_height
        self.panel_offset_x = self.panel_width  # start off-screen

        # Fonts - larger and hierarchical
        self.font_title = pygame.font.Font(None, 34)
        self.font_heading = pygame.font.Font(None, 26)
        self.font_body = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_tiny = pygame.font.Font(None, 13)

        # Organic color palette (deep ocean + bioluminescence)
        self.bg_color = (6, 10, 26, 245)
        self.accent_common = (255, 185, 65)      # warm amber
        self.accent_cleaner = (80, 225, 255)     # cyan
        self.accent_predator = (255, 85, 95)     # red
        self.neutral_glow = (180, 220, 255, 30)

        # Animation
        self.anim_intensity = 0.5
        self.state_flash_timer = 0.0
        self.prev_state = None

    def update(self, dt, selected_fish):
        if selected_fish is not None:
            self.panel_offset_x = max(0, self.panel_offset_x - 14 * dt * 60)
            target_intensity = {
                FishState.RESTING: 0.35,
                FishState.HUNTING: 0.75,
                FishState.FLEEING: 1.0,
                FishState.MATING: 0.65,
                FishState.NESTING: 0.55,
            }.get(selected_fish.state, 0.5)
            self.anim_intensity += (target_intensity - self.anim_intensity) * 3.0 * dt

            if selected_fish.state != self.prev_state:
                self.state_flash_timer = 0.6
            self.prev_state = selected_fish.state
        else:
            self.panel_offset_x = min(self.panel_width, self.panel_offset_x + 14 * dt * 60)

        if self.state_flash_timer > 0:
            self.state_flash_timer = max(0, self.state_flash_timer - dt)

    def draw(self, screen, fish, time):
        if self.panel_offset_x >= self.panel_width:
            return

        accent = self._get_accent_color(fish)

        # Create panel surface
        surf = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        surf.fill(self.bg_color)

        # Soft inner glow border
        pygame.draw.rect(surf, (*accent, 40), (0, 0, self.panel_width, self.panel_height), border_radius=12)
        pygame.draw.rect(surf, accent, (0, 0, self.panel_width, self.panel_height), width=4, border_radius=12)

        y = 24
        y = self._draw_header(surf, fish, accent, y)
        y = self._draw_status_bars(surf, fish, y)
        y = self._draw_neural_network(surf, fish, time, accent, y)
        y = self._draw_output_section(surf, fish, time, y)
        y = self._draw_traits(surf, fish, y)
        y = self._draw_lifetime_stats(surf, fish, y)

        # Blit to main screen
        screen.blit(surf, (self.screen_width - self.panel_width + int(self.panel_offset_x), 0))

    def _get_accent_color(self, fish):
        if fish.is_predator:
            return self.accent_predator
        return self.accent_cleaner if fish.is_cleaner else self.accent_common

    # ===================================================================
    # SECTION DRAWERS
    # ===================================================================

    def _draw_header(self, surf, fish, accent, y):
        species = "PREDATOR" if fish.is_predator else ("CLEANER" if fish.is_cleaner else "COMMON")
        pill_rect = pygame.Rect(24, y, 138, 34)
        pygame.draw.rect(surf, accent, pill_rect, border_radius=17)
        txt = self.font_heading.render(species, True, (255, 255, 255))
        surf.blit(txt, (pill_rect.x + 12, pill_rect.y + 5))

        # Life stage
        if fish.age < FISH_LARVA_DURATION:
            stage = "LARVA"
        elif fish.age < FISH_LARVA_DURATION + FISH_JUVENILE_DURATION:
            stage = "JUVENILE"
        elif fish.age > FISH_MAX_AGE * 0.85:
            stage = "ELDER"
        else:
            stage = "ADULT"

        sex_icon = "♂" if fish.sex == "M" else "♀"
        pregnant = " • PREGNANT" if fish.is_pregnant else ""
        identity = f"{sex_icon} {stage} • { 'MATURE' if fish.is_mature else 'IMMATURE' }{pregnant}"
        txt = self.font_small.render(identity, True, (220, 220, 240))
        surf.blit(txt, (24, y + 42))

        # State with flash
        state_color = (255, 100, 100) if fish.state == FishState.FLEEING else \
                      (255, 170, 60) if fish.state == FishState.HUNTING else \
                      (120, 255, 160) if fish.state == FishState.RESTING else \
                      (200, 140, 255)

        if self.state_flash_timer > 0:
            flash = int(255 * (self.state_flash_timer / 0.6))
            state_color = (min(255, state_color[0] + flash), min(255, state_color[1] + flash), min(255, state_color[2] + flash))

        txt = self.font_body.render(fish.state.name.upper(), True, state_color)
        surf.blit(txt, (24, y + 68))

        return y + 110

    def _draw_status_bars(self, surf, fish, y):
        bar_w, bar_h = 310, 22
        label_x = 24

        for label, ratio, color in [
            ("LIFE", max(0, 1 - fish.age / (FISH_MAX_AGE * fish.traits.physical_traits.get("lifespan_mult", 1.0))), (100, 180, 255)),
            ("ENERGY", max(0, min(1, fish.energy / FISH_MAX_ENERGY)), (255, 200, 80)),
            ("STAMINA", fish.stamina / 100.0, (100, 255, 160)),
        ]:
            # Label
            txt = self.font_body.render(label, True, (200, 210, 230))
            surf.blit(txt, (label_x, y))

            # Bar background
            bar_x = label_x + 78
            pygame.draw.rect(surf, (28, 32, 48), (bar_x, y + 4, bar_w, bar_h), border_radius=8)

            # Fill
            fill_w = int(bar_w * ratio)
            pygame.draw.rect(surf, color, (bar_x, y + 4, fill_w, bar_h), border_radius=8)

            # Percentage
            pct = self.font_small.render(f"{int(ratio * 100)}%", True, (230, 230, 240))
            surf.blit(pct, (bar_x + bar_w + 12, y + 5))

            y += 42

        return y + 12

    def _draw_neural_network(self, surf, fish, time, accent, y):
        title = self.font_heading.render("NEURAL NETWORK", True, (255, 255, 255))
        surf.blit(title, (24, y))
        y += 38

        net_h = 260
        net_top = y

        # Node positions
        cols = {
            "input": 68,
            "hidden1": 168,
            "hidden2": 268,
            "output": 368
        }

        # Input nodes (grouped)
        input_labels = ["FOOD", "THREAT", "MATE", "ENERGY", "STAMINA", "DEPTH", "SPEED", "SAFETY"]
        input_pos = []
        for i in range(8):
            py = net_top + 18 + i * 28
            input_pos.append((cols["input"], py))
            # Draw node
            self._draw_node(surf, input_pos[-1], fish.last_inputs[i] if i < len(fish.last_inputs) else 0, time, 7)

        # Hidden 1 & 2
        h1_pos = [(cols["hidden1"], net_top + 30 + i * 26) for i in range(8)]
        h2_pos = [(cols["hidden2"], net_top + 38 + i * 30) for i in range(6)]

        for pos in h1_pos + h2_pos:
            act = fish.last_hidden1[i] if pos in h1_pos and i < len(fish.last_hidden1) else fish.last_hidden[i % 6]
            self._draw_node(surf, pos, act, time, 8)

        # Output nodes
        out_pos = [(cols["output"], net_top + 70 + i * 60) for i in range(2)]
        for pos, label in zip(out_pos, ["STEER", "THRUST"]):
            act = fish.last_outputs[0] if label == "STEER" else fish.last_outputs[1]
            self._draw_node(surf, pos, act, time, 10)
            txt = self.font_tiny.render(label, True, (200, 220, 255))
            surf.blit(txt, (pos[0] + 18, pos[1] - 8))

        # Connections (background faint + active glowing)
        self._draw_connections(surf, input_pos, h1_pos, fish.last_inputs, time)
        self._draw_connections(surf, h1_pos, h2_pos, fish.last_hidden1, time)
        self._draw_connections(surf, h2_pos, out_pos, fish.last_hidden, time)

        return net_top + net_h + 24

    def _draw_node(self, surf, pos, activation, time, radius):
        color = self._activation_color(activation)
        # Glow
        glow_r = radius + math.sin(time * 3.5 * self.anim_intensity) * 2.5
        glow_surf = pygame.Surface((int(glow_r * 3), int(glow_r * 3)), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 35), (int(glow_r * 1.5), int(glow_r * 1.5)), int(glow_r + 3))
        surf.blit(glow_surf, (pos[0] - glow_r * 1.5, pos[1] - glow_r * 1.5))
        # Core node
        pygame.draw.circle(surf, color, pos, radius)
        pygame.draw.circle(surf, (255, 255, 255), pos, radius, 2)

    def _activation_color(self, value):
        t = min(1.0, abs(value))
        if value > 0:
            return (80 + int(175 * t), 255, 140 + int(115 * t))
        return (255, 80 + int(175 * t), 220 + int(35 * t))

    def _draw_connections(self, surf, from_nodes, to_nodes, activations, time):
        for i, p1 in enumerate(from_nodes):
            act = activations[i] if i < len(activations) else 0
            if abs(act) < 0.15:
                continue
            color = self._activation_color(act)
            alpha = int(40 + abs(act) * 200)
            for p2 in to_nodes:
                self._draw_bezier(surf, p1, p2, (*color, alpha), thickness=2.5)
                # Ripple
                self._draw_ripple(surf, p1, p2, color, time, act)

    def _draw_bezier(self, surf, p0, p1, color, thickness):
        # Simple quadratic bezier
        ctrl_x = (p0[0] + p1[0]) // 2 + 28
        ctrl_y = (p0[1] + p1[1]) // 2
        points = []
        for t in range(21):
            t = t / 20
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl_x + t ** 2 * p1[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl_y + t ** 2 * p1[1]
            points.append((int(x), int(y)))
        for i in range(len(points) - 1):
            pygame.draw.line(surf, color, points[i], points[i + 1], thickness)

    def _draw_ripple(self, surf, p0, p1, color, time, activation):
        t = (time * 2.2 * self.anim_intensity + abs(activation) * 2) % 1.0
        ctrl_x = (p0[0] + p1[0]) // 2 + 28
        ctrl_y = (p0[1] + p1[1]) // 2
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl_x + t ** 2 * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl_y + t ** 2 * p1[1]
        pygame.draw.circle(surf, color, (int(x), int(y)), 4)

    def _draw_output_section(self, surf, fish, time, y):
        title = self.font_heading.render("OUTPUT INTERPRETATION", True, (200, 210, 230))
        surf.blit(title, (24, y))
        y += 36

        # STEER (left-right gauge)
        self._draw_steer_gauge(surf, fish.last_outputs[0] if fish.last_outputs else 0, y)
        y += 68

        # THRUST
        self._draw_thrust_gauge(surf, fish.last_outputs[1] if len(fish.last_outputs) > 1 else 0, y)
        y += 72

        return y

    def _draw_steer_gauge(self, surf, value, y):
        x = 24
        pygame.draw.rect(surf, (28, 32, 48), (x + 72, y, 280, 24), border_radius=12)
        center = x + 72 + 140
        pygame.draw.line(surf, (100, 120, 160), (center, y), (center, y + 24), 2)

        needle_x = center + int(value * 135)
        pygame.draw.rect(surf, (80, 255, 220), (needle_x - 3, y - 4, 6, 32))

        txt = self.font_small.render("← LEFT          RIGHT →", True, (160, 170, 200))
        surf.blit(txt, (x + 82, y + 30))

    def _draw_thrust_gauge(self, surf, value, y):
        norm = (value + 1) / 2
        x = 24
        pygame.draw.rect(surf, (28, 32, 48), (x + 72, y, 280, 24), border_radius=12)
        fill = int(280 * norm)
        col = (255, int(255 * norm * 2), 80) if norm < 0.5 else (int(255 * (1 - (norm - 0.5) * 2)), 255, 100)
        pygame.draw.rect(surf, col, (x + 72, y, fill, 24), border_radius=12)

    def _draw_traits(self, surf, fish, y):
        title = self.font_heading.render("HERITABLE TRAITS", True, (200, 210, 230))
        surf.blit(title, (24, y))
        y += 34

        traits = fish.traits.physical_traits
        data = [
            ("SPEED", traits.get("max_speed_mult", 1.0)),
            ("STAMINA", traits.get("stamina_mult", 1.0)),
            ("AGILITY", traits.get("turn_rate_mult", 1.0)),
            ("METABOLISM", traits.get("metabolism_mult", 1.0)),
            ("SIZE", traits.get("size_mult", 1.0)),
            ("LIFESPAN", traits.get("lifespan_mult", 1.0)),
        ]

        for label, val in data:
            txt = self.font_body.render(label, True, (200, 210, 230))
            surf.blit(txt, (24, y))
            bar_x = 130
            pygame.draw.rect(surf, (28, 32, 48), (bar_x, y + 6, 220, 10), border_radius=5)
            offset = (val - 1.0) * 110
            col = (120, 255, 160) if val > 1 else (255, 170, 80)
            pygame.draw.rect(surf, col, (bar_x + 110, y + 6, offset, 10), border_radius=5)
            val_txt = self.font_small.render(f"{val:.2f}", True, (220, 230, 255))
            surf.blit(val_txt, (bar_x + 240, y + 3))
            y += 28

        return y + 12

    def _draw_lifetime_stats(self, surf, fish, y):
        title = self.font_heading.render("LIFETIME STATS", True, (200, 210, 230))
        surf.blit(title, (24, y))
        y += 32

        stats = [
            ("FOOD EATEN", str(fish.food_eaten), (80, 255, 220)),
            ("DISTANCE", f"{int(fish.distance_traveled)}", (255, 200, 100)),
            ("OFFSPRING", str(fish.offspring_count), (255, 140, 200)),
        ]

        for i, (label, value, col) in enumerate(stats):
            x = 24 + i * 148
            pygame.draw.rect(surf, (20, 24, 38), (x, y, 130, 72), border_radius=12)
            pygame.draw.rect(surf, col, (x, y, 130, 72), width=3, border_radius=12)

            val_txt = self.font_title.render(value, True, col)
            surf.blit(val_txt, (x + 18, y + 12))
            label_txt = self.font_tiny.render(label, True, (160, 170, 200))
            surf.blit(label_txt, (x + 18, y + 48))

        return y + 88