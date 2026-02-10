import { useRef, useEffect, useCallback, useState } from 'react'
import { useGlobalState } from '../context/GlobalState'

const BBOX_COLORS = {
  default: '#3b82f6',
  hovered: '#facc15',
  selected: '#c084fc',
}

export default function ImageViewer({ imageData, width, height }) {
  const canvasRef = useRef(null)
  const { hoveredEntityId, selectedEntityId, setHoveredEntityId, setSelectedEntityId } = useGlobalState()
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const dragRef = useRef({ dragging: false, lastX: 0, lastY: 0 })

  const nodes = imageData?.nodes ?? []
  const imgWidth = imageData?.width ?? 800
  const imgHeight = imageData?.height ?? 600

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const { x, y, scale } = transform

    ctx.clearRect(0, 0, width, height)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)

    // Draw placeholder image background
    ctx.fillStyle = '#1e293b'
    ctx.fillRect(0, 0, imgWidth, imgHeight)

    // Grid pattern for visual context
    ctx.strokeStyle = '#334155'
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

    // Draw bounding boxes
    nodes.forEach((node) => {
      if (!node.bbox) return
      const { x: bx, y: by, w: bw, h: bh } = node.bbox
      const isHovered = hoveredEntityId === node.id
      const isSelected = selectedEntityId === node.id

      // Glow effect for hovered
      if (isHovered) {
        ctx.shadowColor = BBOX_COLORS.hovered
        ctx.shadowBlur = 16
      } else if (isSelected) {
        ctx.shadowColor = BBOX_COLORS.selected
        ctx.shadowBlur = 12
      } else {
        ctx.shadowColor = 'transparent'
        ctx.shadowBlur = 0
      }

      ctx.strokeStyle = isHovered
        ? BBOX_COLORS.hovered
        : isSelected
          ? BBOX_COLORS.selected
          : BBOX_COLORS.default
      ctx.lineWidth = isHovered || isSelected ? 2.5 : 1.5
      ctx.strokeRect(bx, by, bw, bh)

      // Reset shadow
      ctx.shadowColor = 'transparent'
      ctx.shadowBlur = 0

      // Semi-transparent fill on hover
      if (isHovered) {
        ctx.fillStyle = 'rgba(250, 204, 21, 0.08)'
        ctx.fillRect(bx, by, bw, bh)
      }

      // Label
      const fontSize = 12
      ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
      const labelWidth = ctx.measureText(node.label).width
      ctx.fillStyle = isHovered ? 'rgba(250, 204, 21, 0.9)' : 'rgba(59, 130, 246, 0.85)'
      ctx.fillRect(bx, by - fontSize - 4, labelWidth + 8, fontSize + 4)
      ctx.fillStyle = '#ffffff'
      ctx.textBaseline = 'top'
      ctx.fillText(node.label, bx + 4, by - fontSize - 2)
    })

    ctx.restore()
  }, [transform, nodes, hoveredEntityId, selectedEntityId, width, height, imgWidth, imgHeight])

  useEffect(() => { draw() }, [draw])

  // Fit the image to the available space on mount / resize
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
    dragRef.current = { dragging: true, lastX: e.clientX, lastY: e.clientY }
  }, [])

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

  return (
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
  )
}
