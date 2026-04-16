import pygame
import math
import random
from ..config import (
    SOIL_MAX_NUTRIENT,
    CLEANER_CLEANING_FLASH_DURATION,
    DEAD_FISH_SINK_SPEED,
    DEAD_FISH_DECOMPOSITION_TIME,
    DEAD_FISH_NUTRIENT_RETURN,
    FISH_EGG_HATCH_TIME,
    WORLD_WIDTH,
    BLOOD_DROP_DURATION,
    BLOOD_DROP_COUNT,
    BLOOD_DROP_COLORS,
)


class PoopParticle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = random.uniform(0.5, 1.2)
        c_var = random.randint(-10, 10)
        self.color = (90 + c_var, 60 + c_var, 30)
        self.size = random.uniform(2, 4)
        self.rot = random.uniform(0, 360)
        self.nutrition = 0.8  # Added for CleanerFish consumption logic

    def update(self, dt, world):
        self.y += self.vy * 40 * dt
        self.rot += dt * 50
        ty = world.get_terrain_height(self.x)
        if self.y >= ty:
            cell = world.soil_grid.get_cell_at_pixel(self.x, self.y)
            if cell:
                cell.nutrient = min(SOIL_MAX_NUTRIENT, cell.nutrient + 0.35)
            return False
        return True

    def draw(self, screen, camera):
        pos = camera.apply((self.x, self.y))
        pts = []
        for i in range(5):
            angle = math.radians(self.rot + i * 72)
            dist = self.size * (0.8 + 0.4 * math.sin(i))
            pts.append(
                (pos[0] + math.cos(angle) * dist, pos[1] + math.sin(angle) * dist)
            )
        pygame.draw.polygon(screen, self.color, pts)


class CleaningEffect:
    """Short-lived sparkle burst at the point where a cleaner fish cleans a client."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.age = 0.0
        self.duration = CLEANER_CLEANING_FLASH_DURATION
        self.sparks = [
            {
                "angle": random.uniform(0, math.pi * 2),
                "speed": random.uniform(15, 45),
                "size": random.uniform(1.5, 3.0),
                "color": random.choice(
                    [
                        (100, 255, 220),
                        (150, 255, 240),
                        (80, 230, 200),
                        (200, 255, 255),
                        (120, 240, 230),
                    ]
                ),
            }
            for _ in range(8)
        ]

    def update(self, dt):
        self.age += dt
        return self.age < self.duration

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), 50):
            return
        t = self.age / self.duration
        alpha = int(255 * (1.0 - t) ** 1.5)
        screen_pos = camera.apply((self.x, self.y))
        sx, sy = int(screen_pos[0]), int(screen_pos[1])

        # Small expanding glow ring
        ring_r = int(5 + t * 14)
        ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surf,
            (100, 255, 220, max(0, alpha // 3)),
            (ring_r + 2, ring_r + 2),
            ring_r,
            2,
        )
        screen.blit(ring_surf, (sx - ring_r - 2, sy - ring_r - 2))

        for spark in self.sparks:
            dist = spark["speed"] * t
            px = sx + math.cos(spark["angle"]) * dist
            py = sy + math.sin(spark["angle"]) * dist
            spark_alpha = max(0, int(alpha * 0.9))
            r = int(spark["size"] * (1.0 - t * 0.4))
            if r < 1:
                continue
            spark_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                spark_surf, (*spark["color"], spark_alpha), (r + 1, r + 1), r
            )
            screen.blit(spark_surf, (int(px) - r, int(py) - r))


class HeartParticle:
    """Floating heart for mating display."""

    def __init__(self, x, y):
        self.x = x + random.uniform(-20, 20)
        self.y = y + random.uniform(-10, 5)
        self.vy = random.uniform(-0.6, -0.2)
        self.vx = random.uniform(-0.3, 0.3)
        self.life = random.uniform(1.2, 2.2)
        self.max_life = self.life
        self.size = random.uniform(5, 10)

    def update(self, dt):
        self.x += self.vx * 40 * dt
        self.y += self.vy * 40 * dt
        self.vy -= 0.01 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, screen, camera):
        pos = camera.apply((self.x, self.y))
        t = self.life / self.max_life
        alpha = int(255 * t * t)
        size = self.size * (0.6 + 0.4 * t)
        self._draw_heart(screen, int(pos[0]), int(pos[1]), size, alpha)

    @staticmethod
    def _draw_heart(screen, cx, cy, size, alpha):
        surf = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
        r = int(size)
        pygame.draw.circle(surf, (255, 80, 120, alpha), (r, r), r)
        pygame.draw.circle(surf, (255, 80, 120, alpha), (r * 3, r), r)
        pts = [(0, r), (r * 4, r), (r * 2, r * 4)]
        pygame.draw.polygon(surf, (255, 80, 120, alpha), pts)
        screen.blit(surf, (cx - r * 2, cy - r * 2))


class FishEgg:
    def __init__(
        self,
        x,
        y,
        traits,
        parent1=None,
        parent2=None,
        is_cleaner=False,
        is_predator=False,
        brain=None,
    ):
        self.x, self.y = x, y
        self.traits = traits
        self.parent1, self.parent2 = parent1, parent2
        self.is_cleaner, self.is_predator = is_cleaner, is_predator
        self.brain = brain
        self.timer = FISH_EGG_HATCH_TIME
        self.pulse_offset = random.uniform(0, math.pi * 2)
        self.x += random.uniform(-18, 18)
        self.y += random.uniform(-8, 8)

    def update(self, dt, world):
        self.timer -= dt
        ty = world.get_terrain_height(self.x)
        if self.y < ty - 4:
            self.y += 15 * dt
        return self.timer <= 0

    def draw(self, screen, camera):
        time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(time * 3 + self.pulse_offset) + 1) * 0.5
        if self.is_predator:
            base_color, glow_color = (255, 80, 80), (255, 160, 160)
        elif self.is_cleaner:
            base_color, glow_color = (100, 200, 255), (180, 230, 255)
        else:
            base_color, glow_color = (255, 210, 80), (255, 240, 160)

        egg_r = 9 + pulse * 3
        surf = pygame.Surface((50, 50), pygame.SRCALPHA)
        cx, cy = 25, 25
        pygame.draw.circle(surf, (*glow_color, 60), (cx, cy), int(egg_r + 8))
        pygame.draw.circle(surf, (*glow_color, 120), (cx, cy), int(egg_r + 4))
        pygame.draw.circle(surf, (*base_color, 220), (cx, cy), int(egg_r))
        pygame.draw.circle(surf, (255, 255, 255, 180), (cx, cy), int(egg_r), 2)

        hatch_progress = 1.0 - (self.timer / FISH_EGG_HATCH_TIME)
        embryo_r = max(2, int(egg_r * 0.35 * (0.5 + hatch_progress * 0.5)))
        embryo_color = tuple(max(0, c - 60) for c in base_color)
        pygame.draw.circle(surf, (*embryo_color, 200), (cx, cy), embryo_r)

        pos = camera.apply((self.x, self.y))
        screen.blit(surf, (int(pos[0]) - cx, int(pos[1]) - cy))


# ═══════════════════════════════════════════════════════════════════════════
# NEW: DeadFish — fish corpse that sinks and decomposes into soil nutrients
# ═══════════════════════════════════════════════════════════════════════════

class DeadFish:
    """
    A dead fish that sinks to the lake bottom, decomposes over time,
    and releases nutrients back into the soil grid.

    Lifecycle:
      1. Sinking phase — fish drifts downward, slowly rotating
      2. Settled phase — fish rests on the terrain, begins to decompose
      3. Decomposed — nutrients deposited into soil, corpse removed

    Visual:
      - Corpse fades from its original colour toward grey-brown
      - Small bubble particles rise occasionally during decomposition
      - A faint nutrient glow appears on the soil beneath when decomposing
    """

    def __init__(self, x, y, color, size, heading):
        self.x = x
        self.y = y
        self.original_color = color
        self.size = size  # visual size multiplier (from get_current_size_mult)
        self.heading = heading

        # Sinking state
        self.phase = "sinking"  # "sinking" → "decomposing" → "done"
        self.sink_vy = DEAD_FISH_SINK_SPEED
        self.sink_vx = random.uniform(-8, 8)  # slight horizontal drift

        # Decomposition state
        self.decomp_timer = 0.0
        self.decomp_duration = DEAD_FISH_DECOMPOSITION_TIME
        self.fade_progress = 0.0  # 0.0 = fresh, 1.0 = fully decomposed

        # Rotation for the sinking tumble
        self.rotation = 0.0
        self.rotation_speed = random.uniform(-90, 90)  # degrees per second

        # Small bubbles that rise during decomposition
        self.bubbles = []
        self._bubble_timer = 0.0

        # Nutrient glow on soil
        self._nutrient_deposited = False

    def update(self, dt, world):
        """Returns True if still alive (not fully decomposed)."""
        if self.phase == "sinking":
            self.y += self.sink_vy * dt
            self.x += self.sink_vx * dt
            self.sink_vx *= 0.98  # slow horizontal drift to zero
            self.rotation += self.rotation_speed * dt
            self.rotation_speed *= 0.995  # slow tumbling to a stop

            # Slight random wobble for organic feel
            self.x += math.sin(pygame.time.get_ticks() * 0.003 + self.y * 0.05) * 0.3

            # Clamp horizontal position
            self.x = max(10, min(WORLD_WIDTH - 10, self.x))

            # Check if we've hit the terrain
            terrain_y = world.get_terrain_height(self.x)
            if self.y >= terrain_y - 3:
                self.y = terrain_y - 3
                self.phase = "decomposing"
                self.rotation_speed = 0.0
                # Settle at a slight angle
                self.rotation = random.uniform(-30, 30)

        elif self.phase == "decomposing":
            self.decomp_timer += dt
            self.fade_progress = min(1.0, self.decomp_timer / self.decomp_duration)

            # Spawn decomposition bubbles
            self._bubble_timer -= dt
            if self._bubble_timer <= 0:
                self._bubble_timer = random.uniform(0.3, 1.2)
                self.bubbles.append({
                    "x": self.x + random.uniform(-self.size * 2, self.size * 2),
                    "y": self.y - random.uniform(2, self.size),
                    "vy": random.uniform(-15, -30),
                    "vx": random.uniform(-3, 3),
                    "size": random.uniform(1, 3),
                    "life": random.uniform(0.5, 1.5),
                })

            # Update bubbles
            for b in self.bubbles[:]:
                b["y"] += b["vy"] * dt
                b["x"] += b["vx"] * dt
                b["life"] -= dt
                if b["life"] <= 0:
                    self.bubbles.remove(b)

            # Check if decomposition is complete
            if self.decomp_timer >= self.decomp_duration:
                # Deposit nutrients into the soil
                if not self._nutrient_deposited:
                    self._deposit_nutrients(world)
                    self._nutrient_deposited = True
                self.phase = "done"
                return False

        return True

    def _deposit_nutrients(self, world):
        """Spread nutrients across several soil cells around the corpse."""
        soil_grid = world.soil_grid
        if soil_grid is None:
            return

        # Deposit into a small area (3-5 cells wide)
        center_cell = soil_grid.get_cell_at_pixel(self.x, self.y)
        if center_cell is None:
            return

        nutrient_per_cell = DEAD_FISH_NUTRIENT_RETURN / 5.0
        deposited = 0.0

        cx, cy = soil_grid.pixel_to_cell(self.x, self.y)
        for dx in range(-2, 3):
            for dy in range(-1, 2):
                cell = soil_grid.get_cell(cx + dx, cy + dy)
                if cell and not cell.is_water:
                    dist_factor = 1.0 - (abs(dx) + abs(dy)) * 0.15
                    dist_factor = max(0.1, dist_factor)
                    cell.nutrient = min(
                        SOIL_MAX_NUTRIENT,
                        cell.nutrient + nutrient_per_cell * dist_factor,
                    )
                    deposited += nutrient_per_cell * dist_factor

    def get_current_color(self):
        """Lerp from original colour toward grey-brown as decomposition progresses."""
        dead_color = (90, 75, 60)  # grey-brown decomposed colour
        t = self.fade_progress
        return tuple(
            max(0, min(255, int(self.original_color[i] * (1 - t) + dead_color[i] * t)))
            for i in range(3)
        )

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), margin=40):
            return

        color = self.get_current_color()
        alpha = int(255 * (1.0 - self.fade_progress * 0.6))  # fade out but don't go fully transparent
        alpha = max(40, alpha)

        pos = camera.apply((self.x, self.y))
        sx, sy = int(pos[0]), int(pos[1])
        body_size = max(4, int(self.size * 4 * (1.0 - self.fade_progress * 0.3)))

        # Create a small surface for the corpse
        surf_size = body_size * 6 + 8
        surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        cx, cy = surf_size // 2, surf_size // 2

        # Draw body (simple ellipse, slightly tilted)
        body_len = body_size * 2
        body_wid = body_size

        # Calculate rotated ellipse points
        rot_rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)
        pts = []
        for i in range(16):
            angle = i / 16 * math.pi * 2
            ex = math.cos(angle) * body_len
            ey = math.sin(angle) * body_wid
            rx = cx + ex * cos_r - ey * sin_r
            ry = cy + ex * sin_r + ey * cos_r
            pts.append((rx, ry))

        if len(pts) >= 3:
            pygame.draw.polygon(surf, (*color, alpha), pts)
            # Darker outline
            outline_color = tuple(max(0, c - 40) for c in color)
            pygame.draw.polygon(surf, (*outline_color, alpha // 2), pts, 1)

        # Draw a tail stub
        tail_x = cx - math.cos(rot_rad) * body_len * 1.3
        tail_y = cy - math.sin(rot_rad) * body_len * 1.3
        tail_base1 = (
            cx - math.cos(rot_rad) * body_len + math.sin(rot_rad) * body_wid * 0.5,
            cy - math.sin(rot_rad) * body_len - math.cos(rot_rad) * body_wid * 0.5,
        )
        tail_base2 = (
            cx - math.cos(rot_rad) * body_len - math.sin(rot_rad) * body_wid * 0.5,
            cy - math.sin(rot_rad) * body_len + math.cos(rot_rad) * body_wid * 0.5,
        )
        pygame.draw.polygon(surf, (*color, alpha), [tail_base1, tail_base2, (tail_x, tail_y)])

        # Draw an eye (faded, X-shaped to indicate death)
        eye_offset_x = math.cos(rot_rad) * body_len * 0.5 - math.sin(rot_rad) * body_wid * 0.3
        eye_offset_y = math.sin(rot_rad) * body_len * 0.5 + math.cos(rot_rad) * body_wid * 0.3
        eye_x = int(cx + eye_offset_x)
        eye_y = int(cy + eye_offset_y)
        eye_r = max(1, body_size // 4)
        # X marks the spot
        pygame.draw.line(surf, (40, 30, 25, alpha), (eye_x - eye_r, eye_y - eye_r), (eye_x + eye_r, eye_y + eye_r), 1)
        pygame.draw.line(surf, (40, 30, 25, alpha), (eye_x - eye_r, eye_y + eye_r), (eye_x + eye_r, eye_y - eye_r), 1)

        screen.blit(surf, (sx - surf_size // 2, sy - surf_size // 2))

        # Draw decomposition bubbles
        for b in self.bubbles:
            bpos = camera.apply((b["x"], b["y"]))
            b_alpha = int(180 * (b["life"] / 1.5))
            b_alpha = max(0, min(255, b_alpha))
            bsurf = pygame.Surface((int(b["size"] * 2 + 4), int(b["size"] * 2 + 4)), pygame.SRCALPHA)
            pygame.draw.circle(
                bsurf,
                (180, 200, 220, b_alpha),
                (int(b["size"] + 2), int(b["size"] + 2)),
                int(b["size"]),
                1,
            )
            screen.blit(
                bsurf,
                (int(bpos[0]) - int(b["size"]) - 2, int(bpos[1]) - int(b["size"]) - 2),
            )

        # Draw nutrient glow on soil during decomposition
        if self.phase == "decomposing":
            glow_intensity = self.fade_progress * 0.5
            if glow_intensity > 0.05:
                glow_r = int(body_size * 3 + self.fade_progress * 15)
                glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                glow_alpha = int(60 * glow_intensity)
                pygame.draw.circle(
                    glow_surf,
                    (120, 200, 80, glow_alpha),
                    (glow_r + 2, glow_r + 2),
                    glow_r,
                )
                screen.blit(glow_surf, (sx - glow_r - 2, sy - glow_r - 2))


# ═══════════════════════════════════════════════════════════════════════════
# NEW: BloodEffect — visible blood drops when a predator bites a fish
# ═══════════════════════════════════════════════════════════════════════════

class BloodEffect:
    """
    Blood droplet burst that appears when a predator bites a fish.
    Small red particles spray outward from the wound, drift with the water,
    and slowly fade away.
    """

    def __init__(self, x, y, heading):
        self.x = x
        self.y = y
        self.age = 0.0
        self.duration = BLOOD_DROP_DURATION

        # Spawn blood droplets in a cone opposite to the attacker's heading
        # (blood sprays away from the bite direction)
        spray_base_angle = heading + math.pi  # opposite of attacker heading
        self.drops = []
        for _ in range(BLOOD_DROP_COUNT):
            angle = spray_base_angle + random.uniform(-1.2, 1.2)
            speed = random.uniform(30, 90)
            self.drops.append({
                "x": x + random.uniform(-5, 5),
                "y": y + random.uniform(-5, 5),
                "vx": math.cos(angle) * speed + random.uniform(-10, 10),
                "vy": math.sin(angle) * speed + random.uniform(-10, 10),
                "size": random.uniform(1.5, 4.0),
                "color": random.choice(BLOOD_DROP_COLORS),
                "life": random.uniform(0.5, BLOOD_DROP_DURATION),
                "max_life": BLOOD_DROP_DURATION,
                # Some drops are larger "globules" that sink faster
                "is_globule": random.random() < 0.3,
            })

    def update(self, dt):
        self.age += dt
        alive = False

        for drop in self.drops[:]:
            drop["life"] -= dt
            if drop["life"] <= 0:
                self.drops.remove(drop)
                continue
            alive = True

            # Movement — blood drifts in water with drag
            drag = 0.97
            drop["vx"] *= drag
            drop["vy"] *= drag

            # Globules sink; regular drops mostly drift
            if drop["is_globule"]:
                drop["vy"] += 20.0 * dt  # gravity for heavier drops
            else:
                # Light drops drift with slight randomness
                drop["vy"] += random.uniform(-5, 5) * dt

            drop["x"] += drop["vx"] * dt
            drop["y"] += drop["vy"] * dt

            # Water current drift
            drop["x"] += math.sin(pygame.time.get_ticks() * 0.001 + drop["y"] * 0.01) * 0.3

        return alive

    def draw(self, screen, camera):
        if not camera.is_visible((self.x, self.y), margin=80):
            return

        for drop in self.drops:
            pos = camera.apply((drop["x"], drop["y"]))
            sx, sy = int(pos[0]), int(pos[1])

            # Alpha fades based on remaining life
            life_ratio = drop["life"] / drop["max_life"]
            alpha = int(220 * life_ratio ** 0.5)
            alpha = max(0, min(255, alpha))

            r = max(1, int(drop["size"] * (0.5 + 0.5 * life_ratio)))

            # Draw the blood drop
            drop_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            cx, cy = r + 2, r + 2

            # Core
            pygame.draw.circle(drop_surf, (*drop["color"], alpha), (cx, cy), r)

            # Slight glow / halo for larger drops
            if r >= 3:
                pygame.draw.circle(
                    drop_surf,
                    (drop["color"][0], drop["color"][1], drop["color"][2], alpha // 4),
                    (cx, cy),
                    r + 2,
                )

            screen.blit(drop_surf, (sx - cx, sy - cy))
