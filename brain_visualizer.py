"""
Brain Visualizer — Updated for improved neural network architecture.

Displays:
- Input layer (27 neurons): sensors + temporal context
- Hidden layer 1 (14 neurons): tanh activation
- Hidden layer 2 (8 neurons): tanh + recurrent
- Output layer (9 neurons): movement, behavior, states
"""

import pygame
import math
import random
from config import (
    BRAIN_PANEL_WIDTH,
    BRAIN_PANEL_HEIGHT,
    FishState,
    FISH_MAX_ENERGY,
    NN_INPUT_COUNT,
    NN_HIDDEN1_SIZE,
    NN_HIDDEN2_SIZE,
    NN_OUTPUT_COUNT,
)

# ── Palette ────────────────────────────────────────────────────────────────────
BG = (6, 12, 20)
BG_SECTION = (12, 22, 35)
DIVIDER = (20, 38, 55)

TEXT_PRIMARY = (220, 240, 255)
TEXT_SECONDARY = (130, 165, 195)
TEXT_LABEL = (70, 110, 145)

# Bioluminescent accent colours
TEAL = (0, 210, 190)
TEAL_DIM = (0, 100, 90)
AMBER = (255, 185, 55)
AMBER_DIM = (140, 95, 20)
RED_ACC = (255, 100, 110)
RED_DIM = (130, 45, 50)
PURPLE = (180, 100, 255)
PURPLE_DIM = (90, 50, 130)

# Neural activation colours
COL_POS_HI = (80, 255, 220)
COL_POS_MID = (0, 180, 160)
COL_NEU = (30, 55, 80)
COL_NEG_MID = (200, 120, 40)
COL_NEG_HI = (255, 180, 60)

_COL_DIM_WIRE = (18, 35, 52)

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


# ── Helpers ───────────────────────────────────────────────────────────────────


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def activation_color(v):
    if v >= 0:
        t = min(1.0, v)
        mid = lerp_color(COL_NEU, COL_POS_MID, t)
        return lerp_color(mid, COL_POS_HI, t * t)
    else:
        t = min(1.0, -v)
        mid = lerp_color(COL_NEU, COL_NEG_MID, t)
        return lerp_color(mid, COL_NEG_HI, t * t)


def _cubic_bezier(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _bezier_points(p0, p3, steps=18):
    dx = (p3[0] - p0[0]) * 0.45
    p1 = (p0[0] + dx, p0[1])
    p2 = (p3[0] - dx, p3[1])
    return [_cubic_bezier(p0, p1, p2, p3, i / steps) for i in range(steps + 1)]


def draw_capsule(surface, color, x, y, w, h, radius=None):
    if radius is None:
        radius = h // 2
    pygame.draw.rect(surface, color, pygame.Rect(x, y, w, h), border_radius=radius)


# ── Input Labels for New Architecture ───────────────────────────────────────────

INPUT_LABELS = [
    # Radar inputs (0-8)
    "Food L", "Food C", "Food R",
    "Pred L", "Pred C", "Pred R",
    "Mate L", "Mate C", "Mate R",
    # Core stats (9-12)
    "Energy", "Stamina", "Depth", "Speed",
    # Environment (13-16)
    "Cover", "PlantFood", "PlantDist", "Ambush",
    # Mate distance (17)
    "MateDist",
    # Temporal context (18-25) - NEW
    "Time", "Season",
    "WasRest", "WasHunt", "WasFlee", "WasMate", "WasNest",
    "Hunger", "Age",
]

OUTPUT_LABELS = ["Str", "Thr", "Hide", "Spr", "Rest", "Hunt", "Flee", "Mate", "Nest"]

# Temporal input indices for maintainability
TEMPORAL_TIME_IDX = 18
TEMPORAL_SEASON_IDX = 19
TEMPORAL_WAS_REST_IDX = 20
TEMPORAL_WAS_HUNT_IDX = 21
TEMPORAL_WAS_FLEE_IDX = 22
TEMPORAL_WAS_MATE_IDX = 23
TEMPORAL_WAS_NEST_IDX = 24
TEMPORAL_HUNGER_IDX = 25


class BrainVisualizer:
    PANEL_W = BRAIN_PANEL_WIDTH
    PANEL_H = BRAIN_PANEL_HEIGHT

    _GLOW = 48
    _glow_surf = None

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
        BrainVisualizer._glow_surf = pygame.Surface(
            (self._GLOW * 2, self._GLOW * 2), pygame.SRCALPHA
        )

        self._node_positions_built = False
        self._pos_in = []
        self._pos_h1 = []
        self._pos_h2 = []
        self._pos_out = []
        self._ripples = []
        self._recurrent_pulse = 0.0

    def update(self, dt, selected_fish):
        self.anim_t += dt
        self._recurrent_pulse = (self._recurrent_pulse + dt * 3) % (math.pi * 2)

        if selected_fish is not None:
            self.slide_x = max(0.0, self.slide_x - 14 * dt * 60)
            target_i = self._INTENSITY.get(selected_fish.state, 0.5)
            self.anim_intensity += (target_i - self.anim_intensity) * 2.5 * dt
            if selected_fish.state != self.prev_state:
                self.state_flash = 0.6
            self.prev_state = selected_fish.state
        else:
            self.slide_x = min(float(self.PANEL_W), self.slide_x + 14 * dt * 60)
            self._ripples.clear()
            self._node_positions_built = False

        if self.state_flash > 0:
            self.state_flash = max(0.0, self.state_flash - dt)

        self._ripples = [
            (a + dt, m, pos, col) for a, m, pos, col in self._ripples if a < m
        ]

        # Trigger ripples on active inputs
        if self._pos_in and selected_fish is not None:
            inp = selected_fish.last_inputs
            if len(inp) >= NN_INPUT_COUNT:
                for i, node_pos in enumerate(self._pos_in):
                    act = inp[i] if i < len(inp) else 0.0
                    if abs(act) > 0.3 and random.random() < abs(act) * dt * 3:
                        self._ripples.append(
                            (0.0, 0.6, node_pos, activation_color(act))
                        )

    def draw(self, screen, selected_fish, time):
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
        y = self._draw_network(surf, selected_fish, accent, accent_dim, y)
        y = self._draw_divider(surf, y)
        y = self._draw_outputs(surf, selected_fish, accent, y)
        y = self._draw_divider(surf, y)
        y = self._draw_temporal_context(surf, selected_fish, accent, y)
        y = self._draw_divider(surf, y)
        self._draw_traits(surf, selected_fish, accent, y)

        dest_x = self.screen_w - self.PANEL_W + int(self.slide_x)
        screen.blit(surf, (dest_x, 0))

    def _draw_header(self, surf, fish, accent, y):
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
        pygame.draw.line(surf, DIVIDER, (margin, y), (self.PANEL_W - margin, y))
        return y + 10

    def _draw_status_bars(self, surf, fish, accent, y):
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

    def _draw_network(self, surf, fish, accent, accent_dim, y):
        PAD = 16
        surf.blit(self.f_small.render("NEURAL NETWORK (Improved)", True, TEXT_LABEL), (PAD, y))
        y += 20
        NET_H = 200
        net_top = y
        W = self.PANEL_W
        xs = {
            "in": int(W * 0.12),
            "h1": int(W * 0.35),
            "h2": int(W * 0.60),
            "out": int(W * 0.88),
        }

        def col_nodes(x, n):
            return [(x, net_top + int((i + 0.5) * NET_H / n)) for i in range(n)]

        # Build node positions for current architecture
        pos_in = col_nodes(xs["in"], NN_INPUT_COUNT)
        pos_h1 = col_nodes(xs["h1"], NN_HIDDEN1_SIZE)
        pos_h2 = col_nodes(xs["h2"], NN_HIDDEN2_SIZE)
        pos_out = col_nodes(xs["out"], NN_OUTPUT_COUNT)

        if not self._node_positions_built:
            self._pos_in, self._pos_h1, self._pos_h2, self._pos_out = (
                pos_in,
                pos_h1,
                pos_h2,
                pos_out,
            )
            self._node_positions_built = True

        inp = list(fish.last_inputs)
        h1 = list(fish.last_hidden1)
        h2 = list(fish.last_hidden)
        out = list(fish.last_outputs)

        # Draw connections
        def draw_connections(src_pos, dst_pos, src_acts):
            for i, sp in enumerate(src_pos):
                act = src_acts[i] if i < len(src_acts) else 0.0
                for dp in dst_pos:
                    pts = _bezier_points(sp, dp, steps=12)
                    pygame.draw.lines(surf, _COL_DIM_WIRE, False, pts, 1)
                    if abs(act) > 0.25:
                        pygame.draw.lines(surf, activation_color(act), False, pts, 1)

        draw_connections(pos_in, pos_h1, inp)
        draw_connections(pos_h1, pos_h2, h1)
        draw_connections(pos_h2, pos_out, h2)

        # Draw recurrent loop indicator on h2
        if fish.brain.recurrent if hasattr(fish, 'brain') else False:
            pulse_alpha = int(100 + 50 * math.sin(self._recurrent_pulse))
            rec_color = (*PURPLE, pulse_alpha)
            for pos in pos_h2:
                # Small loop arc
                pygame.draw.circle(surf, PURPLE_DIM, (int(pos[0]) - 8, int(pos[1])), 5, 1)

        # Draw nodes
        def draw_node(pos, act, r=5, label=None):
            col = activation_color(act)
            pygame.draw.circle(surf, col, pos, r)
            if label:
                tl = self.f_tiny.render(label, True, TEXT_LABEL)
                surf.blit(tl, (pos[0] + r + 3, pos[1] - 6))

        # Input nodes (smaller, more of them)
        for i, pos in enumerate(pos_in):
            draw_node(pos, inp[i] if i < len(inp) else 0.0, r=3)

        # Hidden 1 nodes
        for i, pos in enumerate(pos_h1):
            draw_node(pos, h1[i] if i < len(h1) else 0.0, r=4)

        # Hidden 2 nodes (with recurrent indicator)
        for i, pos in enumerate(pos_h2):
            draw_node(pos, h2[i] if i < len(h2) else 0.0, r=5)
            # Recurrent pulse
            if fish.brain.recurrent if hasattr(fish, 'brain') else False:
                pulse = int(4 + 2 * math.sin(self._recurrent_pulse + i))
                pygame.draw.circle(surf, (*PURPLE, 100), pos, pulse + 3, 1)

        # Output nodes
        for i, pos in enumerate(pos_out):
            draw_node(pos, out[i] if i < len(out) else 0.0, r=6, label=OUTPUT_LABELS[i] if i < len(OUTPUT_LABELS) else None)

        y += NET_H + 8
        return y

    def _draw_outputs(self, surf, fish, accent, y):
        PAD = 16
        surf.blit(self.f_small.render("BEHAVIOR DRIVES", True, TEXT_LABEL), (PAD, y))
        y += 18
        out = fish.last_outputs
        gx, gw, gh = PAD + 52, self.PANEL_W - PAD * 2 - 80, 10

        drives = [
            ("STEER", out[0], True),
            ("THRUST", max(0.0, min(1.0, out[1] if len(out) > 1 else 0.5)), False),
            ("HIDE/AMBUSH", out[2] if len(out) > 2 else 0.5, False),
            ("SPRINT/DASH", out[3] if len(out) > 3 else 0.5, False),
        ]

        for label, val, dual in drives:
            surf.blit(self.f_tiny.render(label, True, TEXT_SECONDARY), (PAD, y + 1))
            pygame.draw.rect(surf, BG_SECTION, (gx, y, gw, gh), border_radius=5)
            if dual:
                fw = int(abs(val) * gw / 2)
                fx = gx + gw // 2 if val >= 0 else gx + gw // 2 - fw
                pygame.draw.rect(
                    surf, activation_color(val), (fx, y, fw, gh), border_radius=5
                )
            else:
                pygame.draw.rect(
                    surf, accent, (gx, y, int(gw * max(0, min(1, val))), gh), border_radius=5
                )
            y += 16
        return y + 4

    def _draw_temporal_context(self, surf, fish, accent, y):
        """Display the new temporal context inputs."""
        PAD = 16
        surf.blit(self.f_small.render("TEMPORAL CONTEXT (NEW)", True, PURPLE), (PAD, y))
        y += 18
        gx, gw, gh = PAD + 52, self.PANEL_W - PAD * 2 - 80, 8

        inp = fish.last_inputs
        
        # Temporal inputs are at indices 18-25
        temporal_labels = [
            ("TIME", TEMPORAL_TIME_IDX),
            ("SEASON", TEMPORAL_SEASON_IDX),
            ("WAS_REST", TEMPORAL_WAS_REST_IDX),
            ("WAS_HUNT", TEMPORAL_WAS_HUNT_IDX),
            ("WAS_FLEE", TEMPORAL_WAS_FLEE_IDX),
            ("WAS_MATE", TEMPORAL_WAS_MATE_IDX),
            ("WAS_NEST", TEMPORAL_WAS_NEST_IDX),
            ("HUNGER", TEMPORAL_HUNGER_IDX),
        ]
        
        for label, idx in temporal_labels:
            val = inp[idx] if idx < len(inp) else 0.0
            surf.blit(self.f_tiny.render(label, True, TEXT_SECONDARY), (PAD, y + 1))
            pygame.draw.rect(surf, BG_SECTION, (gx, y, gw, gh), border_radius=4)
            pygame.draw.rect(
                surf, PURPLE_DIM, (gx, y, int(gw * max(0, min(1, val))), gh), border_radius=4
            )
            y += 12
        return y + 4

    def _draw_traits(self, surf, fish, accent, y):
        PAD = 16
        surf.blit(self.f_small.render("HERITABLE TRAITS", True, TEXT_LABEL), (PAD, y))
        y += 18
        LW, TW, TH = 70, self.PANEL_W - PAD * 2 - 100, 8

        trait_rows = [
            ("max_speed_mult", "Speed"),
            ("stamina_mult", "Stamina"),
            ("turn_rate_mult", "Turn"),
            ("metabolism_mult", "Metab"),
            ("size_mult", "Size"),
        ]

        for trait_key, display_label in trait_rows:
            if trait_key not in fish.traits.physical_traits:
                continue

            val = fish.traits.physical_traits[trait_key]
            surf.blit(self.f_tiny.render(display_label, True, TEXT_SECONDARY), (PAD, y + 1))
            pygame.draw.rect(surf, BG_SECTION, (PAD + LW, y, TW, TH), border_radius=4)
            dev = (val - 1.0) / 0.8
            bar_width = max(0, int(abs(dev) * TW / 2))
            bar_x = PAD + LW + TW // 2 if dev >= 0 else PAD + LW + TW // 2 - bar_width
            pygame.draw.rect(
                surf,
                TEAL if dev > 0 else AMBER,
                (bar_x, y, bar_width, TH),
                border_radius=4,
            )
            y += 14
        return y + 4
