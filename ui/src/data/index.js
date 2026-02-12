/**
 * Auto-discovers all dataset JSON files under src/data/ at build time,
 * plus manually registered API-backed datasets.
 *
 * Convention:
 *   - src/data/<name>.json           -> dataset named "<name>"
 *   - src/data/<dir>/<name>.json     -> dataset named "<dir>/<name>"
 *
 * Each entry exposes { id, label, type, load?, loadPage? }.
 *   - type 'static'  -> load() returns the full parsed JSON array
 *   - type 'api'     -> loadPage(offset, limit) fetches a page from the API
 */

// ---------------------------------------------------------------------------
// Static datasets (build-time glob)
// ---------------------------------------------------------------------------
const modules = import.meta.glob(
  ['./**/*.json', '!./**/package.json'],
  { eager: false },
)

function labelFromPath(path) {
  const clean = path
    .replace(/^\.\//, '')
    .replace(/\.json$/, '')
    .replace(/Data$/i, '')
  const segment = clean.includes('/') ? clean.split('/').pop() : clean
  return segment
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

const staticDatasets = Object.entries(modules).map(([path, loader]) => ({
  id: path,
  label: labelFromPath(path),
  type: 'static',
  load: async () => {
    const mod = await loader()
    return mod.default
  },
}))

// ---------------------------------------------------------------------------
// API datasets (manual registration)
// ---------------------------------------------------------------------------
const VG_API_PORT = 8100
// Use the browser's current hostname so the UI works both locally and over LAN
const VG_API_BASE = `http://${window.location.hostname}:${VG_API_PORT}`

const apiDatasets = [
  {
    id: 'api:visual_genome',
    label: 'Visual Genome',
    type: 'api',
    async loadPage(offset = 0, limit = 50) {
      const res = await fetch(
        `${VG_API_BASE}/api/vg?offset=${offset}&limit=${limit}`,
      )
      if (!res.ok) throw new Error(`VG API error: ${res.status}`)
      return res.json() // { total, offset, limit, items }
    },
  },
]

// ---------------------------------------------------------------------------
// Combined exports
// ---------------------------------------------------------------------------
export const availableDatasets = [...staticDatasets, ...apiDatasets]
export const defaultDatasetId = availableDatasets[0]?.id ?? null
