"""Underwater Plant Ecosystem Simulation — with Neural Fish, Brain Visualization, and Day/Night + Seasons!"""

import pygame
import sys
import math
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from world import World
from plants import PlantManager
from particles import ParticleSystem
from fish_system import FishSystem
from camera import Camera
from time_system import TimeSystem


_SEASON_HUD_COLORS = {
    "Spring": (160, 240, 160),
    "Summer": (255, 240, 100),
    "Autumn": (240, 160, 60),
    "Winter": (160, 200, 255),
}
_PHASE_ICONS = {
    "Night": "🌙",
    "Dawn": "🌅",
    "Day": "☀",
    "Dusk": "🌇",
}


class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF
        )
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.time = 0

        self.time_system = TimeSystem()
        self.world = World()
        self.camera = Camera()
        self.particle_system = ParticleSystem()

        self.world.particle_system = self.particle_system

        self.plant_manager = PlantManager(self.world)
        self.plant_manager.spawn_initial_seeds()
        self.fish_system = FishSystem(
            self.particle_system, self.plant_manager, self.world
        )

        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 32)

    def _reset(self):
        self.time_system = TimeSystem()
        self.world = World()
        self.camera = Camera()
        self.particle_system = ParticleSystem()

        self.world.particle_system = self.particle_system

        self.plant_manager = PlantManager(self.world)
        self.plant_manager.spawn_initial_seeds()
        self.fish_system = FishSystem(
            self.particle_system, self.plant_manager, self.world
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self._reset()
                elif event.key == pygame.K_t:
                    self.time_system.cycle_speed()
                elif event.key == pygame.K_p:
                    self.time_system.paused = not self.time_system.paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.fish_system.handle_click(event.pos, self.camera)

    def update(self):
        dt = self.clock.get_time() / 1000.0
        self.time += dt
        self.dt = dt

        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        self.camera.pan(dx, dy, dt)

        self.time_system.update(dt)
        self.world.soil_grid.update(dt)
        self.world.update(dt, self.time_system)
        # Use the dt-aware update for particles so effects animate correctly
        self.particle_system.update_with_dt(dt, self.time_system)
        self.plant_manager.update(dt, time_system=self.time_system)
        self.fish_system.update(dt, time_system=self.time_system)

        if self.fish_system.selected_fish:
            self.camera.follow(self.fish_system.selected_fish)
        else:
            self.camera.target = None
        self.camera.update(dt)

    def draw(self):
        self.screen.fill((0, 0, 0))

        self.world.draw(self.screen, self.camera, self.time_system)
        self.particle_system.draw(self.screen, self.camera, self.time_system)
        self.plant_manager.draw(
            self.screen, self.camera, self.time, time_system=self.time_system
        )
        self.fish_system.draw(
            self.screen, self.camera, self.time, self.dt, time_system=self.time_system
        )

        self._draw_hud()
        pygame.display.flip()

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self):
        ts = self.time_system
        hud = ts.get_hud_strings()
        season = hud["season"]
        season_color = _SEASON_HUD_COLORS.get(season, (255, 255, 255))

        panel_x, panel_y = 10, 10
        panel_w, panel_h = 220, 90
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 140))
        pygame.draw.rect(
            panel_surf, (*season_color, 80), (0, 0, panel_w, panel_h), border_radius=8
        )
        pygame.draw.rect(
            panel_surf,
            (*season_color, 160),
            (0, 0, panel_w, panel_h),
            border_radius=8,
            width=1,
        )
        self.screen.blit(panel_surf, (panel_x, panel_y))

        day_text = self.font_large.render(hud["day"], True, (255, 255, 255))
        self.screen.blit(day_text, (panel_x + 10, panel_y + 8))

        season_text = self.font.render(season, True, season_color)
        self.screen.blit(season_text, (panel_x + 10, panel_y + 36))

        time_text = self.font_small.render(hud["time"], True, (200, 220, 240))
        self.screen.blit(time_text, (panel_x + 10, panel_y + 58))

        bar_x = panel_x + 10
        bar_y = panel_y + 76
        bar_w = panel_w - 20
        bar_h = 6
        pygame.draw.rect(
            self.screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=3
        )
        fill_w = int(bar_w * ts.season_progress)
        if fill_w > 0:
            pygame.draw.rect(
                self.screen,
                season_color,
                (bar_x, bar_y, fill_w, bar_h),
                border_radius=3,
            )

        arc_cx = panel_x + panel_w - 28
        arc_cy = panel_y + 28
        arc_r = 18
        pygame.draw.circle(self.screen, (30, 30, 50), (arc_cx, arc_cy), arc_r, 2)
        ll = hud["light"]
        if ll > 0.02:
            glow_col = (int(255 * ll), int(220 * ll), int(80 * ll))
            pygame.draw.circle(
                self.screen, glow_col, (arc_cx, arc_cy), int(arc_r * ll + 4)
            )
            pygame.draw.circle(
                self.screen,
                (255, 255, 200),
                (arc_cx, arc_cy),
                max(2, int(arc_r * 0.4 * ll + 2)),
            )
        else:
            pygame.draw.circle(self.screen, (180, 190, 220), (arc_cx, arc_cy), 6)

        if ts.speed_mult > 1.0 or ts.paused:
            label = "⏸ PAUSED" if ts.paused else f"⏩ {ts.speed_mult:.0f}×"
            speed_col = (255, 200, 80) if not ts.paused else (200, 100, 100)
            sp_text = self.font_small.render(label, True, speed_col)
            sx = panel_x + panel_w - sp_text.get_width() - 6
            self.screen.blit(sp_text, (sx, panel_y + 58))

        instructions = [
            "Click fish to view brain  |  T = time speed  |  P = pause  |  R = restart  |  ESC = quit",
        ]
        y = SCREEN_HEIGHT - 28
        for line in instructions:
            text = self.font_small.render(line, True, (200, 220, 200))
            shadow = self.font_small.render(line, True, (0, 0, 0))
            self.screen.blit(shadow, (12, y + 1))
            self.screen.blit(text, (11, y))

        pop_x = SCREEN_WIDTH - 180
        pop_y = 10
        pop_surf = pygame.Surface((170, 70), pygame.SRCALPHA)
        pop_surf.fill((0, 0, 0, 130))
        pygame.draw.rect(pop_surf, (60, 80, 100, 120), (0, 0, 170, 70), border_radius=6)
        self.screen.blit(pop_surf, (pop_x, pop_y))

        pops = [
            ("Common", len(self.fish_system.fish), (255, 160, 60)),
            ("Cleaner", len(self.fish_system.cleaner_fish), (100, 180, 220)),
            ("Predator", len(self.fish_system.predators), (220, 80, 80)),
        ]
        for i, (name, count, col) in enumerate(pops):
            label = self.font_small.render(f"{name}: {count}", True, col)
            self.screen.blit(label, (pop_x + 8, pop_y + 6 + i * 20))

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    print("=" * 60)
    print("Underwater Neural Ecosystem — Day/Night + Seasons Edition")
    print("=" * 60)
    print("\nFeatures:")
    print("  Day/Night cycle with dawn, dusk, and star-filled nights")
    print("  Bioluminescent fish and plants at night")
    print("  Plankton diel vertical migration")
    print("  Four seasons: Spring / Summer / Autumn / Winter")
    print("  Seasonal mating drives, metabolism, seed dispersal")
    print("  Autumn leaf and winter snow surface particles")
    print("  Mating glow + hearts; egg-laying burst; family bond lines")
    print("\nControls:")
    print("  Left Click  — Select/deselect fish to view brain")
    print("  Arrow Keys  — Pan camera")
    print("  T           — Cycle time speed (1× / 3× / 6×)")
    print("  P           — Pause / resume time")
    print("  R           — Regenerate world")
    print("  ESC         — Quit")
    print("\nStarting simulation...")
    sim = Simulation()
    sim.run()


if __name__ == "__main__":
    main()
