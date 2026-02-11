import { useRef, useEffect, useCallback, useState } from 'react'
import { ZoomIn, ZoomOut, Maximize2, Minimize2, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, LocateFixed, Lock, Unlock } from 'lucide-react'
import { useGlobalState } from '../context/GlobalState'
import { useThemeColors } from '../lib/useThemeColors'

export default function ImageViewer({ imageData, width, height, onToggleFullscreen, isFullscreen }) {
  const canvasRef = useRef(null)
  const { hoveredEntityId, selectedEntityId, setHoveredEntityId, setSelectedEntityId } = useGlobalState()
  const colors = useThemeColors()
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const dragRef = useRef({ dragging: false, lastX: 0, lastY: 0 })
  const [loadedImage, setLoadedImage] = useState(null)
  const [locked, setLocked] = useState(false)

  const nodes = imageData?.nodes ?? []
  const imgWidth = imageData?.width ?? 800
  const imgHeight = imageData?.height ?? 600
  const imageUrl = imageData?.imageUrl ?? null

  // Load the actual image when URL changes
  useEffect(() => {
    if (!imageUrl) {
      setLoadedImage(null)
      return
    }
    const img = new window.Image()
    img.onload = () => setLoadedImage(img)
    img.onerror = () => setLoadedImage(null)
    img.src = imageUrl
  }, [imageUrl])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const { x, y, scale } = transform

    ctx.clearRect(0, 0, width, height)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)

    // Draw actual image or fallback placeholder
    if (loadedImage) {
      ctx.drawImage(loadedImage, 0, 0, imgWidth, imgHeight)
    } else {
      // Placeholder background with grid
      ctx.fillStyle = colors.canvasBg
      ctx.fillRect(0, 0, imgWidth, imgHeight)
      ctx.strokeStyle = colors.canvasGrid
      ctx.lineWidth = 0.5
      for (let gx = 0; gx < imgWidth; gx += 40) {
        ctx.beginPath()
        ctx.moveTo(gx, 0)
        ctx.lineTo(gx, imgHeight)
        ctx.stroke()
      }
      for (let gy = 0; gy < imgHeight; gy += 40) {
        ctx.beginPath()
        ctx.moveTo(0, gy)
        ctx.lineTo(imgWidth, gy)
        ctx.stroke()
      }
      // Loading text
      if (imageUrl) {
        ctx.fillStyle = colors.canvasTextMuted
        ctx.font = '14px Inter, system-ui, sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText('Loading image...', imgWidth / 2, imgHeight / 2)
      }
    }

    // Draw bounding boxes
    nodes.forEach((node) => {
      if (!node.bbox) return
      const { x: bx, y: by, w: bw, h: bh } = node.bbox
      const isHovered = hoveredEntityId === node.id
      const isSelected = selectedEntityId === node.id

      // Glow effect for hovered
      if (isHovered) {
        ctx.shadowColor = colors.highlightHover
        ctx.shadowBlur = 16
      } else if (isSelected) {
        ctx.shadowColor = colors.highlightSelected
        ctx.shadowBlur = 12
      } else {
        ctx.shadowColor = 'transparent'
        ctx.shadowBlur = 0
      }

      ctx.strokeStyle = isHovered
        ? colors.highlightHover
        : isSelected
          ? colors.highlightSelected
          : colors.canvasNodeDefault
      ctx.lineWidth = isHovered || isSelected ? 2.5 : 1.5
      ctx.strokeRect(bx, by, bw, bh)

      // Reset shadow
      ctx.shadowColor = 'transparent'
      ctx.shadowBlur = 0

      // Semi-transparent fill on hover
      if (isHovered) {
        ctx.fillStyle = colors.canvasHoverFill
        ctx.fillRect(bx, by, bw, bh)
      }

      // Label
      const fontSize = 12
      ctx.font = `bold ${fontSize}px Inter, system-ui, sans-serif`
      const labelWidth = ctx.measureText(node.label).width
      ctx.fillStyle = isHovered ? colors.canvasLabelBgHover : colors.canvasLabelBg
      ctx.fillRect(bx, by - fontSize - 4, labelWidth + 8, fontSize + 4)
      ctx.fillStyle = colors.canvasLabelText
      ctx.textBaseline = 'top'
      ctx.fillText(node.label, bx + 4, by - fontSize - 2)
    })

    ctx.restore()
  }, [transform, nodes, hoveredEntityId, selectedEntityId, width, height, imgWidth, imgHeight, colors, loadedImage, imageUrl])

  useEffect(() => { draw() }, [draw])

  // Fit the image to the available space on mount / resize / image load
  useEffect(() => {
    if (!width || !height) return
    const scaleX = width / imgWidth
    const scaleY = height / imgHeight
    const fitScale = Math.min(scaleX, scaleY) * 0.9
    const offsetX = (width - imgWidth * fitScale) / 2
    const offsetY = (height - imgHeight * fitScale) / 2
    setTransform({ x: offsetX, y: offsetY, scale: fitScale })
  }, [width, height, imgWidth, imgHeight])

  // Hit-test on click
  const handleClick = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const mx = (e.clientX - rect.left - transform.x) / transform.scale
    const my = (e.clientY - rect.top - transform.y) / transform.scale

    for (const node of nodes) {
      if (!node.bbox) continue
      const { x: bx, y: by, w: bw, h: bh } = node.bbox
      if (mx >= bx && mx <= bx + bw && my >= by && my <= by + bh) {
        setSelectedEntityId(node.id)
        return
      }
    }
    setSelectedEntityId(null)
  }, [nodes, transform, setSelectedEntityId])

  // Hit-test on mouse move for hover
  const handleMouseMove = useCallback((e) => {
    if (dragRef.current.dragging) return
    const rect = canvasRef.current.getBoundingClientRect()
    const mx = (e.clientX - rect.left - transform.x) / transform.scale
    const my = (e.clientY - rect.top - transform.y) / transform.scale

    for (const node of nodes) {
      if (!node.bbox) continue
      const { x: bx, y: by, w: bw, h: bh } = node.bbox
      if (mx >= bx && mx <= bx + bw && my >= by && my <= by + bh) {
        setHoveredEntityId(node.id)
        return
      }
    }
    setHoveredEntityId(null)
  }, [nodes, transform, setHoveredEntityId])

  // Pan via drag
  const handleMouseDown = useCallback((e) => {
    if (locked) return
    dragRef.current = { dragging: true, lastX: e.clientX, lastY: e.clientY }
  }, [locked])

  const handleMouseUp = useCallback(() => {
    dragRef.current.dragging = false
  }, [])

  const handleDrag = useCallback((e) => {
    if (!dragRef.current.dragging) return
    const dx = e.clientX - dragRef.current.lastX
    const dy = e.clientY - dragRef.current.lastY
    dragRef.current.lastX = e.clientX
    dragRef.current.lastY = e.clientY
    setTransform((prev) => ({ ...prev, x: prev.x + dx, y: prev.y + dy }))
  }, [])

  // Zoom via wheel
  const handleWheel = useCallback((e) => {
    if (locked) return
    e.preventDefault()
    const factor = e.deltaY > 0 ? 0.9 : 1.1
    const rect = canvasRef.current.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    setTransform((prev) => {
      const newScale = Math.min(Math.max(prev.scale * factor, 0.1), 5)
      const ratio = newScale / prev.scale
      return {
        scale: newScale,
        x: mx - ratio * (mx - prev.x),
        y: my - ratio * (my - prev.y),
      }
    })
  }, [])

  const handlePan = useCallback((dx, dy) => {
    setTransform((prev) => ({ ...prev, x: prev.x + dx, y: prev.y + dy }))
  }, [])

  const handleZoomIn = useCallback(() => {
    setTransform((prev) => {
      const factor = 1.4
      const newScale = Math.min(prev.scale * factor, 5)
      const ratio = newScale / prev.scale
      const cx = width / 2
      const cy = height / 2
      return { scale: newScale, x: cx - ratio * (cx - prev.x), y: cy - ratio * (cy - prev.y) }
    })
  }, [width, height])

  const handleZoomOut = useCallback(() => {
    setTransform((prev) => {
      const factor = 1.4
      const newScale = Math.max(prev.scale / factor, 0.1)
      const ratio = newScale / prev.scale
      const cx = width / 2
      const cy = height / 2
      return { scale: newScale, x: cx - ratio * (cx - prev.x), y: cy - ratio * (cy - prev.y) }
    })
  }, [width, height])

  const handleFitToView = useCallback(() => {
    const scaleX = width / imgWidth
    const scaleY = height / imgHeight
    const fitScale = Math.min(scaleX, scaleY) * 0.9
    const offsetX = (width - imgWidth * fitScale) / 2
    const offsetY = (height - imgHeight * fitScale) / 2
    setTransform({ x: offsetX, y: offsetY, scale: fitScale })
  }, [width, height, imgWidth, imgHeight])

  const btnStyle = { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border-primary)' }
  const btnActiveStyle = { backgroundColor: 'var(--text-secondary)', color: 'var(--bg-pane)', border: '1px solid var(--text-secondary)' }

  return (
    <div className="relative" style={{ width, height }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="cursor-grab active:cursor-grabbing"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          handleMouseUp()
          setHoveredEntityId(null)
        }}
        onMouseMoveCapture={handleDrag}
        onWheel={handleWheel}
      />
      {/* Box color legend */}
      <div className="absolute top-2 left-2 flex items-center gap-3 pointer-events-none">
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm border-2"
            style={{ borderColor: 'var(--canvas-node-default)', backgroundColor: 'transparent' }}
          />
          <span className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>
            Default
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm border-2"
            style={{ borderColor: 'var(--highlight-hover)', backgroundColor: 'var(--highlight-hover)', opacity: 0.6 }}
          />
          <span className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>
            Hovered
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="w-3 h-3 rounded-sm border-2"
            style={{ borderColor: 'var(--highlight-selected)', backgroundColor: 'var(--highlight-selected)', opacity: 0.6 }}
          />
          <span className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>
            Selected
          </span>
        </span>
      </div>
      <div className="absolute bottom-2 right-2 flex items-center gap-2">
        <div className="grid grid-cols-3 gap-0.5" style={{ gridTemplateRows: 'repeat(3, auto)' }}>
          <div />
          <button onClick={() => handlePan(0, 50)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan up"><ChevronUp size={12} /></button>
          <div />
          <button onClick={() => handlePan(50, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan left"><ChevronLeft size={12} /></button>
          <button onClick={handleFitToView} className="p-1 rounded cursor-pointer" style={btnStyle} title="Fit to view"><LocateFixed size={12} /></button>
          <button onClick={() => handlePan(-50, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan right"><ChevronRight size={12} /></button>
          <div />
          <button onClick={() => handlePan(0, -50)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan down"><ChevronDown size={12} /></button>
          <div />
        </div>
        <div className="flex flex-col gap-0.5">
          <button onClick={() => setLocked((prev) => !prev)} className="p-1 rounded cursor-pointer" style={locked ? btnActiveStyle : btnStyle} title={locked ? 'Unlock view' : 'Lock view'}>
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
