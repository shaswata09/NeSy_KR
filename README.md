# NeSy_KR: NeuroSymbolic Knowledge Representation

A Python framework for combining symbolic knowledge representation with neural network learning to create hybrid reasoning systems.

## Overview

NeSy_KR integrates:
- **Symbolic Knowledge Representation**: Entities, predicates, facts, and rules
- **Neural Embeddings**: Continuous vector representations of symbolic entities
- **Hybrid Reasoning**: Combining logical inference with neural predictions

## Features

- 🔢 **Symbolic Components**: Define entities, predicates, facts, and rules
- 🧠 **Neural Components**: Entity embeddings and neural predictors
- 🔄 **Hybrid Integration**: Combine symbolic and neural reasoning
- 📊 **Inference Engine**: Forward chaining for deriving new facts
- 🎯 **Confidence Scoring**: Neural prediction of fact confidence
- 📈 **Entity Similarity**: Compute similarity using learned embeddings

## Installation

```bash
# Clone the repository
git clone https://github.com/shaswata09/NeSy_KR.git
cd NeSy_KR

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### Basic Symbolic Knowledge Representation

```python
from nesy_kr import Entity, Predicate, Fact, KnowledgeBase

# Create entities
alice = Entity("Alice")
bob = Entity("Bob")

# Create predicate
parent_of = Predicate("parent_of", arity=2)

# Create and add fact
kb = KnowledgeBase()
kb.add_fact(Fact(parent_of, (alice, bob)))

# Query
results = kb.query("parent_of", alice)
print(results)  # [parent_of(Alice, Bob)]
```

### Neuro-Symbolic Integration

```python
from nesy_kr import Entity, Predicate, Fact, NeuroSymbolicKB

# Create neuro-symbolic knowledge base
kb = NeuroSymbolicKB(embedding_dim=64, hidden_dim=128)

# Add symbolic knowledge
alice = Entity("Alice")
bob = Entity("Bob")
knows = Predicate("knows", arity=2)

kb.add_fact(Fact(knows, (alice, bob)))

# Initialize and train neural components
kb.initialize_neural_components()
kb.train_neural_component(epochs=100)

# Make neural predictions
charlie = Entity("Charlie")
kb.add_entity(charlie)
test_fact = Fact(knows, (alice, charlie))
confidence = kb.predict_fact(test_fact)
print(f"Confidence: {confidence:.3f}")

# Hybrid query (symbolic + neural)
results = kb.hybrid_query("knows", confidence_threshold=0.7)
for fact, conf, source in results:
    print(f"{fact}: {conf:.3f} [{source}]")
```

## Architecture

### Symbolic Module (`symbolic.py`)

- **Entity**: Represents objects in the domain
- **Predicate**: Defines relations between entities
- **Fact**: Ground atoms (predicate applied to entities)
- **Rule**: Horn clauses for logical inference
- **KnowledgeBase**: Storage and querying of symbolic knowledge

### Neural Module (`neural.py`)

- **EntityEmbedding**: Neural embeddings for entities
- **NeuralPredictor**: Neural network for predicting fact confidence

### Neuro-Symbolic Module (`neuro_symbolic.py`)

- **NeuroSymbolicKB**: Hybrid system combining symbolic and neural reasoning

## Examples

Run the provided examples:

```bash
# Basic symbolic knowledge representation
python examples/basic_example.py

# Neuro-symbolic hybrid reasoning
python examples/neuro_symbolic_example.py
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m unittest tests/test_symbolic.py
python -m unittest tests/test_neural.py
python -m unittest tests/test_neuro_symbolic.py
```

## Use Cases

- **Knowledge Graphs**: Build and query knowledge graphs with neural enhancements
- **Relation Prediction**: Predict missing relationships using neural models
- **Hybrid Reasoning**: Combine logical rules with learned patterns
- **Entity Similarity**: Compute semantic similarity between entities
- **Confidence Estimation**: Assess confidence in derived facts

## Requirements

- Python 3.7+
- NumPy >= 1.21.0
- PyTorch >= 1.9.0
- scikit-learn >= 0.24.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{nesy_kr,
  title = {NeSy_KR: NeuroSymbolic Knowledge Representation},
  author = {NeSy_KR Team},
  year = {2026},
  url = {https://github.com/shaswata09/NeSy_KR}
}
```
