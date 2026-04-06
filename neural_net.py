"""Improved Neural Network for Fish AI

Features:
- Recurrent connections for temporal memory
- Layer-specific mutation rates for structured exploration
- Xavier initialization for better gradient flow
- Proper weight clamping to prevent explosion
- Softmax state outputs with support for reduced biases
"""

import math
import random
from config import (
    NN_INPUT_COUNT,
    NN_HIDDEN1_SIZE,
    NN_HIDDEN2_SIZE,
    NN_OUTPUT_COUNT,
    NN_RECURRENT,
    NN_RECURRENT_DECAY,
    NN_MUTATION_RATE_INPUT,
    NN_MUTATION_RATE_HIDDEN,
    NN_MUTATION_RATE_OUTPUT,
    NN_MUTATION_RATE_RECURRENT,
    NN_MUTATION_STRENGTH_INPUT,
    NN_MUTATION_STRENGTH_HIDDEN,
    NN_MUTATION_STRENGTH_OUTPUT,
    NN_MUTATION_STRENGTH_RECURRENT,
    NN_WEIGHT_MAX,
    NN_BIAS_MAX,
    INPUT_MAX_ABS_VALUE,
)


class NeuralNet:
    """Feed-forward neural network with optional recurrent connections.
    
    Architecture:
        Input (NN_INPUT_COUNT) 
          → Hidden1 (NN_HIDDEN1_SIZE, tanh) 
          → Hidden2 (NN_HIDDEN2_SIZE, tanh + recurrent) 
          → Output (NN_OUTPUT_COUNT)
    
    Outputs:
        0: steer (tanh, -1 to 1)
        1: thrust (sigmoid, 0 to 1)
        2: behavior_drive_1 (sigmoid, 0 to 1) - hide/clean/ambush
        3: behavior_drive_2 (sigmoid, 0 to 1) - sprint/dash
        4-8: state probabilities (softmax)
    """

    def __init__(self, input_size=None, hidden_size=None, output_size=None, recurrent=None):
        """Initialize the neural network with Xavier initialization.
        
        Args:
            input_size: Number of input neurons (default: NN_INPUT_COUNT)
            hidden_size: Size of first hidden layer (default: NN_HIDDEN1_SIZE)
            output_size: Number of output neurons (default: NN_OUTPUT_COUNT)
            recurrent: Whether to use recurrent connections (default: NN_RECURRENT)
        """
        # Use config defaults if not specified
        self.input_size = input_size if input_size is not None else NN_INPUT_COUNT
        self.hidden_size = hidden_size if hidden_size is not None else NN_HIDDEN1_SIZE
        self.hidden2_size = NN_HIDDEN2_SIZE
        self.output_size = output_size if output_size is not None else NN_OUTPUT_COUNT
        self.recurrent = recurrent if recurrent is not None else NN_RECURRENT

        # Layer 1: Input -> Hidden 1
        scale1 = math.sqrt(2.0 / (self.input_size + self.hidden_size))
        self.w1 = [
            [random.gauss(0, scale1) for _ in range(self.input_size)]
            for _ in range(self.hidden_size)
        ]
        self.b1 = [0.0 for _ in range(self.hidden_size)]

        # Layer 2: Hidden 1 -> Hidden 2
        scale2 = math.sqrt(2.0 / (self.hidden_size + self.hidden2_size))
        self.w2 = [
            [random.gauss(0, scale2) for _ in range(self.hidden_size)]
            for _ in range(self.hidden2_size)
        ]
        self.b2 = [0.0 for _ in range(self.hidden2_size)]

        # Recurrent weights for temporal memory
        if self.recurrent:
            scale_rec = math.sqrt(1.0 / self.hidden2_size)
            self.w_rec = [
                [random.gauss(0, scale_rec) for _ in range(self.hidden2_size)]
                for _ in range(self.hidden2_size)
            ]
            # Hidden state persists across frames
            self.hidden_state = [0.0] * self.hidden2_size

        # Layer 3: Hidden 2 -> Output
        scale3 = math.sqrt(2.0 / (self.hidden2_size + self.output_size))
        self.w3 = [
            [random.gauss(0, scale3) for _ in range(self.hidden2_size)]
            for _ in range(self.output_size)
        ]
        self.b3 = [0.0 for _ in range(self.output_size)]

    # ── Activation Functions ─────────────────────────────────────────────────

    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid activation: output in (0, 1)"""
        return 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, x))))

    @staticmethod
    def tanh(x: float) -> float:
        """Tanh activation: output in (-1, 1)"""
        return math.tanh(max(-15.0, min(15.0, x)))

    @staticmethod
    def relu(x: float) -> float:
        """ReLU activation: output in [0, inf)"""
        return max(0.0, x)

    @staticmethod
    def softmax(logits: list) -> list:
        """Softmax activation: outputs sum to 1.0"""
        if not logits:
            return []
        max_logit = max(logits)
        exps = [math.exp(v - max_logit) for v in logits]
        sum_exps = sum(exps)
        return [e / sum_exps for e in exps]

    # ── Forward Pass ─────────────────────────────────────────────────────────

    def forward(self, inputs: list) -> tuple:
        """Run forward pass through the network.
        
        Args:
            inputs: List of input values (will be normalized)
            
        Returns:
            Tuple of (outputs, hidden1_activations, hidden2_activations)
            outputs: [steer, thrust, behavior1, behavior2, state_probs...]
        """
        # Normalize inputs to prevent extreme activations
        normalized = [max(-INPUT_MAX_ABS_VALUE, min(INPUT_MAX_ABS_VALUE, x)) for x in inputs]

        # Layer 1: Input -> Hidden 1 (tanh)
        h1 = []
        for i in range(self.hidden_size):
            weighted_sum = sum(normalized[j] * self.w1[i][j] for j in range(self.input_size))
            weighted_sum += self.b1[i]
            h1.append(self.tanh(weighted_sum))

        # Layer 2: Hidden 1 -> Hidden 2 (tanh with optional recurrence)
        h2_pre = []
        for i in range(self.hidden2_size):
            weighted_sum = sum(h1[j] * self.w2[i][j] for j in range(self.hidden_size))
            weighted_sum += self.b2[i]
            h2_pre.append(weighted_sum)

        # Apply recurrent connection
        if self.recurrent:
            h2 = []
            for i in range(self.hidden2_size):
                # Combine feedforward and recurrent signals
                recurrent_sum = sum(
                    self.hidden_state[j] * self.w_rec[i][j]
                    for j in range(self.hidden2_size)
                )
                # Blend with decay factor
                combined = h2_pre[i] + recurrent_sum * 0.5
                h2.append(self.tanh(combined))

            # Update hidden state for next frame (with decay)
            decay = NN_RECURRENT_DECAY
            self.hidden_state = [
                decay * h2[i] + (1.0 - decay) * self.hidden_state[i]
                for i in range(self.hidden2_size)
            ]
        else:
            h2 = [self.tanh(s) for s in h2_pre]

        # Output layer
        raw_outputs = []
        for i in range(self.output_size):
            weighted_sum = sum(h2[j] * self.w3[i][j] for j in range(self.hidden2_size))
            weighted_sum += self.b3[i]
            raw_outputs.append(weighted_sum)

        # Apply output-specific activations
        # Output 0: steer (tanh, -1 to 1)
        steer = self.tanh(raw_outputs[0])
        
        # Output 1: thrust (sigmoid, 0 to 1)
        thrust = self.sigmoid(raw_outputs[1])
        
        # Outputs 2-3: behavior drives (sigmoid, 0 to 1)
        behavior1 = self.sigmoid(raw_outputs[2]) if len(raw_outputs) > 2 else 0.5
        behavior2 = self.sigmoid(raw_outputs[3]) if len(raw_outputs) > 3 else 0.5
        
        # Outputs 4-8: state probabilities (softmax)
        state_logits = raw_outputs[4:9] if len(raw_outputs) >= 9 else [0.0] * 5
        state_probs = self.softmax(state_logits)

        # Combine all outputs
        outputs = [steer, thrust, behavior1, behavior2] + state_probs

        return outputs, h1, h2

    # ── State Management ─────────────────────────────────────────────────────

    def reset_hidden(self):
        """Reset recurrent hidden state (e.g., on fish death/birth)."""
        if self.recurrent:
            self.hidden_state = [0.0] * self.hidden2_size

    def copy(self) -> 'NeuralNet':
        """Create an identical copy of this network."""
        child = NeuralNet(
            self.input_size,
            self.hidden_size,
            self.output_size,
            recurrent=self.recurrent
        )
        
        # Deep copy all weights
        child.w1 = [row[:] for row in self.w1]
        child.b1 = self.b1[:]
        child.w2 = [row[:] for row in self.w2]
        child.b2 = self.b2[:]
        child.w3 = [row[:] for row in self.w3]
        child.b3 = self.b3[:]
        
        if self.recurrent:
            child.w_rec = [row[:] for row in self.w_rec]
            child.hidden_state = [0.0] * self.hidden2_size
            
        return child

    # ── Reproduction ─────────────────────────────────────────────────────────

    @staticmethod
    def blend(parent1: 'NeuralNet', parent2: 'NeuralNet') -> 'NeuralNet':
        """Create a child network via uniform crossover of two parents.
        
        Args:
            parent1: First parent network
            parent2: Second parent network
            
        Returns:
            Child network with mixed weights from both parents
        """
        # Validate compatible architectures
        if (parent1.input_size != parent2.input_size or
            parent1.hidden_size != parent2.hidden_size or
            parent1.output_size != parent2.output_size):
            raise ValueError("Cannot blend networks with different architectures")

        child = NeuralNet(
            parent1.input_size,
            parent1.hidden_size,
            parent1.output_size,
            recurrent=(parent1.recurrent and parent2.recurrent)
        )

        def crossover_matrix(m1: list, m2: list) -> list:
            """Per-weight uniform crossover between two matrices."""
            return [
                [m1[i][j] if random.random() < 0.5 else m2[i][j]
                 for j in range(len(m1[0]))]
                for i in range(len(m1))
            ]

        def crossover_vector(v1: list, v2: list) -> list:
            """Per-weight uniform crossover between two vectors."""
            return [v1[i] if random.random() < 0.5 else v2[i] for i in range(len(v1))]

        # Crossover all layers
        child.w1 = crossover_matrix(parent1.w1, parent2.w1)
        child.b1 = crossover_vector(parent1.b1, parent2.b1)
        child.w2 = crossover_matrix(parent1.w2, parent2.w2)
        child.b2 = crossover_vector(parent1.b2, parent2.b2)
        child.w3 = crossover_matrix(parent1.w3, parent2.w3)
        child.b3 = crossover_vector(parent1.b3, parent2.b3)

        if child.recurrent:
            child.w_rec = crossover_matrix(parent1.w_rec, parent2.w_rec)

        return child

    def mutate(self, rate: float = None, strength: float = None) -> 'NeuralNet':
        """Create a mutated copy with layer-specific mutation rates.
        
        Args:
            rate: Base mutation rate (default: uses config values)
            strength: Base mutation strength (default: uses config values)
            
        Returns:
            Mutated copy of this network
        """
        child = self.copy()

        def mutate_matrix(matrix: list, rate_mult: float, strength_mult: float, base_rate: float, base_strength: float) -> list:
            """Mutate a weight matrix with Gaussian noise."""
            result = []
            for row in matrix:
                new_row = []
                for val in row:
                    if random.random() < base_rate * rate_mult:
                        delta = random.gauss(0, base_strength * strength_mult)
                        new_val = val + delta
                        # Clamp to prevent explosion
                        new_val = max(-NN_WEIGHT_MAX, min(NN_WEIGHT_MAX, new_val))
                        new_row.append(new_val)
                    else:
                        new_row.append(val)
                result.append(new_row)
            return result

        def mutate_vector(vector: list, rate_mult: float, strength_mult: float, base_rate: float, base_strength: float) -> list:
            """Mutate a bias vector with Gaussian noise."""
            return [
                max(-NN_BIAS_MAX, min(NN_BIAS_MAX, v + random.gauss(0, base_strength * strength_mult)))
                if random.random() < base_rate * rate_mult else v
                for v in vector
            ]

        # Use config defaults if not specified (treat 0 as None to avoid division by zero)
        base_rate = rate if rate is not None and rate != 0.0 else 0.1
        base_strength = strength if strength is not None and strength != 0.0 else 0.2

        # Layer 1: Higher mutation for sensory adaptation
        child.w1 = mutate_matrix(child.w1, NN_MUTATION_RATE_INPUT / base_rate, 
                                  NN_MUTATION_STRENGTH_INPUT / base_strength, base_rate, base_strength)
        child.b1 = mutate_vector(child.b1, 1.0, 1.0, base_rate, base_strength)

        # Layer 2: Standard mutation
        child.w2 = mutate_matrix(child.w2, NN_MUTATION_RATE_HIDDEN / base_rate,
                                  NN_MUTATION_STRENGTH_HIDDEN / base_strength, base_rate, base_strength)
        child.b2 = mutate_vector(child.b2, 1.0, 1.0, base_rate, base_strength)

        # Output layer: Lower mutation to preserve learned behaviors
        child.w3 = mutate_matrix(child.w3, NN_MUTATION_RATE_OUTPUT / base_rate,
                                  NN_MUTATION_STRENGTH_OUTPUT / base_strength, base_rate, base_strength)
        child.b3 = mutate_vector(child.b3, 0.5, 0.5, base_rate, base_strength)

        # Recurrent weights: Very low mutation for memory stability
        if child.recurrent:
            child.w_rec = mutate_matrix(child.w_rec, NN_MUTATION_RATE_RECURRENT / base_rate,
                                         NN_MUTATION_STRENGTH_RECURRENT / base_strength, base_rate, base_strength)

        return child

    # ── Utility Methods ──────────────────────────────────────────────────────

    def get_weight_stats(self) -> dict:
        """Get statistics about network weights for debugging."""
        def stats(matrix):
            flat = [v for row in matrix for v in row]
            return {
                'mean': sum(flat) / len(flat),
                'min': min(flat),
                'max': max(flat),
                'std': math.sqrt(sum((v - sum(flat)/len(flat))**2 for v in flat) / len(flat))
            }
        
        return {
            'w1': stats(self.w1),
            'w2': stats(self.w2),
            'w3': stats(self.w3),
            'recurrent': stats(self.w_rec) if self.recurrent else None,
        }
