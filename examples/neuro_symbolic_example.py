"""
NeuroSymbolic Example: Hybrid Reasoning

This example demonstrates the integration of symbolic and neural components
for hybrid reasoning about knowledge.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nesy_kr import Entity, Predicate, Fact, NeuroSymbolicKB


def main():
    print("=" * 60)
    print("NeuroSymbolic KR - Hybrid Reasoning Example")
    print("=" * 60)
    print()
    
    # Create neuro-symbolic knowledge base
    kb = NeuroSymbolicKB(embedding_dim=32, hidden_dim=64)
    
    # Define entities (people and locations)
    print("Creating entities...")
    people = [
        Entity("Alice"),
        Entity("Bob"),
        Entity("Charlie"),
        Entity("Diana"),
        Entity("Eve")
    ]
    
    locations = [
        Entity("New_York"),
        Entity("London"),
        Entity("Paris"),
        Entity("Tokyo")
    ]
    
    for entity in people + locations:
        kb.add_entity(entity)
    
    # Define predicates
    print("Creating predicates...")
    knows = Predicate("knows", arity=2)
    lives_in = Predicate("lives_in", arity=2)
    friends = Predicate("friends", arity=2)
    
    kb.add_predicate(knows)
    kb.add_predicate(lives_in)
    kb.add_predicate(friends)
    
    # Add symbolic facts
    print("\nAdding symbolic facts...")
    kb.add_fact(Fact(knows, (people[0], people[1])))  # Alice knows Bob
    kb.add_fact(Fact(knows, (people[1], people[2])))  # Bob knows Charlie
    kb.add_fact(Fact(friends, (people[0], people[1])))  # Alice friends Bob
    kb.add_fact(Fact(lives_in, (people[0], locations[0])))  # Alice lives in NY
    kb.add_fact(Fact(lives_in, (people[1], locations[0])))  # Bob lives in NY
    kb.add_fact(Fact(lives_in, (people[2], locations[1])))  # Charlie lives in London
    
    print(f"Added {len(kb.symbolic_kb.facts)} symbolic facts")
    
    # Initialize and train neural components
    print("\nInitializing neural components...")
    kb.initialize_neural_components()
    
    print("Training neural predictor on symbolic knowledge...")
    kb.train_neural_component(epochs=50, learning_rate=0.01)
    
    # Query symbolic knowledge
    print("\n" + "=" * 60)
    print("SYMBOLIC QUERIES")
    print("=" * 60)
    
    print("\nQuery: Who does Alice know?")
    results = kb.query("knows", people[0])
    for fact in results:
        print(f"  - {fact}")
    
    print("\nQuery: Who lives in New York?")
    results = kb.query("lives_in", None, locations[0])
    for fact in results:
        print(f"  - {fact}")
    
    # Neural predictions
    print("\n" + "=" * 60)
    print("NEURAL PREDICTIONS")
    print("=" * 60)
    
    print("\nPredicting new relationships...")
    
    # Test neural prediction on new potential facts
    test_facts = [
        Fact(knows, (people[0], people[2])),  # Alice knows Charlie?
        Fact(friends, (people[1], people[2])),  # Bob friends Charlie?
        Fact(knows, (people[2], people[3])),  # Charlie knows Diana?
    ]
    
    for fact in test_facts:
        confidence = kb.predict_fact(fact)
        print(f"  - {fact}: {confidence:.3f}")
    
    # Hybrid query
    print("\n" + "=" * 60)
    print("HYBRID QUERY (Symbolic + Neural)")
    print("=" * 60)
    
    print("\nQuery: All 'knows' relationships with confidence >= 0.5")
    hybrid_results = kb.hybrid_query("knows", confidence_threshold=0.5)
    
    for fact, confidence, source in hybrid_results:
        print(f"  - {fact}: {confidence:.3f} [{source}]")
    
    # Entity similarity
    print("\n" + "=" * 60)
    print("ENTITY SIMILARITY (Neural Embeddings)")
    print("=" * 60)
    
    print("\nComputing entity similarities...")
    pairs = [
        (people[0], people[1]),  # Alice and Bob
        (people[1], people[2]),  # Bob and Charlie
        (people[0], people[3]),  # Alice and Diana
    ]
    
    for e1, e2 in pairs:
        similarity = kb.get_entity_similarity(e1, e2)
        print(f"  - {e1.name} <-> {e2.name}: {similarity:.3f}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
