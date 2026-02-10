"""
Unit tests for symbolic knowledge representation components.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nesy_kr.symbolic import Entity, Predicate, Fact, Rule, KnowledgeBase


class TestEntity(unittest.TestCase):
    def test_entity_creation(self):
        entity = Entity("test")
        self.assertEqual(entity.name, "test")
        self.assertEqual(entity.attributes, {})
    
    def test_entity_with_attributes(self):
        entity = Entity("test", {"age": 30, "type": "person"})
        self.assertEqual(entity.attributes["age"], 30)
        self.assertEqual(entity.attributes["type"], "person")
    
    def test_entity_equality(self):
        e1 = Entity("test")
        e2 = Entity("test")
        e3 = Entity("other")
        self.assertEqual(e1, e2)
        self.assertNotEqual(e1, e3)
    
    def test_entity_hash(self):
        e1 = Entity("test")
        e2 = Entity("test")
        self.assertEqual(hash(e1), hash(e2))
        entity_set = {e1, e2}
        self.assertEqual(len(entity_set), 1)


class TestPredicate(unittest.TestCase):
    def test_predicate_creation(self):
        pred = Predicate("parent_of", 2)
        self.assertEqual(pred.name, "parent_of")
        self.assertEqual(pred.arity, 2)
    
    def test_predicate_equality(self):
        p1 = Predicate("test", 2)
        p2 = Predicate("test", 2)
        p3 = Predicate("test", 3)
        p4 = Predicate("other", 2)
        
        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertNotEqual(p1, p4)


class TestFact(unittest.TestCase):
    def test_fact_creation(self):
        pred = Predicate("parent_of", 2)
        e1 = Entity("Alice")
        e2 = Entity("Bob")
        fact = Fact(pred, (e1, e2))
        
        self.assertEqual(fact.predicate, pred)
        self.assertEqual(fact.entities, (e1, e2))
        self.assertEqual(fact.confidence, 1.0)
    
    def test_fact_arity_mismatch(self):
        pred = Predicate("parent_of", 2)
        e1 = Entity("Alice")
        
        with self.assertRaises(ValueError):
            Fact(pred, (e1,))
    
    def test_fact_equality(self):
        pred = Predicate("parent_of", 2)
        e1 = Entity("Alice")
        e2 = Entity("Bob")
        
        f1 = Fact(pred, (e1, e2))
        f2 = Fact(pred, (e1, e2))
        f3 = Fact(pred, (e2, e1))
        
        self.assertEqual(f1, f2)
        self.assertNotEqual(f1, f3)


class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase()
        self.alice = Entity("Alice")
        self.bob = Entity("Bob")
        self.charlie = Entity("Charlie")
        self.parent_of = Predicate("parent_of", 2)
    
    def test_add_entity(self):
        self.kb.add_entity(self.alice)
        self.assertIn(self.alice, self.kb.entities)
    
    def test_add_predicate(self):
        self.kb.add_predicate(self.parent_of)
        self.assertIn(self.parent_of, self.kb.predicates)
    
    def test_add_fact(self):
        fact = Fact(self.parent_of, (self.alice, self.bob))
        self.kb.add_fact(fact)
        
        self.assertIn(fact, self.kb.facts)
        self.assertIn(self.alice, self.kb.entities)
        self.assertIn(self.bob, self.kb.entities)
        self.assertIn(self.parent_of, self.kb.predicates)
    
    def test_query(self):
        fact1 = Fact(self.parent_of, (self.alice, self.bob))
        fact2 = Fact(self.parent_of, (self.alice, self.charlie))
        fact3 = Fact(self.parent_of, (self.bob, self.charlie))
        
        self.kb.add_fact(fact1)
        self.kb.add_fact(fact2)
        self.kb.add_fact(fact3)
        
        # Query with specific entity
        results = self.kb.query("parent_of", self.alice)
        self.assertEqual(len(results), 2)
        self.assertIn(fact1, results)
        self.assertIn(fact2, results)
        
        # Query all facts for predicate
        results = self.kb.query("parent_of")
        self.assertEqual(len(results), 3)
    
    def test_inference(self):
        # Create grandparent rule
        grandparent = Predicate("grandparent_of", 2)
        diana = Entity("Diana")
        
        # Facts: Alice parent of Bob, Bob parent of Diana
        self.kb.add_fact(Fact(self.parent_of, (self.alice, self.bob)))
        self.kb.add_fact(Fact(self.parent_of, (self.bob, diana)))
        
        # Rule: grandparent(X, Z) :- parent(X, Y), parent(Y, Z)
        rule = Rule(
            head=Fact(grandparent, (self.alice, diana)),
            body=[
                Fact(self.parent_of, (self.alice, self.bob)),
                Fact(self.parent_of, (self.bob, diana))
            ]
        )
        self.kb.add_rule(rule)
        
        # Perform inference
        inferred = self.kb.infer()
        
        # Check if grandparent fact was inferred
        grandparent_fact = Fact(grandparent, (self.alice, diana))
        self.assertIn(grandparent_fact, inferred)


if __name__ == '__main__':
    unittest.main()
