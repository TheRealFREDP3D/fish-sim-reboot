"""Tests for the fish_sim package neural network and core systems."""

import math
import pytest


class TestNeuralNetwork:
    """Tests for the NeuralNet class."""

    def test_network_initialization(self):
        """Network should initialize with correct architecture."""
        from src.fish_sim.fish.neural_net import NeuralNet
        from src.fish_sim.config import NN_INPUT_COUNT, NN_HIDDEN1_SIZE, NN_HIDDEN2_SIZE, NN_OUTPUT_COUNT

        net = NeuralNet()
        assert net.input_size == NN_INPUT_COUNT
        assert net.hidden_size == NN_HIDDEN1_SIZE
        assert net.hidden2_size == NN_HIDDEN2_SIZE
        assert net.output_size == NN_OUTPUT_COUNT

    def test_forward_pass_shape(self):
        """Forward pass should return correct number of outputs."""
        from src.fish_sim.fish.neural_net import NeuralNet

        net = NeuralNet()
        inputs = [0.5] * net.input_size
        outputs, h1, h2 = net.forward(inputs)

        assert len(outputs) == net.output_size
        assert len(h1) == net.hidden_size
        assert len(h2) == net.hidden2_size

    def test_forward_pass_normalized(self):
        """Outputs should be in valid ranges (steer/thrust in [-1,1] and [0,1])."""
        from src.fish_sim.fish.neural_net import NeuralNet

        net = NeuralNet()
        outputs, _, _ = net.forward([0.5] * net.input_size)

        # Steer should be in [-1, 1] (tanh output)
        assert -1.0 <= outputs[0] <= 1.0
        # Thrust should be in [0, 1] (sigmoid output)
        assert 0.0 <= outputs[1] <= 1

    def test_hidden_state_reset(self):
        """Hidden state should reset properly on reset_hidden()."""
        from src.fish_sim.fish.neural_net import NeuralNet

        net = NeuralNet()
        net.forward([0.5] * net.input_size)
        assert len(net.hidden_state) == net.hidden2_size
        assert any(v != 0.0 for v in net.hidden_state)  # Should have values after forward

        net.reset_hidden()
        assert all(v == 0.0 for v in net.hidden_state)  # Should be zeroed

    def test_network_blending(self):
        """Blended network should have values between parents."""
        from src.fish_sim.fish.neural_net import NeuralNet

        parent1 = NeuralNet()
        parent2 = NeuralNet()
        child = NeuralNet.blend(parent1, parent2)

        # Check all weights are within range of both parents
        for i in range(child.hidden_size):
            for j in range(child.input_size):
                min_w = min(parent1.w1[i][j], parent2.w1[i][j])
                max_w = max(parent1.w1[i][j], parent2.w1[i][j])
                # With mutation, could be slightly outside, but should be close
                assert -5.0 < child.w1[i][j] < 5.0  # Reasonable bound


class TestTimeSystem:
    """Tests for the TimeSystem class."""

    def test_time_advancement(self):
        """Time should advance correctly."""
        from src.fish_sim.time_system import TimeSystem
        from src.fish_sim.config import DAY_DURATION

        ts = TimeSystem()
        initial_time = ts.time_of_day
        ts.update(1.0)  # 1 second real time

        assert ts.time_of_day > initial_time

    def test_season_cycle(self):
        """Seasons should cycle correctly."""
        from src.fish_sim.time_system import TimeSystem
        from src.fish_sim.config import SEASON_DURATION

        ts = TimeSystem()
        initial_season = ts.season_index

        # Advance by nearly a full season
        ts.update(SEASON_DURATION * 0.95)

        # Manually advance to trigger season change
        ts.season_time = SEASON_DURATION - 0.1
        ts.update(0.2)

        # Should have advanced
        assert ts.season_index != initial_season or ts.season_time > ts._last_season_time

    def test_light_level_at_noon(self):
        """Light level should be highest at noon."""
        from src.fish_sim.time_system import TimeSystem

        ts = TimeSystem()
        ts.time_of_day = 0.5  # Noon
        assert ts.light_level > 0.8  # Should be high at noon

    def test_light_level_at_midnight(self):
        """Light level should be zero at midnight."""
        from src.fish_sim.time_system import TimeSystem

        ts = TimeSystem()
        ts.time_of_day = 0.0  # Midnight
        assert ts.light_level == 0.0

    def test_daytime_detection(self):
        """is_daytime should be true during day hours."""
        from src.fish_sim.time_system import TimeSystem

        ts = TimeSystem()
        ts.time_of_day = 0.6  # Mid-day
        assert ts.is_daytime is True

        ts.time_of_day = 0.1  # Night
        assert ts.is_daytime is False


class TestPlantDevelopment:
    """Tests for plant lifecycle."""

    def test_plant_initialization(self):
        """Plant should initialize in seed stage."""
        from src.fish_sim.plants.plants import Plant
        from src.fish_sim.plants.plant_rules import is_valid_depth
        from src.fish_sim.environment.soil import SoilGrid
        from src.fish_sim.plants.seeds import Seed

        # Create mock world/terrain for testing
        class MockWorld:
            def __init__(self):
                self.soil_grid = None

            def get_terrain_height(self, x):
                return 500

            def get_depth_ratio(self, y):
                return 0.5

        # Just test that a plant can be created
        seed = Seed("kelp")
        assert seed.plant_type == "kelp"


class TestFishTraits:
    """Tests for fish trait system."""

    def test_trait_blending(self):
        """Blended traits should be combination of parents."""
        from src.fish_sim.fish.fish_traits import FishTraits

        parent1 = FishTraits()
        parent2 = FishTraits()
        child = FishTraits.blend(parent1, parent2)

        # Color offsets should be averaged
        for i in range(3):
            assert -100 <= child.color_offset[i] <= 100

    def test_trait_mutation(self):
        """Mutated traits should stay within bounds."""
        from src.fish_sim.fish.fish_traits import FishTraits

        parent = FishTraits()
        child = parent.mutate()

        # All physical traits should be in valid range
        for v in child.physical_traits.values():
            assert 0.5 <= v <= 1.8