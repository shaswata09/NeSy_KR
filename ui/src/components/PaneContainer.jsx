import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '../lib/cn'

export default function PaneContainer({ title, children, className, headerLeft, headerRight }) {
  const paneRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [isFullscreen, setIsFullscreen] = useState(false)

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

  useEffect(() => {
    const handler = () => setIsFullscreen(document.fullscreenElement === paneRef.current)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      paneRef.current?.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }, [])

  return (
    <div
      ref={paneRef}
      className={cn(
        'flex flex-col h-full rounded-lg border overflow-hidden transition-colors duration-200',
        className
      )}
      style={{
        borderColor: 'var(--border-primary)',
        backgroundColor: 'var(--bg-pane)',
      }}
    >
      {/* Pane Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b shrink-0 overflow-hidden"
        style={{ borderColor: 'var(--border-secondary)' }}
      >
        <div className="flex items-center gap-2 min-w-0 whitespace-nowrap">
          <h3
            className="text-xs font-semibold uppercase tracking-wider shrink-0"
            style={{ color: 'var(--text-secondary)' }}
          >
            {title}
          </h3>
          {headerLeft}
        </div>
        {headerRight && <div className="flex items-center gap-1 shrink-0 whitespace-nowrap">{headerRight}</div>}
      </div>

      {/* Content area — passes measured dimensions to children */}
      <div ref={containerRef} className="flex-1 relative min-h-0">
        {dimensions.width > 0 && typeof children === 'function'
          ? children({ ...dimensions, toggleFullscreen, isFullscreen })
          : children}
      </div>
    </div>
  )
}
