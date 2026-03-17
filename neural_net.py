"""Simple feed-forward neural network for fish AI - Optimized for evolution"""

import math
import random


class NeuralNet:
    """Feed-forward neural network with two hidden layers."""

    MOVEMENT_OUTPUTS = 2
    BEHAVIOR_OUTPUTS = 2
    STATE_OUTPUTS = 5

    def __init__(self, input_size, hidden_size=8, output_size=9):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = max(
            output_size,
            self.MOVEMENT_OUTPUTS + self.BEHAVIOR_OUTPUTS + self.STATE_OUTPUTS,
        )

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
        if not logits:
            return []
        m = max(logits)
        exps = [math.exp(v - m) for v in logits]
        s = sum(exps)
        return [e / s for e in exps]

    def _head_slices(self):
        """Return slices for (movement, behavior, state) in the raw output vector."""
        m = self.MOVEMENT_OUTPUTS
        b = self.BEHAVIOR_OUTPUTS
        s = self.STATE_OUTPUTS
        head_total = m + b + s
        if self.output_size < head_total:
            raise ValueError(f"output_size={self.output_size} < required head size={head_total}")
        movement = slice(0, m)
        behavior = slice(m, m + b)
        state = slice(m + b, m + b + s)
        extra = slice(m + b + s, self.output_size)
        return movement, behavior, state, extra

    def forward(self, inputs):
        """Run forward pass. Returns (outputs, layer1_activations, layer2_activations)."""
        # Input -> Hidden 1
        h1 = []
        for i in range(self.hidden_size):
            s = (
                sum(inputs[j] * self.w1[i][j] for j in range(self.input_size))
                + self.b1[i]
            )
            h1.append(self.tanh(s))

        # Hidden 1 -> Hidden 2
        h2 = []
        for i in range(self.hidden2_size):
            s = sum(h1[j] * self.w2[i][j] for j in range(self.hidden_size)) + self.b2[i]
            h2.append(self.tanh(s))

        # Hidden 2 -> Output
        raw = []
        for i in range(self.output_size):
            s = (
                sum(h2[j] * self.w3[i][j] for j in range(self.hidden2_size))
                + self.b3[i]
            )
            raw.append(s)

        movement_slice, behavior_slice, state_slice, extra_slice = self._head_slices()

        movement_raw = raw[movement_slice]
        behavior_raw = raw[behavior_slice]
        state_raw = raw[state_slice]

        movement = [self.tanh(v) for v in movement_raw]
        behavior = [self.sigmoid(v) for v in behavior_raw]
        states = self.softmax(state_raw)

        outputs = movement + behavior + states

        return outputs, h1, h2

    @staticmethod
    def blend(p1, p2):
        """Create a child network by per-weight uniform crossover of two parents."""
        if (p1.input_size != p2.input_size or
            p1.hidden_size != p2.hidden_size or
            p1.output_size != p2.output_size):
            raise ValueError("Cannot blend networks with different architectures")

        child = NeuralNet(p1.input_size, p1.hidden_size, p1.output_size)

        def crossover_matrix(m1, m2):
            """Per-weight uniform crossover between two matrices."""
            return [
                [
                    m1[i][j] if random.random() < 0.5 else m2[i][j]
                    for j in range(len(m1[0]))
                ]
                for i in range(len(m1))
            ]

        def crossover_vector(v1, v2):
            """Per-weight uniform crossover between two vectors."""
            return [
                v1[i] if random.random() < 0.5 else v2[i]
                for i in range(len(v1))
            ]

        child.w1 = crossover_matrix(p1.w1, p2.w1)
        child.b1 = crossover_vector(p1.b1, p2.b1)
        child.w2 = crossover_matrix(p1.w2, p2.w2)
        child.b2 = crossover_vector(p1.b2, p2.b2)
        child.w3 = crossover_matrix(p1.w3, p2.w3)
        child.b3 = crossover_vector(p1.b3, p2.b3)

        return child

    def mutate(self, rate=0.1, strength=0.2):
        child = NeuralNet(self.input_size, self.hidden_size, self.output_size)

        def mut_l(lst, s):
            for i in range(len(lst)):
                if isinstance(lst[i], list):
                    mut_l(lst[i], s)
                elif random.random() < rate:
                    lst[i] = max(-2.0, min(2.0, lst[i] + random.gauss(0, s)))

        child.w1, child.b1 = [r[:] for r in self.w1], self.b1[:]
        child.w2, child.b2 = [r[:] for r in self.w2], self.b2[:]
        child.w3, child.b3 = [r[:] for r in self.w3], self.b3[:]
        mut_l(child.w1, strength * 1.2)
        mut_l(child.b1, strength * 1.2)
        mut_l(child.w2, strength)
        mut_l(child.b2, strength)
        mut_l(child.w3, strength * 0.5)
        mut_l(child.b3, strength * 0.5)
        return child
