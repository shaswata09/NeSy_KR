/**
 * Auto-discovers all dataset JSON files under src/data/ at build time.
 *
 * Convention:
 *   - src/data/<name>.json           -> dataset named "<name>"
 *   - src/data/<dir>/<name>.json     -> dataset named "<dir>/<name>"
 *
 * Each entry exposes { id, label, load } where load() returns the parsed JSON.
 * Uses Vite's import.meta.glob with eager:false for lazy loading.
 */

const modules = import.meta.glob(
  ['./**/*.json', '!./**/package.json'],
  { eager: false },
)

function labelFromPath(path) {
  // "./sampleData.json"             -> "Sample Data"
  // "./visual_genome/visualGenomeData.json" -> "Visual Genome"
  const clean = path
    .replace(/^\.\//, '')
    .replace(/\.json$/, '')
    .replace(/Data$/i, '')
  // Use last segment, convert camelCase/snake_case to Title Case
  const segment = clean.includes('/') ? clean.split('/').pop() : clean
  return segment
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export const availableDatasets = Object.entries(modules).map(([path, loader]) => ({
  id: path,
  label: labelFromPath(path),
  load: async () => {
    const mod = await loader()
    return mod.default
  },
}))

export const defaultDatasetId = availableDatasets[0]?.id ?? null
