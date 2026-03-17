"""Plant system with organic visual rendering, tapered blades, and visible seed production"""

import pygame
import math
import random
from config import (
    SCREEN_HEIGHT,
    WATER_LINE_Y,
    KELP_HEIGHT_MIN,
    KELP_HEIGHT_MAX,
    KELP_SWAY_SPEED,
    KELP_SWAY_AMPLITUDE,
    KELP_COLOR,
    KELP_HIGHLIGHT,
    KELP_WIDTH,
    KELP_DEPTH_MAX,
    SEAGRASS_HEIGHT_MIN,
    SEAGRASS_HEIGHT_MAX,
    SEAGRASS_SWAY_SPEED,
    SEAGRASS_SWAY_AMPLITUDE,
    SEAGRASS_COLOR,
    SEAGRASS_HIGHLIGHT,
    SEAGRASS_WIDTH,
    SEAGRASS_DEPTH_MIN,
    SEAGRASS_DEPTH_MAX,
    ALGAE_HEIGHT_MIN,
    ALGAE_HEIGHT_MAX,
    ALGAE_SWAY_SPEED,
    ALGAE_SWAY_AMPLITUDE,
    ALGAE_COLOR,
    ALGAE_HIGHLIGHT,
    ALGAE_WIDTH,
    ALGAE_DEPTH_MIN,
    RED_SEAWEED_HEIGHT_MIN,
    RED_SEAWEED_HEIGHT_MAX,
    RED_SEAWEED_SWAY_SPEED,
    RED_SEAWEED_SWAY_AMPLITUDE,
    RED_SEAWEED_COLOR,
    RED_SEAWEED_HIGHLIGHT,
    RED_SEAWEED_WIDTH,
    RED_SEAWEED_DEPTH_MIN,
    RED_SEAWEED_DEPTH_MAX,
    RED_SEAWEED_GLOW_INTENSITY,
    LILY_PAD_SIZE_MIN,
    LILY_PAD_SIZE_MAX,
    LILY_PAD_COLOR,
    LILY_PAD_HIGHLIGHT,
    LILY_PAD_FLOWER_COLOR,
    LILY_PAD_DEPTH_MAX,
    LILY_PAD_ROOT_DEPTH,
    LILY_PAD_SPREAD_RATE,
    TUBE_SPONGE_HEIGHT_MIN,
    TUBE_SPONGE_HEIGHT_MAX,
    TUBE_SPONGE_SEGMENTS,
    TUBE_SPONGE_COLOR,
    TUBE_SPONGE_HIGHLIGHT,
    TUBE_SPONGE_WIDTH,
    TUBE_SPONGE_DEPTH_MIN,
    TUBE_SPONGE_DEPTH_MAX,
    TUBE_SPONGE_FILTER_RATE,
    FAN_CORAL_HEIGHT_MIN,
    FAN_CORAL_HEIGHT_MAX,
    FAN_CORAL_SEGMENTS,
    FAN_CORAL_SWAY_SPEED,
    FAN_CORAL_SWAY_AMPLITUDE,
    FAN_CORAL_COLOR,
    FAN_CORAL_HIGHLIGHT,
    FAN_CORAL_WIDTH,
    FAN_CORAL_DEPTH_MIN,
    FAN_CORAL_DEPTH_MAX,
    FAN_CORAL_BRANCH_FACTOR,
    ANEMONE_HEIGHT_MIN,
    ANEMONE_HEIGHT_MAX,
    ANEMONE_TENTACLES,
    ANEMONE_SWAY_SPEED,
    ANEMONE_COLOR,
    ANEMONE_GLOW_COLOR,
    ANEMONE_HIGHLIGHT,
    ANEMONE_WIDTH,
    ANEMONE_DEPTH_MIN,
    ANEMONE_DEPTH_MAX,
    ANEMONE_PULSE_SPEED,
    ANEMONE_ATTRACT_RADIUS,
    ROOT_BASE_GROWTH_RATE,
    BUBBLE_CHANCE,
    BUBBLE_COLOR,
    SOIL_MAX_NUTRIENT,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    PLANT_COVER_RADIUS,
    PLANT_GRAZE_ENERGY_GAIN,
    PLANT_GRAZE_DAMAGE,
    GRAZING_VISUAL_DURATION,
    PLANKTON_PER_PLANT_CHANCE,
    PLANKTON_HARD_CAP,
    PLANT_HARD_CAP,
    SEED_HARD_CAP,
)
from roots import RootSystem
from seeds import Seed
from plant_development import PlantDevelopment

# Map each plant type to its dominant color for plankton tinting
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
        self.x = x
        self.base_y = base_y
        self.plant_type = plant_type
        self.traits = seed_traits
        self.world = world
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
            # Sync PlantDevelopment so visible_blades never indexes beyond blade_data
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
            self.flower_open = False
            self.flower_timer = random.uniform(0, 10)
        elif plant_type == "fan_coral":
            self.branches = []
            self._branch_dirty = True
            self._last_branch_height = 0
        elif plant_type == "anemone":
            self._init_tentacles()
        elif plant_type == "tube_sponge":
            self._init_pores()

        self.floating_leaves = []
        self.decomposition_particles = []

        self.biomass = 12.0 + random.uniform(0, 8)
        self.graze_timer = 0.0
        self.bite_marks = []

        # Per-plant plankton spawn timer (staggered so plants don't all fire together)
        self._plankton_timer = random.uniform(
            0, 1.0 / max(PLANKTON_PER_PLANT_CHANCE, 0.001)
        )

    # ── Species init ───────────────────────────────────────────────────────────

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
        base_min, base_max = p["h"]
        self.max_height = (
            0
            if self.plant_type == "lily_pad"
            else int(
                base_min + (base_max - base_min) * self.traits["max_height_factor"]
            )
        )
        self.sway_speed = p["sw"]
        self.sway_amplitude = p["sa"]
        self.base_color = p["bc"]
        self.highlight_color = p["hl"]
        self.width = p["w"]

    def _generate_branches(self):
        height = self.development.current_height
        self.branches = []

        def add_branch(x, y, angle, length, width, level):
            if level <= 0 or length < 5:
                return
            end_x = x + math.cos(angle) * length
            end_y = y + math.sin(angle) * length
            self.branches.append(
                {"start": (x, y), "end": (end_x, end_y), "width": width, "level": level}
            )
            if level > 1:
                off = (
                    0.4
                    * FAN_CORAL_BRANCH_FACTOR
                    * self.traits.get("branch_density", 1.0)
                )
                nl, nw = length * 0.7, width * 0.6
                add_branch(end_x, end_y, angle - off, nl, nw, level - 1)
                add_branch(end_x, end_y, angle + off, nl, nw, level - 1)

        add_branch(self.x, self.base_y, -math.pi / 2, height * 0.3, self.width, 4)
        self._last_branch_height = height
        self._branch_dirty = False

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

    # ── Fish-Plant Interaction ──────────────────────────────────────────────────

    def graze(self, amount):
        if self.biomass <= 0.5:
            return 0.0
        damage = min(self.biomass, amount * PLANT_GRAZE_DAMAGE)
        self.biomass -= damage
        self.graze_timer = GRAZING_VISUAL_DURATION
        self.bite_marks.append(
            {
                "ox": random.uniform(-self.width, self.width),
                "oy": -random.uniform(0, self.development.current_height * 0.7),
                "life": GRAZING_VISUAL_DURATION + random.uniform(0, 1),
            }
        )
        return PLANT_GRAZE_ENERGY_GAIN * (damage / PLANT_GRAZE_DAMAGE)

    # ── Plankton production ────────────────────────────────────────────────────

    def try_produce_plankton(self, dt, particle_system, time):
        if not self.development.is_mature:
            return False
        self._plankton_timer -= dt
        if self._plankton_timer > 0:
            return False

        self._plankton_timer = (1.0 / PLANKTON_PER_PLANT_CHANCE) + random.uniform(-2, 2)

        tip_x, tip_y = self.get_tip_position(time)
        color_hint = _PLANT_PLANKTON_COLOR.get(self.plant_type)
        particle_system.spawn_plankton_at(tip_x, tip_y, color_hint=color_hint)
        return True

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt, soil_grid, photosynthesis_rate=1.0, season_index=0):
        self.wind_phase = self.wind_phase + dt * 0.4

        if self.graze_timer > 0:
            self.graze_timer -= dt
        for mark in self.bite_marks[:]:
            mark["life"] -= dt
            if mark["life"] <= 0:
                self.bite_marks.remove(mark)

        if self.plant_type == "lily_pad":
            self.flower_timer += dt
            self.flower_open = (math.sin(self.flower_timer * 0.5) + 1) > 1.0

        base_mult = self.traits["root_aggression"]
        if self.plant_type == "lily_pad":
            base_mult *= LILY_PAD_SPREAD_RATE
        need_mult = self.development.get_root_growth_multiplier(
            self.development.energy, self.development.current_height
        )
        # Roots don't grow in winter or when dormant/seed
        if self.development.stage not in ("seed", "dormant") and season_index != 3:
            self.root_system.adjust_growth_rate(
                ROOT_BASE_GROWTH_RATE * base_mult * need_mult
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

        if self.plant_type == "fan_coral":
            if abs(self.development.current_height - self._last_branch_height) > 5:
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
        # Update floating leaves more efficiently
        self.floating_leaves = [
            {
                "x": leaf["x"] + leaf["vx"],
                "y": leaf["y"] + leaf["vy"],
                "vx": leaf["vx"],
                "vy": leaf["vy"],
                "life": leaf["life"] - dt,
                "rot": leaf["rot"] + leaf["spin"] * dt,
                "spin": leaf["spin"],
            }
            for leaf in self.floating_leaves
            if leaf["life"] > dt  # Only keep leaves that will survive this frame
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
        # Update decomposition particles more efficiently
        self.decomposition_particles = [
            {
                "x": p["x"] + p["vx"],
                "y": p["y"] + p["vy"],
                "vx": p["vx"],
                "vy": p["vy"],
                "life": p["life"] - dt,
            }
            for p in self.decomposition_particles
            if p["life"] > dt  # Only keep particles that will survive this frame
        ]

        return alive

    # ── Seed production ────────────────────────────────────────────────────────

    def try_produce_seed(self, time, seed_dispersal_modifier, season_index):
        if not self.development.can_produce_seed(seed_dispersal_modifier, season_index):
            return None

        child_seed = Seed(self.plant_type)
        child_seed.traits = child_seed.mutate(self.traits)
        tip_x, tip_y = self.get_tip_position(time)
        child_seed.x = tip_x
        child_seed.y = tip_y
        child_seed.vx = random.uniform(-1.5, 1.5) * seed_dispersal_modifier
        child_seed.vy = random.uniform(-2.0, -0.5)
        return child_seed

    # ── Drawing ────────────────────────────────────────────────────────────────

    def draw(self, screen, camera, time, soil_grid, biolum_alpha=0):
        if not camera.is_visible((self.x, self.base_y - 100), margin=200):
            return

        if self.development.stage == "seed":
            pos = camera.apply((self.x, self.base_y - 6))
            pygame.draw.circle(screen, (140, 180, 100, 180), pos, 5)
            pygame.draw.circle(screen, (220, 240, 160, 220), pos, 3)
            return

        # Dormant plants draw as a small withered stub
        if self.development.stage == "dormant":
            pos = camera.apply((self.x, self.base_y))
            stub_h = max(4, int(self.development.current_height * 0.3))
            stub_top = camera.apply((self.x, self.base_y - stub_h))
            pygame.draw.line(screen, (80, 65, 50), pos, stub_top, 3)
            pygame.draw.circle(
                screen, (70, 60, 45), (int(stub_top[0]), int(stub_top[1])), 3
            )
            return

        color = self.get_organic_color()
        height = self.development.current_height

        draw_methods = {
            "seagrass": self.draw_seagrass,
            "kelp": self.draw_kelp,
            "algae": self.draw_algae,
            "red_seaweed": self.draw_red_seaweed,
            "lily_pad": self.draw_lily_pad,
            "tube_sponge": self.draw_tube_sponge,
            "fan_coral": self.draw_fan_coral,
            "anemone": self.draw_anemone,
        }
        draw_methods.get(self.plant_type, self.draw_kelp)(
            screen, camera, time, color, height
        )

        if self.bite_marks:
            for mark in self.bite_marks:
                mx = self.x + mark["ox"]
                my = self.base_y + mark["oy"]
                screen_pos = camera.apply((mx, my))
                alpha = int(255 * (mark["life"] / GRAZING_VISUAL_DURATION))
                # Use surface with SRCALPHA for proper alpha blending
                bite_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(bite_surf, (90, 60, 40, alpha), (6, 6), 4)
                screen.blit(bite_surf, (int(screen_pos[0]) - 6, int(screen_pos[1]) - 6))

        if biolum_alpha > 10 and self.development.is_mature:
            self._draw_bioluminescence(screen, camera, time, biolum_alpha)

        if self.development.is_flowering and self.plant_type != "lily_pad":
            self._draw_flowering(screen, camera, time)

        for p in self.decomposition_particles:
            sp = camera.apply((p["x"], p["y"]))
            pygame.draw.circle(screen, (100, 80, 50), (int(sp[0]), int(sp[1])), 2)

    def _draw_bioluminescence(self, screen, camera, time, biolum_alpha):
        if self.plant_type == "red_seaweed":
            intensity = RED_SEAWEED_GLOW_INTENSITY * self.traits.get(
                "glow_intensity", 1.0
            )
            screen_tip = camera.apply(self.get_tip_position(time))
            glow_r = int(25 * intensity)
            gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                gs,
                (255, 80, 80, int(biolum_alpha * intensity)),
                (glow_r, glow_r),
                glow_r,
            )
            screen.blit(gs, (int(screen_tip[0]) - glow_r, int(screen_tip[1]) - glow_r))
        elif self.plant_type == "anemone":
            pulse = (
                math.sin(
                    time * ANEMONE_PULSE_SPEED * self.traits.get("pulse_speed", 1.0)
                )
                + 1
            ) / 2
            sp = camera.apply((self.x, self.base_y))
            gr = int(20 + pulse * 15)
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                gs,
                (*ANEMONE_GLOW_COLOR, int(biolum_alpha * (0.5 + pulse * 0.5))),
                (gr, gr),
                gr,
            )
            screen.blit(gs, (int(sp[0]) - gr, int(sp[1]) - gr))
        elif self.plant_type == "fan_coral":
            screen_tip = camera.apply(self.get_tip_position(time))
            gs = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 150, 200, biolum_alpha // 2), (15, 15), 12)
            screen.blit(gs, (int(screen_tip[0]) - 15, int(screen_tip[1]) - 15))

    def _draw_flowering(self, screen, camera, time):
        screen_tip = camera.apply(self.get_tip_position(time))
        pulse = (math.sin(time * 5) + 1) * 0.5
        radius = 6 + pulse * 4
        pygame.draw.circle(
            screen,
            (255, 255, 150),
            (int(screen_tip[0]), int(screen_tip[1])),
            int(radius),
        )
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(screen_tip[0]), int(screen_tip[1])),
            int(radius + 2),
            1,
        )

    def get_organic_color(self):
        depth_ratio = (self.base_y - WATER_LINE_Y) / (WORLD_HEIGHT - WATER_LINE_Y)
        energy_ratio = min(1.0, max(0.2, self.development.energy / 10.0))

        if self.plant_type in ("red_seaweed", "lily_pad"):
            f = 0.7 + 0.3 * energy_ratio
            r, g, b = (
                int(self.base_color[0] * f),
                int(self.base_color[1] * f),
                int(self.base_color[2] * f),
            )
        else:
            dr = 1.0 - 0.3 * depth_ratio
            er = 0.6 + 0.4 * energy_ratio
            r = int(self.base_color[0] * er * dr)
            g = int(self.base_color[1] * er * dr)
            b = int(self.base_color[2] * er * dr)

        if self.development.stage == "decomposing":
            return (80, 70, 50)
        if self.development.stage == "dying":
            return (int(r * 0.7), int(g * 0.8), int(b * 0.5))
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    # ── Species draw methods ───────────────────────────────────────────────────

    def draw_seagrass(self, screen, camera, time, color, height):
        visible = max(
            1, min(int(self.development.visible_blades), len(self.blade_data))
        )
        for i in range(visible):
            data = self.blade_data[i]
            points = []
            bh = height * data["h_mult"]
            for s in range(9):
                prog = s / 8
                sway_factor = max(0, prog**1.8)
                sway = (
                    math.sin(
                        time * self.sway_speed * data["speed"]
                        + self.phase_offset
                        + data["phase"]
                        + s * 0.2
                    )
                    * self.sway_amplitude
                    * sway_factor
                )
                points.append(
                    camera.apply(
                        (self.x + data["offset"] + sway, self.base_y - bh * prog)
                    )
                )
            for s in range(len(points) - 1):
                w = max(1, int(self.width * (1.0 - s / len(points))))
                pygame.draw.line(screen, color, points[s], points[s + 1], w)

    def draw_kelp(self, screen, camera, time, color, height):
        segments = max(2, int(self.development.current_segments))
        points = [camera.apply((self.x, self.base_y))]
        seg_h = height / segments
        for i in range(1, segments + 1):
            prog = i / segments
            sway_factor = max(0, prog**1.5)
            sway = (
                math.sin(time * self.sway_speed + self.phase_offset + i * 0.3)
                * self.sway_amplitude
                * sway_factor
            )
            points.append(camera.apply((self.x + sway, self.base_y - seg_h * i)))
            if i > 2 and i % 3 == 0:
                leaf_dir = 1 if i % 6 == 0 else -1
                leaf_surf = pygame.Surface((24, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(leaf_surf, (*color, 180), (0, 0, 24, 12))
                rotated = pygame.transform.rotate(leaf_surf, leaf_dir * 45)
                sx, sy = points[-1]
                screen.blit(rotated, (sx + leaf_dir * 12 - 12, sy - 6))
        for i in range(len(points) - 1):
            thickness = max(1, int(self.width * (1.1 - i / len(points))))
            pygame.draw.line(screen, color, points[i], points[i + 1], thickness)

    def draw_algae(self, screen, camera, time, color, height):
        points = [camera.apply((self.x, self.base_y))]
        seg_h = height / 6
        for i in range(1, 7):
            prog = i / 6
            sway_factor = max(0, prog)
            sway = (
                math.sin(time * self.sway_speed + self.phase_offset + i * 0.5)
                * self.sway_amplitude
                * sway_factor
            )
            points.append(camera.apply((self.x + sway, self.base_y - seg_h * i)))
        for i in range(len(points) - 1):
            thickness = max(2, int((self.width + 2) * (1.0 - i / len(points) * 0.5)))
            pygame.draw.line(screen, color, points[i], points[i + 1], thickness)
        tip = points[-1]
        pygame.draw.circle(screen, color, (int(tip[0]), int(tip[1])), self.width + 2)

    def draw_red_seaweed(self, screen, camera, time, color, height):
        segments = max(2, int(self.development.current_segments))
        for blade in range(3):
            offset = (blade - 1) * 15
            points = [camera.apply((self.x + offset, self.base_y))]
            seg_h = height / segments
            for i in range(1, segments + 1):
                prog = i / segments
                base_sw = (
                    math.sin(
                        time * self.sway_speed
                        + self.phase_offset
                        + blade * 0.5
                        + i * 0.25
                    )
                    * self.sway_amplitude
                )
                sec_sw = (
                    math.sin(time * self.sway_speed * 1.3 + self.phase_offset + i * 0.4)
                    * self.sway_amplitude
                    * 0.3
                )
                sway_factor = max(0, prog**1.2)
                sway = (base_sw + sec_sw) * sway_factor
                points.append(
                    camera.apply((self.x + offset + sway, self.base_y - seg_h * i))
                )
            for i in range(len(points) - 1):
                thickness = max(2, int(self.width * (1.3 - i / len(points) * 0.8)))
                pygame.draw.line(screen, color, points[i], points[i + 1], thickness)
            for i in range(0, len(points) - 1, 2):
                pygame.draw.line(
                    screen, self.highlight_color, points[i], points[i + 1], 2
                )

    def draw_lily_pad(self, screen, camera, time, color, height):
        sp = camera.apply(
            (self.x, WATER_LINE_Y + math.sin(time * 0.5 + self.phase_offset) * 2)
        )
        stem_e = camera.apply((self.x, min(WATER_LINE_Y + 20, self.base_y)))
        pygame.draw.line(
            screen,
            (100, 80, 60),
            (int(sp[0]), int(sp[1])),
            (int(stem_e[0]), int(stem_e[1])),
            2,
        )
        pr = self.pad_radius
        pad_surf = pygame.Surface((pr * 2 + 4, pr * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(pad_surf, (*color, 230), (pr + 2, pr + 2), pr)
        pygame.draw.polygon(
            pad_surf, (0, 0, 0, 0), [(pr + 2, 2), (pr - 6, 12), (pr + 10, 12)]
        )
        vc = tuple(max(0, c - 30) for c in color)
        for angle in [0.3, 0.6, 0.9, 1.2]:
            vx = pr + 2 + math.cos(angle) * (pr * 0.8)
            vy = pr + 2 + math.sin(angle) * (pr * 0.8)
            pygame.draw.line(
                pad_surf, (*vc, 150), (pr + 2, pr + 2), (int(vx), int(vy)), 1
            )
        screen.blit(pad_surf, (int(sp[0]) - pr - 2, int(sp[1]) - pr - 2))
        if self.flower_open:
            pulse = (math.sin(time * 2) + 1) / 2
            fr = int(8 + pulse * 3)
            pygame.draw.circle(
                screen, LILY_PAD_FLOWER_COLOR, (int(sp[0]), int(sp[1]) - 5), fr
            )
            for i in range(5):
                a = (i / 5) * math.pi * 2 + time
                px = sp[0] + math.cos(a) * (fr + 3)
                py = sp[1] - 5 + math.sin(a) * (fr + 3)
                pygame.draw.circle(screen, (255, 220, 240), (int(px), int(py)), 4)

    def draw_tube_sponge(self, screen, camera, time, color, height):
        segments = TUBE_SPONGE_SEGMENTS
        seg_h = height / max(1, segments)
        for i in range(segments + 1):
            prog = i / segments
            y = self.base_y - seg_h * i
            screen_y = camera.apply((self.x, y))[1]
            w = self.width * (1.0 - prog * 0.2)
            rect = pygame.Rect(
                camera.apply((self.x - w / 2, y - seg_h / 2))[0],
                screen_y - int(seg_h / 2),
                int(w),
                int(seg_h) + 2,
            )
            shade = 1.0 - prog * 0.3
            sc = tuple(int(c * shade) for c in color)
            pygame.draw.ellipse(screen, sc, rect)
            for pore in self.pores:
                if abs(pore["y_offset"] - height * prog) < seg_h:
                    px = self.x + math.cos(pore["angle"] + time * 0.5) * (w * 0.4)
                    pore_pos = camera.apply((px, y))
                    pygame.draw.circle(
                        screen,
                        tuple(max(0, c - 40) for c in sc),
                        (int(pore_pos[0]), int(pore_pos[1])),
                        int(pore["size"]),
                    )
        top_pos = camera.apply((self.x, self.base_y - height))
        pygame.draw.ellipse(
            screen,
            (40, 35, 30),
            (top_pos[0] - self.width * 0.3, top_pos[1] - 4, self.width * 0.6, 8),
        )

    def draw_fan_coral(self, screen, camera, time, color, height):
        if self._branch_dirty or not self.branches:
            self._generate_branches()
        sway = (
            math.sin(time * self.sway_speed + self.phase_offset) * self.sway_amplitude
        )

        swayed_positions = {}

        for branch in self.branches:
            sway_factor = max(0, (4 - branch["level"]) / 4)

            if branch["start"] in swayed_positions:
                swayed_start = swayed_positions[branch["start"]]
            else:
                swayed_start = (
                    branch["start"][0] + sway * sway_factor,
                    branch["start"][1],
                )
                swayed_positions[branch["start"]] = swayed_start

            swayed_end = (branch["end"][0] + sway * sway_factor, branch["end"][1])
            swayed_positions[branch["end"]] = swayed_end

            start = camera.apply(swayed_start)
            end = camera.apply(swayed_end)

            tip_t = 1 - branch["level"] / 4
            bc = tuple(
                int(c + (self.highlight_color[i] - c) * tip_t * 0.5)
                for i, c in enumerate(color)
            )
            pygame.draw.line(screen, bc, start, end, max(1, int(branch["width"])))
            if branch["level"] == 1:
                pygame.draw.circle(
                    screen, self.highlight_color, (int(end[0]), int(end[1])), 2
                )

    def draw_anemone(self, screen, camera, time, color, height):
        base_pos = camera.apply((self.x, self.base_y))
        stalk_h = height * 0.3
        pygame.draw.ellipse(
            screen,
            color,
            (
                base_pos[0] - self.width,
                base_pos[1] - int(stalk_h),
                self.width * 2,
                int(stalk_h),
            ),
        )
        pulse = (
            math.sin(time * ANEMONE_PULSE_SPEED * self.traits.get("pulse_speed", 1.0))
            + 1
        ) / 2
        for tentacle in self.tentacles:
            points = [base_pos]
            t_h = height * tentacle["length"]
            for i in range(1, 7):
                prog = i / 6
                wave = (
                    math.sin(time * self.sway_speed + tentacle["phase"] + i * 0.4)
                    * self.sway_amplitude
                    * max(0, prog)
                )
                exp = 1 + pulse * 0.3
                ang = (
                    tentacle["base_angle"] + tentacle["curvature"] * prog + wave * 0.02
                )
                tx = self.x + math.cos(ang) * (t_h * prog * exp)
                ty = self.base_y - stalk_h - t_h * prog
                points.append(camera.apply((tx, ty)))
            for i in range(len(points) - 1):
                thickness = max(1, int(self.width * (1 - i / len(points))))
                ga = int(255 * pulse) if i > len(points) - 3 else 255
                tc = (
                    min(255, color[0] + ga // 3),
                    min(255, color[1] + ga // 3),
                    min(255, color[2] + ga // 2),
                )
                pygame.draw.line(screen, tc, points[i], points[i + 1], thickness)

    def get_tip_position(self, time):
        if self.plant_type == "lily_pad":
            return (self.x, WATER_LINE_Y)
        if self.plant_type == "anemone":
            t = self.tentacles[0]
            h = self.development.current_height * t["length"]
            return (self.x + math.cos(t["base_angle"]) * h * 0.5, self.base_y - h)
        sway = (
            math.sin(time * self.sway_speed + self.phase_offset + 3.0)
            * self.sway_amplitude
        )
        return (self.x + sway, self.base_y - self.development.current_height)

    def draw_roots(self, screen, camera, time=0):
        self.root_system.draw(screen, camera, time)


# ── PlantManager ───────────────────────────────────────────────────────────────


class PlantManager:
    def __init__(self, world):
        self.world = world
        self.plants = []
        self.seeds = []
        self.bubbles = []
        self._renewal_timer = 0.0

    def spawn_initial_seeds(self):
        """Spawn a generous initial seed bank and a handful of established plants."""
        species_weights = [
            ("kelp", 15),
            ("seagrass", 20),
            ("algae", 15),
            ("red_seaweed", 12),
            ("lily_pad", 8),
            ("tube_sponge", 10),
            ("fan_coral", 12),
            ("anemone", 15),
        ]
        # More initial seeds — 40 instead of 30
        for _ in range(40):
            pt = random.choices(
                [s[0] for s in species_weights], weights=[s[1] for s in species_weights]
            )[0]
            self.seeds.append(Seed(pt))

        # Also spawn a small number of pre-established plants so the world
        # never starts completely empty while seeds are waiting to germinate.
        soil_grid = self.world.soil_grid
        for pt, _ in species_weights:
            for _ in range(2):
                seed = Seed(pt)
                terrain_y = self.world.get_terrain_height(seed.x)
                depth_ratio = self.world.get_depth_ratio(terrain_y)
                if _is_valid_depth(pt, depth_ratio):
                    plant = Plant(
                        seed.x, terrain_y, pt, soil_grid, seed.traits, self.world
                    )
                    # Fast-forward to seedling/mature stage so the world looks alive
                    plant.development.stage = "seedling"
                    plant.development.energy = 4.0
                    plant.development.current_height = plant.max_height * 0.4
                    self.plants.append(plant)

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, dt, time_system=None):
        soil_grid = self.world.soil_grid
        time = pygame.time.get_ticks() / 1000.0
        photo_rate = time_system.photosynthesis_rate if time_system else 1.0
        seed_mod = time_system.seed_dispersal_modifier if time_system else 1.0
        season_idx = time_system.season_index if time_system else 0

        n_plants = len(self.plants)
        n_seeds = len(self.seeds)
        total = n_plants + n_seeds

        # ── Emergency renewal: inject seeds whenever the ecosystem is critically low ──
        # Allow renewal in any non-summer season (seeds wait out winter safely)
        RENEWAL_THRESHOLD = 12
        if total < RENEWAL_THRESHOLD:
            self._renewal_timer += dt
            # Inject faster in Spring, slower other seasons
            renewal_interval = 4.0 if season_idx == 0 else 8.0
            if self._renewal_timer >= renewal_interval:
                self._renewal_timer = 0.0
                species_counts = {}
                for p in self.plants:
                    species_counts[p.plant_type] = (
                        species_counts.get(p.plant_type, 0) + 1
                    )
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
                # Weight toward under-represented species
                weights = [max(1, 5 - species_counts.get(s, 0)) for s in all_sp]
                new_seed = Seed(random.choices(all_sp, weights=weights)[0])
                self.seeds.append(new_seed)
                n_seeds += 1
                total += 1
        else:
            self._renewal_timer = 0.0

        # If critically low AND in Spring, also directly spawn a plant to jumpstart recovery
        if n_plants < 5 and season_idx == 0 and random.random() < 0.005 * dt * 60:
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
            pt = random.choice(all_sp)
            x = random.uniform(100, WORLD_WIDTH - 100)
            terrain_y = self.world.get_terrain_height(x)
            depth_ratio = self.world.get_depth_ratio(terrain_y)
            if _is_valid_depth(pt, depth_ratio) and n_plants < PLANT_HARD_CAP:
                from seeds import Seed as _Seed

                tmp_seed = _Seed(pt)
                tmp_seed.x = x
                plant = Plant(x, terrain_y, pt, soil_grid, tmp_seed.traits, self.world)
                plant.development.stage = "seedling"
                plant.development.energy = 3.0
                self.plants.append(plant)
                n_plants += 1

        # Update seeds — seeds settle and germinate according to seasonal rules
        for seed in self.seeds[:]:
            if seed.update(dt, self.world, time_system):
                self.seeds.remove(seed)
                n_seeds -= 1
                if n_plants < PLANT_HARD_CAP:
                    terrain_y = self.world.get_terrain_height(seed.x)
                    depth_ratio = self.world.get_depth_ratio(terrain_y)
                    if _is_valid_depth(seed.plant_type, depth_ratio):
                        self.plants.append(
                            Plant(
                                seed.x,
                                terrain_y,
                                seed.plant_type,
                                soil_grid,
                                seed.traits,
                                self.world,
                            )
                        )
                        n_plants += 1

        # Update plants + plant-driven plankton spawning
        particle_system = getattr(self.world, "particle_system", None)

        for plant in self.plants[:]:
            alive = plant.update(
                dt, soil_grid, photosynthesis_rate=photo_rate, season_index=season_idx
            )
            if not alive:
                nutrients = plant.development.get_decomposition_return()
                cell = soil_grid.get_cell_at_pixel(plant.x, plant.base_y)
                if cell:
                    cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + nutrients)
                    for nb, _ in soil_grid.get_neighbors(cell.x, cell.y):
                        if nb:  # Defensive check for null neighbor cells
                            nb.nutrient = min(
                                SOIL_MAX_NUTRIENT, nb.nutrient + nutrients * 0.3
                            )
                self.plants.remove(plant)
                n_plants -= 1
                continue

            # Plant → plankton production (only when mature)
            if particle_system is not None and plant.development.is_mature:
                plant.try_produce_plankton(dt, particle_system, time)

            # Seed production — Summer (1) and Autumn (2)
            if (
                season_idx in (1, 2)
                and (n_plants + len(self.seeds)) < PLANT_HARD_CAP + SEED_HARD_CAP
            ):
                new_seed = plant.try_produce_seed(time, seed_mod, season_idx)
                if new_seed and len(self.seeds) < SEED_HARD_CAP:
                    self.seeds.append(new_seed)

            # Bubble emissions
            bc = BUBBLE_CHANCE
            if plant.plant_type == "tube_sponge":
                bc *= 3
            elif plant.plant_type == "anemone" and plant.development.is_mature:
                bc *= 1.5
            if plant.development.is_mature and random.random() < bc:
                self.bubbles.append(
                    {
                        "x": plant.x + random.uniform(-10, 10),
                        "y": plant.base_y - plant.development.current_height * 0.9,
                        "vy": random.uniform(-1.0, -0.5),
                        "life": random.uniform(2.0, 4.0),
                        "size": random.randint(2, 5),
                    }
                )

        for bubble in self.bubbles[:]:
            bubble["y"] += bubble["vy"] * 60 * dt
            bubble["life"] -= dt
            if bubble["life"] <= 0 or bubble["y"] < WATER_LINE_Y:
                self.bubbles.remove(bubble)

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self, screen, camera, time, time_system=None):
        biolum = time_system.get_bioluminescence_alpha() if time_system else 0

        for seed in self.seeds:
            seed.draw(screen, camera)

        for plant in self.plants:
            plant.draw_roots(screen, camera, time)

        for plant in sorted(self.plants, key=lambda p: p.base_y):
            plant.draw(screen, camera, time, self.world.soil_grid, biolum_alpha=biolum)

        for bubble in self.bubbles:
            alpha = max(0, min(255, int(255 * (bubble["life"] / 4.0))))
            screen_b = camera.apply((bubble["x"], bubble["y"]))
            pygame.draw.circle(
                screen,
                (*BUBBLE_COLOR, alpha),
                (int(screen_b[0]), int(screen_b[1])),
                bubble["size"],
            )


# ── Depth validation ──────────────────────────────────────────────────────────


def _is_valid_depth(plant_type, depth_ratio):
    rules = {
        "kelp": lambda d: d <= KELP_DEPTH_MAX,
        "seagrass": lambda d: SEAGRASS_DEPTH_MIN <= d <= SEAGRASS_DEPTH_MAX,
        "algae": lambda d: d >= ALGAE_DEPTH_MIN,
        "red_seaweed": lambda d: RED_SEAWEED_DEPTH_MIN <= d <= RED_SEAWEED_DEPTH_MAX,
        "lily_pad": lambda d: d <= LILY_PAD_DEPTH_MAX,
        "tube_sponge": lambda d: TUBE_SPONGE_DEPTH_MIN <= d <= TUBE_SPONGE_DEPTH_MAX,
        "fan_coral": lambda d: FAN_CORAL_DEPTH_MIN <= d <= FAN_CORAL_DEPTH_MAX,
        "anemone": lambda d: ANEMONE_DEPTH_MIN <= d <= ANEMONE_DEPTH_MAX,
    }
    return rules.get(plant_type, lambda d: True)(depth_ratio)
