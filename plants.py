"""Plant system with organic visual rendering, tapered blades, and visible seed production"""

import pygame
import math
import random
from config import (
    WATER_LINE_Y,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    KELP_HEIGHT_MIN,
    KELP_HEIGHT_MAX,
    KELP_SWAY_SPEED,
    KELP_SWAY_AMPLITUDE,
    KELP_COLOR,
    KELP_HIGHLIGHT,
    KELP_WIDTH,
    SEAGRASS_HEIGHT_MIN,
    SEAGRASS_HEIGHT_MAX,
    SEAGRASS_SWAY_SPEED,
    SEAGRASS_SWAY_AMPLITUDE,
    SEAGRASS_COLOR,
    SEAGRASS_HIGHLIGHT,
    SEAGRASS_WIDTH,
    ALGAE_HEIGHT_MIN,
    ALGAE_HEIGHT_MAX,
    ALGAE_SWAY_SPEED,
    ALGAE_SWAY_AMPLITUDE,
    ALGAE_COLOR,
    ALGAE_HIGHLIGHT,
    ALGAE_WIDTH,
    RED_SEAWEED_HEIGHT_MIN,
    RED_SEAWEED_HEIGHT_MAX,
    RED_SEAWEED_SWAY_SPEED,
    RED_SEAWEED_SWAY_AMPLITUDE,
    RED_SEAWEED_COLOR,
    RED_SEAWEED_HIGHLIGHT,
    RED_SEAWEED_WIDTH,
    RED_SEAWEED_GLOW_INTENSITY,
    LILY_PAD_COLOR,
    LILY_PAD_HIGHLIGHT,
    LILY_PAD_SIZE_MIN,
    LILY_PAD_SIZE_MAX,
    LILY_PAD_FLOWER_COLOR,
    TUBE_SPONGE_HEIGHT_MIN,
    TUBE_SPONGE_HEIGHT_MAX,
    TUBE_SPONGE_SEGMENTS,
    TUBE_SPONGE_FILTER_RATE,
    TUBE_SPONGE_COLOR,
    TUBE_SPONGE_HIGHLIGHT,
    TUBE_SPONGE_WIDTH,
    FAN_CORAL_HEIGHT_MIN,
    FAN_CORAL_HEIGHT_MAX,
    FAN_CORAL_SWAY_SPEED,
    FAN_CORAL_SWAY_AMPLITUDE,
    FAN_CORAL_BRANCH_FACTOR,
    FAN_CORAL_COLOR,
    FAN_CORAL_HIGHLIGHT,
    FAN_CORAL_WIDTH,
    ANEMONE_HEIGHT_MIN,
    ANEMONE_HEIGHT_MAX,
    ANEMONE_SWAY_SPEED,
    ANEMONE_TENTACLES,
    ANEMONE_COLOR,
    ANEMONE_HIGHLIGHT,
    ANEMONE_WIDTH,
    ANEMONE_PULSE_SPEED,
    ANEMONE_GLOW_COLOR,
    PLANT_GRAZE_DAMAGE,
    PLANT_GRAZE_ENERGY_GAIN,
    GRAZING_VISUAL_DURATION,
    PLANKTON_PER_PLANT_CHANCE,
    ROOT_BASE_GROWTH_RATE,
    PLANT_HARD_CAP,
    SEED_HARD_CAP,
    BUBBLE_CHANCE,
    BUBBLE_COLOR,
    SOIL_MAX_NUTRIENT,
)
from plant_rules import is_valid_depth
from roots import RootSystem
from seeds import Seed
from plant_development import PlantDevelopment


_PLANT_PLANKTON_COLOR = {
    "kelp": (60, 160, 60),
    "seagrass": (80, 200, 80),
    "algae": (40, 110, 40),
    "red_seaweed": (180, 60, 60),
    "lily_pad": (60, 150, 60),
    "tube_sponge": (180, 160, 120),
    "fan_coral": (220, 110, 170),
    "anemone": (130, 80, 200),
}


class Plant:
    def __init__(self, x, base_y, plant_type, soil_grid, seed_traits, world=None):
        self.x, self.base_y, self.plant_type = x, base_y, plant_type
        self.traits, self.world = seed_traits, world
        self.development = PlantDevelopment(plant_type, seed_traits)
        self._init_species_params()
        self.development._max_height_ref = self.max_height
        self.phase_offset = random.uniform(0, math.pi * 2)
        self.wind_phase = 0.0
        self.root_system = RootSystem(self.x, self.base_y, soil_grid)

        if plant_type == "seagrass":
            self.blade_count = random.randint(4, 7)
            self.blade_data = [
                {
                    "offset": random.uniform(-12, 12),
                    "h_mult": random.uniform(0.7, 1.1),
                    "phase": random.uniform(0, math.pi * 2),
                    "speed": random.uniform(0.8, 1.2),
                }
                for _ in range(self.blade_count)
            ]
            self.development.total_blades = self.blade_count
        elif plant_type == "lily_pad":
            self.pad_radius = int(
                (
                    LILY_PAD_SIZE_MIN
                    + (LILY_PAD_SIZE_MAX - LILY_PAD_SIZE_MIN)
                    * self.traits.get("spread_factor", 1.0)
                    * 0.5
                )
                * self.traits["max_height_factor"]
            )
            self.flower_open, self.flower_timer = False, random.uniform(0, 10)
        elif plant_type == "fan_coral":
            self.branches, self._branch_dirty, self._last_branch_height = [], True, 0
        elif plant_type == "anemone":
            self._init_tentacles()
        elif plant_type == "tube_sponge":
            self._init_pores()

        self.floating_leaves, self.decomposition_particles, self.bite_marks = [], [], []
        self.biomass, self.graze_timer = 12.0 + random.uniform(0, 8), 0.0
        self._plankton_timer = random.uniform(
            0, 1.0 / max(PLANKTON_PER_PLANT_CHANCE, 0.001)
        )

    def _init_species_params(self):
        params_map = {
            "kelp": dict(
                h=(KELP_HEIGHT_MIN, KELP_HEIGHT_MAX),
                sw=KELP_SWAY_SPEED,
                sa=KELP_SWAY_AMPLITUDE,
                bc=KELP_COLOR,
                hl=KELP_HIGHLIGHT,
                w=KELP_WIDTH,
            ),
            "seagrass": dict(
                h=(SEAGRASS_HEIGHT_MIN, SEAGRASS_HEIGHT_MAX),
                sw=SEAGRASS_SWAY_SPEED,
                sa=SEAGRASS_SWAY_AMPLITUDE,
                bc=SEAGRASS_COLOR,
                hl=SEAGRASS_HIGHLIGHT,
                w=SEAGRASS_WIDTH,
            ),
            "algae": dict(
                h=(ALGAE_HEIGHT_MIN, ALGAE_HEIGHT_MAX),
                sw=ALGAE_SWAY_SPEED,
                sa=ALGAE_SWAY_AMPLITUDE,
                bc=ALGAE_COLOR,
                hl=ALGAE_HIGHLIGHT,
                w=ALGAE_WIDTH,
            ),
            "red_seaweed": dict(
                h=(RED_SEAWEED_HEIGHT_MIN, RED_SEAWEED_HEIGHT_MAX),
                sw=RED_SEAWEED_SWAY_SPEED,
                sa=RED_SEAWEED_SWAY_AMPLITUDE,
                bc=RED_SEAWEED_COLOR,
                hl=RED_SEAWEED_HIGHLIGHT,
                w=RED_SEAWEED_WIDTH,
            ),
            "lily_pad": dict(
                h=(0, 0),
                sw=0.5,
                sa=3,
                bc=LILY_PAD_COLOR,
                hl=LILY_PAD_HIGHLIGHT,
                w=LILY_PAD_SIZE_MAX,
            ),
            "tube_sponge": dict(
                h=(TUBE_SPONGE_HEIGHT_MIN, TUBE_SPONGE_HEIGHT_MAX),
                sw=0.3,
                sa=2,
                bc=TUBE_SPONGE_COLOR,
                hl=TUBE_SPONGE_HIGHLIGHT,
                w=TUBE_SPONGE_WIDTH,
            ),
            "fan_coral": dict(
                h=(FAN_CORAL_HEIGHT_MIN, FAN_CORAL_HEIGHT_MAX),
                sw=FAN_CORAL_SWAY_SPEED,
                sa=FAN_CORAL_SWAY_AMPLITUDE,
                bc=FAN_CORAL_COLOR,
                hl=FAN_CORAL_HIGHLIGHT,
                w=FAN_CORAL_WIDTH,
            ),
            "anemone": dict(
                h=(ANEMONE_HEIGHT_MIN, ANEMONE_HEIGHT_MAX),
                sw=ANEMONE_SWAY_SPEED,
                sa=8,
                bc=ANEMONE_COLOR,
                hl=ANEMONE_HIGHLIGHT,
                w=ANEMONE_WIDTH,
            ),
        }
        p = params_map.get(self.plant_type, params_map["kelp"])
        b_min, b_max = p["h"]
        self.max_height = (
            0
            if self.plant_type == "lily_pad"
            else int(b_min + (b_max - b_min) * self.traits["max_height_factor"])
        )
        (
            self.sway_speed,
            self.sway_amplitude,
            self.base_color,
            self.highlight_color,
            self.width,
        ) = (p["sw"], p["sa"], p["bc"], p["hl"], p["w"])

    def _generate_branches(self):
        h = self.development.current_height
        self.branches = []

        def add(x, y, a, l, w, lev):
            if lev <= 0 or l < 5:
                return
            ex, ey = x + math.cos(a) * l, y + math.sin(a) * l
            self.branches.append(
                {"start": (x, y), "end": (ex, ey), "width": w, "level": lev}
            )
            if lev > 1:
                off = (
                    0.4
                    * FAN_CORAL_BRANCH_FACTOR
                    * self.traits.get("branch_density", 1.0)
                )
                add(ex, ey, a - off, l * 0.7, w * 0.6, lev - 1)
                add(ex, ey, a + off, l * 0.7, w * 0.6, lev - 1)

        add(self.x, self.base_y, -math.pi / 2, h * 0.3, self.width, 4)
        self._last_branch_height, self._branch_dirty = h, False

    def _init_tentacles(self):
        self.tentacles = [
            {
                "base_angle": (i / ANEMONE_TENTACLES) * math.pi * 2,
                "length": random.uniform(0.8, 1.2),
                "phase": random.uniform(0, math.pi * 2),
                "curvature": random.uniform(-0.3, 0.3),
            }
            for i in range(ANEMONE_TENTACLES)
        ]

    def _init_pores(self):
        self.pores = [
            {
                "y_offset": (i / TUBE_SPONGE_SEGMENTS) * self.max_height,
                "angle": (i / TUBE_SPONGE_SEGMENTS) * math.pi * 4,
                "size": random.uniform(2, 4),
            }
            for i in range(TUBE_SPONGE_SEGMENTS)
        ]

    def graze(self, amount):
        if self.biomass <= 0.5:
            return 0.0
        dmg = min(self.biomass, amount * PLANT_GRAZE_DAMAGE)
        self.biomass -= dmg
        self.graze_timer = GRAZING_VISUAL_DURATION
        self.bite_marks.append(
            {
                "ox": random.uniform(-self.width, self.width),
                "oy": -random.uniform(0, self.development.current_height * 0.7),
                "life": GRAZING_VISUAL_DURATION + random.uniform(0, 1),
            }
        )
        return PLANT_GRAZE_ENERGY_GAIN * (dmg / PLANT_GRAZE_DAMAGE)

    def try_produce_plankton(self, dt, particle_system, time):
        if not self.development.is_mature:
            return False
        self._plankton_timer -= dt
        if self._plankton_timer > 0:
            return False
        self._plankton_timer = (1.0 / PLANKTON_PER_PLANT_CHANCE) + random.uniform(-2, 2)
        tx, ty = self.get_tip_position(time)
        particle_system.spawn_plankton_at(
            tx, ty, color_hint=_PLANT_PLANKTON_COLOR.get(self.plant_type)
        )
        return True

    def update(self, dt, soil_grid, photosynthesis_rate=1.0, season_index=0):
        self.wind_phase += dt * 0.4
        if self.graze_timer > 0:
            self.graze_timer -= dt
        for m in self.bite_marks[:]:
            m["life"] -= dt
            if m["life"] <= 0:
                self.bite_marks.remove(m)
        if self.plant_type == "lily_pad":
            self.flower_timer += dt
            self.flower_open = (math.sin(self.flower_timer * 0.5) + 1) > 1.0

        need_mult = self.development.get_root_growth_multiplier(
            self.development.energy, self.development.current_height
        )
        if self.development.stage not in ("seed", "dormant") and season_index != 3:
            self.root_system.adjust_growth_rate(
                ROOT_BASE_GROWTH_RATE * self.traits["root_aggression"] * need_mult
            )
        else:
            self.root_system.adjust_growth_rate(0.0)

        self.root_system.update(dt, self.development.current_height)
        nutrients = self.root_system.harvest_nutrients()
        if self.plant_type == "tube_sponge":
            nutrients += (
                TUBE_SPONGE_FILTER_RATE * self.traits.get("filter_efficiency", 1.0) * dt
            )

        alive = self.development.update(
            dt,
            nutrients * self.traits["growth_rate_mult"],
            self.development.current_height,
            photosynthesis_rate=photosynthesis_rate,
            season_index=season_index,
        )
        if (
            self.plant_type == "fan_coral"
            and abs(self.development.current_height - self._last_branch_height) > 5
        ):
            self._generate_branches()

        if (
            self.plant_type in ("kelp", "red_seaweed")
            and self.development.is_mature
            and random.random() < 0.0005
        ):
            self.floating_leaves.append(
                {
                    "x": self.x,
                    "y": self.base_y - self.development.current_height * 0.7,
                    "vx": random.uniform(-0.5, 0.5),
                    "vy": random.uniform(-0.8, -0.4),
                    "life": random.uniform(6, 12),
                    "rot": 0,
                    "spin": random.uniform(-5, 5),
                }
            )
        self.floating_leaves = [
            {
                "x": l["x"] + l["vx"],
                "y": l["y"] + l["vy"],
                "vx": l["vx"],
                "vy": l["vy"],
                "life": l["life"] - dt,
                "rot": l["rot"] + l["spin"] * dt,
                "spin": l["spin"],
            }
            for l in self.floating_leaves
            if l["life"] > dt
        ]

        if self.development.stage == "decomposing" and random.random() < 0.1:
            self.decomposition_particles.append(
                {
                    "x": self.x + random.uniform(-10, 10),
                    "y": self.base_y
                    - random.uniform(0, self.development.current_height),
                    "vx": random.uniform(-0.3, 0.3),
                    "vy": random.uniform(-0.2, 0.2),
                    "life": 2.0,
                }
            )
        self.decomposition_particles = [
            {
                "x": p["x"] + p["vx"],
                "y": p["y"] + p["vy"],
                "vx": p["vx"],
                "vy": p["vy"],
                "life": p["life"] - dt,
            }
            for p in self.decomposition_particles
            if p["life"] > dt
        ]
        return alive

    def try_produce_seed(self, time, mod, season):
        if not self.development.can_produce_seed(mod, season):
            return None
        cs = Seed(self.plant_type)
        cs.traits = cs.mutate(self.traits)
        tx, ty = self.get_tip_position(time)
        cs.x, cs.y, cs.vx, cs.vy = (
            tx,
            ty,
            random.uniform(-1.5, 1.5) * mod,
            random.uniform(-2.0, -0.5),
        )
        return cs

    def draw(self, screen, camera, time, soil_grid, biolum_alpha=0):
        if not camera.is_visible((self.x, self.base_y - 100), margin=200):
            return
        if self.development.stage == "seed":
            pos = camera.apply((self.x, self.base_y - 6))
            pygame.draw.circle(screen, (140, 180, 100, 180), pos, 5)
            pygame.draw.circle(screen, (220, 240, 160, 220), pos, 3)
            return
        if self.development.stage == "dormant":
            pos = camera.apply((self.x, self.base_y))
            stub_h = max(4, int(self.development.current_height * 0.3))
            stub_top = camera.apply((self.x, self.base_y - stub_h))
            pygame.draw.line(screen, (80, 65, 50), pos, stub_top, 3)
            return

        c, h = self.get_organic_color(), self.development.current_height
        draws = {
            "seagrass": self.draw_seagrass,
            "kelp": self.draw_kelp,
            "algae": self.draw_algae,
            "red_seaweed": self.draw_red_seaweed,
            "lily_pad": self.draw_lily_pad,
            "tube_sponge": self.draw_tube_sponge,
            "fan_coral": self.draw_fan_coral,
            "anemone": self.draw_anemone,
        }
        draws.get(self.plant_type, self.draw_kelp)(screen, camera, time, c, h)

        if self.bite_marks:
            for m in self.bite_marks:
                sp = camera.apply((self.x + m["ox"], self.base_y + m["oy"]))
                a = max(0, min(255, int(255 * (m["life"] / GRAZING_VISUAL_DURATION))))
                bs = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(bs, (90, 60, 40, a), (6, 6), 4)
                screen.blit(bs, (int(sp[0]) - 6, int(sp[1]) - 6))

        if biolum_alpha > 10 and self.development.is_mature:
            self._draw_bioluminescence(screen, camera, time, biolum_alpha)
        if self.development.is_flowering and self.plant_type != "lily_pad":
            self._draw_flowering(screen, camera, time)
        for p in self.decomposition_particles:
            sp = camera.apply((p["x"], p["y"]))
            pygame.draw.circle(screen, (100, 80, 50), (int(sp[0]), int(sp[1])), 2)

    def _draw_bioluminescence(self, screen, camera, time, alpha):
        if self.plant_type == "red_seaweed":
            i = RED_SEAWEED_GLOW_INTENSITY * self.traits.get("glow_intensity", 1.0)
            st = camera.apply(self.get_tip_position(time))
            gr = int(25 * i)
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 80, 80, int(alpha * i)), (gr, gr), gr)
            screen.blit(gs, (int(st[0]) - gr, int(st[1]) - gr))
        elif self.plant_type == "anemone":
            p = (
                math.sin(
                    time * ANEMONE_PULSE_SPEED * self.traits.get("pulse_speed", 1.0)
                )
                + 1
            ) / 2
            sp, gr = camera.apply((self.x, self.base_y)), int(20 + p * 15)
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                gs, (*ANEMONE_GLOW_COLOR, int(alpha * (0.5 + p * 0.5))), (gr, gr), gr
            )
            screen.blit(gs, (int(sp[0]) - gr, int(sp[1]) - gr))

    def _draw_flowering(self, screen, camera, time):
        st = camera.apply(self.get_tip_position(time))
        r = 6 + (math.sin(time * 5) + 1) * 2.5
        pygame.draw.circle(screen, (255, 255, 150), (int(st[0]), int(st[1])), int(r))

    def get_organic_color(self):
        er = min(1.0, max(0.2, self.development.energy / 10.0))
        if self.plant_type in ("red_seaweed", "lily_pad"):
            f = 0.7 + 0.3 * er
            r, g, b = (
                int(self.base_color[0] * f),
                int(self.base_color[1] * f),
                int(self.base_color[2] * f),
            )
        else:
            dr = 1.0 - 0.3 * (
                (self.base_y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y)
            )
            er = 0.6 + 0.4 * er
            r, g, b = (
                int(self.base_color[0] * er * dr),
                int(self.base_color[1] * er * dr),
                int(self.base_color[2] * er * dr),
            )
        if self.development.stage == "decomposing":
            return (80, 70, 50)
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    def draw_seagrass(self, screen, camera, time, c, h):
        v = max(1, min(int(self.development.visible_blades), len(self.blade_data)))
        for i in range(v):
            d, points = self.blade_data[i], []
            bh = h * d["h_mult"]
            for s in range(9):
                p = s / 8
                sw = (
                    math.sin(
                        time * self.sway_speed * d["speed"]
                        + self.phase_offset
                        + d["phase"]
                        + s * 0.2
                    )
                    * self.sway_amplitude
                    * (p**1.8)
                )
                points.append(
                    camera.apply((self.x + d["offset"] + sw, self.base_y - bh * p))
                )
            for s in range(len(points) - 1):
                pygame.draw.line(
                    screen,
                    c,
                    points[s],
                    points[s + 1],
                    max(1, int(self.width * (1.0 - s / len(points)))),
                )

    def draw_kelp(self, screen, camera, time, c, h):
        seg = max(2, int(self.development.current_segments))
        pts, sh = [camera.apply((self.x, self.base_y))], h / seg
        for i in range(1, seg + 1):
            p = i / seg
            sw = (
                math.sin(time * self.sway_speed + self.phase_offset + i * 0.3)
                * self.sway_amplitude
                * (p**1.5)
            )
            pts.append(camera.apply((self.x + sw, self.base_y - sh * i)))
            if i > 2 and i % 3 == 0:
                ld = 1 if i % 6 == 0 else -1
                ls = pygame.Surface((24, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(ls, (*c, 180), (0, 0, 24, 12))
                rot = pygame.transform.rotate(ls, ld * 45)
                sx, sy = pts[-1]
                screen.blit(rot, (sx + ld * 12 - 12, sy - 6))
        for i in range(len(pts) - 1):
            pygame.draw.line(
                screen,
                c,
                pts[i],
                pts[i + 1],
                max(1, int(self.width * (1.1 - i / len(pts)))),
            )

    def draw_algae(self, screen, camera, time, c, h):
        pts, sh = [camera.apply((self.x, self.base_y))], h / 6
        for i in range(1, 7):
            p = i / 6
            sw = (
                math.sin(time * self.sway_speed + self.phase_offset + i * 0.5)
                * self.sway_amplitude
                * p
            )
            pts.append(camera.apply((self.x + sw, self.base_y - sh * i)))
        for i in range(len(pts) - 1):
            pygame.draw.line(
                screen,
                c,
                pts[i],
                pts[i + 1],
                max(2, int((self.width + 2) * (1.0 - i / len(pts) * 0.5))),
            )
        pygame.draw.circle(
            screen, c, (int(pts[-1][0]), int(pts[-1][1])), self.width + 2
        )

    def draw_red_seaweed(self, screen, camera, time, c, h):
        seg = max(2, int(self.development.current_segments))
        for b in range(3):
            pts, sh = [camera.apply((self.x + (b - 1) * 15, self.base_y))], h / seg
            for i in range(1, seg + 1):
                p = i / seg
                sw = (
                    (
                        math.sin(
                            time * self.sway_speed
                            + self.phase_offset
                            + b * 0.5
                            + i * 0.25
                        )
                        + math.sin(
                            time * self.sway_speed * 1.3 + self.phase_offset + i * 0.4
                        )
                        * 0.3
                    )
                    * self.sway_amplitude
                    * (p**1.2)
                )
                pts.append(
                    camera.apply((self.x + (b - 1) * 15 + sw, self.base_y - sh * i))
                )
            for i in range(len(pts) - 1):
                pygame.draw.line(
                    screen,
                    c,
                    pts[i],
                    pts[i + 1],
                    max(2, int(self.width * (1.3 - i / len(pts) * 0.8))),
                )

    def draw_lily_pad(self, screen, camera, time, c, h):
        sp = camera.apply(
            (self.x, WATER_LINE_Y + math.sin(time * 0.5 + self.phase_offset) * 2)
        )
        st = camera.apply((self.x, min(WATER_LINE_Y + 20, self.base_y)))
        pygame.draw.line(
            screen, (100, 80, 60), (int(sp[0]), int(sp[1])), (int(st[0]), int(st[1])), 2
        )
        pr = self.pad_radius
        ps = pygame.Surface((pr * 2 + 4, pr * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*c, 230), (pr + 2, pr + 2), pr)
        pygame.draw.polygon(
            ps, (0, 0, 0, 0), [(pr + 2, 2), (pr - 6, 12), (pr + 10, 12)]
        )
        screen.blit(ps, (int(sp[0]) - pr - 2, int(sp[1]) - pr - 2))
        if self.flower_open:
            pygame.draw.circle(
                screen,
                LILY_PAD_FLOWER_COLOR,
                (int(sp[0]), int(sp[1]) - 5),
                int(8 + (math.sin(time * 2) + 1) * 1.5),
            )

    def draw_tube_sponge(self, screen, camera, time, c, h):
        seg_h = h / max(1, TUBE_SPONGE_SEGMENTS)
        for i in range(TUBE_SPONGE_SEGMENTS + 1):
            p = i / TUBE_SPONGE_SEGMENTS
            y = self.base_y - seg_h * i
            w = self.width * (1.0 - p * 0.2)
            rect = pygame.Rect(
                camera.apply((self.x - w / 2, y - seg_h / 2))[0],
                camera.apply((self.x, y))[1] - int(seg_h / 2),
                int(w),
                int(seg_h) + 2,
            )
            pygame.draw.ellipse(
                screen, tuple(int(ch * (1.0 - p * 0.3)) for ch in c), rect
            )
        tp = camera.apply((self.x, self.base_y - h))
        pygame.draw.ellipse(
            screen,
            (40, 35, 30),
            (tp[0] - self.width * 0.3, tp[1] - 4, self.width * 0.6, 8),
        )

    def draw_fan_coral(self, screen, camera, time, c, h):
        if self._branch_dirty or not self.branches:
            self._generate_branches()
        sw = math.sin(time * self.sway_speed + self.phase_offset) * self.sway_amplitude
        for b in self.branches:
            sf = max(0, (4 - b["level"]) / 4)
            s, e = camera.apply((b["start"][0] + sw * sf, b["start"][1])), camera.apply(
                (b["end"][0] + sw * sf, b["end"][1])
            )
            pygame.draw.line(screen, c, s, e, max(1, int(b["width"])))

    def draw_anemone(self, screen, camera, time, c, h):
        bp = camera.apply((self.x, self.base_y))
        sh = h * 0.3
        pygame.draw.ellipse(
            screen, c, (bp[0] - self.width, bp[1] - int(sh), self.width * 2, int(sh))
        )
        pu = (
            math.sin(time * ANEMONE_PULSE_SPEED * self.traits.get("pulse_speed", 1.0))
            + 1
        ) / 2
        for t in self.tentacles:
            pts, th = [bp], h * t["length"]
            for i in range(1, 7):
                p = i / 6
                ang = (
                    t["base_angle"]
                    + t["curvature"] * p
                    + (
                        math.sin(time * self.sway_speed + t["phase"] + i * 0.4)
                        * self.sway_amplitude
                        * 0.02
                    )
                )
                pts.append(
                    camera.apply(
                        (
                            self.x + math.cos(ang) * (th * p * (1 + pu * 0.3)),
                            self.base_y - sh - th * p,
                        )
                    )
                )
            for i in range(len(pts) - 1):
                pygame.draw.line(
                    screen,
                    c,
                    pts[i],
                    pts[i + 1],
                    max(1, int(self.width * (1 - i / len(pts)))),
                )

    def get_tip_position(self, time):
        if self.plant_type == "lily_pad":
            return (self.x, WATER_LINE_Y)
        if self.plant_type == "anemone":
            t = self.tentacles[0]
            h = self.development.current_height * t["length"]
            return (self.x + math.cos(t["base_angle"]) * h * 0.5, self.base_y - h)
        sw = (
            math.sin(time * self.sway_speed + self.phase_offset + 3.0)
            * self.sway_amplitude
        )
        return (self.x + sw, self.base_y - self.development.current_height)

    def draw_roots(self, screen, camera, time=0):
        self.root_system.draw(screen, camera, time)


class PlantManager:
    def __init__(self, world):
        self.world, self.plants, self.seeds, self.bubbles, self._renewal_timer = (
            world,
            [],
            [],
            [],
            0.0,
        )

    def spawn_initial_seeds(self):
        sp_w = [
            ("kelp", 15),
            ("seagrass", 20),
            ("algae", 15),
            ("red_seaweed", 12),
            ("lily_pad", 8),
            ("tube_sponge", 10),
            ("fan_coral", 12),
            ("anemone", 15),
        ]
        for _ in range(40):
            self.seeds.append(
                Seed(
                    random.choices([s[0] for s in sp_w], weights=[s[1] for s in sp_w])[
                        0
                    ]
                )
            )
        for pt, _ in sp_w:
            for _ in range(2):
                s = Seed(pt)
                ty = self.world.get_terrain_height(s.x)
                if is_valid_depth(pt, self.world.get_depth_ratio(ty)):
                    p = Plant(s.x, ty, pt, self.world.soil_grid, s.traits, self.world)
                    (
                        p.development.stage,
                        p.development.energy,
                        p.development.current_height,
                    ) = ("seedling", 4.0, p.max_height * 0.4)
                    self.plants.append(p)

    def update(self, dt, time_system=None):
        sg, time = self.world.soil_grid, pygame.time.get_ticks() / 1000.0
        pr = time_system.photosynthesis_rate if time_system else 1.0
        sm = time_system.seed_dispersal_modifier if time_system else 1.0
        si = time_system.season_index if time_system else 0

        if (len(self.plants) + len(self.seeds)) < 12:
            self._renewal_timer += dt
            if self._renewal_timer >= (4.0 if si == 0 else 8.0):
                self._renewal_timer = 0.0
                all_sp = [
                    "kelp",
                    "seagrass",
                    "algae",
                    "red_seaweed",
                    "lily_pad",
                    "tube_sponge",
                    "fan_coral",
                    "anemone",
                ]
                self.seeds.append(Seed(random.choice(all_sp)))

        for s in self.seeds[:]:
            if s.update(dt, self.world, time_system):
                self.seeds.remove(s)
                if len(self.plants) < PLANT_HARD_CAP:
                    ty = self.world.get_terrain_height(s.x)
                    if is_valid_depth(s.plant_type, self.world.get_depth_ratio(ty)):
                        self.plants.append(
                            Plant(s.x, ty, s.plant_type, sg, s.traits, self.world)
                        )

        ps = getattr(self.world, "particle_system", None)
        for p in self.plants[:]:
            if not p.update(dt, sg, pr, si):
                r = p.development.get_decomposition_return()
                c = sg.get_cell_at_pixel(p.x, p.base_y)
                if c:
                    c.nutrient = min(SOIL_MAX_NUTRIENT, c.nutrient + r)
                self.plants.remove(p)
                continue
            if ps and p.development.is_mature:
                p.try_produce_plankton(dt, ps, time)
            if si in (1, 2) and (len(self.plants) + len(self.seeds)) < (
                PLANT_HARD_CAP + SEED_HARD_CAP
            ):
                ns = p.try_produce_seed(time, sm, si)
                if ns and len(self.seeds) < SEED_HARD_CAP:
                    self.seeds.append(ns)
            bc = BUBBLE_CHANCE * (
                3
                if p.plant_type == "tube_sponge"
                else 1.5 if p.plant_type == "anemone" else 1
            )
            if p.development.is_mature and random.random() < bc:
                self.bubbles.append(
                    {
                        "x": p.x + random.uniform(-10, 10),
                        "y": p.base_y - p.development.current_height * 0.9,
                        "vy": random.uniform(-1.0, -0.5),
                        "life": random.uniform(2.0, 4.0),
                        "size": random.randint(2, 5),
                    }
                )

        for b in self.bubbles[:]:
            b["y"] += b["vy"] * 60 * dt
            b["life"] -= dt
            if b["life"] <= 0 or b["y"] < WATER_LINE_Y:
                self.bubbles.remove(b)

    def draw(self, screen, camera, time, time_system=None):
        ba = time_system.get_bioluminescence_alpha() if time_system else 0
        for s in self.seeds:
            s.draw(screen, camera)
        for p in self.plants:
            p.draw_roots(screen, camera, time)
        for p in sorted(self.plants, key=lambda p: p.base_y):
            p.draw(screen, camera, time, self.world.soil_grid, ba)
        for b in self.bubbles:
            pos = camera.apply((b["x"], b["y"]))
            pygame.draw.circle(
                screen,
                (*BUBBLE_COLOR, int(255 * (b["life"] / 4.0))),
                (int(pos[0]), int(pos[1])),
                b["size"],
            )
