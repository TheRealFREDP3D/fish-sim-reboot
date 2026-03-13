"""Simple feed-forward neural network for fish AI - Optimized for evolution"""

import math
import random
import copy

class NeuralNet:
    """Simplified feed-forward neural network with two hidden layers"""
    
    def __init__(self, input_size, hidden_size=8, output_size=3):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Initialize weights with Xavier/Glorot-like variance for better starting stability
        scale1 = math.sqrt(2.0 / (input_size + hidden_size))
        self.w1 = [[random.uniform(-scale1, scale1) for _ in range(input_size)] for _ in range(hidden_size)]
        self.b1 = [0.0 for _ in range(hidden_size)]
        
        # Add second hidden layer with 6 neurons
        self.hidden2_size = 6
        scale2 = math.sqrt(2.0 / (hidden_size + self.hidden2_size))
        self.w2 = [[random.uniform(-scale2, scale2) for _ in range(hidden_size)] for _ in range(self.hidden2_size)]
        self.b2 = [0.0 for _ in range(self.hidden2_size)]
        
        scale3 = math.sqrt(2.0 / (self.hidden2_size + output_size))
        self.w3 = [[random.uniform(-scale3, scale3) for _ in range(self.hidden2_size)] for _ in range(output_size)]
        self.b3 = [0.0 for _ in range(output_size)]
    
    def sigmoid(self, x):
        return 1 / (1 + math.exp(-max(-15, min(15, x))))

    def tanh(self, x):
        return math.tanh(max(-15, min(15, x)))
    
    def forward(self, inputs):
        """Run forward pass and return outputs (using tanh for steering)"""
        # Input to first hidden
        hidden = []
        for i in range(self.hidden_size):
            sum_val = sum(inputs[j] * self.w1[i][j] for j in range(self.input_size)) + self.b1[i]
            hidden.append(self.tanh(sum_val))
        
        # First hidden to second hidden
        hidden2 = []
        for i in range(self.hidden2_size):
            sum_val = sum(hidden[j] * self.w2[i][j] for j in range(self.hidden_size)) + self.b2[i]
            hidden2.append(self.tanh(sum_val))
        
        # Second hidden to output
        outputs = []
        for i in range(self.output_size):
            sum_val = sum(hidden2[j] * self.w3[i][j] for j in range(self.hidden2_size)) + self.b3[i]
            outputs.append(self.tanh(sum_val))
        
        return outputs, hidden, hidden2
    
    @staticmethod
    def blend(parent1, parent2):
        """Create a new network by blending weights from two parents."""
        if (parent1.input_size != parent2.input_size or
            parent1.hidden_size != parent2.hidden_size or
            parent1.output_size != parent2.output_size):
            raise ValueError("Cannot blend networks with different architectures")
        
        child = NeuralNet(parent1.input_size, parent1.hidden_size, parent1.output_size)
        
        def blend_matrix(m1, m2):
            """Element-wise average of two matrices."""
            return [[(m1[i][j] + m2[i][j]) * 0.5 for j in range(len(m1[0]))] for i in range(len(m1))]
        
        def blend_vector(v1, v2):
            """Element-wise average of two vectors."""
            return [(v1[i] + v2[i]) * 0.5 for i in range(len(v1))]
        
        child.w1 = blend_matrix(parent1.w1, parent2.w1)
        child.b1 = blend_vector(parent1.b1, parent2.b1)
        child.w2 = blend_matrix(parent1.w2, parent2.w2)
        child.b2 = blend_vector(parent1.b2, parent2.b2)
        child.w3 = blend_matrix(parent1.w3, parent2.w3)
        child.b3 = blend_vector(parent1.b3, parent2.b3)
        
        return child
    
    def mutate(self, mutation_rate=0.1, mutation_strength=0.2):
        """Create mutated copy for offspring"""
        # Create new network with same architecture
        child = NeuralNet(self.input_size, self.hidden_size, self.output_size)
        
        # Copy weights and biases efficiently using list comprehensions
        child.w1 = [row[:] for row in self.w1]
        child.b1 = self.b1[:]
        child.w2 = [row[:] for row in self.w2]
        child.b2 = self.b2[:]
        child.w3 = [row[:] for row in self.w3]
        child.b3 = self.b3[:]
        
        def mutate_list(lst):
            for i in range(len(lst)):
                if isinstance(lst[i], list):
                    mutate_list(lst[i])
                elif random.random() < mutation_rate:
                    lst[i] += random.gauss(0, mutation_strength)
                    # Keep weights in a reasonable range
                    lst[i] = max(-2.0, min(2.0, lst[i]))

        mutate_list(child.w1)
        mutate_list(child.b1)
        mutate_list(child.w2)
        mutate_list(child.b2)
        mutate_list(child.w3)
        mutate_list(child.b3)
        
        return child