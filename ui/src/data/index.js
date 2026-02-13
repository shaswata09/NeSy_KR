/**
 * Auto-discovers all dataset JSON files under src/data/ at build time,
 * plus dynamically registered API-backed datasets fetched from the
 * unified API server.
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

export const staticDatasets = Object.entries(modules).map(([path, loader]) => ({
  id: path,
  label: labelFromPath(path),
  type: 'static',
  load: async () => {
    const mod = await loader()
    return mod.default
  },
}))

// ---------------------------------------------------------------------------
// API datasets (fetched dynamically from unified server)
// ---------------------------------------------------------------------------
// Use the browser's current hostname so the UI works both locally and over LAN.
export const API_BASE = `http://${window.location.hostname}:8200`

/**
 * Fetch available datasets from the unified API server and return
 * UI-ready entries with loadPage() functions.
 * Returns [] if the server is unreachable.
 */
export async function fetchApiDatasets() {
  try {
    const res = await fetch(`${API_BASE}/api/datasets`)
    if (!res.ok) return []
    const datasets = await res.json()
    return datasets.map((ds) => ({
      id: `api:${ds.name}`,
      label: ds.displayName,
      type: 'api',
      total: ds.total,
      splits: ds.splits,
      hasLocalImages: ds.hasLocalImages,
      async loadPage(offset = 0, limit = 50) {
        const r = await fetch(
          `${API_BASE}/api/datasets/${ds.name}?offset=${offset}&limit=${limit}`,
        )
        if (!r.ok) throw new Error(`${ds.displayName} API error: ${r.status}`)
        return r.json() // { total, offset, limit, items }
      },
    }))
  } catch {
    console.warn('Unified API server not reachable — no API datasets loaded.')
    return []
  }
}

export const defaultStaticDatasetId = staticDatasets[0]?.id ?? null
