"""
NeuroSymbolic Integration Module

This module combines symbolic knowledge representation with neural learning
to create a hybrid reasoning system.
"""

import torch
from typing import List, Set, Dict, Optional, Tuple
from .symbolic import Entity, Predicate, Fact, Rule, KnowledgeBase
from .neural import EntityEmbedding, NeuralPredictor


class NeuroSymbolicKB:
    """
    NeuroSymbolic Knowledge Base combining symbolic and neural reasoning.
    
    This class integrates:
    - Symbolic knowledge (facts, rules)
    - Neural embeddings (entity representations)
    - Neural prediction (confidence estimation)
    """
    
    def __init__(self, embedding_dim: int = 64, hidden_dim: int = 128):
        """
        Initialize neuro-symbolic knowledge base.
        
        Args:
            embedding_dim: Dimension for entity embeddings
            hidden_dim: Hidden dimension for neural predictor
        """
        self.symbolic_kb = KnowledgeBase()
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Neural components (initialized lazily)
        self.entity_embedding: Optional[EntityEmbedding] = None
        self.neural_predictor: Optional[NeuralPredictor] = None
        
        self._entity_idx_counter = 0
        self._predicate_idx_counter = 0
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the knowledge base."""
        self.symbolic_kb.add_entity(entity)
    
    def add_predicate(self, predicate: Predicate) -> None:
        """Add a predicate to the knowledge base."""
        self.symbolic_kb.add_predicate(predicate)
    
    def add_fact(self, fact: Fact) -> None:
        """Add a fact to the knowledge base."""
        self.symbolic_kb.add_fact(fact)
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the knowledge base."""
        self.symbolic_kb.add_rule(rule)
    
    def initialize_neural_components(self) -> None:
        """
        Initialize neural components based on current symbolic knowledge.
        Must be called before using neural features.
        """
        num_entities = len(self.symbolic_kb.entities)
        num_predicates = len(self.symbolic_kb.predicates)
        
        # Initialize entity embeddings
        self.entity_embedding = EntityEmbedding(num_entities, self.embedding_dim)
        
        # Map entities to indices
        for idx, entity in enumerate(self.symbolic_kb.entities):
            self.entity_embedding.add_entity(entity, idx)
        
        # Initialize neural predictor
        self.neural_predictor = NeuralPredictor(
            self.embedding_dim,
            self.hidden_dim,
            num_predicates
        )
        
        # Map predicates to indices
        for idx, predicate in enumerate(self.symbolic_kb.predicates):
            self.neural_predictor.add_predicate(predicate, idx)
    
    def train_neural_component(self, epochs: int = 100, 
                              learning_rate: float = 0.001) -> None:
        """
        Train neural components on symbolic facts.
        
        Args:
            epochs: Number of training epochs
            learning_rate: Learning rate for optimization
        """
        if self.entity_embedding is None or self.neural_predictor is None:
            self.initialize_neural_components()
        
        # Train on existing facts
        facts_list = list(self.symbolic_kb.facts)
        if facts_list:
            print(f"Training on {len(facts_list)} facts...")
            self.neural_predictor.train_on_facts(
                facts_list,
                self.entity_embedding,
                epochs=epochs,
                learning_rate=learning_rate
            )
    
    def query(self, predicate_name: str, *entities: Entity) -> List[Fact]:
        """
        Query facts from symbolic knowledge base.
        
        Args:
            predicate_name: Name of predicate to query
            *entities: Entities to match (None for wildcard)
            
        Returns:
            List of matching facts
        """
        return self.symbolic_kb.query(predicate_name, *entities)
    
    def predict_fact(self, fact: Fact) -> float:
        """
        Predict confidence for a fact using neural components.
        
        Args:
            fact: Fact to predict
            
        Returns:
            Predicted confidence (0-1)
        """
        if self.entity_embedding is None or self.neural_predictor is None:
            raise ValueError(
                "Neural components not initialized. "
                "Call initialize_neural_components() first."
            )
        
        return self.neural_predictor.predict_fact(fact, self.entity_embedding)
    
    def hybrid_query(self, predicate_name: str, *entities: Entity,
                    confidence_threshold: float = 0.7) -> List[Tuple[Fact, float, str]]:
        """
        Perform hybrid query combining symbolic and neural reasoning.
        
        Args:
            predicate_name: Name of predicate to query
            *entities: Entities to match
            confidence_threshold: Minimum confidence for neural predictions
            
        Returns:
            List of tuples (fact, confidence, source) where source is 'symbolic' or 'neural'
        """
        results = []
        
        # Get symbolic facts
        symbolic_facts = self.query(predicate_name, *entities)
        for fact in symbolic_facts:
            results.append((fact, fact.confidence, 'symbolic'))
        
        # Add neural predictions if components are initialized
        if self.entity_embedding is not None and self.neural_predictor is not None:
            # For binary predicates, try all entity pairs
            if entities and len(entities) == 2:
                # Get predicate
                pred = None
                for p in self.symbolic_kb.predicates:
                    if p.name == predicate_name:
                        pred = p
                        break
                
                if pred and pred.arity == 2:
                    # Create candidate fact
                    candidate_fact = Fact(pred, entities)
                    
                    # Check if not already in symbolic facts
                    if candidate_fact not in self.symbolic_kb.facts:
                        # Predict confidence
                        confidence = self.predict_fact(candidate_fact)
                        
                        if confidence >= confidence_threshold:
                            results.append((candidate_fact, confidence, 'neural'))
        
        return results
    
    def infer(self, max_depth: int = 3) -> Set[Fact]:
        """
        Perform symbolic inference to derive new facts.
        
        Args:
            max_depth: Maximum inference depth
            
        Returns:
            Set of all facts (original + inferred)
        """
        return self.symbolic_kb.infer(max_depth)
    
    def get_entity_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """
        Compute similarity between two entities using embeddings.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Cosine similarity between entity embeddings
        """
        if self.entity_embedding is None:
            raise ValueError(
                "Neural components not initialized. "
                "Call initialize_neural_components() first."
            )
        
        emb1 = self.entity_embedding.get_embedding(entity1)
        emb2 = self.entity_embedding.get_embedding(entity2)
        
        # Cosine similarity
        similarity = torch.nn.functional.cosine_similarity(
            emb1.unsqueeze(0),
            emb2.unsqueeze(0)
        )
        
        return similarity.item()
    
    def __repr__(self):
        neural_status = "initialized" if self.entity_embedding is not None else "not initialized"
        return (f"NeuroSymbolicKB({self.symbolic_kb}, "
                f"neural_components={neural_status})")
