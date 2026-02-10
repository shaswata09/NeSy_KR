"""
Unit tests for neural components.
"""

import unittest
import torch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nesy_kr.symbolic import Entity, Predicate, Fact
from nesy_kr.neural import EntityEmbedding, NeuralPredictor


class TestEntityEmbedding(unittest.TestCase):
    def setUp(self):
        self.embedding = EntityEmbedding(num_entities=5, embedding_dim=16)
        self.alice = Entity("Alice")
        self.bob = Entity("Bob")
        
        self.embedding.add_entity(self.alice, 0)
        self.embedding.add_entity(self.bob, 1)
    
    def test_embedding_creation(self):
        self.assertEqual(self.embedding.embedding_dim, 16)
        self.assertEqual(len(self.embedding.entity_to_idx), 2)
    
    def test_get_embedding(self):
        emb = self.embedding.get_embedding(self.alice)
        self.assertEqual(emb.shape, (16,))
        self.assertIsInstance(emb, torch.Tensor)
    
    def test_embedding_consistency(self):
        emb1 = self.embedding.get_embedding(self.alice)
        emb2 = self.embedding.get_embedding(self.alice)
        self.assertTrue(torch.equal(emb1, emb2))
    
    def test_unknown_entity(self):
        unknown = Entity("Unknown")
        with self.assertRaises(ValueError):
            self.embedding.get_embedding(unknown)


class TestNeuralPredictor(unittest.TestCase):
    def setUp(self):
        self.predictor = NeuralPredictor(
            embedding_dim=16,
            hidden_dim=32,
            num_predicates=3
        )
        self.embedding = EntityEmbedding(num_entities=5, embedding_dim=16)
        
        self.alice = Entity("Alice")
        self.bob = Entity("Bob")
        self.knows = Predicate("knows", 2)
        
        self.embedding.add_entity(self.alice, 0)
        self.embedding.add_entity(self.bob, 1)
        self.predictor.add_predicate(self.knows, 0)
    
    def test_predictor_creation(self):
        self.assertEqual(self.predictor.embedding_dim, 16)
        self.assertEqual(self.predictor.hidden_dim, 32)
    
    def test_forward_pass(self):
        # Create random embeddings
        entity_embeddings = torch.randn(2, 2, 16)
        scores = self.predictor.forward(entity_embeddings)
        
        self.assertEqual(scores.shape, (2, 3))
        self.assertIsInstance(scores, torch.Tensor)
    
    def test_predict_fact(self):
        fact = Fact(self.knows, (self.alice, self.bob))
        confidence = self.predictor.predict_fact(fact, self.embedding)
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_predict_non_binary_predicate(self):
        ternary_pred = Predicate("ternary", 3)
        charlie = Entity("Charlie")
        self.embedding.add_entity(charlie, 2)
        
        fact = Fact(ternary_pred, (self.alice, self.bob, charlie))
        
        with self.assertRaises(ValueError):
            self.predictor.predict_fact(fact, self.embedding)


if __name__ == '__main__':
    unittest.main()
