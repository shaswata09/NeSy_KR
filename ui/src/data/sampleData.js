/**
 * Real scene graph data from Visual Genome (images 1, 2, 3).
 * Objects and relationships sourced from VG objects.json and relationships.json.
 * Images hosted at Stanford: https://cs.stanford.edu/people/rak248/VG_100K[_2]/
 */

export const DIFF_STATUS = {
  CORRECT: 'correct',
  MISSING: 'missing',
  HALLUCINATED: 'hallucinated',
}

export const sampleDataset = [
  // ── Image 1: Street with trees, sidewalk, van ──
  {
    id: 'vg_1',
    name: 'Street & Sidewalk',
    imageUrl: 'https://cs.stanford.edu/people/rak248/VG_100K_2/1.jpg',
    width: 800,
    height: 600,
    metadata: {
      source: 'Visual Genome',
      imageId: 1,
      numObjects: 31,
      numRelations: 41,
    },
    groundTruth: {
      nodes: [
        { id: '1058545', label: 'Tree',     bbox: { x: 178, y: 0,   w: 476, h: 360 } },
        { id: '1058534', label: 'Sidewalk',  bbox: { x: 78,  y: 308, w: 722, h: 290 } },
        { id: '1058508', label: 'Building',  bbox: { x: 1,   y: 0,   w: 222, h: 538 } },
        { id: '1058539', label: 'Street',    bbox: { x: 439, y: 283, w: 359, h: 258 } },
        { id: '5045',    label: 'Shade',     bbox: { x: 116, y: 344, w: 274, h: 189 } },
        { id: '1058542', label: 'Van',       bbox: { x: 533, y: 278, w: 241, h: 176 } },
        { id: '1058507', label: 'Sign',      bbox: { x: 49,  y: 168, w: 62,  h: 105 } },
        { id: '1058529', label: 'Man',       bbox: { x: 373, y: 307, w: 61,  h: 191 } },
      ],
      links: [
        { source: '5045',    target: '1058534', label: 'ON' },
        { source: '1058507', target: '1058508', label: 'ON' },
        { source: '1058534', target: '1058539', label: 'next to' },
        { source: '1058529', target: '1058534', label: 'on' },
        { source: '1058542', target: '1058539', label: 'on' },
      ],
    },
    prediction: {
      nodes: [
        { id: '1058545', label: 'Tree',     status: DIFF_STATUS.CORRECT },
        { id: '1058534', label: 'Sidewalk',  status: DIFF_STATUS.CORRECT },
        { id: '1058508', label: 'Building',  status: DIFF_STATUS.CORRECT },
        { id: '1058539', label: 'Street',    status: DIFF_STATUS.CORRECT },
        { id: '5045',    label: 'Shade',     status: DIFF_STATUS.MISSING },
        { id: '1058542', label: 'Van',       status: DIFF_STATUS.CORRECT },
        { id: '1058507', label: 'Sign',      status: DIFF_STATUS.CORRECT },
        { id: '1058529', label: 'Man',       status: DIFF_STATUS.MISSING },
        { id: 'h_bus',   label: 'Bus',       status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: '1058507', target: '1058508', label: 'ON',      status: DIFF_STATUS.CORRECT },
        { source: '1058534', target: '1058539', label: 'next to', status: DIFF_STATUS.CORRECT },
        { source: '1058542', target: '1058539', label: 'on',      status: DIFF_STATUS.CORRECT },
        { source: '5045',    target: '1058534', label: 'ON',      status: DIFF_STATUS.MISSING },
        { source: '1058529', target: '1058534', label: 'on',      status: DIFF_STATUS.MISSING },
        { source: 'h_bus',   target: '1058539', label: 'on',      status: DIFF_STATUS.HALLUCINATED },
      ],
    },
  },

  // ── Image 2: Urban crosswalk, buildings, man with backpack ──
  {
    id: 'vg_2',
    name: 'Urban Crosswalk',
    imageUrl: 'https://cs.stanford.edu/people/rak248/VG_100K/2.jpg',
    width: 800,
    height: 600,
    metadata: {
      source: 'Visual Genome',
      imageId: 2,
      numObjects: 25,
      numRelations: 23,
    },
    groundTruth: {
      nodes: [
        { id: '1023841', label: 'Road',         bbox: { x: 0,   y: 345, w: 364, h: 254 } },
        { id: '1023813', label: 'Sidewalk',      bbox: { x: 320, y: 347, w: 478, h: 253 } },
        { id: '1023819', label: 'Building',      bbox: { x: 569, y: 0,   w: 228, h: 414 } },
        { id: '1023846', label: 'Building 2',    bbox: { x: 171, y: 0,   w: 258, h: 319 } },
        { id: '1023845', label: 'Street Light',  bbox: { x: 386, y: 120, w: 114, h: 412 } },
        { id: '5077',    label: 'Crosswalk',     bbox: { x: 0,   y: 531, w: 366, h: 68  } },
        { id: '1023838', label: 'Man',           bbox: { x: 321, y: 325, w: 142, h: 246 } },
        { id: '1023836', label: 'Car',           bbox: { x: 0,   y: 392, w: 152, h: 119 } },
      ],
      links: [
        { source: '1023836', target: '1023841', label: 'parked on' },
        { source: '5077',    target: '1023838', label: 'in front of' },
        { source: '1023838', target: '1023813', label: 'on' },
        { source: '1023845', target: '1023841', label: 'next to' },
        { source: '1023819', target: '1023841', label: 'beside' },
      ],
      },
    prediction: {
      nodes: [
        { id: '1023841', label: 'Road',         status: DIFF_STATUS.CORRECT },
        { id: '1023813', label: 'Sidewalk',      status: DIFF_STATUS.CORRECT },
        { id: '1023819', label: 'Building',      status: DIFF_STATUS.CORRECT },
        { id: '1023846', label: 'Building 2',    status: DIFF_STATUS.CORRECT },
        { id: '1023845', label: 'Street Light',  status: DIFF_STATUS.MISSING },
        { id: '5077',    label: 'Crosswalk',     status: DIFF_STATUS.CORRECT },
        { id: '1023838', label: 'Man',           status: DIFF_STATUS.CORRECT },
        { id: '1023836', label: 'Car',           status: DIFF_STATUS.CORRECT },
        { id: 'h_bike',  label: 'Bicycle',       status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: '1023836', target: '1023841', label: 'parked on',   status: DIFF_STATUS.CORRECT },
        { source: '5077',    target: '1023838', label: 'in front of', status: DIFF_STATUS.CORRECT },
        { source: '1023838', target: '1023813', label: 'on',          status: DIFF_STATUS.CORRECT },
        { source: '1023819', target: '1023841', label: 'beside',      status: DIFF_STATUS.CORRECT },
        { source: '1023845', target: '1023841', label: 'next to',     status: DIFF_STATUS.MISSING },
        { source: 'h_bike',  target: '1023841', label: 'on',          status: DIFF_STATUS.HALLUCINATED },
      ],
    },
  },

  // ── Image 3: Office cubicles, desk, computer ──
  {
    id: 'vg_3',
    name: 'Office Cubicles',
    imageUrl: 'https://cs.stanford.edu/people/rak248/VG_100K/3.jpg',
    width: 640,
    height: 480,
    metadata: {
      source: 'Visual Genome',
      imageId: 3,
      numObjects: 37,
      numRelations: 50,
    },
    groundTruth: {
      nodes: [
        { id: '1060291', label: 'Cubicles',        bbox: { x: 130, y: 89,  w: 511, h: 389 } },
        { id: '1060248', label: 'Table',            bbox: { x: 130, y: 231, w: 509, h: 246 } },
        { id: '1060274', label: 'Wall',             bbox: { x: 0,   y: 0,   w: 540, h: 86  } },
        { id: '1060290', label: 'Dividing Screen',  bbox: { x: 243, y: 88,  w: 299, h: 201 } },
        { id: '5118',    label: 'Floor',            bbox: { x: 110, y: 339, w: 506, h: 141 } },
        { id: '5098',    label: 'Filing Cabinet',   bbox: { x: 0,   y: 266, w: 132, h: 200 } },
        { id: '1060286', label: 'Keyboard',         bbox: { x: 285, y: 330, w: 125, h: 48  } },
        { id: '1060246', label: 'Monitor',          bbox: { x: 300, y: 190, w: 130, h: 120 } },
      ],
      links: [
        { source: '1060286', target: '1060246', label: 'in front of' },
        { source: '1060246', target: '1060248', label: 'on' },
        { source: '5098',    target: '1060248', label: 'next to' },
        { source: '1060286', target: '1060248', label: 'on' },
        { source: '1060290', target: '1060291', label: 'in' },
      ],
    },
    prediction: {
      nodes: [
        { id: '1060291', label: 'Cubicles',        status: DIFF_STATUS.CORRECT },
        { id: '1060248', label: 'Table',            status: DIFF_STATUS.CORRECT },
        { id: '1060274', label: 'Wall',             status: DIFF_STATUS.CORRECT },
        { id: '1060290', label: 'Dividing Screen',  status: DIFF_STATUS.MISSING },
        { id: '5118',    label: 'Floor',            status: DIFF_STATUS.CORRECT },
        { id: '5098',    label: 'Filing Cabinet',   status: DIFF_STATUS.CORRECT },
        { id: '1060286', label: 'Keyboard',         status: DIFF_STATUS.CORRECT },
        { id: '1060246', label: 'Monitor',          status: DIFF_STATUS.CORRECT },
        { id: 'h_chair', label: 'Chair',            status: DIFF_STATUS.HALLUCINATED },
      ],
      links: [
        { source: '1060286', target: '1060246', label: 'in front of', status: DIFF_STATUS.CORRECT },
        { source: '1060246', target: '1060248', label: 'on',          status: DIFF_STATUS.CORRECT },
        { source: '5098',    target: '1060248', label: 'next to',     status: DIFF_STATUS.CORRECT },
        { source: '1060286', target: '1060248', label: 'on',          status: DIFF_STATUS.CORRECT },
        { source: '1060290', target: '1060291', label: 'in',          status: DIFF_STATUS.MISSING },
        { source: 'h_chair', target: '1060248', label: 'at',          status: DIFF_STATUS.HALLUCINATED },
      ],
    },
  },
]
