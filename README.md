# NeSy_KR: NeuroSymbolic Knowledge Representation

Augmenter is a visual comparison workspace for evaluating model predictions against ground truth annotations. It supports scene graphs, bounding boxes, object attributes, and visual question answering — all rendered side-by-side with diff overlays.

## Dataset Format

Any dataset can be visualized in Augmenter by converting it to the standardized JSON format defined in [`dataset-template.json`](dataset-template.json).

The format is an array of **dataset entries**. Each entry contains an image reference, ground truth annotations, and model predictions with diff statuses.

### Entry Structure

```
id              string    Unique identifier (e.g. "vg_12345", "gqa_67890")
name            string    Display name shown in the sidebar
image_id        string    Original image ID from the source dataset
image_path      string    Local filesystem path to the image (optional)
image_url       string    Remote URL to the image (optional)
width           number    Image width in pixels
height          number    Image height in pixels
metadata        object    Source info and dataset-specific fields (see below)
groundTruth     object    Ground truth annotations (see below)
prediction      object    Model prediction data with diff statuses (see below)
```

**Metadata**
| Field | Type | Source | Description |
|---|---|---|---|
| `source` | string | all | Dataset origin (`"vg"`, `"gqa"`) |
| `split` | string | all | Dataset split (`"train"`, `"val"`) |
| `cocoId` | number | VG | COCO dataset cross-reference ID |
| `flickrId` | number | VG | Flickr cross-reference ID |

### Ground Truth

Contains the reference annotations without any status fields. The unified schema preserves all data from both Visual Genome and GQA.

```json
{
  "nodes": [
    {
      "id": "n1",
      "label": "Car",
      "bbox": { "x": 100, "y": 50, "w": 200, "h": 150 },
      "names": ["car", "automobile"],
      "synsets": ["car.n.01"]
    }
  ],
  "links": [
    {
      "source": "n1",
      "target": "n2",
      "label": "parked on",
      "synsets": "park.v.01",
      "subjectName": "car",
      "objectName": "street"
    }
  ],
  "attributes": [
    { "entityId": "n1", "attribute": "color", "value": "red" }
  ],
  "qas": [
    {
      "id": "qa_1",
      "question": "What color is the car?",
      "answer": "red",
      "fullAnswer": "The car is red.",
      "types": { "structural": "query", "semantic": "attr", "detailed": "attrColor" },
      "semanticProgram": [],
      "isBalanced": true,
      "entailed": [],
      "equivalent": [],
      "questionObjects": [{ "objectId": "n1", "names": ["car"], "synsets": [], "bbox": {} }],
      "answerObjects": []
    }
  ],
  "regions": [
    {
      "id": "reg_1",
      "phrase": "A red car parked on the street",
      "bbox": { "x": 80, "y": 40, "w": 250, "h": 180 }
    }
  ]
}
```

### Field Availability by Source

Not all fields are present for every entry — optional fields are omitted when not applicable.

| Field | VG | GQA | Description |
|---|---|---|---|
| `image_path` | — | yes | Local path to JPEG |
| `image_url` | yes | — | Remote image URL |
| `nodes[].names` | yes | — | Alternative object names |
| `nodes[].synsets` | yes | — | WordNet synset mappings |
| `links[].synsets` | yes | — | Relationship synset |
| `links[].subjectName` | yes | — | Subject object name |
| `links[].objectName` | yes | — | Object name in relationship |
| `qas[].fullAnswer` | — | yes | Full sentence answer |
| `qas[].types` | — | yes | Question type annotations (structural, semantic, detailed) |
| `qas[].semanticProgram` | — | yes | Functional program steps |
| `qas[].isBalanced` | — | yes | Whether question is in the balanced set |
| `qas[].entailed` | — | yes | Related question IDs |
| `qas[].equivalent` | — | yes | Equivalent question IDs |
| `qas[].questionObjects` | yes | — | Objects referenced in question |
| `qas[].answerObjects` | yes | — | Objects referenced in answer |
| `regions` | yes | — | Region descriptions with bounding boxes |

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
| Image | `image_url`/`image_path` + nodes with `bbox` | Renders the image with bounding box overlays |
| Graph | `nodes` (1+) | Force-directed scene graph with labeled edges |
| Attributes | `attributes` (1+) | Scrollable table of entity properties |
| Q&A | `qas` (1+) | Question-answer cards with diff badges |
| Regions | `regions` (1+) | Region descriptions with localized bounding boxes |

Prediction nodes without `bbox` fields will not enable Image mode in the prediction pane.

### Field Reference

**Node (ground truth)**
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique node identifier |
| `label` | string | yes | Display name |
| `bbox` | object | no | Bounding box `{ x, y, w, h }` in image coordinates |
| `names` | string[] | no | Alternative names for the object (VG) |
| `synsets` | string[] | no | WordNet synset mappings (VG) |
| `mergedObjectIds` | number[] | no | IDs of merged duplicate objects (VG) |

**Node (prediction)** — same as above, plus:
| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | yes | `"correct"`, `"missing"`, or `"hallucinated"` |

**Link**
| Field | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `label` | string | yes | Relationship label (predicate) |
| `synsets` | string | no | Relationship synset (VG) |
| `subjectName` | string | no | Subject object name (VG) |
| `objectName` | string | no | Object name in relationship (VG) |
| `status` | string | prediction only | Diff status |

**Attribute**
| Field | Type | Required | Description |
|---|---|---|---|
| `entityId` | string | yes | Reference to a node `id` |
| `attribute` | string | yes | Property category (color, material, size, shape, property) |
| `value` | string | yes | Raw attribute value |
| `status` | string | prediction only | Diff status |

**QA**
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique QA identifier |
| `question` | string | yes | The question text |
| `answer` | string\|null | yes | The answer (`null` for missing predictions) |
| `fullAnswer` | string | no | Full sentence answer (GQA) |
| `types` | object | no | Question type annotations — `{ structural, semantic, detailed }` (GQA) |
| `semanticProgram` | array | no | Functional program steps for compositional reasoning (GQA) |
| `isBalanced` | boolean | no | Whether question is in the balanced set (GQA) |
| `entailed` | array | no | IDs of entailed questions (GQA) |
| `equivalent` | array | no | IDs of semantically equivalent questions (GQA) |
| `questionObjects` | array | no | Objects referenced in the question (VG) |
| `answerObjects` | array | no | Objects referenced in the answer (VG) |
| `status` | string | prediction only | Diff status |

**Region** (VG only)
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique region identifier |
| `phrase` | string | yes | Natural language description of the region |
| `bbox` | object | yes | Bounding box `{ x, y, w, h }` in image coordinates |

### Merged Dataset Generation

The unified dataset merges Visual Genome and GQA into JSONL files:

```bash
python poc_scripts/dataset_generation/merge_vg_gqa.py
```

| Split | Sources | Output |
|---|---|---|
| `train.jsonl` | All Visual Genome (108K) + GQA train (~75K) | `data/merged/train.jsonl` |
| `val.jsonl` | GQA val (~10K) | `data/merged/val.jsonl` |

Use `--format json` for a single JSON array, or `--output-dir <path>` to change the output location.

## UI Setup

```bash
cd ui
npm install
npm run dev
```

See [`ui/README.md`](ui/README.md) for development details.
