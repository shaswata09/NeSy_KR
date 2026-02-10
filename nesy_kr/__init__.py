"""
NeuroSymbolic Knowledge Representation Framework

This package provides a framework for combining symbolic knowledge representation
with neural network learning for hybrid reasoning systems.
"""

__version__ = "0.1.0"

from .symbolic import Entity, Predicate, Fact, Rule, KnowledgeBase
from .neural import NeuralPredictor, EntityEmbedding
from .neuro_symbolic import NeuroSymbolicKB

__all__ = [
    "Entity",
    "Predicate", 
    "Fact",
    "Rule",
    "KnowledgeBase",
    "NeuralPredictor",
    "EntityEmbedding",
    "NeuroSymbolicKB",
]
