"""
Enhanced Brain Visualizer — Fluid Underwater Neural Theatre

Design: Organic, fluid, bioluminescent. The panel feels like peering through
glass into a living brain suspended in deep water — caustic light ripples
across the surface, neurons pulse like jellyfish, connections flow like
luminous currents.

Features:
- Animated caustic light background (light through water surface)
- Organic nodes with triple-layer bioluminescent glow
- Flowing gradient connections with trailing signal particles
- Wave distortion on all elements (underwater shimmer)
- Meaningful input labels (Food-L, Threat-C, etc.)
- Decision reasoning computed from real inputs
- Compact state probability bars
- Recurrent memory heatmap strip
- Top active inputs panel
"""

import math
import random

import pygame

from ..config import (
    BRAIN_PANEL_HEIGHT,
    BRAIN_PANEL_WIDTH,
    FISH_MAX_ENERGY,
    FISH_STATE_ORDER,
    NN_HIDDEN1_SIZE,
    NN_HIDDEN2_SIZE,
    NN_INPUT_COUNT,
)

# ── Palette ───────────────────────────────────────────────────────────────────

BG_DEEP = (4, 8, 16)

# Node layer colours — bioluminescent
COL_INPUT_BASE = (20, 160, 200)
COL_INPUT_HI = (80, 255, 240)
COL_H1_BASE = (160, 100, 220)
COL_H1_HI = (210, 160, 255)
COL_H2_BASE = (100, 180, 120)
COL_H2_HI = (160, 255, 180)
COL_OUT_BASE = (220, 160, 60)
COL_OUT_HI = (255, 220, 100)

# Species accents
ACCENT_COMMON = (255, 185, 55)
ACCENT_CLEANER = (0, 230, 200)
ACCENT_PREDATOR = (255, 80, 90)

# UI text
TEXT_DIM = (90, 130, 165)
TEXT_MID = (150, 195, 225)
TEXT_HI = (220, 240, 255)
TEXT_BRIGHT = (255, 255, 255)

# Connections
CONN_DIM = (15, 30, 50)
CONN_POS = (40, 180, 160)
CONN_NEG = (180, 90, 40)

# Behaviour drives
DRIVE_HIDE = (80, 140, 255)
DRIVE_SPRINT = (255, 190, 60)
DRIVE_CLEAN = (80, 255, 140)
DRIVE_AMBUSH = (255, 100, 160)
DRIVE_DASH = (255, 60, 60)

# State colours
STATE_COLS = [
    (100, 140, 255),
    (255, 180, 60),
    (255, 70, 70),
    (255, 100, 200),
    (180, 100, 255),
]

STATE_NAMES = ["REST", "HUNT", "FLEE", "MATE", "NEST"]

# Meaningful input labels (30 inputs)
INPUT_LABELS = [
    "FD-L", "FD-C", "FD-R",       # Food radar: Left, Center, Right
    "TH-L", "TH-C", "TH-R",       # Threat radar
    "MT-L", "MT-C", "MT-R",       # Mate radar
    "NRJ", "STM",                  # Energy, Stamina
    "DPT", "SPD",                  # Depth, Speed
    "COV", "PLT", "PLD",          # Cover, Plant food, Plant dist
    "AMB", "MTE",                  # Ambush alert, Mate distance
    "TOD", "SEA",                  # Time of day, Season
    "P-R", "P-H", "P-F",          # Prev state: Rest, Hunt
    "P-FL", "P-M",                 # Prev state: Flee, Mate
    "HNG", "AGE",                  # Hunger memory, Life stage
    "PRE", "CLI", "WST",           # Prey dist, Client dist, Waste dist
]

# Meaningful input descriptions (for decision reasoning)
INPUT_DESC = [
    "Food L", "Food C", "Food R",
    "Threat L", "Threat C", "Threat R",
    "Mate L", "Mate C", "Mate R",
    "Energy", "Stamina",
    "Depth", "Speed",
    "Cover", "Plant food", "Plant dist",
    "Ambush", "Mate dist",
    "Time", "Season",
    "Prev Rest", "Prev Hunt", "Prev Flee", "Prev Mate", "Prev Nest",
    "Hunger", "Age",
    "Prey dist", "Client dist", "Waste dist",
]

# ── Configuration ─────────────────────────────────────────────────────────────

DRIFT_SPEED_BASE = 0.4
DRIFT_SPEED_MULT = 1.2
DRIFT_MAGNITUDE = 3.0
DRIFT_Y_FREQ_MULT = 0.7

WAVE_AMP = 6.0
WAVE_FREQ = 1.5
WAVE_PHASE_SCALE = 0.012

CAUSTIC_SPEED = 0.3
CAUSTIC_SCALE = 0.025
CAUSTIC_INTENSITY = 18

DUST_COUNT = 18
DUST_SPEED = 8.0

# ── Helpers ───────────────────────────────────────────────────────────────────


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def glow_circle(surf, color, pos, radius, alpha=180, layers=3):
    x, y = int(pos[0]), int(pos[1])
    for i in range(layers, 0, -1):
        r = radius + (layers - i) * 6
        a = alpha // (layers - i + 1)
        gsurf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*color, a), (r + 1, r + 1), r)
        surf.blit(gsurf, (x - r - 1, y - r - 1))
    pygame.draw.circle(surf, (*color, min(255, int(alpha * 1.3))), (x, y), radius)


def draw_rounded_rect(surf, color, rect, radius=8, alpha=255):
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
    surf.blit(s, (rect[0], rect[1]))


def quad_bezier(p0, p1, p2, t):
    (x0, y0), (cx, cy), (x2, y2) = p0, p1, p2
    u = 1 - t
    return u * u * x0 + 2 * u * t * cx + t * t * x2, u * u * y0 + 2 * u * t * cy + t * t * y2


def make_wavy_control(p0, p2, phase, amp=WAVE_AMP):
    mid_x = (p0[0] + p2[0]) / 2
    mid_y = (p0[1] + p2[1]) / 2
    wave = math.sin(phase + (p0[0] + p0[1]) * WAVE_PHASE_SCALE) * amp
    return mid_x, mid_y + wave


def draw_separator(surf, y, width, color, anim_t):
    a = int(30 + 10 * math.sin(anim_t * 1.5))
    for dx in range(0, width, 3):
        seg_a = a + int(8 * math.sin(anim_t * 2.0 + dx * 0.05))
        seg_a = max(0, min(255, seg_a))
        pygame.draw.line(surf, (*color, seg_a), (dx, y), (dx + 1, y))


# ── Ambient Dust Particle ────────────────────────────────────────────────────


class DustParticle:
    __slots__ = ("x", "y", "vx", "vy", "size", "alpha", "phase")

    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-DUST_SPEED, DUST_SPEED) * 0.3
        self.vy = random.uniform(-DUST_SPEED, DUST_SPEED) * 0.15 - 2.0
        self.size = random.uniform(1.0, 2.5)
        self.alpha = random.randint(15, 40)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, dt, w, h):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x += math.sin(self.phase) * 0.3 * dt
        if self.y < -5:
            self.y = h + 5
            self.x = random.uniform(0, w)
        if self.x < -5:
            self.x = w + 5
        elif self.x > w + 5:
            self.x = -5

    def draw(self, surf):
        r = int(self.size)
        gsurf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (180, 210, 230, self.alpha), (r + 1, r + 1), r)
        surf.blit(gsurf, (int(self.x) - r - 1, int(self.y) - r - 1))


# ── Synaptic Signal Particle ─────────────────────────────────────────────────


class SynapticParticle:
    __slots__ = ("x1", "y1", "x2", "y2", "t", "speed", "color", "strength", "alive")

    def __init__(self, x1, y1, x2, y2, color, strength=1.0):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.t = 0.0
        self.speed = random.uniform(0.7, 1.5)
        self.color = color
        self.strength = strength
        self.alive = True

    def update(self, dt):
        self.t += dt * self.speed
        if self.t >= 1.0:
            self.alive = False

    def draw(self, surf, global_t):
        if not self.alive:
            return
        p0 = (self.x1, self.y1)
        p2 = (self.x2, self.y2)
        c = make_wavy_control(p0, p2, phase=global_t * WAVE_FREQ, amp=WAVE_AMP)

        # Draw trail of fading dots along the path
        trail_len = 5
        for i in range(trail_len):
            tt = self.t - i * 0.02
            if tt < 0:
                break
            px, py = quad_bezier(p0, c, p2, tt)
            fade = math.sin(tt * math.pi) * (1.0 - i / trail_len)
            r = int((2 + self.strength * 2) * (1.0 - i / trail_len * 0.5))
            alpha = int(180 * fade)
            if alpha < 5:
                continue
            gsurf = pygame.Surface((r * 4 + 2, r * 4 + 2), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (*self.color, alpha // 3), (r * 2 + 1, r * 2 + 1), r * 2)
            pygame.draw.circle(gsurf, (*self.color, alpha), (r * 2 + 1, r * 2 + 1), r)
            surf.blit(gsurf, (int(px) - r * 2 - 1, int(py) - r * 2 - 1))


# ── Neuron Node ──────────────────────────────────────────────────────────────


class NeuronNode:
    __slots__ = (
        "x", "y", "_drift_x", "_drift_y", "activation", "smooth_act",
        "phase", "base_color", "hi_color", "radius", "pulse_t",
        "fire_t", "label",
    )

    def __init__(self, x, y, base_color, hi_color, radius=7, label=""):
        self.x, self.y = x, y
        self._drift_x, self._drift_y = x, y
        self.activation = 0.0
        self.smooth_act = 0.0
        self.phase = random.uniform(0, math.pi * 2)
        self.base_color = base_color
        self.hi_color = hi_color
        self.radius = radius
        self.pulse_t = 0.0
        self.fire_t = 0.0
        self.label = label

    def set_activation(self, val):
        prev = self.activation
        self.activation = max(-1.0, min(1.0, val))
        if abs(self.activation) > 0.6 and abs(prev) < 0.4:
            self.fire_t = 1.0

    def update(self, dt, global_t):
        self.smooth_act = lerp(self.smooth_act, self.activation, min(1.0, dt * 8))
        self.pulse_t = (self.pulse_t + dt * 3) % (math.pi * 2)
        if self.fire_t > 0:
            self.fire_t = max(0.0, self.fire_t - dt * 3)

        drift_speed = DRIFT_SPEED_BASE + abs(self.smooth_act) * DRIFT_SPEED_MULT
        self._drift_x = self.x + math.sin(global_t * drift_speed + self.phase) * DRIFT_MAGNITUDE
        y_off = global_t * drift_speed * DRIFT_Y_FREQ_MULT + self.phase
        self._drift_y = self.y + math.cos(y_off) * DRIFT_MAGNITUDE

    def get_draw_pos(self):
        return int(self._drift_x), int(self._drift_y)

    def draw(self, surf, global_t):
        act = self.smooth_act
        abs_act = abs(act)
        cx, cy = self.get_draw_pos()

        # Organic breathing
        breath = 0.15 * math.sin(self.pulse_t + self.phase)
        display_r = self.radius * (0.8 + 0.2 * abs_act + breath * (0.3 + 0.7 * abs_act))

        # Colour
        if act >= 0:
            col = lerp_color(self.base_color, self.hi_color, abs_act)
        else:
            neg_col = (200, 80, 40)
            col = lerp_color(self.base_color, neg_col, abs_act)

        # Fire flash
        if self.fire_t > 0:
            col = lerp_color(col, (255, 255, 255), self.fire_t * 0.7)
            display_r += self.fire_t * 6

        # Triple-layer glow (jellyfish feel)
        if abs_act > 0.05:
            # Outer halo
            glow_r = int(display_r * 3.0)
            glow_a = int(20 + 50 * abs_act)
            outer = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(outer, (*col, glow_a // 3), (glow_r + 1, glow_r + 1), glow_r)
            surf.blit(outer, (cx - glow_r - 1, cy - glow_r - 1))

            # Mid halo
            mid_r = int(display_r * 2.0)
            mid_a = int(30 + 70 * abs_act)
            mid_s = pygame.Surface((mid_r * 2 + 2, mid_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(mid_s, (*col, mid_a // 2), (mid_r + 1, mid_r + 1), mid_r)
            surf.blit(mid_s, (cx - mid_r - 1, cy - mid_r - 1))

        # Inactive ring
        pygame.draw.circle(surf, (20, 40, 60), (cx, cy), int(self.radius + 1), 1)
        # Core
        pygame.draw.circle(surf, col, (cx, cy), max(1, int(display_r)))

        # Specular highlight
        if abs_act > 0.2:
            spec_x = int(cx - display_r * 0.3)
            spec_y = int(cy - display_r * 0.3)
            pygame.draw.circle(
                surf, (255, 255, 255), (spec_x, spec_y), max(1, int(display_r * 0.2)))


# ── Main Visualizer ──────────────────────────────────────────────────────────


class EnhancedBrainVisualizer:
    PANEL_W = BRAIN_PANEL_WIDTH
    PANEL_H = BRAIN_PANEL_HEIGHT

    DISPLAY_INPUTS = 18
    DISPLAY_H1 = NN_HIDDEN1_SIZE
    DISPLAY_H2 = NN_HIDDEN2_SIZE
    DISPLAY_OUTPUTS = 7

    def __init__(self, screen_width, screen_height):
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.panel_h = min(self.PANEL_H, screen_height)
        self.slide_x = float(self.PANEL_W)

        self.anim_t = 0.0
        self.prev_state = None
        self.state_flash = 0.0

        # Fonts — sans-serif for readability
        try:
            self.f_title = pygame.font.SysFont("segoeui", 24, bold=True)
            self.f_body = pygame.font.SysFont("segoeui", 17)
            self.f_small = pygame.font.SysFont("segoeui", 14)
            self.f_tiny = pygame.font.SysFont("segoeui", 12)
        except Exception:
            self.f_title = pygame.font.Font(None, 28)
            self.f_body = pygame.font.Font(None, 22)
            self.f_small = pygame.font.Font(None, 18)
            self.f_tiny = pygame.font.Font(None, 15)

        # Node layout
        self._nodes_input = []
        self._nodes_h1 = []
        self._nodes_h2 = []
        self._nodes_output = []
        self._nodes_built = False

        # Particles
        self._particles = []
        self._particle_timer = 0.0

        # Ambient dust
        self._dust = [DustParticle(self.PANEL_W, self.panel_h) for _ in range(DUST_COUNT)]

        # Smoothed values
        self._drive_smooth = {"hide": 0.0, "sprint": 0.0, "clean": 0.0, "ambush": 0.0, "dash": 0.0}
        self._state_probs_smooth = [0.2] * 5
        self._energy_smooth = 0.8
        self._stamina_smooth = 1.0

        # Cached surfaces
        self._panel_surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)
        self._bg_surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)
        self._bg_frame = 0

        # Connection weights
        self._conn_w1 = []
        self._conn_w2 = []
        self._conn_w3 = []

        self.net_top = 200

        # Recurrent arc
        self._recurrent_angle = 0.0

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_nodes(self, fish_accent):
        PAD_X = 20
        net_height = 300
        net_top = self.net_top
        net_bot = net_top + net_height

        col_xs = [PAD_X + 25, PAD_X + 110, PAD_X + 210, PAD_X + 310]

        def even_ys(count, top, bot):
            if count == 1:
                return [(top + bot) / 2]
            return [top + i * (bot - top) / (count - 1) for i in range(count)]

        # Input nodes
        ys = even_ys(self.DISPLAY_INPUTS, net_top, net_bot)
        self._nodes_input = [
            NeuronNode(col_xs[0], y, COL_INPUT_BASE, COL_INPUT_HI, radius=6)
            for y in ys
        ]
        for i, n in enumerate(self._nodes_input):
            n.label = INPUT_LABELS[i] if i < len(INPUT_LABELS) else f"I{i}"

        # Hidden1
        ys = even_ys(self.DISPLAY_H1, net_top, net_bot)
        self._nodes_h1 = [
            NeuronNode(col_xs[1], y, COL_H1_BASE, COL_H1_HI, radius=8)
            for y in ys
        ]

        # Hidden2
        ys = even_ys(self.DISPLAY_H2, net_top + 20, net_bot - 20)
        self._nodes_h2 = [
            NeuronNode(col_xs[2], y, COL_H2_BASE, COL_H2_HI, radius=9)
            for y in ys
        ]

        # Output nodes
        out_labels = ["STEER", "THRUST", "HIDE", "SPRINT", "CLEAN", "AMBUSH", "DASH"]
        ys = even_ys(self.DISPLAY_OUTPUTS, net_top + 30, net_bot - 30)
        self._nodes_output = [
            NeuronNode(col_xs[3], y, COL_OUT_BASE, COL_OUT_HI, radius=8, label=lbl)
            for y, lbl in zip(ys, out_labels, strict=False)
        ]

        self._nodes_built = True

    def _sample_weights(self, fish):
        brain = fish.brain
        step_in = max(1, NN_INPUT_COUNT // self.DISPLAY_INPUTS)
        self._conn_w1 = []
        for i in range(self.DISPLAY_H1):
            row = []
            for j in range(self.DISPLAY_INPUTS):
                src = min(j * step_in, NN_INPUT_COUNT - 1)
                row.append(brain.w1[i][src])
            self._conn_w1.append(row)

        self._conn_w2 = [[brain.w2[i][j] for j in range(self.DISPLAY_H1)]
                          for i in range(self.DISPLAY_H2)]

        self._conn_w3 = [[brain.w3[i][j] for j in range(self.DISPLAY_H2)]
                          for i in range(self.DISPLAY_OUTPUTS)]

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt, selected_fish):
        self.anim_t += dt

        if selected_fish is not None:
            self.slide_x = max(0.0, self.slide_x - 1800 * dt)

            if not self._nodes_built:
                acc = self._get_accent(selected_fish)
                self._build_nodes(acc)
                self._sample_weights(selected_fish)

            if selected_fish.state != self.prev_state:
                self.state_flash = 1.0
            self.prev_state = selected_fish.state
            if self.state_flash > 0:
                self.state_flash = max(0.0, self.state_flash - dt * 4)

            # Push activations into nodes
            inputs = selected_fish.last_inputs
            step = max(1, len(inputs) // self.DISPLAY_INPUTS)
            for i, node in enumerate(self._nodes_input):
                val = inputs[min(i * step, len(inputs) - 1)] * 2 - 1
                node.set_activation(val)

            h1 = selected_fish.last_hidden1
            for i, node in enumerate(self._nodes_h1):
                node.set_activation(h1[i] if i < len(h1) else 0.0)

            h2 = selected_fish.last_hidden
            for i, node in enumerate(self._nodes_h2):
                node.set_activation(h2[i] if i < len(h2) else 0.0)

            outputs = selected_fish.last_outputs
            for i, node in enumerate(self._nodes_output):
                node.set_activation(outputs[i] * 2 - 1 if i < len(outputs) else 0.0)

            for node in (self._nodes_input + self._nodes_h1 + self._nodes_h2 + self._nodes_output):
                node.update(dt, self.anim_t)

            # Smooth drives
            if len(outputs) >= 7:
                targets = {
                    "hide": outputs[2], "sprint": outputs[3],
                    "clean": outputs[4], "ambush": outputs[5], "dash": outputs[6],
                }
            else:
                targets = {k: 0.0 for k in self._drive_smooth}
            for k, v in targets.items():
                self._drive_smooth[k] = lerp(self._drive_smooth[k], v, min(1.0, dt * 6))

            # Smooth state probs
            probs = selected_fish.last_state_probs
            for i in range(5):
                target = probs[i] if i < len(probs) else 0.2
                self._state_probs_smooth[i] = lerp(self._state_probs_smooth[i], target, dt * 4)

            # Smooth vitals
            energy_ratio = selected_fish.energy / FISH_MAX_ENERGY
            self._energy_smooth = lerp(self._energy_smooth, energy_ratio, dt * 5)
            stamina_ratio = selected_fish.stamina / 100.0
            self._stamina_smooth = lerp(self._stamina_smooth, stamina_ratio, dt * 5)

            # Synaptic particles
            self._particle_timer -= dt
            if self._particle_timer <= 0:
                self._emit_particle(selected_fish)
                freq = 0.06 if len(outputs) >= 2 and abs(outputs[1]) > 0.5 else 0.18
                self._particle_timer = random.uniform(freq, freq * 2)

            for p in self._particles[:]:
                p.update(dt)
                if not p.alive:
                    self._particles.remove(p)

            self._recurrent_angle = (self._recurrent_angle + dt * 180) % 360

        else:
            self.slide_x = min(float(self.PANEL_W), self.slide_x + 1800 * dt)
            if self.slide_x >= self.PANEL_W:
                self._nodes_built = False
                self._particles.clear()

        # Update dust
        for d in self._dust:
            d.update(dt, self.PANEL_W, self.panel_h)

    def _emit_particle(self, fish):
        outputs = fish.last_outputs
        roll = random.random()

        if roll < 0.35 and self._nodes_input and self._nodes_h1:
            src = random.choice(self._nodes_input)
            dst = random.choice(self._nodes_h1)
            strength = abs(src.smooth_act) * 0.5 + abs(dst.smooth_act) * 0.5
            if strength > 0.1:
                col = lerp_color(COL_INPUT_HI, COL_H1_HI, 0.5)
                sx, sy = src.get_draw_pos()
                dx, dy = dst.get_draw_pos()
                self._particles.append(SynapticParticle(sx, sy, dx, dy, col, strength))

        elif roll < 0.65 and self._nodes_h1 and self._nodes_h2:
            src = random.choice(self._nodes_h1)
            dst = random.choice(self._nodes_h2)
            strength = abs(src.smooth_act) * 0.5 + abs(dst.smooth_act) * 0.5
            if strength > 0.1:
                col = lerp_color(COL_H1_HI, COL_H2_HI, 0.5)
                sx, sy = src.get_draw_pos()
                dx, dy = dst.get_draw_pos()
                self._particles.append(SynapticParticle(sx, sy, dx, dy, col, strength))

        elif self._nodes_h2 and self._nodes_output:
            src = random.choice(self._nodes_h2)
            dst_idx = random.randint(0, len(self._nodes_output) - 1)
            dst = self._nodes_output[dst_idx]
            out_val = outputs[dst_idx] if dst_idx < len(outputs) else 0.0
            strength = abs(src.smooth_act) * 0.3 + out_val * 0.7
            if strength > 0.15:
                accent = self._get_accent_from_flags(
                    getattr(fish, "is_cleaner", False), getattr(fish, "is_predator", False))
                sx, sy = src.get_draw_pos()
                dx, dy = dst.get_draw_pos()
                self._particles.append(SynapticParticle(sx, sy, dx, dy, accent, strength))

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _get_accent(self, fish):
        if fish.is_predator:
            return ACCENT_PREDATOR
        if fish.is_cleaner:
            return ACCENT_CLEANER
        return ACCENT_COMMON

    def _get_accent_from_flags(self, is_cleaner, is_predator):
        if is_predator:
            return ACCENT_PREDATOR
        if is_cleaner:
            return ACCENT_CLEANER
        return ACCENT_COMMON

    def draw(self, screen, selected_fish, time):
        if self.slide_x >= self.PANEL_W:
            return

        W, H = self.PANEL_W, self.panel_h
        surf = self._panel_surf
        surf.fill((0, 0, 0, 0))

        accent = self._get_accent(selected_fish) if selected_fish else ACCENT_COMMON

        # Background with caustic
        self._draw_background(surf, accent)

        # Left edge glow
        for i in range(6):
            a = int(50 * (1 - i / 6) * (0.7 + 0.3 * math.sin(self.anim_t * 1.8 + i)))
            lsurf = pygame.Surface((1, H), pygame.SRCALPHA)
            lsurf.fill((*accent, a))
            surf.blit(lsurf, (i, 0))

        # Header
        y = self._draw_header(surf, selected_fish, accent)

        # Vitals
        y = self._draw_vitals(surf, selected_fish, accent, y)

        # Top active inputs
        y = self._draw_top_inputs(surf, selected_fish, accent, y)

        # Neural network
        self.net_top = y + 10
        y = self._draw_neural_network(surf, selected_fish, accent, y + 10)

        # State bars
        y = self._draw_state_bars(surf, selected_fish, accent, y + 8)

        # Decision reasoning
        y = self._draw_reasoning(surf, selected_fish, accent, y + 8)

        # Recurrent memory strip
        y = self._draw_recurrent_strip(surf, selected_fish, accent, y + 6)

        # Footer
        self._draw_footer(surf, selected_fish, accent, y + 8)

        # Dust particles
        for d in self._dust:
            d.draw(surf)

        # Blit to screen
        dest_x = self.screen_w - W + int(self.slide_x)
        screen.blit(surf, (dest_x, 0))

    # ── Background ────────────────────────────────────────────────────────────

    def _draw_background(self, surf, accent):
        W, H = self.PANEL_W, self.panel_h
        surf.fill((*BG_DEEP, 250))

        # Update caustic every 3 frames for performance
        self._bg_frame += 1
        if self._bg_frame % 3 == 0:
            self._bg_surf.fill((0, 0, 0, 0))
            t = self.anim_t
            for cy in range(0, H, 4):
                for cx in range(0, W, 4):
                    # Overlapping sine waves for caustic pattern
                    v1 = math.sin(cx * CAUSTIC_SCALE + t * CAUSTIC_SPEED)
                    v2 = math.sin(cy * CAUSTIC_SCALE * 1.3 + t * CAUSTIC_SPEED * 0.7)
                    v3 = math.sin((cx + cy) * CAUSTIC_SCALE * 0.8 + t * CAUSTIC_SPEED * 1.2)
                    val = (v1 + v2 + v3) / 3.0
                    if val > 0.3:
                        a = int(CAUSTIC_INTENSITY * (val - 0.3) / 0.7)
                        a = max(0, min(60, a))
                        pygame.draw.rect(self._bg_surf, (*accent, a), (cx, cy, 4, 4))

        surf.blit(self._bg_surf, (0, 0))

        # Top gradient
        for y in range(0, min(40, H)):
            a = int(15 * (1 - y / 40))
            pygame.draw.line(surf, (*accent, a), (0, y), (W, y))

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, surf, fish, accent):
        PAD = 16
        y = 12

        # Species pill
        species = "PREDATOR" if fish.is_predator else "CLEANER" if fish.is_cleaner else "COMMON"
        pill_w, pill_h = 90, 22
        draw_rounded_rect(surf, accent, (PAD, y, pill_w, pill_h), radius=11, alpha=200)
        t = self.f_tiny.render(species, True, BG_DEEP)
        surf.blit(t, (PAD + (pill_w - t.get_width()) // 2, y + 5))

        # Sex
        sex_col = (120, 160, 255) if fish.sex == "M" else (255, 120, 180)
        sex_sym = "\u2642" if fish.sex == "M" else "\u2640"
        sx = self.f_body.render(sex_sym, True, sex_col)
        surf.blit(sx, (PAD + pill_w + 10, y))
        y += pill_h + 8

        # State — pulsing
        flash_t = self.state_flash
        state_col = lerp_color(TEXT_MID, accent, flash_t)
        brightness = 0.8 + 0.2 * math.sin(self.anim_t * 4)
        state_col = tuple(int(c * brightness) for c in state_col)
        st = self.f_title.render(fish.state.name, True, state_col)
        surf.blit(st, (PAD, y))
        y += 30

        # Age + food
        age_t = self.f_small.render(
            f"Age {fish.age:.0f}s  |  Fed {fish.food_eaten}x", True, TEXT_DIM)
        surf.blit(age_t, (PAD, y))
        y += 20

        draw_separator(surf, y, self.PANEL_W, accent, self.anim_t)
        return y + 6

    # ── Vitals ────────────────────────────────────────────────────────────────

    def _draw_vitals(self, surf, fish, accent, y):
        PAD = 16
        BAR_W = self.PANEL_W - PAD * 2 - 58
        BAR_H = 14

        bars = [
            ("ENERGY", self._energy_smooth, accent, (255, 80, 80)),
            ("STAMINA", self._stamina_smooth, (80, 220, 140), (180, 180, 60)),
        ]

        for label, ratio, col_full, col_low in bars:
            lt = self.f_tiny.render(label, True, TEXT_DIM)
            surf.blit(lt, (PAD, y + 2))
            bx = PAD + 58

            draw_rounded_rect(surf, (12, 22, 36), (bx, y, BAR_W, BAR_H), radius=7)

            fill_w = max(2, int(BAR_W * ratio))
            fill_col = lerp_color(col_low, col_full, ratio)
            draw_rounded_rect(surf, fill_col, (bx, y, fill_w, BAR_H), radius=7)

            # Shimmer
            shimmer_x = bx + int((self.anim_t * 100) % (BAR_W + 40)) - 20
            if bx < shimmer_x < bx + fill_w:
                sw = min(16, fill_w - (shimmer_x - bx))
                if sw > 0:
                    ssurf = pygame.Surface((sw, BAR_H), pygame.SRCALPHA)
                    ssurf.fill((255, 255, 255, 50))
                    surf.blit(ssurf, (shimmer_x, y))

            pct = self.f_tiny.render(f"{int(ratio * 100)}%", True, TEXT_MID)
            surf.blit(pct, (bx + BAR_W + 4, y + 2))
            y += 24

        return y + 4

    # ── Top Active Inputs ─────────────────────────────────────────────────────

    def _draw_top_inputs(self, surf, fish, accent, y):
        PAD = 16
        t = self.f_small.render("TOP SENSORS", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 18

        inputs = fish.last_inputs
        # Find top 4 active inputs
        indexed = [(i, inputs[i]) for i in range(min(len(inputs), NN_INPUT_COUNT))]
        indexed.sort(key=lambda x: abs(x[1]), reverse=True)
        top = indexed[:4]

        BAR_W = self.PANEL_W - PAD * 2 - 90
        for idx, val in top:
            label = INPUT_LABELS[idx] if idx < len(INPUT_LABELS) else f"I{idx}"
            # Colour by layer
            if idx < 9:
                col = COL_INPUT_HI
            elif idx < 18:
                col = (180, 220, 255)
            else:
                col = TEXT_MID

            lt = self.f_tiny.render(label, True, lerp_color(TEXT_DIM, col, min(1.0, val * 2)))
            surf.blit(lt, (PAD, y + 1))
            bx = PAD + 42

            # Mini bar
            draw_rounded_rect(surf, (12, 22, 36), (bx, y + 1, BAR_W, 8), radius=4)
            fw = max(1, int(BAR_W * min(1.0, val)))
            draw_rounded_rect(surf, col, (bx, y + 1, fw, 8), radius=4)

            vt = self.f_tiny.render(f"{val:.2f}", True, TEXT_DIM)
            surf.blit(vt, (bx + BAR_W + 4, y))
            y += 14

        return y + 4

    # ── Neural Network ────────────────────────────────────────────────────────

    def _draw_neural_network(self, surf, fish, accent, y_start):
        self._draw_connections(surf)

        for p in self._particles:
            p.draw(surf, self.anim_t)

        for node in (self._nodes_input + self._nodes_h1 + self._nodes_h2 + self._nodes_output):
            node.draw(surf, self.anim_t)

        # Layer labels
        labels = [
            (self._nodes_input[0].x if self._nodes_input else 30, "INPUT"),
            (self._nodes_h1[0].x if self._nodes_h1 else 110, "HIDDEN 1"),
            (self._nodes_h2[0].x if self._nodes_h2 else 210, "HIDDEN 2"),
            (self._nodes_output[0].x if self._nodes_output else 310, "OUTPUT"),
        ]
        for lx, lbl in labels:
            lt = self.f_tiny.render(lbl, True, TEXT_DIM)
            surf.blit(lt, (int(lx) - lt.get_width() // 2, y_start - 14))

        # Recurrent arc
        if self._nodes_h2 and fish.brain.recurrent:
            self._draw_recurrent_arc(surf)

        # Input labels (left side)
        for node in self._nodes_input:
            lt = self.f_tiny.render(
                node.label, True,
                lerp_color(TEXT_DIM, COL_INPUT_HI, abs(node.smooth_act)))
            curr_x, curr_y = node.get_draw_pos()
            surf.blit(lt, (curr_x - lt.get_width() - 14, curr_y - 5))

        # Output labels (right side) — with drive values
        out_drive_map = {
            "HIDE": "hide", "SPRINT": "sprint", "CLEAN": "clean",
            "AMBUSH": "ambush", "DASH": "dash",
        }
        for node in self._nodes_output:
            drive_key = out_drive_map.get(node.label)
            if drive_key and drive_key in self._drive_smooth:
                val = self._drive_smooth[drive_key]
                lbl_text = f"{node.label} {val:.2f}"
            else:
                lbl_text = node.label
            lt = self.f_tiny.render(
                lbl_text, True,
                lerp_color(TEXT_DIM, COL_OUT_HI, abs(node.smooth_act)))
            curr_x, curr_y = node.get_draw_pos()
            surf.blit(lt, (curr_x + 14, curr_y - 5))

        all_nodes = self._nodes_input + self._nodes_h1 + self._nodes_h2 + self._nodes_output
        if all_nodes:
            return int(max(n.y for n in all_nodes)) + 20
        return y_start + 310

    def _draw_connections(self, surf):
        def draw_layer_connections(src_nodes, dst_nodes, weights, max_conns=60):
            pairs = []
            for di, dst in enumerate(dst_nodes):
                for si, src in enumerate(src_nodes):
                    if si < len(weights[di]) if di < len(weights) else False:
                        w = weights[di][si]
                        pairs.append((abs(w), w, src, dst))
            pairs.sort(key=lambda x: x[0])

            for _i, (absw, w, src, dst) in enumerate(pairs[-max_conns:]):
                intensity = min(1.0, absw / 2.0)
                if intensity < 0.05:
                    continue
                src_act = abs(src.smooth_act)
                dst_act = abs(dst.smooth_act)
                activity = (src_act + dst_act) / 2.0

                if w >= 0:
                    col = lerp_color(CONN_DIM, CONN_POS, intensity * activity)
                else:
                    col = lerp_color(CONN_DIM, CONN_NEG, intensity * activity)

                alpha = int(15 + 140 * intensity * max(0.15, activity))
                width = max(1, int(1 + intensity * 2))

                x1, y1 = src.get_draw_pos()
                x2, y2 = dst.get_draw_pos()
                p0, p2 = (x1, y1), (x2, y2)
                c = make_wavy_control(p0, p2, phase=self.anim_t * WAVE_FREQ, amp=WAVE_AMP)

                points = [quad_bezier(p0, c, p2, t) for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
                points = [(int(px), int(py)) for px, py in points]
                pygame.draw.lines(surf, (*col, alpha), False, points, width)

        if self._conn_w1:
            draw_layer_connections(self._nodes_input, self._nodes_h1, self._conn_w1, 25)
        if self._conn_w2:
            draw_layer_connections(self._nodes_h1, self._nodes_h2, self._conn_w2, 20)
        if self._conn_w3:
            draw_layer_connections(self._nodes_h2, self._nodes_output, self._conn_w3, 15)

    def _draw_recurrent_arc(self, surf):
        if not self._nodes_h2:
            return
        top_node = self._nodes_h2[0]
        bot_node = self._nodes_h2[-1]
        tx, ty = top_node.get_draw_pos()
        bx, by = bot_node.get_draw_pos()
        cx = tx + 38
        cy = int((ty + by) / 2)
        rx, ry = 22, int((by - ty) / 2)

        angle_rad = math.radians(self._recurrent_angle)
        a = int(35 + 55 * math.sin(angle_rad))
        arc_rect = pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2)
        try:
            pygame.draw.arc(surf, (*COL_H2_HI, a), arc_rect,
                            angle_rad, angle_rad + math.pi, 2)
        except Exception:
            pass

        # Pulse dot
        px = cx + math.cos(angle_rad) * rx
        py = cy + math.sin(angle_rad) * ry
        gsurf = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*COL_H2_HI, 160), (8, 8), 5)
        surf.blit(gsurf, (int(px) - 8, int(py) - 8))

        lt = self.f_tiny.render("REC", True, TEXT_DIM)
        surf.blit(lt, (cx - lt.get_width() // 2 + 4, cy - 8))

    # ── State Bars ────────────────────────────────────────────────────────────

    def _draw_state_bars(self, surf, fish, accent, y):
        PAD = 16
        t = self.f_small.render("STATE PROBABILITIES", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 18

        cur_idx = FISH_STATE_ORDER.index(fish.state)
        probs = self._state_probs_smooth
        total = sum(probs) or 1.0
        BAR_W = self.PANEL_W - PAD * 2

        # Draw stacked horizontal bar
        x = PAD
        for i, prob in enumerate(probs):
            seg_w = int(BAR_W * (prob / total))
            if seg_w < 1:
                seg_w = 1
            col = STATE_COLS[i]
            is_active = (i == cur_idx)
            alpha = 220 if is_active else 140
            draw_rounded_rect(surf, col, (x, y, seg_w, 14), radius=3, alpha=alpha)
            if seg_w > 20:
                name = STATE_NAMES[i]
                lbl_col = (0, 0, 0) if is_active else (200, 200, 200)
                label_t = self.f_tiny.render(name, True, lbl_col)
                surf.blit(label_t, (x + 3, y + 1))
            x += seg_w

        y += 20

        # Legend row
        lx = PAD
        for i, (name, col) in enumerate(zip(STATE_NAMES, STATE_COLS, strict=False)):
            is_active = (i == cur_idx)
            lc = lerp_color(TEXT_DIM, col, 0.4 + 0.6 * (1 if is_active else 0))
            pygame.draw.circle(surf, col, (int(lx) + 4, int(y) + 6), 4)
            pct = int(probs[i] / total * 100)
            lt = self.f_tiny.render(f"{name} {pct}%", True, lc)
            surf.blit(lt, (int(lx) + 12, int(y)))
            lx += lt.get_width() + 16

        return y + 18

    # ── Decision Reasoning ────────────────────────────────────────────────────

    def _draw_reasoning(self, surf, fish, accent, y):
        PAD = 16
        t = self.f_small.render("NEURAL DECISION", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 18

        inputs = fish.last_inputs
        state = fish.state

        # Build reasoning from actual inputs
        signals = []
        if len(inputs) > 4:
            # Find strongest threat
            threat_vals = [inputs[3], inputs[4], inputs[5]]
            max_threat = max(threat_vals)
            if max_threat > 0.3:
                signals.append(f"Threat:{max_threat:.2f}")

            # Find strongest food
            food_vals = [inputs[0], inputs[1], inputs[2]]
            max_food = max(food_vals)
            if max_food > 0.3:
                signals.append(f"Food:{max_food:.2f}")

            # Energy
            energy = inputs[9] if len(inputs) > 9 else 0.5
            if energy < 0.4:
                signals.append(f"LowEnergy:{energy:.2f}")
            elif energy > 0.7:
                signals.append(f"HighEnergy:{energy:.2f}")

            # Cover
            cover = inputs[13] if len(inputs) > 13 else 0.0
            if cover > 0.3:
                signals.append(f"Cover:{cover:.2f}")

            # Ambush alert
            ambush = inputs[16] if len(inputs) > 16 else 0.0
            if ambush > 0.3:
                signals.append("AmbushAlert!")

        # Compose reasoning line
        if signals:
            reasoning = " + ".join(signals[:3]) + f" -> {state.name}"
        else:
            reasoning = f"Baseline activity -> {state.name}"

        # Wrap text
        x, max_w = PAD, self.PANEL_W - PAD * 2
        words = reasoning.split()
        line = ""
        for word in words:
            test = line + word + " "
            if self.f_tiny.size(test)[0] <= max_w:
                line = test
            else:
                rt = self.f_tiny.render(line, True, TEXT_MID)
                surf.blit(rt, (x, y))
                y += 14
                line = word + " "
        if line:
            rt = self.f_tiny.render(line, True, TEXT_MID)
            surf.blit(rt, (x, y))
            y += 14

        return y + 4

    # ── Recurrent Memory Strip ────────────────────────────────────────────────

    def _draw_recurrent_strip(self, surf, fish, accent, y):
        PAD = 16
        t = self.f_small.render("MEMORY STATE", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 16

        h2 = fish.last_hidden
        if not h2:
            return y

        # Draw 8-cell heatmap strip
        cell_w = 24
        cell_h = 14
        gap = 3
        start_x = PAD

        for i, val in enumerate(h2):
            x = start_x + i * (cell_w + gap)
            # Map [-1, 1] to colour: blue negative, dark zero, amber positive
            if val >= 0:
                col = lerp_color((10, 15, 30), COL_OUT_HI, min(1.0, val))
            else:
                col = lerp_color((10, 15, 30), (60, 120, 200), min(1.0, abs(val)))
            draw_rounded_rect(surf, col, (x, y, cell_w, cell_h), radius=3)

        y += cell_h + 4

        # Activity summary
        avg_act = sum(abs(v) for v in h2) / max(1, len(h2))
        act_text = f"Avg activity: {avg_act:.3f}"
        at = self.f_tiny.render(act_text, True, TEXT_DIM)
        surf.blit(at, (PAD, y))

        return y + 16

    # ── Footer ────────────────────────────────────────────────────────────────

    def _draw_footer(self, surf, fish, accent, y):
        PAD = 16
        if y + 30 > self.panel_h:
            return
        info = (f"dist:{fish.distance_traveled:.0f}  "
                f"offs:{fish.offspring_count}  "
                f"{'PREGNANT' if fish.is_pregnant else ''}")
        ft = self.f_tiny.render(info, True, TEXT_DIM)
        surf.blit(ft, (PAD, min(y, self.panel_h - 20)))

        # Bottom accent line
        pygame.draw.line(surf, (*accent, 50),
                         (0, self.panel_h - 1),
                         (self.PANEL_W, self.panel_h - 1), 1)
