/**
 * Sample scene graph data modeled after Visual Genome format.
 * Each dataset entry has an image, a ground truth scene graph,
 * and a model prediction scene graph (with diff status annotations).
 */

export const DIFF_STATUS = {
  CORRECT: 'correct',
  MISSING: 'missing',
  HALLUCINATED: 'hallucinated',
}

export const sampleDataset = [
  {
    id: 'vg_2315842',
    name: 'Park Scene',
    thumbnail: null,
    width: 800,
    height: 600,
    metadata: {
      source: 'Visual Genome',
      split: 'val',
      numObjects: 6,
      numRelations: 5,
    },
    groundTruth: {
      nodes: [
        { id: 'dog', label: 'Dog', x: 200, y: 300, bbox: { x: 150, y: 250, w: 120, h: 100 } },
        { id: 'tree', label: 'Tree', x: 500, y: 150, bbox: { x: 430, y: 50, w: 140, h: 250 } },
        { id: 'grass', label: 'Grass', x: 400, y: 500, bbox: { x: 50, y: 450, w: 700, h: 150 } },
        { id: 'sky', label: 'Sky', x: 400, y: 80, bbox: { x: 0, y: 0, w: 800, h: 200 } },
        { id: 'person', label: 'Person', x: 300, y: 250, bbox: { x: 260, y: 150, w: 80, h: 200 } },
        { id: 'bench', label: 'Bench', x: 600, y: 400, bbox: { x: 530, y: 360, w: 140, h: 80 } },
      ],
      links: [
        { source: 'dog', target: 'grass', label: 'standing on' },
        { source: 'person', target: 'dog', label: 'walking' },
        { source: 'tree', target: 'grass', label: 'growing on' },
        { source: 'bench', target: 'grass', label: 'on' },
        { source: 'sky', target: 'tree', label: 'above' },
      ],
    },
    prediction: {
      nodes: [
        { id: 'dog', label: 'Dog', status: DIFF_STATUS.CORRECT },
        { id: 'tree', label: 'Tree', status: DIFF_STATUS.CORRECT },
        { id: 'grass', label: 'Grass', status: DIFF_STATUS.CORRECT },
        { id: 'sky', label: 'Sky', status: DIFF_STATUS.CORRECT },
        { id: 'person', label: 'Person', status: DIFF_STATUS.MISSING },
        { id: 'bench', label: 'Bench', status: DIFF_STATUS.CORRECT },
        { id: 'car', label: 'Car', status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: 'dog', target: 'grass', label: 'standing on', status: DIFF_STATUS.CORRECT },
        { source: 'tree', target: 'grass', label: 'growing on', status: DIFF_STATUS.CORRECT },
        { source: 'bench', target: 'grass', label: 'on', status: DIFF_STATUS.CORRECT },
        { source: 'sky', target: 'tree', label: 'above', status: DIFF_STATUS.CORRECT },
        { source: 'car', target: 'grass', label: 'parked on', status: DIFF_STATUS.HALLUCINATED },
        { source: 'person', target: 'dog', label: 'walking', status: DIFF_STATUS.MISSING },
      ],
    },
  },
  {
    id: 'vg_2340091',
    name: 'Kitchen Scene',
    thumbnail: null,
    width: 800,
    height: 600,
    metadata: {
      source: 'Visual Genome',
      split: 'val',
      numObjects: 5,
      numRelations: 4,
    },
    groundTruth: {
      nodes: [
        { id: 'table', label: 'Table', x: 400, y: 400, bbox: { x: 200, y: 350, w: 400, h: 120 } },
        { id: 'cup', label: 'Cup', x: 350, y: 300, bbox: { x: 320, y: 270, w: 60, h: 70 } },
        { id: 'plate', label: 'Plate', x: 500, y: 320, bbox: { x: 460, y: 290, w: 80, h: 60 } },
        { id: 'window', label: 'Window', x: 400, y: 100, bbox: { x: 300, y: 30, w: 200, h: 170 } },
        { id: 'chair', label: 'Chair', x: 250, y: 450, bbox: { x: 190, y: 380, w: 120, h: 160 } },
      ],
      links: [
        { source: 'cup', target: 'table', label: 'on' },
        { source: 'plate', target: 'table', label: 'on' },
        { source: 'chair', target: 'table', label: 'near' },
        { source: 'window', target: 'table', label: 'behind' },
      ],
    },
    prediction: {
      nodes: [
        { id: 'table', label: 'Table', status: DIFF_STATUS.CORRECT },
        { id: 'cup', label: 'Cup', status: DIFF_STATUS.CORRECT },
        { id: 'plate', label: 'Plate', status: DIFF_STATUS.CORRECT },
        { id: 'window', label: 'Window', status: DIFF_STATUS.MISSING },
        { id: 'chair', label: 'Chair', status: DIFF_STATUS.CORRECT },
        { id: 'vase', label: 'Vase', status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: 'cup', target: 'table', label: 'on', status: DIFF_STATUS.CORRECT },
        { source: 'plate', target: 'table', label: 'on', status: DIFF_STATUS.CORRECT },
        { source: 'chair', target: 'table', label: 'near', status: DIFF_STATUS.CORRECT },
        { source: 'vase', target: 'table', label: 'on', status: DIFF_STATUS.HALLUCINATED },
        { source: 'window', target: 'table', label: 'behind', status: DIFF_STATUS.MISSING },
      ],
    },
  },
  {
    id: 'vg_2359870',
    name: 'Street Scene',
    thumbnail: null,
    width: 800,
    height: 600,
    metadata: {
      source: 'Visual Genome',
      split: 'test',
      numObjects: 5,
      numRelations: 4,
    },
    groundTruth: {
      nodes: [
        { id: 'car', label: 'Car', x: 300, y: 350, bbox: { x: 200, y: 280, w: 200, h: 140 } },
        { id: 'road', label: 'Road', x: 400, y: 500, bbox: { x: 0, y: 420, w: 800, h: 180 } },
        { id: 'building', label: 'Building', x: 600, y: 200, bbox: { x: 500, y: 50, w: 250, h: 350 } },
        { id: 'sign', label: 'Sign', x: 150, y: 200, bbox: { x: 120, y: 150, w: 60, h: 100 } },
        { id: 'pedestrian', label: 'Pedestrian', x: 450, y: 300, bbox: { x: 420, y: 220, w: 60, h: 160 } },
      ],
      links: [
        { source: 'car', target: 'road', label: 'driving on' },
        { source: 'pedestrian', target: 'road', label: 'crossing' },
        { source: 'sign', target: 'road', label: 'beside' },
        { source: 'building', target: 'road', label: 'along' },
      ],
    },
    prediction: {
      nodes: [
        { id: 'car', label: 'Car', status: DIFF_STATUS.CORRECT },
        { id: 'road', label: 'Road', status: DIFF_STATUS.CORRECT },
        { id: 'building', label: 'Building', status: DIFF_STATUS.CORRECT },
        { id: 'sign', label: 'Sign', status: DIFF_STATUS.MISSING },
        { id: 'pedestrian', label: 'Pedestrian', status: DIFF_STATUS.CORRECT },
        { id: 'truck', label: 'Truck', status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: 'car', target: 'road', label: 'driving on', status: DIFF_STATUS.CORRECT },
        { source: 'pedestrian', target: 'road', label: 'crossing', status: DIFF_STATUS.CORRECT },
        { source: 'building', target: 'road', label: 'along', status: DIFF_STATUS.CORRECT },
        { source: 'truck', target: 'road', label: 'on', status: DIFF_STATUS.HALLUCINATED },
        { source: 'sign', target: 'road', label: 'beside', status: DIFF_STATUS.MISSING },
      ],
    },
  },
]
