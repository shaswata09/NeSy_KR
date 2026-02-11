# NeSy_KR: NeuroSymbolic Knowledge Representation

Augmenter is a visual comparison workspace for evaluating model predictions against ground truth annotations. It supports scene graphs, bounding boxes, object attributes, and visual question answering — all rendered side-by-side with diff overlays.

## Dataset Format

Any dataset can be visualized in Augmenter by converting it to the standardized JSON format defined in [`dataset-template.json`](dataset-template.json).

The format is an array of **dataset entries**. Each entry contains an image reference, ground truth annotations, and model predictions with diff statuses.

### Entry Structure

```
id              string    Unique identifier for the entry
name            string    Display name shown in the sidebar
imageUrl        string    URL to the source image (optional)
width           number    Image width in pixels
height          number    Image height in pixels
metadata        object    Arbitrary key-value pairs (source, split, etc.)
groundTruth     object    Ground truth data (see below)
prediction      object    Model prediction data with diff statuses (see below)
```

### Ground Truth

Contains the reference annotations without any status fields.

```json
{
  "nodes": [
    { "id": "n1", "label": "Car", "bbox": { "x": 100, "y": 50, "w": 200, "h": 150 } }
  ],
  "links": [
    { "source": "n1", "target": "n2", "label": "parked on" }
  ],
  "attributes": [
    { "entityId": "n1", "attribute": "color", "value": "red" }
  ],
  "qas": [
    { "id": "qa_1", "question": "What color is the car?", "answer": "Red." }
  ]
}
```

### Prediction

Same structure as ground truth, but every element includes a `status` field:

| Status | Meaning |
|---|---|
| `"correct"` | Matches ground truth |
| `"missing"` | Present in ground truth but absent/wrong in prediction |
| `"hallucinated"` | Present in prediction but not in ground truth |

```json
{
  "nodes": [
    { "id": "n1", "label": "Car", "status": "correct" },
    { "id": "h1", "label": "Bus", "status": "hallucinated" }
  ],
  "links": [
    { "source": "n1", "target": "h1", "label": "near", "status": "hallucinated" }
  ],
  "attributes": [
    { "entityId": "n1", "attribute": "color", "value": "red", "status": "correct" }
  ],
  "qas": [
    { "id": "qa_1", "question": "What color is the car?", "answer": "Red.", "status": "correct" },
    { "id": "qa_2", "question": "How many wheels?", "answer": null, "status": "missing" }
  ]
}
```

### Data Types and View Modes

Each pane automatically detects which view modes are available based on what data is present:

| View Mode | Required Data | Description |
|---|---|---|
| Image | `imageUrl` + nodes with `bbox` | Renders the image with bounding box overlays |
| Graph | `nodes` (1+) | Force-directed scene graph with labeled edges |
| Attributes | `attributes` (1+) | Scrollable table of entity properties |
| Q&A | `qas` (1+) | Question-answer cards with diff badges |

Prediction nodes without `bbox` fields will not enable Image mode in the prediction pane.

### Field Reference

**Node (ground truth)**
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique node identifier |
| `label` | string | yes | Display name |
| `bbox` | object | no | Bounding box `{ x, y, w, h }` in image coordinates |

**Node (prediction)** — same as above, plus:
| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | yes | `"correct"`, `"missing"`, or `"hallucinated"` |

**Link**
| Field | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `label` | string | yes | Relationship label |
| `status` | string | prediction only | Diff status |

**Attribute**
| Field | Type | Required | Description |
|---|---|---|---|
| `entityId` | string | yes | Reference to a node `id` |
| `attribute` | string | yes | Property name (e.g., "color", "material") |
| `value` | string | yes | Property value |
| `status` | string | prediction only | Diff status |

**QA**
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique QA identifier |
| `question` | string | yes | The question text |
| `answer` | string\|null | yes | The answer (`null` for missing predictions) |
| `status` | string | prediction only | Diff status |

## UI Setup

```bash
cd ui
npm install
npm run dev
```

See [`ui/README.md`](ui/README.md) for development details.
