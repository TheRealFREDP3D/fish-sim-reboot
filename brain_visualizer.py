"""
Brain Visualizer — Bioluminescent deep-sea neuron aesthetic.
Organic curves, flowing signal particles, living pulse rhythms.
"""

import pygame
import math
import random
from config import (
    BRAIN_PANEL_WIDTH,
    BRAIN_PANEL_HEIGHT,
    FishState,
    FISH_MAX_AGE,
    FISH_MAX_ENERGY,
    FISH_LARVA_DURATION,
    FISH_JUVENILE_DURATION,
    FISH_ELDER_DURATION,
    FISH_ADULT_DURATION,
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

# Neural activation colours — deep-sea bioluminescence
COL_POS_HI = (80, 255, 220)   # teal-white: high positive
COL_POS_MID = (0, 180, 160)   # mid teal
COL_NEU = (30, 55, 80)        # dark slate: near-zero
COL_NEG_MID = (200, 120, 40)  # amber: mid negative
COL_NEG_HI = (255, 180, 60)   # bright amber: high negative

# Dim wire colour used in draw_connections — extracted as a constant
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
    """Smooth tri-colour ramp: amber (neg) → slate (zero) → teal (pos)."""
    if v >= 0:
        t = min(1.0, v)
        mid = lerp_color(COL_NEU, COL_POS_MID, t)
        return lerp_color(mid, COL_POS_HI, t * t)
    else:
        t = min(1.0, -v)
        mid = lerp_color(COL_NEU, COL_NEG_MID, t)
        return lerp_color(mid, COL_NEG_HI, t * t)


def _cubic_bezier(p0, p1, p2, p3, t):
    """Evaluate a cubic Bezier at parameter t."""
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _bezier_points(p0, p3, steps=18):
    """Return a polyline approximating the S-curve between two nodes."""
    dx = (p3[0] - p0[0]) * 0.45
    p1 = (p0[0] + dx, p0[1])
    p2 = (p3[0] - dx, p3[1])
    return [_cubic_bezier(p0, p1, p2, p3, i / steps) for i in range(steps + 1)]


def draw_capsule(surface, color, x, y, w, h, radius=None):
    if radius is None:
        radius = h // 2
    pygame.draw.rect(surface, color, pygame.Rect(x, y, w, h), border_radius=radius)


def draw_capsule_outline(surface, color, x, y, w, h, radius=None, width=1):
    if radius is None:
        radius = h // 2
    pygame.draw.rect(
        surface, color, pygame.Rect(x, y, w, h), border_radius=radius, width=width
    )


# ── Signal particle ───────────────────────────────────────────────────────────


class _Particle:
    """A glowing dot that travels along one connection."""

    __slots__ = ("t", "speed", "src", "dst", "col", "size")

    def __init__(self, src, dst, col):
        self.t = random.uniform(0.0, 1.0)
        self.speed = random.uniform(0.35, 0.75)
        self.src = src
        self.dst = dst
        self.col = col
        self.size = random.uniform(2.0, 3.5)

    def update(self, dt):
        self.t = (self.t + self.speed * dt) % 1.0

    def pos(self):
        dx = (self.dst[0] - self.src[0]) * 0.45
        p1 = (self.src[0] + dx, self.src[1])
        p2 = (self.dst[0] - dx, self.dst[1])
        return _cubic_bezier(self.src, p1, p2, self.dst, self.t)


# ── Main class ────────────────────────────────────────────────────────────────


class BrainVisualizer:
    PANEL_W = BRAIN_PANEL_WIDTH
    PANEL_H = BRAIN_PANEL_HEIGHT

    # Shared glow surface
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

        # Signal particles — populated once node positions are known
        self._particles: list[_Particle] = []
        self._node_positions_built = False
        # Store last node layout so particles can reference it
        self._pos_in = []
        self._pos_h1 = []
        self._pos_h2 = []
        self._pos_out = []

        # Ripple rings per node: list of (age, max_age, pos, col)
        self._ripples: list[tuple] = []

        # Node "heartbeat" timers (staggered phase per node)
        self._node_phases: dict = {}

    # ── Public API ────────────────────────────────────────────

    def update(self, dt, selected_fish):
        self.anim_t += dt

        if selected_fish is not None:
            self.slide_x = max(0.0, self.slide_x - 14 * dt * 60)
            target_i = self._INTENSITY.get(selected_fish.state, 0.5)
            self.anim_intensity += (target_i - self.anim_intensity) * 2.5 * dt
            if selected_fish.state != self.prev_state:
                self.state_flash = 0.6
            self.prev_state = selected_fish.state
        else:
            self.slide_x = min(float(self.PANEL_W), self.slide_x + 14 * dt * 60)
            self._particles.clear()
            self._ripples.clear()
            self._node_positions_built = False

        if self.state_flash > 0:
            self.state_flash = max(0.0, self.state_flash - dt)

        # Update particles
        for p in self._particles:
            p.update(dt)

        # Update ripples
        self._ripples = [
            (a + dt, m, pos, col) for a, m, pos, col in self._ripples if a < m
        ]

        # Occasionally spawn ripples on active input nodes
        if self._pos_in and selected_fish is not None:
            inp = selected_fish.last_inputs
            if len(inp) == 15:
                for i, node_pos in enumerate(self._pos_in):
                    act = inp[i] if i < len(inp) else 0.0
                    if abs(act) > 0.25 and random.random() < abs(act) * dt * 4:
                        self._ripples.append(
                            (0.0, 0.7, node_pos, activation_color(act))
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

        # Left glow stripe
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
        y = self._draw_traits(surf, selected_fish, accent, y)
        y = self._draw_divider(surf, y)
        self._draw_stats(surf, selected_fish, accent, y)

        dest_x = self.screen_w - self.PANEL_W + int(self.slide_x)
        screen.blit(surf, (dest_x, 0))

    # ── Sections ──────────────────────────────────────────────────────────

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

        elder_t = FISH_LARVA_DURATION + FISH_JUVENILE_DURATION + FISH_ADULT_DURATION
        adult_t = FISH_LARVA_DURATION + FISH_JUVENILE_DURATION
        juv_t = FISH_LARVA_DURATION
        stage = (
            "Elder"
            if fish.age >= elder_t
            else (
                "Adult"
                if fish.age >= adult_t
                else "Juvenile" if fish.age >= juv_t else "Larva"
            )
        )
        sex_sym = "♂" if fish.sex == "M" else "♀"
        preg = "  ◉ PREGNANT" if fish.is_pregnant else ""
        t = self.f_body.render(f"{sex_sym} {stage}{preg}", True, TEXT_PRIMARY)
        surf.blit(t, (PAD + pill_w + 10, y + 3))
        y += 32

        STATE_COLORS = {
            FishState.RESTING: (70, 160, 120),
            FishState.HUNTING: AMBER,
            FishState.FLEEING: RED_ACC,
            FishState.MATING: (190, 110, 210),
            FishState.NESTING: (120, 185, 255),
        }
        base_c = STATE_COLORS.get(fish.state, TEXT_SECONDARY)
        state_c = (
            lerp_color(base_c, TEXT_PRIMARY, self.state_flash / 0.6)
            if self.state_flash > 0
            else base_c
        )
        # Pulsing dot before state name
        pulse_r = 3 + int(math.sin(self.anim_t * 4) * 1.5)
        pygame.draw.circle(surf, state_c, (PAD + 5, y + 8), pulse_r)
        t = self.f_body.render(f"  {fish.state.name}", True, state_c)
        surf.blit(t, (PAD + 4, y))
        y += 26
        return y

    def _draw_divider(self, surf, y, margin=16):
        # Faint gradient divider
        for i in range(self.PANEL_W - margin * 2):
            alpha = int(60 * math.sin(math.pi * i / (self.PANEL_W - margin * 2)))
            pygame.draw.line(surf, (*DIVIDER, alpha), (margin + i, y), (margin + i, y))
        pygame.draw.line(surf, DIVIDER, (margin, y), (self.PANEL_W - margin, y))
        return y + 10

    def _draw_status_bars(self, surf, fish, accent, y):
        PAD = 16
        LW = 62
        BAR_W = self.PANEL_W - PAD * 2 - LW - 32
        BAR_H = 10
        RAD = 5

        lifespan = FISH_MAX_AGE * fish.traits.physical_traits.get("lifespan_mult", 1.0)
        bars = [
            ("LIFE", max(0.0, 1.0 - fish.age / lifespan), (80, 160, 255)),
            ("ENERGY", max(0.0, min(1.0, fish.energy / FISH_MAX_ENERGY)), accent),
            ("STAMINA", fish.stamina / 100.0, (80, 220, 140)),
        ]

        for label, ratio, color in bars:
            surf.blit(self.f_tiny.render(label, True, TEXT_LABEL), (PAD, y + 1))
            bx = PAD + LW
            # Track background
            pygame.draw.rect(surf, BG_SECTION, (bx, y, BAR_W, BAR_H), border_radius=RAD)
            # Fill with subtle glow bleed
            fw = max(RAD * 2, int(BAR_W * ratio))
            pygame.draw.rect(
                surf,
                tuple(c // 3 for c in color),
                (bx, y, fw, BAR_H),
                border_radius=RAD,
            )
            pygame.draw.rect(surf, color, (bx, y, fw, BAR_H), border_radius=RAD)
            # Bright leading edge
            if fw > RAD * 2:
                ex = bx + fw - 3
                pygame.draw.rect(
                    surf,
                    tuple(min(255, c + 80) for c in color),
                    (ex, y + 1, 3, BAR_H - 2),
                    border_radius=2,
                )
            pct = self.f_tiny.render(f"{int(ratio * 100)}%", True, TEXT_SECONDARY)
            surf.blit(pct, (bx + BAR_W + 6, y + 1))
            y += 20
        return y + 6

    def _draw_network(self, surf, fish, accent, accent_dim, y):
        PAD = 16
        surf.blit(self.f_small.render("NEURAL NETWORK", True, TEXT_LABEL), (PAD, y))
        y += 20

        NET_H = 260
        net_top = y
        W = self.PANEL_W
        xs = {
            "in": int(W * 0.13),
            "h1": int(W * 0.38),
            "h2": int(W * 0.64),
            "out": int(W * 0.88),
        }

        def col_nodes(x, n):
            return [(x, net_top + int((i + 0.5) * NET_H / n)) for i in range(n)]

        pos_in = col_nodes(xs["in"], 15)
        pos_h1 = col_nodes(xs["h1"], 12)
        pos_h2 = col_nodes(xs["h2"], 6)
        pos_out = col_nodes(xs["out"], 2)

        # Cache for particle system
        if not self._node_positions_built:
            self._pos_in = pos_in
            self._pos_h1 = pos_h1
            self._pos_h2 = pos_h2
            self._pos_out = pos_out
            self._seed_particles(fish)
            self._node_positions_built = True

        inp = list(fish.last_inputs) if len(fish.last_inputs) == 15 else [0.0] * 15
        h1 = list(getattr(fish, "last_hidden1", []))
        if len(h1) != 12:
            h1 = [0.0] * 12
        h2 = list(fish.last_hidden) if len(fish.last_hidden) == 6 else [0.0] * 6
        out = list(fish.last_outputs) if len(fish.last_outputs) == 2 else [0.0] * 2

        # ── Draw bezier connections ────────────────────────────────────────
        THRESH = 0.10

        def draw_connections(src_pos, dst_pos, src_acts):
            for i, sp in enumerate(src_pos):
                act = src_acts[i] if i < len(src_acts) else 0.0
                strength = abs(act)

                for dp in dst_pos:
                    pts = _bezier_points(sp, dp, steps=14)

                    if strength < THRESH:
                        # Dim wire — draw as single thin polyline
                        if len(pts) > 1:
                            pygame.draw.lines(surf, _COL_DIM_WIRE, False, pts, 1)
                    else:
                        col = activation_color(act)
                        thick = 1 + int(strength * 2.5)
                        alpha_col = tuple(
                            max(0, min(255, int(c * (0.4 + 0.6 * strength))))
                            for c in col
                        )
                        if len(pts) > 1:
                            pygame.draw.lines(
                                surf, alpha_col, False, pts, max(1, thick - 1)
                            )
                        # Bright core
                        if strength > 0.4 and len(pts) > 1:
                            bright = tuple(min(255, c + 60) for c in col)
                            pygame.draw.lines(surf, bright, False, pts, 1)

        draw_connections(pos_in, pos_h1, inp)
        draw_connections(pos_h1, pos_h2, h1)
        draw_connections(pos_h2, pos_out, h2)

        # ── Draw signal particles ──────────────────────────────────────────
        gs = BrainVisualizer._glow_surf
        for p in self._particles:
            px, py = p.pos()
            # Only draw if inside network area
            if net_top <= py <= net_top + NET_H + 10:
                r = int(p.size)
                gs.fill((0, 0, 0, 0))
                # Outer halo
                pygame.draw.circle(gs, (*p.col, 50), (self._GLOW, self._GLOW), r + 5)
                # Mid glow
                pygame.draw.circle(gs, (*p.col, 120), (self._GLOW, self._GLOW), r + 2)
                # Bright core
                pygame.draw.circle(
                    gs, (255, 255, 255, 200), (self._GLOW, self._GLOW), max(1, r - 1)
                )
                surf.blit(gs, (int(px) - self._GLOW, int(py) - self._GLOW))

        # ── Draw ripple rings ──────────────────────────────────────────────
        for age, max_age, (rx, ry), rcol in self._ripples:
            progress = age / max_age
            ring_r = int(4 + progress * 18)
            ring_a = max(0, min(255, int(180 * (1 - progress))))
            ring_color = (rcol[0], rcol[1], rcol[2], ring_a)
            pygame.draw.circle(surf, ring_color, (int(rx), int(ry)), ring_r, 1)

        # ── Draw nodes ────────────────────────────────────────────────────
        INPUT_LABELS = [
            "L", "C", "R",
            "L", "C", "R",
            "L", "C", "R",
            "Nrg", "Stm", "Dep", "Spd", "Cover", "Food",
        ]
        INPUT_GROUPS = [
            ("Food", slice(0, 3)),
            ("Threat", slice(3, 6)),
            ("Mate", slice(6, 9)),
            ("Self", slice(9, 15)),
        ]

        def draw_node(pos, act, r=5, label=None):
            col = activation_color(act)
            strength = abs(act)
            phase = self._node_phases.get(pos, random.uniform(0, math.pi * 2))
            self._node_phases[pos] = phase

            # Pulsing outer halo for active nodes
            if strength > 0.15:
                pulse = 0.7 + 0.3 * math.sin(self.anim_t * 3.5 + phase)
                halo_r = int(r + 3 + strength * 8 * pulse)
                halo_r = min(halo_r, self._GLOW - 2)
                halo_a = int(strength * 90 * pulse)
                gs.fill((0, 0, 0, 0))
                gs.set_alpha(halo_a)
                halo_color = (col[0], col[1], col[2])
                pygame.draw.circle(gs, halo_color, (self._GLOW, self._GLOW), halo_r)
                surf.blit(gs, (pos[0] - self._GLOW, pos[1] - self._GLOW))
                gs.set_alpha(255)

            # Node body — filled circle with organic size wobble
            wobble = 0.0
            if strength > 0.3:
                wobble = math.sin(self.anim_t * 5 + phase) * strength * 1.5
            node_r = r + int(strength * 2 + wobble)
            pygame.draw.circle(surf, tuple(c // 2 for c in col), pos, node_r + 2)
            pygame.draw.circle(surf, col, pos, node_r)
            # Inner highlight
            hi = tuple(min(255, c + 100) for c in col)
            pygame.draw.circle(surf, hi, (pos[0] - 1, pos[1] - 1), max(1, node_r // 2))
            # Outer ring
            ring_col = tuple(min(255, c + 40) for c in col)
            pygame.draw.circle(surf, ring_col, pos, node_r + 1, 1)

            if label:
                tl = self.f_tiny.render(
                    label, True, lerp_color(TEXT_LABEL, col, strength * 0.6)
                )
                surf.blit(tl, (pos[0] + node_r + 3, pos[1] - 6))

        # Group bracket lines
        for g_name, g_slice in INPUT_GROUPS:
            idxs = list(range(*g_slice.indices(15)))
            ys_g = [pos_in[i][1] for i in idxs if i < len(pos_in)]
            if not ys_g:
                continue
            mid_y = (min(ys_g) + max(ys_g)) // 2
            gl = self.f_tiny.render(g_name, True, TEXT_LABEL)
            surf.blit(gl, (4, mid_y - 6))
            bx = xs["in"] - 14
            pygame.draw.line(
                surf, (35, 58, 80), (bx, min(ys_g) - 4), (bx, max(ys_g) + 4), 1
            )

        for i, pos in enumerate(pos_in):
            draw_node(
                pos,
                inp[i] if i < len(inp) else 0.0,
                r=4,
                label=INPUT_LABELS[i] if i < len(INPUT_LABELS) else "",
            )
        for i, pos in enumerate(pos_h1):
            draw_node(pos, h1[i] if i < len(h1) else 0.0, r=5)
        for i, pos in enumerate(pos_h2):
            draw_node(pos, h2[i] if i < len(h2) else 0.0, r=6)

        OUT_LABELS = ["Steer", "Thrust"]
        for i, pos in enumerate(pos_out):
            draw_node(pos, out[i] if i < len(out) else 0.0, r=8, label=OUT_LABELS[i])

        # Column headers
        for label, x in [
            ("IN(15)", xs["in"]),
            ("H1(12)", xs["h1"]),
            ("H2(6)", xs["h2"]),
            ("OUT", xs["out"]),
        ]:
            t = self.f_tiny.render(label, True, TEXT_LABEL)
            surf.blit(t, (x - t.get_width() // 2, net_top - 14))

        y += NET_H + 8
        return y

    def _seed_particles(self, fish):
        """Populate signal particles across all layer connections."""
        self._particles.clear()
        layers = [
            (self._pos_in, self._pos_h1),
            (self._pos_h1, self._pos_h2),
            (self._pos_h2, self._pos_out),
        ]
        for src_layer, dst_layer in layers:
            for sp in src_layer:
                for dp in dst_layer:
                    # Spawn 0-2 particles per connection, biased by layer density
                    n = random.randint(0, 1)
                    for _ in range(n):
                        col = activation_color(random.uniform(-0.6, 0.8))
                        self._particles.append(_Particle(sp, dp, col))

    # ── Outputs ───────────────────────────────────────────────────────────

    def _draw_outputs(self, surf, fish, accent, y):
        PAD = 16
        surf.blit(self.f_small.render("OUTPUTS", True, TEXT_LABEL), (PAD, y))
        y += 18

        out = fish.last_outputs if len(fish.last_outputs) == 2 else [0.0, 0.0]
        gx = PAD + 52
        gw = self.PANEL_W - gx - PAD - 28
        gh = 12
        mid = gx + gw // 2
        steer = out[0]

        # Steer gauge
        surf.blit(self.f_tiny.render("STEER", True, TEXT_SECONDARY), (PAD, y + 2))
        pygame.draw.rect(surf, BG_SECTION, (gx, y, gw, gh), border_radius=gh // 2)
        pygame.draw.line(surf, DIVIDER, (mid, y + 2), (mid, y + gh - 2))
        fw = int(abs(steer) * gw / 2)
        if fw > 0:
            fx = mid if steer >= 0 else mid - fw
            col = activation_color(steer)
            pygame.draw.rect(
                surf,
                tuple(c // 3 for c in col),
                (fx, y + 1, fw, gh - 2),
                border_radius=(gh - 2) // 2,
            )
            pygame.draw.rect(
                surf, col, (fx, y + 1, fw, gh - 2), border_radius=(gh - 2) // 2
            )
        nx = mid + int(steer * gw / 2)
        pygame.draw.line(surf, TEXT_PRIMARY, (nx, y - 3), (nx, y + gh + 3), 2)
        surf.blit(
            self.f_tiny.render(f"{steer:+.2f}", True, TEXT_SECONDARY),
            (gx + gw + 4, y + 2),
        )
        y += 22

        # Thrust gauge
        surf.blit(self.f_tiny.render("THRUST", True, TEXT_SECONDARY), (PAD, y + 2))
        thrust_n = (out[1] + 1.0) / 2.0
        pygame.draw.rect(surf, BG_SECTION, (gx, y, gw, gh), border_radius=gh // 2)
        fw = max(gh, int(thrust_n * gw))
        col = lerp_color((50, 120, 190), accent, thrust_n)
        pygame.draw.rect(
            surf, tuple(c // 3 for c in col), (gx, y, fw, gh), border_radius=gh // 2
        )
        pygame.draw.rect(surf, col, (gx, y, fw, gh), border_radius=gh // 2)
        surf.blit(
            self.f_tiny.render(f"{int(thrust_n * 100)}%", True, TEXT_SECONDARY),
            (gx + gw + 4, y + 2),
        )
        y += 22

        # Sparklines
        if len(fish.output_history) > 4:
            SH = 28
            SW = self.PANEL_W - PAD * 2
            for ch_idx, (ch_label, col_line) in enumerate(
                [("Steer", accent), ("Thrust", (60, 150, 220))]
            ):
                surf.blit(
                    self.f_tiny.render(ch_label, True, TEXT_LABEL),
                    (PAD, y + SH // 2 - 6),
                )
                sx = PAD + 42
                sw = SW - 42
                mid_y = y + SH // 2
                pygame.draw.rect(surf, BG_SECTION, (sx, y, sw, SH))
                pygame.draw.line(surf, DIVIDER, (sx, mid_y), (sx + sw, mid_y))
                pts = []
                hist = list(fish.output_history)
                for i, pair in enumerate(hist):
                    if len(pair) <= ch_idx:
                        continue
                    v = pair[ch_idx]
                    px = sx + int(i * sw / len(hist))
                    py = mid_y - int(v * (SH // 2 - 2))
                    pts.append((px, py))
                if len(pts) > 1:
                    # Shadow line
                    shadow = [(p[0], p[1] + 1) for p in pts]
                    pygame.draw.lines(
                        surf, tuple(c // 3 for c in col_line), False, shadow, 1
                    )
                    pygame.draw.lines(surf, col_line, False, pts, 1)
                    # Bright dot at latest value
                    pygame.draw.circle(
                        surf, tuple(min(255, c + 80) for c in col_line), pts[-1], 2
                    )
                y += SH + 6
        return y + 4

    # ── Traits ────────────────────────────────────────────────────────────

    def _draw_traits(self, surf, fish, accent, y):
        PAD = 16
        surf.blit(self.f_small.render("HERITABLE TRAITS", True, TEXT_LABEL), (PAD, y))
        y += 18
        traits = fish.traits.physical_traits
        rows = [
            ("Speed", traits.get("max_speed_mult", 1.0)),
            ("Stamina", traits.get("stamina_mult", 1.0)),
            ("Agility", traits.get("turn_rate_mult", 1.0)),
            ("Metabolism", traits.get("metabolism_mult", 1.0)),
            ("Size", traits.get("size_mult", 1.0)),
            ("Lifespan", traits.get("lifespan_mult", 1.0)),
        ]
        LW = 70
        TW = self.PANEL_W - PAD * 2 - LW - 30
        TH = 8
        CENT = PAD + LW + TW // 2
        for label, val in rows:
            surf.blit(self.f_tiny.render(label, True, TEXT_SECONDARY), (PAD, y + 1))
            tx = PAD + LW
            pygame.draw.rect(surf, BG_SECTION, (tx, y, TW, TH), border_radius=TH // 2)
            pygame.draw.line(surf, DIVIDER, (CENT, y + 1), (CENT, y + TH - 1))
            deviation = max(-1.0, min(1.0, (val - 1.0) / 0.8))
            fw = max(4, int(abs(deviation) * TW / 2))
            fx = CENT if deviation >= 0 else CENT - fw
            col = TEAL if deviation >= 0 else AMBER
            pygame.draw.rect(
                surf,
                tuple(c // 3 for c in col),
                (fx, y + 1, fw, TH - 2),
                border_radius=(TH - 2) // 2,
            )
            pygame.draw.rect(
                surf, col, (fx, y + 1, fw, TH - 2), border_radius=(TH - 2) // 2
            )
            surf.blit(
                self.f_tiny.render(f"{val:.2f}", True, TEXT_LABEL), (tx + TW + 4, y + 1)
            )
            y += 17
        return y + 4

    # ── Stats ─────────────────────────────────────────────────────────────

    def _draw_stats(self, surf, fish, accent, y):
        PAD = 16
        surf.blit(self.f_small.render("LIFETIME STATS", True, TEXT_LABEL), (PAD, y))
        y += 18
        BOX_W = (self.PANEL_W - PAD * 2 - 16) // 3
        BOX_H = 52
        spacing = 8
        stats = [
            ("EATEN", str(fish.food_eaten)),
            ("DISTANCE", str(int(fish.distance_traveled))),
            ("OFFSPRING", str(fish.offspring_count)),
        ]
        for i, (label, val) in enumerate(stats):
            bx = PAD + i * (BOX_W + spacing)
            # Subtle glow behind box
            pygame.draw.rect(
                surf,
                tuple(c // 5 for c in accent),
                (bx - 1, y - 1, BOX_W + 2, BOX_H + 2),
                border_radius=7,
            )
            pygame.draw.rect(surf, BG_SECTION, (bx, y, BOX_W, BOX_H), border_radius=6)
            draw_capsule_outline(surf, DIVIDER, bx, y, BOX_W, BOX_H, 6, width=1)
            tv = self.f_body.render(val, True, accent)
            surf.blit(tv, (bx + (BOX_W - tv.get_width()) // 2, y + 8))
            tl = self.f_tiny.render(label, True, TEXT_LABEL)
            surf.blit(tl, (bx + (BOX_W - tl.get_width()) // 2, y + 32))
        return y + BOX_H + 8
