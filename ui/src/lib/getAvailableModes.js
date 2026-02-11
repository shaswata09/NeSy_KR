/**
 * Returns the list of view modes available for a given data slice.
 *
 * @param {Object} opts
 * @param {string} [opts.imageUrl]    — if truthy, IMAGE mode is available
 * @param {Array}  [opts.nodes]       — if non-empty, GRAPH mode is available
 * @param {Array}  [opts.attributes]  — if non-empty, ATTRIBUTES mode is available
 * @param {Array}  [opts.qas]         — if non-empty, QA mode is available
 * @param {boolean}[opts.hasBbox]     — override: set false to suppress IMAGE even if imageUrl exists
 * @returns {string[]} e.g. ['IMAGE', 'GRAPH', 'ATTRIBUTES', 'QA']
 */
export function getAvailableModes({ imageUrl, nodes, attributes, qas, hasBbox } = {}) {
  const modes = []

  // IMAGE mode requires an image URL and bounding boxes on at least one node
  const bboxAvailable = hasBbox ?? (nodes ?? []).some((n) => n.bbox)
  if (imageUrl && bboxAvailable) {
    modes.push('IMAGE')
  }

  // GRAPH mode requires at least one node
  if ((nodes ?? []).length > 0) {
    modes.push('GRAPH')
  }

  // ATTRIBUTES mode requires at least one attribute entry
  if ((attributes ?? []).length > 0) {
    modes.push('ATTRIBUTES')
  }

  // QA mode requires at least one question-answer pair
  if ((qas ?? []).length > 0) {
    modes.push('QA')
  }

  return modes
}
