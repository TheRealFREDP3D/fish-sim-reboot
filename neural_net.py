"""Simple feed-forward neural network for fish AI - Optimized for evolution"""

import math
import random


class NeuralNet:
    """Feed-forward neural network with two hidden layers.

    Output layout (9 neurons):
        [0] steer        — tanh, movement direction delta
        [1] thrust       — tanh, forward drive
        [2] hide_drive   — sigmoid, tendency to seek plant cover
        [3] sprint_drive — sigmoid, temporary speed ceiling boost
        [4] REST         — state logit (raw, passed through softmax externally)
        [5] HUNT         — state logit
        [6] FLEE         — state logit
        [7] MATE         — state logit
        [8] NEST         — state logit
    """

    MOVEMENT_OUTPUTS = 2
    BEHAVIOR_OUTPUTS = 2
    STATE_OUTPUTS = 5

    def __init__(self, input_size, hidden_size=8, output_size=9):
        self.input_size = input_size
        self.hidden_size = hidden_size
        # Total outputs: 2 movement + 2 behavior + 5 states
        self.output_size = max(output_size, self.MOVEMENT_OUTPUTS + self.BEHAVIOR_OUTPUTS + self.STATE_OUTPUTS)

        scale1 = math.sqrt(2.0 / (input_size + hidden_size))
        self.w1 = [
            [random.uniform(-scale1, scale1) for _ in range(input_size)]
            for _ in range(hidden_size)
        ]
        self.b1 = [0.0 for _ in range(hidden_size)]

        self.hidden2_size = 6
        scale2 = math.sqrt(2.0 / (hidden_size + self.hidden2_size))
        self.w2 = [
            [random.uniform(-scale2, scale2) for _ in range(hidden_size)]
            for _ in range(self.hidden2_size)
        ]
        self.b2 = [0.0 for _ in range(self.hidden2_size)]

        scale3 = math.sqrt(2.0 / (self.hidden2_size + self.output_size))
        self.w3 = [
            [random.uniform(-scale3, scale3) for _ in range(self.hidden2_size)]
            for _ in range(self.output_size)
        ]
        self.b3 = [0.0 for _ in range(self.output_size)]

    def sigmoid(self, x):
        return 1 / (1 + math.exp(-max(-15, min(15, x))))

    def tanh(self, x):
        return math.tanh(max(-15, min(15, x)))

    @staticmethod
    def softmax(logits):
        """Numerically stable softmax over a list of floats."""
        if not logits:
            return []
        m = max(logits)
        exps = [math.exp(v - m) for v in logits]
        s = sum(exps)
        return [e / s for e in exps]

    def forward(self, inputs):
        """Run forward pass.

        Returns:
            outputs   — list[9]: [steer, thrust, hide, sprint, rest_p, hunt_p, flee_p, mate_p, nest_p]
            hidden    — list[6]: second hidden layer activations
            hidden2   — alias for hidden
        """
        # Input → hidden1
        hidden = []
        for i in range(self.hidden_size):
            s = sum(inputs[j] * self.w1[i][j] for j in range(self.input_size)) + self.b1[i]
            hidden.append(self.tanh(s))

        # Hidden1 → hidden2
        hidden2 = []
        for i in range(self.hidden2_size):
            s = sum(hidden[j] * self.w2[i][j] for j in range(self.hidden_size)) + self.b2[i]
            hidden2.append(self.tanh(s))

        # Hidden2 → raw outputs
        raw = []
        for i in range(self.output_size):
            s = sum(hidden2[j] * self.w3[i][j] for j in range(self.hidden2_size)) + self.b3[i]
            raw.append(s)

        # 1. Movement: tanh (indices 0-1)
        steer = self.tanh(raw[0])
        thrust = self.tanh(raw[1])

        # 2. Behavior Drives: sigmoid (indices 2-3)
        hide_drive = self.sigmoid(raw[2])
        sprint_drive = self.sigmoid(raw[3])

        # 3. States: softmax (indices 4-8)
        state_probs = self.softmax(raw[4:9])

        outputs = [steer, thrust, hide_drive, sprint_drive] + state_probs
        return outputs, hidden, hidden2

    @staticmethod
    def blend(parent1, parent2):
        """Create a new network by uniform crossover from two parents.
        
        Each weight/bias is randomly taken from either parent (not averaged),
        preserving complete sub-circuits and learned behaviors.
        """
        if (parent1.input_size != parent2.input_size or
                parent1.hidden_size != parent2.hidden_size or
                parent1.output_size != parent2.output_size):
            raise ValueError("Cannot blend networks with different architectures")

        child = NeuralNet(parent1.input_size, parent1.hidden_size, parent1.output_size)

        def crossover_matrix(m1, m2):
            """Randomly pick each weight from either parent."""
            return [
                [m1[i][j] if random.random() < 0.5 else m2[i][j] 
                 for j in range(len(m1[0]))]
                for i in range(len(m1))
            ]

        def crossover_vector(v1, v2):
            """Randomly pick each bias from either parent."""
            return [v1[i] if random.random() < 0.5 else v2[i] 
                    for i in range(len(v1))]

        child.w1 = crossover_matrix(parent1.w1, parent2.w1)
        child.b1 = crossover_vector(parent1.b1, parent2.b1)
        child.w2 = crossover_matrix(parent1.w2, parent2.w2)
        child.b2 = crossover_vector(parent1.b2, parent2.b2)
        child.w3 = crossover_matrix(parent1.w3, parent2.w3)
        child.b3 = crossover_vector(parent1.b3, parent2.b3)

        return child

    def mutate(self, mutation_rate=0.1, mutation_strength=0.2):
        """Create a mutated copy for offspring with layer-specific exploration rates."""
        child = NeuralNet(self.input_size, self.hidden_size, self.output_size)

        child.w1 = [row[:] for row in self.w1]
        child.b1 = self.b1[:]
        child.w2 = [row[:] for row in self.w2]
        child.b2 = self.b2[:]
        child.w3 = [row[:] for row in self.w3]
        child.b3 = self.b3[:]

        def mutate_list(lst, strength):
            for i in range(len(lst)):
                if isinstance(lst[i], list):
                    mutate_list(lst[i], strength)
                elif random.random() < mutation_rate:
                    lst[i] += random.gauss(0, strength)
                    lst[i] = max(-2.0, min(2.0, lst[i]))

        # Early layers explore more (higher strength)
        mutate_list(child.w1, mutation_strength * 1.2)
        mutate_list(child.b1, mutation_strength * 1.2)

        # Middle layer standard strength
        mutate_list(child.w2, mutation_strength)
        mutate_list(child.b2, mutation_strength)

        # Output layer mutates conservatively (lower strength)
        mutate_list(child.w3, mutation_strength * 0.5)
        mutate_list(child.b3, mutation_strength * 0.5)

        return child