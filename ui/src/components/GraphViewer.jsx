import { useRef, useEffect, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { useGlobalState } from '../context/GlobalState'
import { useThemeColors } from '../lib/useThemeColors'
import { DIFF_STATUS } from '../data/sampleData'

export default function GraphViewer({
  graphData,
  isDiffView = false,
  paneId = 'default',
  width,
  height,
}) {
  const fgRef = useRef()
  const {
    selectedEntityId,
    setSelectedEntityId,
    hoveredEntityId,
    setHoveredEntityId,
    zoomState,
    updateZoom,
    zoomLockRef,
  } = useGlobalState()

  const colors = useThemeColors()

  // Deep clone graph data so force-graph can mutate it without affecting source
  const data = useMemo(() => ({
    nodes: graphData.nodes.map((n) => ({ ...n })),
    links: graphData.links.map((l) => ({ ...l })),
  }), [graphData])

  // Configure physics on mount
  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.d3Force('charge').strength(-150)
    fg.d3Force('link').distance(80)
  }, [])

  // Respond to zoom sync from other panes
  useEffect(() => {
    const fg = fgRef.current
    if (!fg || !zoomState.source || zoomState.source === paneId) return
    fg.centerAt(zoomState.x, zoomState.y, 300)
    fg.zoom(zoomState.k, 300)
  }, [zoomState, paneId])

  // Emit zoom changes to global state
  const handleZoom = useCallback(({ k, x, y }) => {
    if (zoomLockRef.current) return
    updateZoom(x, y, k, paneId)
  }, [updateZoom, paneId, zoomLockRef])

  const handleNodeClick = useCallback((node) => {
    setSelectedEntityId(node.id)
  }, [setSelectedEntityId])

  const handleNodeHover = useCallback((node) => {
    setHoveredEntityId(node ? node.id : null)
  }, [setHoveredEntityId])

  // Custom node rendering
  const paintNode = useCallback((node, ctx, globalScale) => {
    const isHovered = hoveredEntityId === node.id
    const isSelected = selectedEntityId === node.id
    const radius = isHovered ? 8 : 6
    const label = node.label || node.id

    let fillColor = colors.canvasNodeDefault
    let strokeColor = null
    let strokeWidth = 0
    let isDashed = false

    if (isDiffView && node.status) {
      const statusColors = {
        [DIFF_STATUS.CORRECT]: colors.diffCorrect,
        [DIFF_STATUS.MISSING]: colors.diffMissing,
        [DIFF_STATUS.HALLUCINATED]: colors.diffHallucinated,
      }
      fillColor = statusColors[node.status] || colors.canvasNodeDefault
      if (node.status === DIFF_STATUS.MISSING) {
        isDashed = true
        fillColor = 'transparent'
        strokeColor = colors.diffMissing
        strokeWidth = 2
      } else if (node.status === DIFF_STATUS.HALLUCINATED) {
        strokeColor = colors.diffHallucinated
        strokeWidth = 3
      } else {
        strokeColor = colors.diffCorrect
        strokeWidth = 2
      }
    }

    if (isHovered) {
      strokeColor = colors.highlightHover
      strokeWidth = 3
    }
    if (isSelected) {
      strokeColor = colors.highlightSelected
      strokeWidth = 3
    }

    // Draw node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)

    if (isDashed) {
      ctx.setLineDash([3, 3])
    }

    if (fillColor !== 'transparent') {
      ctx.fillStyle = fillColor
      ctx.fill()
    }

    if (strokeColor) {
      ctx.strokeStyle = strokeColor
      ctx.lineWidth = strokeWidth / globalScale
      ctx.stroke()
    }

    ctx.setLineDash([])

    // Pulse animation for hovered entity (in non-source panes)
    if (isHovered && !isDiffView) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI)
      ctx.strokeStyle = colors.highlightHover
      ctx.lineWidth = 1.5 / globalScale
      ctx.globalAlpha = 0.5
      ctx.stroke()
      ctx.globalAlpha = 1
    }

    // Label
    const fontSize = Math.max(12 / globalScale, 3)
    ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillStyle = isHovered || isSelected ? colors.canvasTextHighlight : colors.canvasText
    ctx.fillText(label, node.x, node.y + radius + 2)
  }, [hoveredEntityId, selectedEntityId, isDiffView, colors])

  // Custom link rendering
  const paintLink = useCallback((link, ctx, globalScale) => {
    const start = link.source
    const end = link.target
    if (!start.x || !end.x) return

    let color = colors.canvasLinkDefault
    let lineWidth = 1
    let isDashed = false

    if (isDiffView && link.status) {
      if (link.status === DIFF_STATUS.CORRECT) {
        color = colors.diffCorrect
        lineWidth = 1.5
      } else if (link.status === DIFF_STATUS.MISSING) {
        color = colors.diffMissing
        isDashed = true
        lineWidth = 1
      } else if (link.status === DIFF_STATUS.HALLUCINATED) {
        color = colors.diffHallucinated
        lineWidth = 2.5
      }
    }

    // Highlight link if either node is hovered
    if (hoveredEntityId && (start.id === hoveredEntityId || end.id === hoveredEntityId)) {
      color = colors.highlightHover
      lineWidth = 2
    }

    ctx.beginPath()
    if (isDashed) ctx.setLineDash([4, 4])
    ctx.moveTo(start.x, start.y)
    ctx.lineTo(end.x, end.y)
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth / globalScale
    ctx.stroke()
    ctx.setLineDash([])

    // Edge label
    if (link.label) {
      const midX = (start.x + end.x) / 2
      const midY = (start.y + end.y) / 2
      const fontSize = Math.max(10 / globalScale, 2.5)
      ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = isDiffView && link.status === DIFF_STATUS.HALLUCINATED
        ? colors.canvasHallucinatedLabel
        : colors.canvasTextMuted
      ctx.fillText(link.label, midX, midY)
    }
  }, [hoveredEntityId, isDiffView, colors])

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={data}
      width={width}
      height={height}
      backgroundColor="transparent"
      nodeCanvasObject={paintNode}
      nodePointerAreaPaint={(node, color, ctx) => {
        ctx.beginPath()
        ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI)
        ctx.fillStyle = color
        ctx.fill()
      }}
      linkCanvasObject={paintLink}
      onNodeClick={handleNodeClick}
      onNodeHover={handleNodeHover}
      onZoom={handleZoom}
      cooldownTicks={80}
      enableNodeDrag={true}
    />
  )
}
