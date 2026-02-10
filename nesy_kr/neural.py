"""
Neural Network Module for NeuroSymbolic KR

This module provides neural network components for learning embeddings
and making predictions about symbolic knowledge.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional
from .symbolic import Entity, Predicate, Fact


class EntityEmbedding(nn.Module):
    """
    Neural embeddings for symbolic entities.
    
    Maps entities to continuous vector representations that can be used
    for neural reasoning and similarity computation.
    """
    
    def __init__(self, num_entities: int, embedding_dim: int = 64):
        """
        Initialize entity embeddings.
        
        Args:
            num_entities: Number of entities to embed
            embedding_dim: Dimension of embedding vectors
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.embeddings = nn.Embedding(num_entities, embedding_dim)
        nn.init.xavier_uniform_(self.embeddings.weight)
        
        # Mapping from entity name to index
        self.entity_to_idx: Dict[str, int] = {}
        self.idx_to_entity: Dict[int, str] = {}
    
    def add_entity(self, entity: Entity, idx: int) -> None:
        """Register an entity with a specific index."""
        self.entity_to_idx[entity.name] = idx
        self.idx_to_entity[idx] = entity.name
    
    def get_embedding(self, entity: Entity) -> torch.Tensor:
        """Get embedding vector for an entity."""
        idx = self.entity_to_idx.get(entity.name)
        if idx is None:
            raise ValueError(f"Entity {entity.name} not found in embeddings")
        return self.embeddings(torch.tensor([idx]))[0]
    
    def forward(self, entity_indices: torch.Tensor) -> torch.Tensor:
        """Forward pass returning embeddings for entity indices."""
        return self.embeddings(entity_indices)


class NeuralPredictor(nn.Module):
    """
    Neural network for predicting truth values of symbolic predicates.
    
    This network takes entity embeddings as input and predicts the
    confidence/probability that a relation holds between entities.
    """
    
    def __init__(self, embedding_dim: int, hidden_dim: int = 128, 
                 num_predicates: int = 10):
        """
        Initialize neural predictor.
        
        Args:
            embedding_dim: Dimension of entity embeddings
            hidden_dim: Dimension of hidden layers
            num_predicates: Number of predicates to predict
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Network for binary relations (arity 2)
        self.binary_net = nn.Sequential(
            nn.Linear(2 * embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, num_predicates),
        )
        
        # Predicate embeddings for relation-specific scoring
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        self.predicate_to_idx: Dict[str, int] = {}
        self.idx_to_predicate: Dict[int, str] = {}
    
    def add_predicate(self, predicate: Predicate, idx: int) -> None:
        """Register a predicate with a specific index."""
        self.predicate_to_idx[predicate.name] = idx
        self.idx_to_predicate[idx] = predicate.name
    
    def forward(self, entity_embeddings: torch.Tensor) -> torch.Tensor:
        """
        Predict relation scores for entity pairs.
        
        Args:
            entity_embeddings: Tensor of shape (batch_size, 2, embedding_dim)
            
        Returns:
            Tensor of shape (batch_size, num_predicates) with scores
        """
        batch_size = entity_embeddings.shape[0]
        
        # Concatenate entity embeddings
        combined = entity_embeddings.view(batch_size, -1)
        
        # Predict scores
        scores = self.binary_net(combined)
        
        return scores
    
    def predict_fact(self, fact: Fact, entity_embedding: EntityEmbedding) -> float:
        """
        Predict confidence for a specific fact.
        
        Args:
            fact: Fact to predict
            entity_embedding: Entity embedding module
            
        Returns:
            Predicted confidence score (0-1)
        """
        if fact.predicate.arity != 2:
            raise ValueError("Currently only supports binary predicates")
        
        # Get embeddings for entities in the fact
        emb1 = entity_embedding.get_embedding(fact.entities[0])
        emb2 = entity_embedding.get_embedding(fact.entities[1])
        
        # Stack embeddings
        combined = torch.stack([emb1, emb2]).unsqueeze(0)
        
        # Get scores
        with torch.no_grad():
            scores = self.forward(combined)[0]
            
            # Get predicate index
            pred_idx = self.predicate_to_idx.get(fact.predicate.name)
            if pred_idx is None:
                return 0.5  # Unknown predicate
            
            # Apply sigmoid to get probability
            confidence = torch.sigmoid(scores[pred_idx]).item()
        
        return confidence
    
    def train_on_facts(self, facts: List[Fact], 
                      entity_embedding: EntityEmbedding,
                      negative_samples: int = 5,
                      epochs: int = 100,
                      learning_rate: float = 0.001) -> None:
        """
        Train the predictor on a set of facts.
        
        Args:
            facts: List of facts to train on
            entity_embedding: Entity embedding module
            negative_samples: Number of negative samples per positive fact
            epochs: Number of training epochs
            learning_rate: Learning rate for optimization
        """
        optimizer = torch.optim.Adam(
            list(self.parameters()) + list(entity_embedding.parameters()),
            lr=learning_rate
        )
        
        # Prepare training data (store entity references, not embeddings)
        positive_samples = []
        for fact in facts:
            if fact.predicate.arity == 2:
                pred_idx = self.predicate_to_idx.get(fact.predicate.name)
                if pred_idx is not None:
                    positive_samples.append((
                        fact.entities[0],
                        fact.entities[1],
                        pred_idx,
                        1.0
                    ))
        
        # Train
        for epoch in range(epochs):
            total_loss = 0.0
            
            for entity1, entity2, pred_idx, label in positive_samples:
                optimizer.zero_grad()
                
                # Get fresh embeddings for this iteration
                emb1 = entity_embedding.get_embedding(entity1)
                emb2 = entity_embedding.get_embedding(entity2)
                emb = torch.stack([emb1, emb2])
                
                # Forward pass
                scores = self.forward(emb.unsqueeze(0))[0]
                pred_score = scores[pred_idx]
                
                # Binary cross-entropy loss
                loss = F.binary_cross_entropy_with_logits(
                    pred_score,
                    torch.tensor(label)
                )
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(positive_samples) if positive_samples else 0
                print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
