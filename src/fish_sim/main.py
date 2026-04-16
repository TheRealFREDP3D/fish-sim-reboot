"""Main simulation entry point - imported by the root launcher"""

import pygame
import sys
from .config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from .core.world import World
from .plants.plants import PlantManager
from .core.particles import ParticleSystem
from .fish.fish_system import FishSystem
from .core.camera import Camera
from .time_system import TimeSystem   # New seasonal/day-night system


class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF
        )
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Core systems
        self.world = World()
        self.camera = Camera()
        self.plant_manager = PlantManager(self.world)
        self.plant_manager.spawn_initial_seeds()
        self.particle_system = ParticleSystem()
        self.fish_system = FishSystem(
            self.particle_system, self.plant_manager, self.world
        )
        self.time_system = TimeSystem()   # New: day/night + seasons

        self.font = pygame.font.Font(None, 24)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.restart()
                elif event.key == pygame.K_t:      # Cycle time speed
                    self.time_system.cycle_speed()
                elif event.key == pygame.K_p:      # Pause toggle
                    self.time_system.toggle_pause()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.fish_system.handle_click(event.pos, self.camera)

    def restart(self):
        """Fully restart the simulation"""
        self.world = World()
        self.camera = Camera()
        self.plant_manager = PlantManager(self.world)
        self.plant_manager.spawn_initial_seeds()
        self.fish_system = FishSystem(
            self.particle_system, self.plant_manager, self.world
        )
        self.time_system.reset()

    def update(self, dt):
        self.time_system.update(dt)                    # Update day/night & seasons

        self.world.soil_grid.update(dt)
        self.particle_system.update_with_dt(dt, self.time_system)
        self.plant_manager.update(dt, self.time_system)   # Pass time_system for seasonal effects
        self.fish_system.update(dt, self.time_system)     # Pass time_system for behavior modulation

        # Camera follow
        if self.fish_system.selected_fish:
            self.camera.follow(self.fish_system.selected_fish)
        else:
            self.camera.target = None
        self.camera.update()

    def draw(self):
        self.screen.fill((0, 0, 0))

        # Draw world with time-of-day lighting
        self.world.draw(self.screen, self.camera, self.time_system)
        self.particle_system.draw(self.screen, self.camera, self.time_system)
        self.plant_manager.draw(self.screen, self.camera, self.time_system.time_of_day)
        self.fish_system.draw(self.screen, self.camera, self.time_system.time_of_day)

        # Instructions (bottom left)
        instructions = [
            "Click on any fish to view its neural activity!",
            "Blue-striped = Cleaner fish (eat poop, fertilize soil)",
            "R = Restart   T = Cycle time speed   P = Pause   ESC = Quit",
        ]
        y = SCREEN_HEIGHT - 110
        for line in instructions:
            text = self.font.render(line, True, (255, 255, 200))
            shadow = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(shadow, (12, y + 2))
            self.screen.blit(text, (10, y))
            y += 25

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.get_time() / 1000.0
            self.handle_events()
            if not self.time_system.paused:
                self.update(dt)
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def run_simulation():
    """Public entry point called by root main.py"""
    print("Starting simulation from src/fish_sim package...")
    sim = Simulation()
    sim.run()


if __name__ == "__main__":
    run_simulation()