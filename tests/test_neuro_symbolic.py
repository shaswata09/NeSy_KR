"""
Unit tests for neuro-symbolic integration.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nesy_kr import Entity, Predicate, Fact, NeuroSymbolicKB


class TestNeuroSymbolicKB(unittest.TestCase):
    def setUp(self):
        self.kb = NeuroSymbolicKB(embedding_dim=16, hidden_dim=32)
        
        # Create entities
        self.alice = Entity("Alice")
        self.bob = Entity("Bob")
        self.charlie = Entity("Charlie")
        
        # Create predicates
        self.knows = Predicate("knows", 2)
        self.friends = Predicate("friends", 2)
        
        # Add to KB
        self.kb.add_entity(self.alice)
        self.kb.add_entity(self.bob)
        self.kb.add_entity(self.charlie)
        self.kb.add_predicate(self.knows)
        self.kb.add_predicate(self.friends)
    
    def test_initialization(self):
        self.assertEqual(self.kb.embedding_dim, 16)
        self.assertEqual(self.kb.hidden_dim, 32)
        self.assertIsNone(self.kb.entity_embedding)
        self.assertIsNone(self.kb.neural_predictor)
    
    def test_add_entity(self):
        new_entity = Entity("Diana")
        self.kb.add_entity(new_entity)
        self.assertIn(new_entity, self.kb.symbolic_kb.entities)
    
    def test_add_fact(self):
        fact = Fact(self.knows, (self.alice, self.bob))
        self.kb.add_fact(fact)
        self.assertIn(fact, self.kb.symbolic_kb.facts)
    
    def test_query(self):
        fact1 = Fact(self.knows, (self.alice, self.bob))
        fact2 = Fact(self.knows, (self.bob, self.charlie))
        
        self.kb.add_fact(fact1)
        self.kb.add_fact(fact2)
        
        results = self.kb.query("knows", self.alice)
        self.assertEqual(len(results), 1)
        self.assertIn(fact1, results)
    
    def test_initialize_neural_components(self):
        self.kb.add_fact(Fact(self.knows, (self.alice, self.bob)))
        self.kb.initialize_neural_components()
        
        self.assertIsNotNone(self.kb.entity_embedding)
        self.assertIsNotNone(self.kb.neural_predictor)
    
    def test_predict_fact(self):
        self.kb.add_fact(Fact(self.knows, (self.alice, self.bob)))
        self.kb.initialize_neural_components()
        
        test_fact = Fact(self.friends, (self.alice, self.charlie))
        confidence = self.kb.predict_fact(test_fact)
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_predict_without_initialization(self):
        fact = Fact(self.knows, (self.alice, self.bob))
        
        with self.assertRaises(ValueError):
            self.kb.predict_fact(fact)
    
    def test_hybrid_query(self):
        self.kb.add_fact(Fact(self.knows, (self.alice, self.bob)))
        self.kb.initialize_neural_components()
        
        results = self.kb.hybrid_query("knows")
        
        # Should have at least the symbolic fact
        self.assertGreaterEqual(len(results), 1)
        
        # Each result should be a tuple of (fact, confidence, source)
        for fact, confidence, source in results:
            self.assertIsInstance(fact, Fact)
            self.assertIsInstance(confidence, float)
            self.assertIn(source, ['symbolic', 'neural'])
    
    def test_entity_similarity(self):
        self.kb.add_fact(Fact(self.knows, (self.alice, self.bob)))
        self.kb.initialize_neural_components()
        
        similarity = self.kb.get_entity_similarity(self.alice, self.bob)
        
        self.assertIsInstance(similarity, float)
        self.assertGreaterEqual(similarity, -1.0)
        self.assertLessEqual(similarity, 1.0)


if __name__ == '__main__':
    unittest.main()
