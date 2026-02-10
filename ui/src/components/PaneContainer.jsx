import { useRef, useState, useEffect } from 'react'
import { cn } from '../lib/cn'

export default function PaneContainer({ title, children, className, headerRight }) {
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setDimensions({ width: Math.floor(width), height: Math.floor(height) })
      }
    })

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border overflow-hidden transition-colors duration-200',
        className
      )}
      style={{
        borderColor: 'var(--border-primary)',
        backgroundColor: 'var(--bg-pane)',
      }}
    >
      {/* Pane Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b shrink-0"
        style={{ borderColor: 'var(--border-secondary)' }}
      >
        <h3
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: 'var(--text-secondary)' }}
        >
          {title}
        </h3>
        {headerRight && <div className="flex items-center gap-1">{headerRight}</div>}
      </div>

      {/* Content area — passes measured dimensions to children */}
      <div ref={containerRef} className="flex-1 relative min-h-0">
        {dimensions.width > 0 && typeof children === 'function'
          ? children(dimensions)
          : children}
      </div>
    </div>
  )
}
