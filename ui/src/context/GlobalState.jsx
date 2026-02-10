import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { sampleDataset } from '../data/sampleData'

const GlobalStateContext = createContext(null)

export function StateProvider({ children }) {
  // Dataset browsing
  const [dataset] = useState(sampleDataset)
  const [selectedImageId, setSelectedImageId] = useState(sampleDataset[0]?.id ?? null)

  // Entity interaction
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [hoveredEntityId, setHoveredEntityId] = useState(null)

  // View mode for InputPane: 'IMAGE' | 'GRAPH'
  const [viewMode, setViewMode] = useState('IMAGE')

  // Zoom / pan sync state
  // { x, y, k, source } — source is the pane id that initiated the transform
  const [zoomState, setZoomState] = useState({ x: 0, y: 0, k: 1, source: null })

  // Ref to prevent zoom feedback loops between panes
  const zoomLockRef = useRef(false)

  const updateZoom = useCallback((x, y, k, source) => {
    if (zoomLockRef.current) return
    zoomLockRef.current = true
    setZoomState({ x, y, k, source })
    // Release lock after a short delay to allow the receiving pane to apply
    setTimeout(() => { zoomLockRef.current = false }, 50)
  }, [])

  const selectedImage = dataset.find((d) => d.id === selectedImageId) ?? null

  const value = {
    // Dataset
    dataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,

    // Entity
    selectedEntityId,
    setSelectedEntityId,
    hoveredEntityId,
    setHoveredEntityId,

    // View mode
    viewMode,
    setViewMode,

    // Zoom sync
    zoomState,
    updateZoom,
    zoomLockRef,
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
