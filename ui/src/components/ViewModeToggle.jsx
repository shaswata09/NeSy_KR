import { useState, useRef, useEffect } from 'react'
import { Eye, GitGraph, TableProperties, ChevronDown } from 'lucide-react'

const MODE_META = {
  IMAGE:      { icon: Eye,             label: 'Image' },
  GRAPH:      { icon: GitGraph,        label: 'Graph' },
  ATTRIBUTES: { icon: TableProperties, label: 'Attributes' },
}

export default function ViewModeToggle({ modes, value, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  if (!modes || modes.length < 2) return null

  const current = MODE_META[value] ?? { label: value }
  const CurrentIcon = current.icon

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-[11px] font-medium pl-2 pr-1.5 py-1 rounded border cursor-pointer transition-colors"
        style={{
          backgroundColor: 'var(--bg-elevated)',
          borderColor: open ? 'var(--text-tertiary)' : 'var(--border-secondary)',
          color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--text-tertiary)'
          e.currentTarget.style.color = 'var(--text-primary)'
        }}
        onMouseLeave={(e) => {
          if (!open) {
            e.currentTarget.style.borderColor = 'var(--border-secondary)'
            e.currentTarget.style.color = 'var(--text-secondary)'
          }
        }}
      >
        {CurrentIcon && <CurrentIcon className="w-3 h-3" />}
        {current.label}
        <ChevronDown
          className="w-3 h-3 transition-transform"
          style={{
            color: 'var(--text-tertiary)',
            transform: open ? 'rotate(180deg)' : 'none',
          }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-full mt-1 min-w-full rounded border shadow-lg z-50 py-0.5"
          style={{
            backgroundColor: 'var(--bg-elevated)',
            borderColor: 'var(--border-secondary)',
          }}
        >
          {modes.map((mode) => {
            const { icon: Icon, label } = MODE_META[mode] ?? { label: mode }
            const isActive = value === mode
            return (
              <button
                key={mode}
                onClick={() => { onChange(mode); setOpen(false) }}
                className="w-full flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium transition-colors text-left"
                style={{
                  backgroundColor: isActive ? 'var(--bg-active)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                    e.currentTarget.style.color = 'var(--text-primary)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent'
                    e.currentTarget.style.color = 'var(--text-secondary)'
                  }
                }}
              >
                {Icon && <Icon className="w-3 h-3" />}
                {label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
