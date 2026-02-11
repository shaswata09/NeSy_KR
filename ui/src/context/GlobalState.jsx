import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { availableDatasets, defaultDatasetId } from '../data/index.js'

const GlobalStateContext = createContext(null)

// Apply data-theme attribute synchronously so CSS vars resolve before children render
function applyTheme(t) {
  const root = document.documentElement
  if (t === 'dark') {
    root.setAttribute('data-theme', 'dark')
  } else {
    root.removeAttribute('data-theme')
  }
}

export function StateProvider({ children }) {
  // Theme: 'light' | 'dark'
  const [theme, setTheme] = useState(() => {
    let initial = 'light'
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('nesy-theme')
      if (stored === 'dark' || stored === 'light') {
        initial = stored
      } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        initial = 'dark'
      }
      applyTheme(initial)
    }
    return initial
  })

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem('nesy-theme', next)
      applyTheme(next)
      return next
    })
  }, [])

  // Dataset selection
  const [activeDatasetId, setActiveDatasetId] = useState(
    () => localStorage.getItem('nesy-dataset') ?? defaultDatasetId,
  )
  const [dataset, setDataset] = useState([])
  const [datasetLoading, setDatasetLoading] = useState(true)

  // Load dataset when activeDatasetId changes
  useEffect(() => {
    let cancelled = false
    const entry = availableDatasets.find((d) => d.id === activeDatasetId)
    if (!entry) {
      setDataset([])
      setDatasetLoading(false)
      return
    }
    setDatasetLoading(true)
    entry.load().then((data) => {
      if (cancelled) return
      setDataset(data)
      setSelectedImageId(data[0]?.id ?? null)
      setDatasetLoading(false)
    })
    return () => { cancelled = true }
  }, [activeDatasetId])

  const switchDataset = useCallback((id) => {
    localStorage.setItem('nesy-dataset', id)
    setActiveDatasetId(id)
  }, [])

  // Image selection
  const [selectedImageId, setSelectedImageId] = useState(null)

  // Entity interaction
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState(null)
  const [hoveredEntityId, setHoveredEntityId] = useState(null)

  const selectedImage = dataset.find((d) => d.id === selectedImageId) ?? null

  const value = {
    // Theme
    theme,
    toggleTheme,

    // Dataset switching
    availableDatasets,
    activeDatasetId,
    switchDataset,
    datasetLoading,

    // Dataset
    dataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,

    // Entity
    selectedEntityId,
    setSelectedEntityId,
    selectedEdgeId,
    setSelectedEdgeId,
    hoveredEntityId,
    setHoveredEntityId,
  }

  return (
    <GlobalStateContext.Provider value={value}>
      {children}
    </GlobalStateContext.Provider>
  )
}

export function useGlobalState() {
  const ctx = useContext(GlobalStateContext)
  if (!ctx) throw new Error('useGlobalState must be used within a StateProvider')
  return ctx
}
