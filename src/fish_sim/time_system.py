"""
TimeSystem — Master clock for day/night cycles and seasons.

Time-of-day:  0.0 = midnight, 0.25 = dawn, 0.5 = noon, 0.75 = dusk, 1.0 = midnight
Season index: 0 = Spring, 1 = Summer, 2 = Autumn, 3 = Winter
"""

import math
from .config import (
    DAY_DURATION,
    SEASON_DURATION,
    DAWN_START,
    DAWN_END,
    DUSK_START,
    DUSK_END,
    SEASON_NAMES,
    SEASON_COLORS,
)


class TimeSystem:
    def __init__(self):
        # Start at early morning so the player sees a dawn immediately
        self.time_of_day = 0.22  # 0.0–1.0, fraction of a full day
        self.day_count = 0
        self.season_time = 0.0  # seconds elapsed in current season
        self.season_index = 0  # 0=Spring 1=Summer 2=Autumn 3=Winter
        self.paused = False
        self.speed_mult = 1.0  # can be raised for fast-forward

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        if self.paused:
            return

        real_dt = dt * self.speed_mult

        # Advance time of day
        self.time_of_day += real_dt / DAY_DURATION
        if self.time_of_day >= 1.0:
            self.time_of_day -= 1.0
            self.day_count += 1

        # Advance season
        self.season_time += real_dt
        if self.season_time >= SEASON_DURATION:
            self.season_time -= SEASON_DURATION
            self.season_index = (self.season_index + 1) % 4

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def season_name(self):
        return SEASON_NAMES[self.season_index]

    @property
    def season_progress(self):
        """0.0 → 1.0 through the current season."""
        if SEASON_DURATION <= 0:
            return 0.0
        return self.season_time / SEASON_DURATION

    @property
    def is_daytime(self):
        return DAWN_END <= self.time_of_day <= DUSK_START

    @property
    def is_dawn(self):
        return DAWN_START <= self.time_of_day < DAWN_END

    @property
    def is_dusk(self):
        return DUSK_START <= self.time_of_day < DUSK_END

    @property
    def is_night(self):
        return self.time_of_day < DAWN_START or self.time_of_day > DUSK_END

    @property
    def light_level(self):
        """
        0.0 = full night, 1.0 = full noon.
        Smooth transitions at dawn and dusk.
        """
        t = self.time_of_day
        if t < DAWN_START:
            return 0.0
        elif t < DAWN_END:
            return _smoothstep((t - DAWN_START) / (DAWN_END - DAWN_START))
        elif t <= DUSK_START:
            # Slight cosine dip at noon for realism
            noon_pos = (t - DAWN_END) / (DUSK_START - DAWN_END)
            return 0.85 + 0.15 * math.sin(noon_pos * math.pi)
        elif t <= DUSK_END:
            return _smoothstep(1.0 - (t - DUSK_START) / (DUSK_END - DUSK_START))
        else:
            return 0.0

    @property
    def photosynthesis_rate(self):
        """How efficiently plants convert nutrients. 0 at night, 1 at noon."""
        ll = self.light_level
        # Season modifier
        mods = {0: 1.0, 1: 1.2, 2: 0.7, 3: 0.3}  # Spring/Summer/Autumn/Winter
        return ll * mods[self.season_index]

    @property
    def plankton_depth_bias(self):
        """
        +1.0 = plankton migrate to surface (day),
        -1.0 = plankton sink deep (night).
        Diel vertical migration.
        """
        return math.sin(self.light_level * math.pi - math.pi / 2)

    @property
    def metabolism_modifier(self):
        """
        Seasonal cold/warm effect on fish metabolism.
        Winter = 0.6 (sluggish), Summer = 1.2 (active).
        """
        mods = {0: 1.0, 1: 1.2, 2: 0.9, 3: 0.6}
        return mods[self.season_index]

    @property
    def mating_drive_modifier(self):
        """
        Spring mating surge, winter suppression.
        """
        mods = {0: 1.5, 1: 1.0, 2: 0.8, 3: 0.4}
        return mods[self.season_index]

    @property
    def predator_activity_modifier(self):
        """Predators peak in summer, slow in winter."""
        mods = {0: 1.0, 1: 1.3, 2: 1.0, 3: 0.6}
        return mods[self.season_index]

    @property
    def seed_dispersal_modifier(self):
        """Autumn heavy seed fall, spring moderate, summer/winter sparse."""
        mods = {0: 0.8, 1: 0.4, 2: 2.0, 3: 0.2}
        return mods[self.season_index]

    @property
    def nutrient_upwelling(self):
        """Extra base nutrient injection per second. Spring surge."""
        mods = {0: 0.003, 1: 0.001, 2: 0.001, 3: 0.0}
        return mods[self.season_index]

    # ── Sky / Water colours ───────────────────────────────────────────────────

    def get_sky_color(self):
        """Interpolate sky colour through day phases and seasons."""
        t = self.time_of_day
        ll = self.light_level

        # Base day/night sky
        if self.is_night:
            base = (10, 10, 35)
        elif self.is_dawn:
            p = (t - DAWN_START) / (DAWN_END - DAWN_START)
            base = _lerp_color((10, 10, 35), (255, 140, 60), min(1.0, p * 2))
            if p > 0.5:
                base = _lerp_color(base, (152, 219, 249), (p - 0.5) * 2)
        elif self.is_dusk:
            p = (t - DUSK_START) / (DUSK_END - DUSK_START)
            base = _lerp_color((152, 219, 249), (255, 100, 40), min(1.0, p * 2))
            if p > 0.5:
                base = _lerp_color(base, (10, 10, 35), (p - 0.5) * 2)
        else:
            base = (152, 219, 249)

        # Season tint
        season_tint = SEASON_COLORS[self.season_index]
        blended = _lerp_color(base, season_tint, 0.15)
        return blended

    def get_water_surface_color(self):
        """Water surface darkens at night, warms at sunset."""
        ll = self.light_level
        day_color = (80, 170, 210)
        night_color = (15, 30, 60)
        base = _lerp_color(night_color, day_color, ll)

        if self.is_dawn or self.is_dusk:
            warm = (120, 80, 60)
            base = _lerp_color(base, warm, 0.3 * (1.0 - abs(ll - 0.5) * 2))
        return base

    def get_ambient_light_alpha(self):
        """
        Alpha for a dark overlay drawn over the whole screen at night.
        0 = no overlay (day), 180 = deep night.
        """
        return int((1.0 - self.light_level) * 185)

    def get_light_ray_alpha(self):
        """Light rays fade at night and are strongest at noon."""
        return int(self.light_level * 45)

    def get_bioluminescence_alpha(self):
        """Glow intensity for fish/plants at night. 0 during day."""
        return int(max(0.0, 1.0 - self.light_level * 2.5) * 120)

    # ── HUD helpers ───────────────────────────────────────────────────────────

    def get_hud_strings(self):
        hour = int(self.time_of_day * 24)
        minute = int((self.time_of_day * 24 - hour) * 60)
        phase = (
            "Night"
            if self.is_night
            else "Dawn" if self.is_dawn else "Dusk" if self.is_dusk else "Day"
        )
        return {
            "time": f"{hour:02d}:{minute:02d}  ({phase})",
            "season": self.season_name,
            "day": f"Day {self.day_count + 1}",
            "light": self.light_level,
        }

    def cycle_speed(self):
        """Cycle through 1x → 3x → 6x → 1x."""
        if self.speed_mult < 2:
            self.speed_mult = 3.0
        elif self.speed_mult < 5:
            self.speed_mult = 6.0
        else:
            self.speed_mult = 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
