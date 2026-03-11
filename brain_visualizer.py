"""
Brain Visualizer — Deep-sea instrument panel aesthetic.
Clean, readable, purposeful. Warm text on deep slate.
"""

import pygame
import math
from config import (
    BRAIN_PANEL_WIDTH, BRAIN_PANEL_HEIGHT, FishState, FISH_MAX_AGE,
    FISH_MAX_ENERGY, FISH_LARVA_DURATION, FISH_JUVENILE_DURATION,
    FISH_ELDER_DURATION, FISH_ADULT_DURATION,
)

# ── Palette ────────────────────────────────────────────────────────────────────
BG          = (12, 20, 28)          # deeper ocean slate
BG_SECTION  = (20, 30, 42)         # slightly lighter panel sections
BORDER      = (35, 55, 75)         # subtle border
DIVIDER     = (30, 48, 65)         # section dividers

TEXT_PRIMARY   = (240, 250, 255)   # brighter near-white
TEXT_SECONDARY = (160, 180, 200)   # brighter blue-grey
TEXT_LABEL     = (100, 130, 155)    # brighter labels

TEAL      = (0, 240, 220)          # brighter bioluminescent accent
TEAL_DIM  = (0, 140, 120)
AMBER     = (255, 200, 80)         # brighter amber
AMBER_DIM = (160, 110, 30)
RED_ACC   = (255, 120, 120)        # brighter red
RED_DIM   = (150, 60, 60)

# Node activation colours: teal=positive, slate=neutral, amber=negative
COL_POS     = (0, 240, 220)        # brighter positive
COL_NEU     = (70, 90, 110)        # brighter neutral
COL_NEG     = (255, 180, 80)       # brighter negative

# Species accent colours
SPECIES_ACCENT = {
    (False, False): AMBER,           # common
    (True,  False): TEAL,            # cleaner
    (False, True ): RED_ACC,         # predator
}
SPECIES_ACCENT_DIM = {
    (False, False): AMBER_DIM,
    (True,  False): TEAL_DIM,
    (False, True ): RED_DIM,
}


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def activation_color(v):
    """Map tanh value [-1,1] to teal/slate/amber colour."""
    t = min(1.0, abs(v))
    if v >= 0:
        return lerp_color(COL_NEU, COL_POS, t)
    else:
        return lerp_color(COL_NEU, COL_NEG, t)


def draw_capsule(surface, color, x, y, w, h, radius=None):
    """Draw a rounded rectangle (capsule)."""
    if radius is None:
        radius = h // 2
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_capsule_outline(surface, color, x, y, w, h, radius=None, width=1):
    if radius is None:
        radius = h // 2
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, color, rect, border_radius=radius, width=width)


class BrainVisualizer:
    PANEL_W = BRAIN_PANEL_WIDTH      # 420
    PANEL_H = BRAIN_PANEL_HEIGHT     # 800

    def __init__(self, screen_width, screen_height):
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.panel_h  = min(self.PANEL_H, screen_height)
        self.slide_x  = float(self.PANEL_W)   # start fully off-screen (right side)
        self.anim_t   = 0.0                    # global animation clock

        self.prev_state       = None
        self.state_flash      = 0.0
        self.anim_intensity   = 0.5

        self._INTENSITY = {
            FishState.RESTING: 0.25,
            FishState.HUNTING: 0.70,
            FishState.FLEEING: 1.00,
            FishState.MATING:  0.55,
            FishState.NESTING: 0.45,
        }

        # Fonts — using pygame's built-in vector-style font for clean look
        self.f_title  = pygame.font.Font(None, 26)
        self.f_body   = pygame.font.Font(None, 21)
        self.f_small  = pygame.font.Font(None, 18)
        self.f_tiny   = pygame.font.Font(None, 15)

        # Pre-build the static background panel surface
        self._panel_surf = None

    # ── Public API ─────────────────────────────────────────────────────────────

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

        if self.state_flash > 0:
            self.state_flash = max(0.0, self.state_flash - dt)

    def draw(self, screen, selected_fish, time):
        if self.slide_x >= self.PANEL_W:
            return

        surf = pygame.Surface((self.PANEL_W, self.panel_h), pygame.SRCALPHA)
        
        # Animated background with subtle pulse
        bg_pulse = 0.92 + 0.08 * math.sin(self.anim_t * 2)
        bg_color = tuple(int(c * bg_pulse) for c in BG)
        surf.fill((*bg_color, 248))

        accent = SPECIES_ACCENT.get((selected_fish.is_cleaner, selected_fish.is_predator), AMBER)
        accent_dim = SPECIES_ACCENT_DIM.get((selected_fish.is_cleaner, selected_fish.is_predator), AMBER_DIM)

        # Enhanced left accent stripe with glow
        glow_pulse = 0.8 + 0.2 * math.sin(self.anim_t * 3)
        glow_surf = pygame.Surface((8, self.panel_h), pygame.SRCALPHA)
        glow_alpha = int(60 * glow_pulse)
        pygame.draw.rect(glow_surf, (*accent, glow_alpha), (0, 0, 8, self.panel_h))
        surf.blit(glow_surf, (-4, 0))
        pygame.draw.rect(surf, accent, (0, 0, 3, self.panel_h))

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

    # ── Sections ───────────────────────────────────────────────────────────────

    def _draw_header(self, surf, fish, accent, y):
        PAD = 16

        # Species pill
        key = (fish.is_cleaner, fish.is_predator)
        species = "PREDATOR" if fish.is_predator else ("CLEANER" if fish.is_cleaner else "COMMON")
        pill_w = 80
        draw_capsule(surf, accent, PAD, y, pill_w, 22, radius=11)
        t = self.f_tiny.render(species, True, BG)
        surf.blit(t, (PAD + (pill_w - t.get_width()) // 2, y + 4))

        # Life stage + sex on same row
        elder_t  = FISH_LARVA_DURATION + FISH_JUVENILE_DURATION + FISH_ADULT_DURATION
        adult_t  = FISH_LARVA_DURATION + FISH_JUVENILE_DURATION
        juv_t    = FISH_LARVA_DURATION
        if fish.age >= elder_t:   stage = "Elder"
        elif fish.age >= adult_t: stage = "Adult"
        elif fish.age >= juv_t:   stage = "Juvenile"
        else:                     stage = "Larva"

        sex_sym = "♂" if fish.sex == "M" else "♀"
        preg    = "  PREGNANT" if fish.is_pregnant else ""
        line    = f"{sex_sym} {stage}{preg}"
        t = self.f_body.render(line, True, TEXT_PRIMARY)
        surf.blit(t, (PAD + pill_w + 10, y + 3))

        y += 32

        # State badge with flash
        STATE_COLORS = {
            FishState.RESTING: (90, 160, 120),
            FishState.HUNTING: AMBER,
            FishState.FLEEING: RED_ACC,
            FishState.MATING:  (210, 130, 220),
            FishState.NESTING: (150, 200, 255),
        }
        base_c = STATE_COLORS.get(fish.state, TEXT_SECONDARY)
        if self.state_flash > 0:
            f = self.state_flash / 0.6
            state_c = lerp_color(base_c, TEXT_PRIMARY, f)
        else:
            state_c = base_c

        label = f"● {fish.state.name}"
        t = self.f_body.render(label, True, state_c)
        surf.blit(t, (PAD, y))
        y += 26

        return y

    def _draw_divider(self, surf, y, margin=16):
        pygame.draw.line(surf, DIVIDER, (margin, y), (self.PANEL_W - margin, y))
        return y + 10

    def _draw_status_bars(self, surf, fish, accent, y):
        PAD    = 16
        LW     = 62     # label column width
        BAR_W  = self.PANEL_W - PAD * 2 - LW - 32
        BAR_H  = 12     # Taller bars
        RADIUS = 6

        lifespan = FISH_MAX_AGE * fish.traits.physical_traits.get("lifespan_mult", 1.0)
        bars = [
            ("LIFE",    max(0.0, 1.0 - fish.age / lifespan), (100, 180, 255)),
            ("ENERGY",  max(0.0, min(1.0, fish.energy / FISH_MAX_ENERGY)), accent),
            ("STAMINA", fish.stamina / 100.0, (140, 230, 160)),
        ]

        for label, ratio, color in bars:
            # Label
            tl = self.f_tiny.render(label, True, TEXT_LABEL)
            surf.blit(tl, (PAD, y + 2))

            bx = PAD + LW
            # Enhanced track with subtle gradient
            draw_capsule(surf, BG_SECTION, bx, y, BAR_W, BAR_H, RADIUS)
            
            # Add subtle inner highlight
            highlight_surf = pygame.Surface((BAR_W - 4, BAR_H - 4), pygame.SRCALPHA)
            highlight_surf.fill((*TEXT_PRIMARY, 15))
            surf.blit(highlight_surf, (bx + 2, y + 2))
            
            # Enhanced fill with glow effect
            fill_w = max(RADIUS * 2, int(BAR_W * ratio))
            
            # Glow for high values
            if ratio > 0.7:
                glow_surf = pygame.Surface((fill_w + 8, BAR_H + 8), pygame.SRCALPHA)
                glow_alpha = int((ratio - 0.7) * 100)
                pygame.draw.rect(glow_surf, (*color, glow_alpha), 
                               (0, 0, fill_w + 8, BAR_H + 8), border_radius=RADIUS + 2)
                surf.blit(glow_surf, (bx - 4, y - 4))
            
            draw_capsule(surf, color, bx, y, fill_w, BAR_H, RADIUS)
            
            # Add shimmer effect
            shimmer = 0.8 + 0.2 * math.sin(self.anim_t * 3 + bx * 0.1)
            shimmer_surf = pygame.Surface((fill_w - 4, BAR_H - 4), pygame.SRCALPHA)
            shimmer_surf.fill((*TEXT_PRIMARY, int(20 * shimmer)))
            surf.blit(shimmer_surf, (bx + 2, y + 2))
            
            # Brighter percentage
            pct = self.f_tiny.render(f"{int(ratio * 100)}%", True, TEXT_SECONDARY)
            surf.blit(pct, (bx + BAR_W + 6, y + 2))

            y += 22

        return y + 6

    def _draw_network(self, surf, fish, accent, accent_dim, y):
        PAD = 16
        title = self.f_small.render("NEURAL NETWORK", True, TEXT_LABEL)
        surf.blit(title, (PAD, y))
        y += 20

        NET_H = 240
        net_top = y

        # Column x positions
        W = self.PANEL_W
        xs = {
            "in":  int(W * 0.13),
            "h1":  int(W * 0.38),
            "h2":  int(W * 0.64),
            "out": int(W * 0.88),
        }

        # Node positions
        def col_nodes(x, n):
            return [(x, net_top + int((i + 0.5) * NET_H / n)) for i in range(n)]

        pos_in  = col_nodes(xs["in"],  14)
        pos_h1  = col_nodes(xs["h1"],  12)
        pos_h2  = col_nodes(xs["h2"],   6)
        pos_out = col_nodes(xs["out"],  2)

        # Gather activations
        inp  = fish.last_inputs   if len(fish.last_inputs)  == 14 else [0.0] * 14
        h1   = getattr(fish, "last_hidden1", [0.0] * 12)
        h2   = fish.last_hidden   if len(fish.last_hidden)  == 6  else [0.0] * 6
        out  = fish.last_outputs  if len(fish.last_outputs) == 2  else [0.0] * 2

        # ── Connections ────────────────────────────────────────────────────────
        # Draw faint background wires first, then bright active ones on top.
        # This helper is reused for all connection passes (in→h1, h1→h2, h2→out).
        def draw_connections(src_pos, dst_pos, src_acts, threshold=0.15, dim_color=(30, 48, 65)):
            """
            Draw connections from each source node to each destination node.

            - If |activation| < threshold: draw a thin dim wire.
            - Otherwise: draw a brighter, thicker wire based on activation_color().
            """
            for i, sp in enumerate(src_pos):
                act = src_acts[i] if i < len(src_acts) else 0.0
                strength = abs(act)

                for dp in dst_pos:
                    if strength < threshold:
                        # dim background wire
                        pygame.draw.line(surf, dim_color, sp, dp, 1)
                    else:
                        # Enhanced active connections with glow
                        col = activation_color(act)
                        thick = 2 + int(strength * 3)  # Thicker for more visibility
                        
                        # Add subtle glow for strong connections
                        if strength > 0.5:
                            glow_surf = pygame.Surface((abs(dp[0] - sp[0]) + 20, abs(dp[1] - sp[1]) + 20), pygame.SRCALPHA)
                            glow_alpha = int(strength * 40)
                            pygame.draw.line(glow_surf, (*col, glow_alpha), 
                                           (10, 10), (dp[0] - sp[0] + 10, dp[1] - sp[1] + 10), thick + 2)
                            surf.blit(glow_surf, (min(sp[0], dp[0]) - 10, min(sp[1], dp[1]) - 10))
                        
                        pygame.draw.line(surf, col, sp, dp, thick)

        # All faint wires (background layer) — use a huge threshold so all wires stay dim
        draw_connections(pos_in,  pos_h1, inp, threshold=1e9)
        draw_connections(pos_h1, pos_h2, h1, threshold=1e9)
        draw_connections(pos_h2, pos_out, h2, threshold=1e9)

        # Active wires (foreground layer)
        draw_connections(pos_in,  pos_h1, inp, threshold=0.12)
        draw_connections(pos_h1, pos_h2, h1, threshold=0.12)
        draw_connections(pos_h2, pos_out, h2, threshold=0.12)

        # ── Nodes ──────────────────────────────────────────────────────────────
        # Ripple phase for active nodes

        INPUT_GROUPS = [
            ("Food",   slice(0, 3),  (0, 180, 130)),
            ("Threat", slice(3, 6),  (200, 80,  80)),
            ("Mate",   slice(6, 9),  (180, 120, 220)),
            ("Self",   slice(9, 14), (130, 160, 200)),
        ]
        INPUT_LABELS = [
            "L", "C", "R",   # food
            "L", "C", "R",   # threat
            "L", "C", "R",   # mate
            "Nrg", "Stm", "Dep", "Spd", "Safe",  # self
        ]

        def draw_node(pos, act, r=5, label=None, label_left=False):
            col = activation_color(act)
            strength = abs(act)
            
            # Enhanced glow for active nodes with pulsing effect
            if strength > 0.2:
                # Pulsing glow based on animation time
                pulse = 0.8 + 0.2 * math.sin(self.anim_t * 4 + pos[0] * 0.01 + pos[1] * 0.01)
                glow_r = r + 4 + int(strength * 6 * pulse)
                glow_alpha = int(strength * 80 * pulse)
                glow_surf = pygame.Surface((glow_r * 2 + 8, glow_r * 2 + 8), pygame.SRCALPHA)
                
                # Multi-layer glow for more depth
                for i in range(3):
                    layer_alpha = glow_alpha // (i + 1)
                    layer_r = glow_r - i * 2
                    if layer_r > 0:
                        pygame.draw.circle(glow_surf, (*col, layer_alpha),
                                           (glow_r + 4, glow_r + 4), layer_r)
                surf.blit(glow_surf, (pos[0] - glow_r - 4, pos[1] - glow_r - 4))
            
            # Larger, brighter filled circle
            node_r = r + int(strength * 2)
            pygame.draw.circle(surf, col, pos, node_r)
            
            # Brighter white ring with glow
            pygame.draw.circle(surf, (255, 255, 255), pos, node_r, 2)
            
            # Label
            if label:
                tl = self.f_tiny.render(label, True, TEXT_LABEL)
                if label_left:
                    surf.blit(tl, (pos[0] - tl.get_width() - node_r - 2, pos[1] - 6))
                else:
                    surf.blit(tl, (pos[0] + node_r + 3, pos[1] - 6))

        # Draw input nodes with group labels
        group_start_y = {}
        group_end_y   = {}
        for g_name, g_slice, g_col in INPUT_GROUPS:
            idxs = range(*g_slice.indices(14))
            ys_g = [pos_in[i][1] for i in idxs]
            group_start_y[g_name] = min(ys_g)
            group_end_y[g_name]   = max(ys_g)

        # Group bracket labels on far left
        for g_name, g_slice, g_col in INPUT_GROUPS:
            idxs = list(range(*g_slice.indices(14)))
            mid_y = (group_start_y[g_name] + group_end_y[g_name]) // 2
            gl = self.f_tiny.render(g_name, True, TEXT_LABEL)
            surf.blit(gl, (4, mid_y - 6))
            # Bracket line
            bx = xs["in"] - 14
            pygame.draw.line(surf, (45, 68, 90),
                             (bx, group_start_y[g_name] - 4),
                             (bx, group_end_y[g_name] + 4), 1)

        for i, pos in enumerate(pos_in):
            act = inp[i]
            label = INPUT_LABELS[i] if i < len(INPUT_LABELS) else ""
            draw_node(pos, act, r=4, label=label, label_left=False)

        # H1 — no labels (12 nodes, dense)
        for i, pos in enumerate(pos_h1):
            act = h1[i] if i < len(h1) else 0.0
            draw_node(pos, act, r=5)

                # H2 — no labels (6 nodes, sparse)
        for i, pos in enumerate(pos_h2):
            act = h2[i] if i < len(h2) else 0.0
            draw_node(pos, act, r=6)

        # Output nodes — larger, labelled right
        OUT_LABELS = ["Steer", "Thrust"]
        for i, pos in enumerate(pos_out):
            act = out[i] if i < len(out) else 0.0
            draw_node(pos, act, r=8, label=OUT_LABELS[i], label_left=False)

        # Layer column headers
        for label, x in [("IN(14)", xs["in"]), ("H1(12)", xs["h1"]),
                          ("H2(6)", xs["h2"]), ("OUT", xs["out"])]:
            t = self.f_tiny.render(label, True, TEXT_LABEL)
            surf.blit(t, (x - t.get_width() // 2, net_top - 14))

        y += NET_H + 8
        return y

    def _draw_outputs(self, surf, fish, accent, y):
        PAD   = 16
        title = self.f_small.render("OUTPUTS", True, TEXT_LABEL)
        surf.blit(title, (PAD, y))
        y += 18

        out = fish.last_outputs if len(fish.last_outputs) == 2 else [0.0, 0.0]

        # ── Steer gauge (bidirectional) ────────────────────────────────────────
        label = self.f_tiny.render("STEER", True, TEXT_SECONDARY)
        surf.blit(label, (PAD, y + 2))

        gx    = PAD + 48
        gw    = self.PANEL_W - gx - PAD - 28
        gh    = 14
        mid   = gx + gw // 2
        steer = out[0]  # [-1, 1]

        draw_capsule(surf, BG_SECTION, gx, y, gw, gh, gh // 2)
        # Centre tick
        pygame.draw.line(surf, DIVIDER, (mid, y + 2), (mid, y + gh - 2))
        # Fill from centre
        fill_w = int(abs(steer) * gw / 2)
        fx = mid if steer >= 0 else mid - fill_w
        col = activation_color(steer)
        if fill_w > 0:
            draw_capsule(surf, col, fx, y + 2, fill_w, gh - 4, (gh - 4) // 2)
        # Needle
        nx = mid + int(steer * gw / 2)
        pygame.draw.line(surf, TEXT_PRIMARY, (nx, y - 2), (nx, y + gh + 2), 2)

        pv = self.f_tiny.render(f"{steer:+.2f}", True, TEXT_SECONDARY)
        surf.blit(pv, (gx + gw + 4, y + 2))

        # Side labels
        ll = self.f_tiny.render("◄", True, TEXT_LABEL)
        rl = self.f_tiny.render("►", True, TEXT_LABEL)
        surf.blit(ll, (gx - 10, y + 2))
        surf.blit(rl, (gx + gw + 20, y + 2))

        y += 24

        # ── Thrust gauge (unidirectional fill) ────────────────────────────────
        label = self.f_tiny.render("THRUST", True, TEXT_SECONDARY)
        surf.blit(label, (PAD, y + 2))

        thrust_n = (out[1] + 1.0) / 2.0  # [0, 1]
        draw_capsule(surf, BG_SECTION, gx, y, gw, gh, gh // 2)
        fill_w = max(gh, int(thrust_n * gw))
        col = lerp_color((80, 140, 200), accent, thrust_n)
        draw_capsule(surf, col, gx, y, fill_w, gh, gh // 2)
        pv = self.f_tiny.render(f"{int(thrust_n * 100)}%", True, TEXT_SECONDARY)
        surf.blit(pv, (gx + gw + 4, y + 2))
        y += 24

        # ── Sparklines ────────────────────────────────────────────────────────
        if len(fish.output_history) > 4:
            SH = 30
            SW = self.PANEL_W - PAD * 2

            for ch_idx, (ch_label, col_line) in enumerate([
                ("Steer",  accent),
                ("Thrust", (90, 160, 230)),
            ]):
                tl = self.f_tiny.render(ch_label, True, TEXT_LABEL)
                surf.blit(tl, (PAD, y + SH // 2 - 6))
                sx = PAD + 42
                sw = SW - 42
                pygame.draw.rect(surf, BG_SECTION, (sx, y, sw, SH))
                pygame.draw.rect(surf, DIVIDER, (sx, y, sw, SH), 1)
                # Zero line
                mid_y = y + SH // 2
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
                    pygame.draw.lines(surf, col_line, False, pts, 1)

                y += SH + 6

        return y + 4

    def _draw_traits(self, surf, fish, accent, y):
        PAD  = 16
        title = self.f_small.render("HERITABLE TRAITS", True, TEXT_LABEL)
        surf.blit(title, (PAD, y))
        y += 18

        traits = fish.traits.physical_traits
        rows = [
            ("Speed",      traits.get("max_speed_mult",   1.0)),
            ("Stamina",    traits.get("stamina_mult",      1.0)),
            ("Agility",    traits.get("turn_rate_mult",    1.0)),
            ("Metabolism", traits.get("metabolism_mult",   1.0)),
            ("Size",       traits.get("size_mult",         1.0)),
            ("Lifespan",   traits.get("lifespan_mult",     1.0)),
        ]

        LW    = 70
        TW    = self.PANEL_W - PAD * 2 - LW - 30
        TH    = 8
        CENT  = PAD + LW + TW // 2

        for label, val in rows:
            tl = self.f_tiny.render(label, True, TEXT_SECONDARY)
            surf.blit(tl, (PAD, y + 1))

            tx = PAD + LW
            draw_capsule(surf, BG_SECTION, tx, y, TW, TH, TH // 2)
            # Centre tick
            pygame.draw.line(surf, DIVIDER, (CENT, y + 1), (CENT, y + TH - 1))

            # Fill offset from centre
            deviation = (val - 1.0) / 0.8   # normalise ±0.8 → ±1
            deviation = max(-1.0, min(1.0, deviation))
            fill_w = max(4, int(abs(deviation) * TW / 2))
            if deviation >= 0:
                fx = CENT
                col = TEAL
            else:
                fx = CENT - fill_w
                col = AMBER
            draw_capsule(surf, col, fx, y + 1, fill_w, TH - 2, (TH - 2) // 2)

            vt = self.f_tiny.render(f"{val:.2f}", True, TEXT_LABEL)
            surf.blit(vt, (tx + TW + 4, y + 1))

            y += 17

        return y + 4

    def _draw_stats(self, surf, fish, accent, y):
        PAD   = 16
        title = self.f_small.render("LIFETIME STATS", True, TEXT_LABEL)
        surf.blit(title, (PAD, y))
        y += 18

        BOX_W   = (self.PANEL_W - PAD * 2 - 16) // 3
        BOX_H   = 52
        spacing = 8

        stats = [
            ("EATEN",     str(fish.food_eaten)),
            ("DISTANCE",  str(int(fish.distance_traveled))),
            ("OFFSPRING", str(fish.offspring_count)),
        ]

        for i, (label, val) in enumerate(stats):
            bx = PAD + i * (BOX_W + spacing)
            # Box
            draw_capsule(surf, BG_SECTION, bx, y, BOX_W, BOX_H, 6)
            draw_capsule_outline(surf, DIVIDER, bx, y, BOX_W, BOX_H, 6, width=1)

            # Value (large)
            tv = self.f_body.render(val, True, accent)
            surf.blit(tv, (bx + (BOX_W - tv.get_width()) // 2, y + 8))

            # Label (small, below)
            tl = self.f_tiny.render(label, True, TEXT_LABEL)
            surf.blit(tl, (bx + (BOX_W - tl.get_width()) // 2, y + 32))

        return y + BOX_H + 8