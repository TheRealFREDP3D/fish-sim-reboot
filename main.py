"""Underwater Plant Ecosystem Simulation - Now with neural fish and brain visualization!"""

import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from world import World
from plants import PlantManager
from particles import ParticleSystem
from fish_system import FishSystem
from camera import Camera


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

        self.world = World()
        self.camera = Camera()
        self.plant_manager = PlantManager(self.world)
        self.plant_manager.spawn_initial_seeds()
        self.particle_system = ParticleSystem()
        self.fish_system = FishSystem(
            self.particle_system, self.plant_manager, self.world
        )

        self.font = pygame.font.Font(None, 24)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.world = World()
                    self.camera = Camera()
                    self.plant_manager = PlantManager(self.world)
                    self.plant_manager.spawn_initial_seeds()
                    self.fish_system = FishSystem(
                        self.particle_system, self.plant_manager, self.world
                    )
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.fish_system.handle_click(event.pos, self.camera)

    def update(self):
        dt = self.clock.get_time() / 1000.0
        self.time += dt

        self.world.soil_grid.update(dt)
        self.particle_system.update(self.time)
        self.plant_manager.update(dt)
        self.fish_system.update(dt)

        # Update camera focus
        if self.fish_system.selected_fish:
            self.camera.follow(self.fish_system.selected_fish)
        else:
            self.camera.target = None

        self.camera.update()

    def draw(self):
        self.screen.fill((0, 0, 0))

        self.world.draw(self.screen, self.camera)
        self.particle_system.draw(self.screen, self.camera)
        self.plant_manager.draw(self.screen, self.camera, self.time)
        self.fish_system.draw(self.screen, self.camera, self.time)

        # Instructions
        instructions = [
            "Click on any fish to view its neural activity!",
            "Blue-striped = Cleaner fish (eat poop, fertilize soil)",
            "Click again to deselect. R = Restart, ESC = Quit",
        ]
        y = SCREEN_HEIGHT - 100
        for line in instructions:
            text = self.font.render(line, True, (255, 255, 200))
            shadow = self.font.render(line, True, (0, 0, 0))
            self.screen.blit(shadow, (12, y + 2))
            self.screen.blit(text, (10, y))
            y += 25

        pygame.display.flip()

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
    print("Underwater Neural Ecosystem Simulation")
    print("Now with Cleaner Fish subspecies!")
    print("=" * 60)
    print("\nNEW: Blue-striped cleaner fish eat poop particles and fertilize the soil")
    print("They evolve separately and help maintain the ecosystem")
    print("\nClick on any fish (orange or blue-striped) to visualize its brain!")
    print("\nControls:")
    print(" Left Click - Select/deselect fish to view brain")
    print(" R - Regenerate world")
    print(" ESC - Quit")
    print("\nStarting simulation...")
    sim = Simulation()
    sim.run()


if __name__ == "__main__":
    main()
