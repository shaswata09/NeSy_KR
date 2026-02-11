import { useRef, useState, useEffect, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { ZoomIn, ZoomOut, Maximize2, Minimize2, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, LocateFixed, Lock, Unlock } from 'lucide-react'
import { useGlobalState } from '../context/GlobalState'
import { useThemeColors } from '../lib/useThemeColors'
import { DIFF_STATUS } from '../lib/diffStatus'

export default function GraphViewer({
  graphData,
  isDiffView = false,
  paneId = 'default',
  width,
  height,
  onToggleFullscreen,
  isFullscreen,
}) {
  const fgRef = useRef()
  const {
    selectedEntityId,
    setSelectedEntityId,
    hoveredEntityId,
    setHoveredEntityId,
  } = useGlobalState()

  const colors = useThemeColors()

  const [locked, setLocked] = useState(false)

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

  const handlePan = useCallback((dx, dy) => {
    const fg = fgRef.current
    if (!fg) return
    const center = fg.screen2GraphCoords(width / 2, height / 2)
    fg.centerAt(center.x + dx, center.y + dy, 300)
  }, [width, height])

  const handleToggleLock = useCallback(() => {
    setLocked((prev) => {
      const fg = fgRef.current
      if (!fg) return prev
      if (!prev) {
        data.nodes.forEach((node) => { node.fx = node.x; node.fy = node.y })
      } else {
        data.nodes.forEach((node) => { node.fx = undefined; node.fy = undefined })
        fg.d3ReheatSimulation()
      }
      return !prev
    })
  }, [data])

  const handleZoomIn = useCallback(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.zoom(fg.zoom() * 1.4, 300)
  }, [])

  const handleZoomOut = useCallback(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.zoom(fg.zoom() / 1.4, 300)
  }, [])

  const handleFit = useCallback(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.zoomToFit(300, 40)
  }, [])

  const btnStyle = { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border-primary)' }
  const btnActiveStyle = { backgroundColor: 'var(--text-secondary)', color: 'var(--bg-pane)', border: '1px solid var(--text-secondary)' }

  return (
    <div className="relative" style={{ width, height }}>
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
        cooldownTicks={80}
        enableNodeDrag={!locked}
      />
      <div className="absolute bottom-2 right-2 flex items-center gap-2">
        <div className="grid grid-cols-3 gap-0.5" style={{ gridTemplateRows: 'repeat(3, auto)' }}>
          <div />
          <button onClick={() => handlePan(0, -40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan up"><ChevronUp size={12} /></button>
          <div />
          <button onClick={() => handlePan(-40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan left"><ChevronLeft size={12} /></button>
          <button onClick={handleFit} className="p-1 rounded cursor-pointer" style={btnStyle} title="Re-center"><LocateFixed size={12} /></button>
          <button onClick={() => handlePan(40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan right"><ChevronRight size={12} /></button>
          <div />
          <button onClick={() => handlePan(0, 40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan down"><ChevronDown size={12} /></button>
          <div />
        </div>
        <div className="flex flex-col gap-0.5">
          <button onClick={handleToggleLock} className="p-1 rounded cursor-pointer" style={locked ? btnActiveStyle : btnStyle} title={locked ? 'Unlock layout' : 'Lock layout'}>
            {locked ? <Lock size={12} /> : <Unlock size={12} />}
          </button>
          <button onClick={handleZoomIn} className="p-1 rounded cursor-pointer" style={btnStyle} title="Zoom in"><ZoomIn size={12} /></button>
          <button onClick={handleZoomOut} className="p-1 rounded cursor-pointer" style={btnStyle} title="Zoom out"><ZoomOut size={12} /></button>
          {onToggleFullscreen && (
            <button onClick={onToggleFullscreen} className="p-1 rounded cursor-pointer" style={btnStyle} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
              {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
