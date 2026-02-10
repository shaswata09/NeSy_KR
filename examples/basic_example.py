"""
Basic Example: Simple Family Relationships

This example demonstrates basic symbolic knowledge representation
with facts about family relationships.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nesy_kr import Entity, Predicate, Fact, Rule, KnowledgeBase


def main():
    print("=" * 60)
    print("NeuroSymbolic KR - Basic Example: Family Relationships")
    print("=" * 60)
    print()
    
    # Create knowledge base
    kb = KnowledgeBase()
    
    # Define entities (people)
    alice = Entity("Alice")
    bob = Entity("Bob")
    charlie = Entity("Charlie")
    diana = Entity("Diana")
    
    print("Entities:")
    for entity in [alice, bob, charlie, diana]:
        print(f"  - {entity}")
    print()
    
    # Define predicates
    parent_of = Predicate("parent_of", arity=2)
    grandparent_of = Predicate("grandparent_of", arity=2)
    sibling_of = Predicate("sibling_of", arity=2)
    
    print("Predicates:")
    for pred in [parent_of, grandparent_of, sibling_of]:
        print(f"  - {pred}")
    print()
    
    # Add facts
    kb.add_fact(Fact(parent_of, (alice, bob)))
    kb.add_fact(Fact(parent_of, (alice, charlie)))
    kb.add_fact(Fact(parent_of, (bob, diana)))
    
    print("Initial Facts:")
    for fact in kb.facts:
        print(f"  - {fact}")
    print()
    
    # Add rules
    # Rule: If X is parent of Y, and Y is parent of Z, then X is grandparent of Z
    rule1 = Rule(
        head=Fact(grandparent_of, (alice, diana)),
        body=[
            Fact(parent_of, (alice, bob)),
            Fact(parent_of, (bob, diana))
        ]
    )
    kb.add_rule(rule1)
    
    print("Rules:")
    print(f"  - {rule1}")
    print()
    
    # Query facts
    print("Query: Who are Alice's children?")
    results = kb.query("parent_of", alice)
    for fact in results:
        print(f"  - {fact}")
    print()
    
    # Perform inference
    print("Performing inference...")
    inferred_facts = kb.infer(max_depth=3)
    print(f"Total facts after inference: {len(inferred_facts)}")
    print("\nAll facts (including inferred):")
    for fact in inferred_facts:
        confidence_str = f" (confidence: {fact.confidence:.2f})" if fact.confidence < 1.0 else ""
        print(f"  - {fact}{confidence_str}")
    print()
    
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
