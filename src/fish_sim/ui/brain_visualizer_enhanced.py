"""
Enhanced Brain Visualizer — Bioluminescent Neural Theatre

Design Direction: Deep-sea bioluminescence. Pulsing neurons like glowing jellyfish,
synaptic flows as luminous tendrils, the whole panel feels alive and breathing.

Features:
- Animated nodes with organic pulsing shaped by real activation values
- Signal particles that travel along active connections (synaptic firing)
- Layer-specific glow halos (radar = cool teal, hidden = warm amber, output = species accent)
- Layered connection rendering: dim inactive, bright active with flow particles
- Behavior drive gauges with liquid-fill animation
- State probability arc/pie visualization with animated transitions
- Breathing background with subtle noise
- Smooth slide-in/out panel
"""

import pygame
import math
import random
import collections
from ..config import (
    BRAIN_PANEL_WIDTH,
    BRAIN_PANEL_HEIGHT,
    FishState,
    FISH_STATE_ORDER,
    FISH_MAX_ENERGY,
    NN_INPUT_COUNT,
    NN_HIDDEN1_SIZE,
    NN_HIDDEN2_SIZE,
    NN_OUTPUT_COUNT,
)

# ── Palette ───────────────────────────────────────────────────────────────────

BG_DEEP        = (4, 8, 16)
BG_MID         = (8, 16, 28)
BG_PANEL       = (6, 12, 22, 250)

# Node layer colours
COL_INPUT_BASE  = (20, 160, 200)   # cold teal — sensory
COL_INPUT_HI    = (80, 255, 240)
COL_H1_BASE     = (160, 100, 220)  # violet — processing
COL_H1_HI      = (210, 160, 255)
COL_H2_BASE     = (100, 180, 120)  # seafoam — integration
COL_H2_HI      = (160, 255, 180)
COL_OUT_BASE    = (220, 160, 60)   # amber — action
COL_OUT_HI     = (255, 220, 100)

# Species accents
ACCENT_COMMON   = (255, 185, 55)
ACCENT_CLEANER  = (0, 230, 200)
ACCENT_PREDATOR = (255, 80, 90)

# UI text - improved contrast
TEXT_DIM        = (100, 140, 170)
TEXT_MID        = (160, 200, 230)
TEXT_HI         = (220, 240, 255)
TEXT_BRIGHT     = (255, 255, 255)

# Connection colours
CONN_DIM        = (20, 40, 60)
CONN_POS        = (60, 200, 180)
CONN_NEG        = (200, 100, 50)

# Behaviour drives
DRIVE_HIDE      = (80, 140, 255)
DRIVE_SPRINT    = (255, 190, 60)
DRIVE_CLEAN     = (80, 255, 140)
DRIVE_AMBUSH    = (255, 100, 160)
DRIVE_DASH      = (255, 60, 60)

STATE_COLS = [
    (100, 140, 255),   # RESTING
    (255, 180, 60),    # HUNTING
    (255, 70,  70),    # FLEEING
    (255, 100, 200),   # MATING
    (180, 100, 255),   # NESTING
]

STATE_NAMES = ["REST", "HUNT", "FLEE", "MATE", "NEST"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def lerp_color_alpha(c1, c2, t, a1=255, a2=255):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
        int(a1 + (a2 - a1) * t),
    )

def glow_circle(surf, color, pos, radius, alpha=180, layers=3):
    """Draw a soft multi-layer glow circle."""
    x, y = int(pos[0]), int(pos[1])
    for i in range(layers, 0, -1):
        r = radius + (layers - i) * 5
        a = alpha // (layers - i + 1)
        gsurf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*color, a), (r + 1, r + 1), r)
        surf.blit(gsurf, (x - r - 1, y - r - 1))
    pygame.draw.circle(surf, (*color, min(255, int(alpha * 1.4))), (x, y), radius)

def draw_rounded_rect(surf, color, rect, radius=8, alpha=255):
    """Draw a rounded rectangle with optional alpha."""
    s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
    surf.blit(s, (rect[0], rect[1]))


# ── Synaptic Signal Particle ──────────────────────────────────────────────────

class SynapticParticle:
    """A glowing pulse that travels from one node to another along a connection."""
    __slots__ = ('x1','y1','x2','y2','t','speed','color','strength','alive')

    def __init__(self, x1, y1, x2, y2, color, strength=1.0):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.t = 0.0
        self.speed = random.uniform(0.6, 1.4)
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
        # Calculate current position with curve
        x1, y1 = self.x1, self.y1
        x2, y2 = self.x2, self.y2

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        wave = math.sin(global_t * 2 + (x1 + y1) * 0.01) * 10
        cx, cy = mid_x, mid_y + wave

        # Quadratic Bezier
        t = self.t
        px = (1-t)**2 * x1 + 2*(1-t)*t * cx + t**2 * x2
        py = (1-t)**2 * y1 + 2*(1-t)*t * cy + t**2 * y2
        fade = math.sin(self.t * math.pi)
        r = int(2 + self.strength * 3)
        alpha = int(200 * fade)
        gsurf = pygame.Surface((r * 4 + 2, r * 4 + 2), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*self.color, alpha // 3), (r * 2 + 1, r * 2 + 1), r * 2)
        pygame.draw.circle(gsurf, (*self.color, alpha), (r * 2 + 1, r * 2 + 1), r)
        surf.blit(gsurf, (int(px) - r * 2 - 1, int(py) - r * 2 - 1))


# ── Node ─────────────────────────────────────────────────────────────────────

class NeuronNode:
    """A single visualized neuron with animated activation state."""
    __slots__ = ('x','y','drift_x','drift_y','activation','smooth_act','phase','base_color','hi_color',
                 'radius','pulse_t','fire_t','label')

    def __init__(self, x, y, base_color, hi_color, radius=7, label=''):
        self.x, self.y = x, y
        self.drift_x, self.drift_y = x, y
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

        # Organic drift
        drift_speed = 0.5 + abs(self.smooth_act) * 1.5
        self.drift_x = self.x + math.sin(global_t * drift_speed + self.phase) * 4
        self.drift_y = self.y + math.cos(global_t * drift_speed * 0.7 + self.phase) * 4

    def draw(self, surf, global_t):
        act = self.smooth_act
        abs_act = abs(act)
        curr_x, curr_y = int(self.drift_x), int(self.drift_y)

        # Base idle breath
        breath = 0.15 * math.sin(self.pulse_t + self.phase)
        display_r = self.radius * (0.85 + 0.15 * abs_act + breath * (0.3 + 0.7 * abs_act))

        # Color interpolation
        if act >= 0:
            col = lerp_color(self.base_color, self.hi_color, abs_act)
        else:
            # Negative: shift toward red/orange
            neg_col = (200, 80, 40)
            col = lerp_color(self.base_color, neg_col, abs_act)

        # Fire flash
        if self.fire_t > 0:
            col = lerp_color(col, (255, 255, 255), self.fire_t * 0.7)
            display_r += self.fire_t * 5

        # Glow layers (scale with activation)
        if abs_act > 0.1:
            glow_alpha = int(40 + 80 * abs_act)
            glow_r = int(display_r * 2.5)
            outer = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(outer, (*col, glow_alpha // 2), (glow_r + 1, glow_r + 1), glow_r)
            surf.blit(outer, (curr_x - glow_r - 1, curr_y - glow_r - 1))

        # Inactive ring
        pygame.draw.circle(surf, (20, 40, 60), (curr_x, curr_y), int(self.radius), 1)
        # Core
        pygame.draw.circle(surf, col, (curr_x, curr_y), max(1, int(display_r)))

        # Highlight spec
        if abs_act > 0.3:
            spec_x = int(curr_x - display_r * 0.3)
            spec_y = int(curr_y - display_r * 0.3)
            pygame.draw.circle(surf, (255, 255, 255), (spec_x, spec_y), max(1, int(display_r * 0.25)))


# ── Main Visualizer ──────────────────────────────────────────────────────────

class EnhancedBrainVisualizer:
    """Organic, animated neural network visualizer — the centrepiece feature."""

    PANEL_W = BRAIN_PANEL_WIDTH   # 420
    PANEL_H = BRAIN_PANEL_HEIGHT  # 800

    # How many inputs/nodes to actually display (sample from full set)
    DISPLAY_INPUTS  = 18   # 9 radar + 9 sampled stats
    DISPLAY_H1      = NN_HIDDEN1_SIZE   # 14
    DISPLAY_H2      = NN_HIDDEN2_SIZE   # 8
    DISPLAY_OUTPUTS = 7    # steer, thrust, hide, sprint, clean, ambush, dash

    def __init__(self, screen_width, screen_height):
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.panel_h = min(self.PANEL_H, screen_height)
        self.slide_x = float(self.PANEL_W)

        self.anim_t = 0.0
        self.prev_state = None
        self.state_flash = 0.0

        # Fonts — monospace for the techy feel
        self.f_title   = pygame.font.SysFont("Courier New", 22, bold=True)
        self.f_body    = pygame.font.SysFont("Courier New", 16)
        self.f_small   = pygame.font.SysFont("Courier New", 13)
        self.f_tiny    = pygame.font.SysFont("Courier New", 11)

        # Pre-built nodes
        self._nodes_input  = []
        self._nodes_h1     = []
        self._nodes_h2     = []
        self._nodes_output = []
        self._nodes_built  = False

        # Particles
        self._particles: list[SynapticParticle] = []
        self._particle_timer = 0.0

        # Smooth drive values
        self._drive_smooth = {
            'hide': 0.0, 'sprint': 0.0, 'clean': 0.0,
            'ambush': 0.0, 'dash': 0.0
        }

        # State probability smoothing
        self._state_probs_smooth = [0.2] * 5

        # Energy/stamina smoothing
        self._energy_smooth = 0.8
        self._stamina_smooth = 1.0

        # Background surface (rendered once, updated slowly)
        self._bg_surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)
        self._bg_t = 0.0

        # Cached surfaces for performance
        self._panel_surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)
        self._conn_surf  = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)

        # Connection weight cache (sampled)
        self._conn_w1 = []   # [h1][input] — sampled weights
        self._conn_w2 = []   # [h2][h1]
        self._conn_w3 = []   # [output][h2]

        # Section Y positions (set during layout)
        self.net_top = 200   # where neural net drawing starts

        # Recurrent state arc
        self._recurrent_angle = 0.0

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_nodes(self, fish_accent):
        """Create NeuronNode objects with layout positions."""
        W = self.PANEL_W
        PAD_X = 20

        # Neural net occupies rows from net_top to net_top + net_height
        net_height = 300
        net_top = self.net_top
        net_bot = net_top + net_height

        # 4 columns
        n_cols = 4
        col_xs = [
            PAD_X + 20,
            PAD_X + 100,
            PAD_X + 200,
            PAD_X + 300,
        ]

        def even_ys(count, top, bot):
            if count == 1:
                return [(top + bot) / 2]
            return [top + i * (bot - top) / (count - 1) for i in range(count)]

        # Input nodes (column 0) — DISPLAY_INPUTS
        ys = even_ys(self.DISPLAY_INPUTS, net_top, net_bot)
        self._nodes_input = [
            NeuronNode(col_xs[0], y, COL_INPUT_BASE, COL_INPUT_HI, radius=5)
            for y in ys
        ]
        # Label first 9 as radar, rest as stats
        for i, n in enumerate(self._nodes_input):
            n.label = f"R{i}" if i < 9 else f"S{i-9}"

        # Hidden1 nodes (column 1)
        ys = even_ys(self.DISPLAY_H1, net_top, net_bot)
        self._nodes_h1 = [
            NeuronNode(col_xs[1], y, COL_H1_BASE, COL_H1_HI, radius=7)
            for y in ys
        ]

        # Hidden2 nodes (column 2)
        ys = even_ys(self.DISPLAY_H2, net_top + 20, net_bot - 20)
        self._nodes_h2 = [
            NeuronNode(col_xs[2], y, COL_H2_BASE, COL_H2_HI, radius=8)
            for y in ys
        ]

        # Output nodes (column 3)
        out_labels = ["STEER", "THRUS", "HIDE", "SPRINT", "CLEAN", "AMBSH", "DASH"]
        ys = even_ys(self.DISPLAY_OUTPUTS, net_top + 30, net_bot - 30)
        self._nodes_output = [
            NeuronNode(col_xs[3], y, COL_OUT_BASE, COL_OUT_HI, radius=7, label=lbl)
            for y, lbl in zip(ys, out_labels)
        ]

        self._nodes_built = True

    def _sample_weights(self, fish):
        """Cache sampled connection weights from the brain for visual rendering."""
        brain = fish.brain
        # w1: h1 x input  → sample DISPLAY_INPUTS inputs per h1 node
        step_in = max(1, NN_INPUT_COUNT // self.DISPLAY_INPUTS)
        self._conn_w1 = []
        for i in range(self.DISPLAY_H1):
            row = []
            for j in range(self.DISPLAY_INPUTS):
                src = min(j * step_in, NN_INPUT_COUNT - 1)
                row.append(brain.w1[i][src])
            self._conn_w1.append(row)

        # w2: h2 x h1
        self._conn_w2 = [[brain.w2[i][j] for j in range(self.DISPLAY_H1)]
                          for i in range(self.DISPLAY_H2)]

        # w3: output x h2
        self._conn_w3 = [[brain.w3[i][j] for j in range(self.DISPLAY_H2)]
                          for i in range(self.DISPLAY_OUTPUTS)]

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt, selected_fish):
        self.anim_t += dt

        if selected_fish is not None:
            self.slide_x = max(0.0, self.slide_x - 1800 * dt)

            # Build nodes on first frame or species change
            if not self._nodes_built:
                acc = self._get_accent(selected_fish)
                self._build_nodes(acc)
                self._sample_weights(selected_fish)

            # State change flash
            if selected_fish.state != self.prev_state:
                self.state_flash = 1.0
            self.prev_state = selected_fish.state
            if self.state_flash > 0:
                self.state_flash = max(0.0, self.state_flash - dt * 4)

            # Push activations into nodes
            inputs = selected_fish.last_inputs
            step = max(1, len(inputs) // self.DISPLAY_INPUTS)
            for i, node in enumerate(self._nodes_input):
                val = inputs[min(i * step, len(inputs) - 1)] * 2 - 1   # [0,1] → [-1,1]
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

            # Update all nodes
            for node in (self._nodes_input + self._nodes_h1 +
                          self._nodes_h2 + self._nodes_output):
                node.update(dt, self.anim_t)

            # Smooth drives
            if len(outputs) >= 7:
                targets = {
                    'hide': outputs[2], 'sprint': outputs[3],
                    'clean': outputs[4], 'ambush': outputs[5], 'dash': outputs[6]
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
            self._energy_smooth = lerp(self._energy_smooth,
                                        selected_fish.energy / FISH_MAX_ENERGY, dt * 5)
            self._stamina_smooth = lerp(self._stamina_smooth,
                                         selected_fish.stamina / 100.0, dt * 5)

            # Synaptic particle emission
            self._particle_timer -= dt
            if self._particle_timer <= 0:
                # Emit more particles if fish is active
                freq = 0.05 if abs(selected_fish.last_outputs[1]) > 0.5 else 0.15
                self._emit_particle(selected_fish)
                self._particle_timer = random.uniform(freq, freq * 2)

            # Update existing particles
            for p in self._particles[:]:
                p.update(dt)
                if not p.alive:
                    self._particles.remove(p)

            # Recurrent arc animation
            self._recurrent_angle = (self._recurrent_angle + dt * 180) % 360

        else:
            self.slide_x = min(float(self.PANEL_W), self.slide_x + 1800 * dt)
            if self.slide_x >= self.PANEL_W:
                self._nodes_built = False
                self._particles.clear()

    def _emit_particle(self, fish):
        """Emit a synaptic signal particle on an active connection."""
        outputs = fish.last_outputs
        h1 = fish.last_hidden1
        h2 = fish.last_hidden

        # Choose which layer to fire based on activation strengths
        roll = random.random()

        if roll < 0.35 and self._nodes_input and self._nodes_h1:
            # Input → H1
            src = random.choice(self._nodes_input)
            dst = random.choice(self._nodes_h1)
            strength = abs(src.smooth_act) * 0.5 + abs(dst.smooth_act) * 0.5
            if strength > 0.1:
                col = lerp_color(COL_INPUT_HI, COL_H1_HI, 0.5)
                self._particles.append(SynapticParticle(
                    src.drift_x, src.drift_y, dst.drift_x, dst.drift_y, col, strength))

        elif roll < 0.65 and self._nodes_h1 and self._nodes_h2:
            # H1 → H2
            src = random.choice(self._nodes_h1)
            dst = random.choice(self._nodes_h2)
            strength = abs(src.smooth_act) * 0.5 + abs(dst.smooth_act) * 0.5
            if strength > 0.1:
                col = lerp_color(COL_H1_HI, COL_H2_HI, 0.5)
                self._particles.append(SynapticParticle(
                    src.drift_x, src.drift_y, dst.drift_x, dst.drift_y, col, strength))

        elif self._nodes_h2 and self._nodes_output:
            # H2 → Output
            src = random.choice(self._nodes_h2)
            dst_idx = random.randint(0, len(self._nodes_output) - 1)
            dst = self._nodes_output[dst_idx]
            out_val = outputs[dst_idx] if dst_idx < len(outputs) else 0.0
            strength = abs(src.smooth_act) * 0.3 + out_val * 0.7
            if strength > 0.15:
                accent = self._get_accent_from_fish_flags(
                    getattr(fish, 'is_cleaner', False),
                    getattr(fish, 'is_predator', False))
                self._particles.append(SynapticParticle(
                    src.x, src.y, dst.x, dst.y, accent, strength))

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _get_accent(self, fish):
        if fish.is_predator: return ACCENT_PREDATOR
        if fish.is_cleaner:  return ACCENT_CLEANER
        return ACCENT_COMMON

    def _get_accent_from_fish_flags(self, is_cleaner, is_predator):
        if is_predator: return ACCENT_PREDATOR
        if is_cleaner:  return ACCENT_CLEANER
        return ACCENT_COMMON

    def draw(self, screen, selected_fish, time):
        if self.slide_x >= self.PANEL_W:
            return

        W, H = self.PANEL_W, self.panel_h
        surf = self._panel_surf
        surf.fill((0, 0, 0, 0))

        accent = self._get_accent(selected_fish)

        # ── Animated background ───────────────────────────────────────────
        self._draw_background(surf, accent)

        # ── Left accent edge glow ─────────────────────────────────────────
        for i in range(6):
            a = int(60 * (1 - i / 6) * (0.7 + 0.3 * math.sin(self.anim_t * 1.8 + i)))
            lsurf = pygame.Surface((1, H), pygame.SRCALPHA)
            lsurf.fill((*accent, a))
            surf.blit(lsurf, (i, 0))

        # ── Header ───────────────────────────────────────────────────────
        y = self._draw_header(surf, selected_fish, accent)

        # ── Vital bars ───────────────────────────────────────────────────
        y = self._draw_vitals(surf, selected_fish, accent, y)

        # ── Neural network ───────────────────────────────────────────────
        self.net_top = y + 12
        y = self._draw_neural_network(surf, selected_fish, accent, y + 12)

        # ── Behaviour drives ─────────────────────────────────────────────
        y = self._draw_drives(surf, selected_fish, accent, y + 10)

        # ── State distribution arc ────────────────────────────────────────
        y = self._draw_state_arcs(surf, selected_fish, accent, y + 8)

        # ── Behavioral Insights ──────────────────────────────────────────
        y = self._draw_insights(surf, selected_fish, accent, y + 10)

        # ── Stats footer ─────────────────────────────────────────────────
        self._draw_footer(surf, selected_fish, accent, y + 8)

        # Blit to screen with slide offset
        dest_x = self.screen_w - W + int(self.slide_x)
        screen.blit(surf, (dest_x, 0))

    def _draw_background(self, surf, accent):
        """Clean dark background with subtle gradient."""
        W, H = self.PANEL_W, self.panel_h
        surf.fill((*BG_DEEP, 250))

        # Simple top gradient for depth
        for y in range(0, min(60, H)):
            a = int(20 * (1 - y / 60))
            pygame.draw.line(surf, (*accent, a), (0, y), (W, y))

    def _draw_header(self, surf, fish, accent):
        """Species badge, state, sex, age."""
        PAD = 16
        y = 14

        # Species pill
        species = ("PREDATOR" if fish.is_predator
                   else "CLEANER" if fish.is_cleaner else "COMMON")
        pill_w, pill_h = 90, 20
        draw_rounded_rect(surf, accent, (PAD, y, pill_w, pill_h), radius=10, alpha=200)
        t = self.f_tiny.render(species, True, BG_DEEP)
        surf.blit(t, (PAD + (pill_w - t.get_width()) // 2, y + 4))

        # Sex badge
        sex_col = (120, 160, 255) if fish.sex == "M" else (255, 120, 180)
        sex_sym = "♂" if fish.sex == "M" else "♀"
        sx = self.f_body.render(sex_sym, True, sex_col)
        surf.blit(sx, (PAD + pill_w + 10, y))
        y += pill_h + 8

        # State — big pulsing text
        flash_t = self.state_flash
        state_col = lerp_color(TEXT_MID, accent, flash_t)
        brightness = 0.8 + 0.2 * math.sin(self.anim_t * 4)
        state_col = tuple(int(c * brightness) for c in state_col)
        st = self.f_title.render(f"◈ {fish.state.name}", True, state_col)
        surf.blit(st, (PAD, y))
        y += 28

        # Age + food eaten
        age_t = self.f_small.render(
            f"AGE {fish.age:.0f}s  |  FED {fish.food_eaten}x", True, TEXT_DIM)
        surf.blit(age_t, (PAD, y))
        y += 20

        return y + 6

    def _draw_vitals(self, surf, fish, accent, y):
        """Energy and stamina with animated liquid fill."""
        PAD = 16
        BAR_W = self.PANEL_W - PAD * 2 - 55
        BAR_H = 12

        bars = [
            ("ENERGY", self._energy_smooth, accent, (255, 80, 80)),
            ("STAMINA", self._stamina_smooth, (80, 220, 140), (180, 180, 60)),
        ]

        for label, ratio, col_full, col_low in bars:
            # Label
            lt = self.f_tiny.render(label, True, TEXT_DIM)
            surf.blit(lt, (PAD, y + 1))
            bx = PAD + 55

            # Background trough
            draw_rounded_rect(surf, (12, 22, 36), (bx, y, BAR_W, BAR_H), radius=6)

            # Fill with shimmer
            fill_w = max(2, int(BAR_W * ratio))
            fill_col = lerp_color(col_low, col_full, ratio)
            draw_rounded_rect(surf, fill_col, (bx, y, fill_w, BAR_H), radius=6)

            # Shimmer pass
            shimmer_x = bx + int((self.anim_t * 120) % (BAR_W + 40)) - 20
            if bx < shimmer_x < bx + fill_w:
                sw = min(20, fill_w - (shimmer_x - bx))
                if sw > 0:
                    ssurf = pygame.Surface((sw, BAR_H), pygame.SRCALPHA)
                    ssurf.fill((255, 255, 255, 60))
                    surf.blit(ssurf, (shimmer_x, y))

            # Percentage text
            pct = self.f_tiny.render(f"{int(ratio * 100)}%", True, TEXT_MID)
            surf.blit(pct, (bx + BAR_W + 4, y + 1))
            y += 22

        return y + 4

    def _draw_neural_network(self, surf, fish, accent, y_start):
        """Draw the full layered neural network with connections and nodes."""
        # Draw connections first (behind nodes)
        self._draw_connections(surf)

        # Draw particles
        for p in self._particles:
            p.draw(surf, self.anim_t)

        # Draw nodes
        for node in (self._nodes_input + self._nodes_h1 +
                      self._nodes_h2 + self._nodes_output):
            node.draw(surf, self.anim_t)

        # Layer labels
        labels = [
            (self._nodes_input[0].x if self._nodes_input else 30,  "INPUT"),
            (self._nodes_h1[0].x if self._nodes_h1 else 110,       "HIDDEN 1"),
            (self._nodes_h2[0].x if self._nodes_h2 else 210,       "HIDDEN 2"),
            (self._nodes_output[0].x if self._nodes_output else 310,"OUTPUT"),
        ]
        for lx, lbl in labels:
            lt = self.f_tiny.render(lbl, True, TEXT_DIM)
            surf.blit(lt, (int(lx) - lt.get_width() // 2,
                           y_start - 14))

        # Recurrent loop indicator on h2
        if self._nodes_h2 and fish.brain.recurrent:
            self._draw_recurrent_arc(surf)

        # Input node labels on the left
        for node in self._nodes_input:
            lt = self.f_tiny.render(node.label, True,
                                     lerp_color(TEXT_DIM, COL_INPUT_HI,
                                                abs(node.smooth_act)))
            surf.blit(lt, (int(node.x) - lt.get_width() - 12, int(node.y) - 5))

        # Output node labels on the right
        for node in self._nodes_output:
            lt = self.f_tiny.render(node.label, True,
                                     lerp_color(TEXT_DIM, COL_OUT_HI,
                                                abs(node.smooth_act)))
            surf.blit(lt, (int(node.x) + 12, int(node.y) - 5))

        # Find the bottom of the lowest node
        all_nodes = (self._nodes_input + self._nodes_h1 +
                     self._nodes_h2 + self._nodes_output)
        if all_nodes:
            return int(max(n.y for n in all_nodes)) + 20
        return y_start + 310

    def _draw_connections(self, surf):
        """Draw weighted connections between layers, coloured by sign and magnitude."""
        def draw_layer_connections(src_nodes, dst_nodes, weights, max_conns=60):
            # Sort by absolute weight to draw strongest on top
            pairs = []
            for di, dst in enumerate(dst_nodes):
                for si, src in enumerate(src_nodes):
                    if si < len(weights[di]) if di < len(weights) else False:
                        w = weights[di][si]
                        pairs.append((abs(w), w, src, dst))
            pairs.sort(key=lambda x: x[0])
            # Draw weakest first, limit total
            for i, (absw, w, src, dst) in enumerate(pairs[-max_conns:]):
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

                alpha = int(20 + 160 * intensity * max(0.15, activity))
                width = max(1, int(1 + intensity * 2))
                # Draw organic curved connections
                x1, y1 = int(src.drift_x), int(src.drift_y)
                x2, y2 = int(dst.drift_x), int(dst.drift_y)

                # Control point for quadratic bezier
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                # Offset mid point based on global_t for subtle waving
                wave = math.sin(self.anim_t * 2 + (x1 + y1) * 0.01) * 10
                cx = mid_x
                cy = mid_y + wave

                # Draw as 3 segments for a "curved" look without heavy math
                p1 = (x1, y1)
                p2 = (int((x1 + cx) / 2), int((y1 + cy) / 2))
                p3 = (int(cx), int(cy))
                p4 = (int((cx + x2) / 2), int((cy + y2) / 2))
                p5 = (x2, y2)

                pygame.draw.lines(surf, (*col, alpha), False, [p1, p2, p3, p4, p5], width)

        if self._conn_w1:
            draw_layer_connections(self._nodes_input, self._nodes_h1, self._conn_w1, 25)
        if self._conn_w2:
            draw_layer_connections(self._nodes_h1, self._nodes_h2, self._conn_w2, 20)
        if self._conn_w3:
            draw_layer_connections(self._nodes_h2, self._nodes_output, self._conn_w3, 15)

    def _draw_recurrent_arc(self, surf):
        """Draw a looping arc on the h2 column to indicate recurrent memory."""
        if not self._nodes_h2:
            return
        top_node = self._nodes_h2[0]
        bot_node = self._nodes_h2[-1]
        cx = int(top_node.x) + 35
        cy = int((top_node.y + bot_node.y) / 2)
        rx, ry = 20, int((bot_node.y - top_node.y) / 2)

        # Animated arc
        angle_rad = math.radians(self._recurrent_angle)
        a = int(40 + 60 * math.sin(angle_rad))
        arc_rect = pygame.Rect(cx - rx, cy - ry, rx * 2, ry * 2)
        try:
            pygame.draw.arc(surf, (*COL_H2_HI, a), arc_rect,
                            angle_rad, angle_rad + math.pi, 2)
        except Exception:
            pass  # pygame.draw.arc can fail with bad rects

        # Pulse dot on arc
        px = cx + math.cos(angle_rad) * rx
        py = cy + math.sin(angle_rad) * ry
        gsurf = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(gsurf, (*COL_H2_HI, 180), (7, 7), 5)
        surf.blit(gsurf, (int(px) - 7, int(py) - 7))

        # Label
        lt = self.f_tiny.render("REC", True, TEXT_DIM)
        surf.blit(lt, (cx - lt.get_width() // 2 + 4, cy - 8))

    def _draw_drives(self, surf, fish, accent, y):
        """Behaviour drive indicators with liquid fill and glow."""
        PAD = 16
        t = self.f_small.render("BEHAVIOUR DRIVES", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 18

        is_pred = fish.is_predator
        is_cln  = fish.is_cleaner

        if is_pred:
            drives = [
                ("AMBUSH", self._drive_smooth['ambush'], DRIVE_AMBUSH),
                ("DASH",   self._drive_smooth['dash'],   DRIVE_DASH),
            ]
        elif is_cln:
            drives = [
                ("CLEAN",  self._drive_smooth['clean'],  DRIVE_CLEAN),
                ("SPRINT", self._drive_smooth['sprint'], DRIVE_SPRINT),
            ]
        else:
            drives = [
                ("HIDE",   self._drive_smooth['hide'],   DRIVE_HIDE),
                ("SPRINT", self._drive_smooth['sprint'], DRIVE_SPRINT),
            ]

        BAR_W = self.PANEL_W - PAD * 2 - 58
        for label, val, col in drives:
            lt = self.f_tiny.render(label, True,
                                     lerp_color(TEXT_DIM, col, val))
            surf.blit(lt, (PAD, y + 2))
            bx = PAD + 58

            # Trough
            draw_rounded_rect(surf, (12, 22, 36), (bx, y, BAR_W, 10), radius=5)

            # Fill
            fw = max(1, int(BAR_W * val))
            draw_rounded_rect(surf, col, (bx, y, fw, 10), radius=5)

            # Pulsing edge glow
            if val > 0.4:
                gw = 8
                gsurf = pygame.Surface((gw * 2, 12), pygame.SRCALPHA)
                pulse_a = int(100 * val * (0.6 + 0.4 * math.sin(self.anim_t * 8)))
                pygame.draw.rect(gsurf, (*col, pulse_a), (0, 0, gw * 2, 12),
                                 border_radius=5)
                surf.blit(gsurf, (bx + fw - gw, y - 1))

            y += 18

        return y + 4

    def _draw_state_arcs(self, surf, fish, accent, y):
        """State probability shown as filled arc segments (pie-ish chart)."""
        PAD = 16
        t = self.f_small.render("STATE PROBABILITIES", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 16

        # Arc chart
        cx = self.PANEL_W // 2
        cy = y + 52
        outer_r = 48
        inner_r = 28

        # Flash the current state arc
        cur_idx = FISH_STATE_ORDER.index(fish.state)

        # Draw arcs
        start_angle = -math.pi / 2
        probs = self._state_probs_smooth
        total = sum(probs) or 1.0

        for i, prob in enumerate(probs):
            sweep = (prob / total) * math.pi * 2
            col = STATE_COLS[i]

            is_active = (i == cur_idx)
            flash_boost = self.state_flash if is_active else 0.0
            r_outer = outer_r + (8 if is_active else 0)
            alpha = int(180 + 75 * flash_boost + 30 * prob * 5)

            # Draw filled arc segment
            num_steps = max(4, int(sweep * 12))
            for step in range(num_steps):
                a0 = start_angle + step / num_steps * sweep
                a1 = start_angle + (step + 1) / num_steps * sweep
                pts = [
                    (cx + math.cos(a0) * inner_r, cy + math.sin(a0) * inner_r),
                    (cx + math.cos(a1) * inner_r, cy + math.sin(a1) * inner_r),
                    (cx + math.cos(a1) * r_outer,  cy + math.sin(a1) * r_outer),
                    (cx + math.cos(a0) * r_outer,  cy + math.sin(a0) * r_outer),
                ]
                try:
                    asurf = pygame.Surface((self.PANEL_W, 140), pygame.SRCALPHA)
                    pygame.draw.polygon(asurf, (*col, alpha), pts)
                    surf.blit(asurf, (0, y))
                except Exception:
                    pass

            # Outer glow for active state
            if is_active and prob > 0.1:
                mid_a = start_angle + sweep / 2
                gx = cx + math.cos(mid_a) * (r_outer + 8)
                gy = (cy + math.sin(mid_a) * (r_outer + 8)) + y
                gsurf = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(gsurf, (*col, 120), (12, 12), 12)
                surf.blit(gsurf, (int(gx) - 12, int(gy) - 12))

            start_angle += sweep

        # Centre label
        name_surf = self.f_small.render(fish.state.name[:4], True, accent)
        surf.blit(name_surf, (cx - name_surf.get_width() // 2, y + cy - 10))
        prob_surf = self.f_tiny.render(
            f"{int(self._state_probs_smooth[cur_idx] * 100)}%", True, TEXT_MID)
        surf.blit(prob_surf, (cx - prob_surf.get_width() // 2, y + cy + 6))

        # Legend
        legend_y = y + cy + outer_r + 8
        lx = PAD
        for i, (name, col) in enumerate(zip(STATE_NAMES, STATE_COLS)):
            is_active = (i == cur_idx)
            lc = lerp_color(TEXT_DIM, col, 0.4 + 0.6 * (1 if is_active else 0))
            pygame.draw.circle(surf, col, (int(lx) + 4, int(legend_y) + 6), 4)
            lt = self.f_tiny.render(name, True, lc)
            surf.blit(lt, (int(lx) + 12, int(legend_y)))
            lx += lt.get_width() + 22

        return legend_y + 18

    def _draw_insights(self, surf, fish, accent, y):
        """Explain the current state based on dominant inputs."""
        PAD = 16
        t = self.f_small.render("NEURAL INSIGHTS", True, TEXT_DIM)
        surf.blit(t, (PAD, y))
        y += 18

        # Determine why fish is in current state
        insight = "Maintaining baseline metabolism."
        if fish.state == FishState.HUNTING:
            if fish.energy < 25:
                insight = "Critical hunger driving foraging."
            else:
                insight = "Seeking prey/food sources."
        elif fish.state == FishState.FLEEING:
            insight = "Threat detected! Evasive action."
        elif fish.state == FishState.MATING:
            insight = "Energy surplus: seeking mate."
        elif fish.state == FishState.NESTING:
            insight = "Protecting offspring/eggs."
        elif fish.state == FishState.RESTING:
            insight = "Conserving energy."

        words = insight.split()
        line = ""
        for word in words:
            if self.f_tiny.size(line + word)[0] < self.PANEL_W - PAD*2:
                line += word + " "
            else:
                it = self.f_tiny.render(line, True, TEXT_MID)
                surf.blit(it, (PAD, y))
                y += 12
                line = word + " "
        it = self.f_tiny.render(line, True, TEXT_MID)
        surf.blit(it, (PAD, y))

        return y + 15

    def _draw_footer(self, surf, fish, accent, y):
        """Small stats row at the bottom."""
        PAD = 16
        if y + 30 > self.panel_h:
            return
        info = (f"dst:{fish.distance_traveled:.0f}  "
                f"offs:{fish.offspring_count}  "
                f"{'♦PREGNANT' if fish.is_pregnant else ''}")
        ft = self.f_tiny.render(info, True, TEXT_DIM)
        surf.blit(ft, (PAD, min(y, self.panel_h - 20)))

        # Bottom accent line
        pygame.draw.line(surf, (*accent, 60),
                         (0, self.panel_h - 1),
                         (self.PANEL_W, self.panel_h - 1), 1)
