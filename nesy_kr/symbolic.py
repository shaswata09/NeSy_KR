"""
Symbolic Knowledge Representation Module

This module provides classes for representing symbolic knowledge including
entities, predicates, facts, rules, and knowledge bases.
"""

from typing import List, Set, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Entity:
    """Represents a symbolic entity in the knowledge base."""
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.name == other.name
        return False
    
    def __repr__(self):
        return f"Entity({self.name})"


@dataclass
class Predicate:
    """Represents a symbolic predicate (relation)."""
    name: str
    arity: int
    
    def __hash__(self):
        return hash((self.name, self.arity))
    
    def __eq__(self, other):
        if isinstance(other, Predicate):
            return self.name == other.name and self.arity == other.arity
        return False
    
    def __repr__(self):
        return f"Predicate({self.name}/{self.arity})"


@dataclass
class Fact:
    """Represents a symbolic fact (ground atom)."""
    predicate: Predicate
    entities: Tuple[Entity, ...]
    confidence: float = 1.0
    
    def __post_init__(self):
        if len(self.entities) != self.predicate.arity:
            raise ValueError(
                f"Fact arity mismatch: {self.predicate.name} expects "
                f"{self.predicate.arity} entities, got {len(self.entities)}"
            )
    
    def __hash__(self):
        return hash((self.predicate, self.entities))
    
    def __eq__(self, other):
        if isinstance(other, Fact):
            return (self.predicate == other.predicate and 
                    self.entities == other.entities)
        return False
    
    def __repr__(self):
        entities_str = ", ".join(str(e.name) for e in self.entities)
        return f"{self.predicate.name}({entities_str})"


@dataclass
class Rule:
    """Represents a symbolic rule (horn clause)."""
    head: Fact
    body: List[Fact]
    confidence: float = 1.0
    
    def __repr__(self):
        body_str = ", ".join(str(f) for f in self.body)
        return f"{self.head} :- {body_str}"


class KnowledgeBase:
    """
    A symbolic knowledge base for storing and querying facts and rules.
    """
    
    def __init__(self):
        self.entities: Set[Entity] = set()
        self.predicates: Set[Predicate] = set()
        self.facts: Set[Fact] = set()
        self.rules: List[Rule] = []
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the knowledge base."""
        self.entities.add(entity)
    
    def add_predicate(self, predicate: Predicate) -> None:
        """Add a predicate to the knowledge base."""
        self.predicates.add(predicate)
    
    def add_fact(self, fact: Fact) -> None:
        """Add a fact to the knowledge base."""
        self.add_predicate(fact.predicate)
        for entity in fact.entities:
            self.add_entity(entity)
        self.facts.add(fact)
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the knowledge base."""
        self.rules.append(rule)
        self.add_fact(rule.head)
        for fact in rule.body:
            self.add_fact(fact)
    
    def query(self, predicate_name: str, *entities: Entity) -> List[Fact]:
        """
        Query facts matching a predicate name and entities.
        
        Args:
            predicate_name: Name of the predicate to query
            *entities: Optional entities to match (None acts as wildcard)
            
        Returns:
            List of matching facts
        """
        results = []
        for fact in self.facts:
            if fact.predicate.name != predicate_name:
                continue
            
            # If entities provided, check if they match
            if entities:
                matches = True
                for i, entity in enumerate(entities):
                    if entity is not None and fact.entities[i] != entity:
                        matches = False
                        break
                if matches:
                    results.append(fact)
            else:
                results.append(fact)
        
        return results
    
    def infer(self, max_depth: int = 3) -> Set[Fact]:
        """
        Perform forward chaining inference to derive new facts.
        
        Args:
            max_depth: Maximum inference depth
            
        Returns:
            Set of all facts (original + inferred)
        """
        inferred = set(self.facts)
        
        for _ in range(max_depth):
            new_facts = set()
            
            for rule in self.rules:
                # Check if all body facts are satisfied
                body_satisfied = all(
                    any(self._unify(body_fact, kb_fact) 
                        for kb_fact in inferred)
                    for body_fact in rule.body
                )
                
                if body_satisfied:
                    # Add head fact with combined confidence
                    min_confidence = min(
                        [rule.confidence] + 
                        [f.confidence for f in rule.body]
                    )
                    new_fact = Fact(
                        rule.head.predicate,
                        rule.head.entities,
                        min_confidence
                    )
                    new_facts.add(new_fact)
            
            if not new_facts - inferred:
                break
            
            inferred.update(new_facts)
        
        return inferred
    
    def _unify(self, fact1: Fact, fact2: Fact) -> bool:
        """Check if two facts can be unified (simple equality check)."""
        return (fact1.predicate == fact2.predicate and 
                fact1.entities == fact2.entities)
    
    def __repr__(self):
        return (f"KnowledgeBase(entities={len(self.entities)}, "
                f"predicates={len(self.predicates)}, "
                f"facts={len(self.facts)}, "
                f"rules={len(self.rules)})")
