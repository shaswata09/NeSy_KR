import { Image, ScanEye, ChevronRight, Eye, GitGraph, Sun, Moon } from 'lucide-react'
import { useGlobalState } from '../context/GlobalState'
import { cn } from '../lib/cn'

export default function Sidebar({ className, style }) {
  const {
    dataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,
    viewMode,
    setViewMode,
    theme,
    toggleTheme,
  } = useGlobalState()

  return (
    <aside
      className={cn('flex flex-col transition-colors duration-200', className)}
      style={{ backgroundColor: 'var(--bg-sidebar)', ...style }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--border-primary)' }}
      >
        <div className="flex items-center gap-2">
          <ScanEye className="w-4 h-4" style={{ color: 'var(--text-accent)' }} />
          <h2
            className="text-sm font-semibold tracking-wide uppercase"
            style={{ color: 'var(--text-secondary)' }}
          >
            Augmenter
          </h2>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-md transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
            e.currentTarget.style.color = 'var(--text-primary)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent'
            e.currentTarget.style.color = 'var(--text-tertiary)'
          }}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      {/* View Mode Toggle */}
      <div
        className="flex gap-1 px-3 py-2 border-b"
        style={{ borderColor: 'var(--border-secondary)' }}
      >
        <button
          onClick={() => setViewMode('IMAGE')}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs font-medium transition-colors"
          style={{
            backgroundColor: viewMode === 'IMAGE' ? 'var(--bg-active-strong)' : 'transparent',
            color: viewMode === 'IMAGE' ? 'var(--text-inverse)' : 'var(--text-secondary)',
          }}
          onMouseEnter={(e) => {
            if (viewMode !== 'IMAGE') {
              e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
              e.currentTarget.style.color = 'var(--text-primary)'
            }
          }}
          onMouseLeave={(e) => {
            if (viewMode !== 'IMAGE') {
              e.currentTarget.style.backgroundColor = 'transparent'
              e.currentTarget.style.color = 'var(--text-secondary)'
            }
          }}
        >
          <Eye className="w-3.5 h-3.5" />
          Image
        </button>
        <button
          onClick={() => setViewMode('GRAPH')}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs font-medium transition-colors"
          style={{
            backgroundColor: viewMode === 'GRAPH' ? 'var(--bg-active-strong)' : 'transparent',
            color: viewMode === 'GRAPH' ? 'var(--text-inverse)' : 'var(--text-secondary)',
          }}
          onMouseEnter={(e) => {
            if (viewMode !== 'GRAPH') {
              e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
              e.currentTarget.style.color = 'var(--text-primary)'
            }
          }}
          onMouseLeave={(e) => {
            if (viewMode !== 'GRAPH') {
              e.currentTarget.style.backgroundColor = 'transparent'
              e.currentTarget.style.color = 'var(--text-secondary)'
            }
          }}
        >
          <GitGraph className="w-3.5 h-3.5" />
          Graph
        </button>
      </div>

      {/* Image List */}
      <div className="flex-1 overflow-y-auto">
        {dataset.map((item) => {
          const isSelected = selectedImageId === item.id
          return (
            <button
              key={item.id}
              onClick={() => setSelectedImageId(item.id)}
              className="w-full flex items-center gap-3 px-3 py-3 text-left transition-colors border-l-2"
              style={{
                backgroundColor: isSelected ? 'var(--bg-active)' : 'transparent',
                borderLeftColor: isSelected ? 'var(--accent-blue)' : 'transparent',
                color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                  e.currentTarget.style.color = 'var(--text-primary)'
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                  e.currentTarget.style.color = 'var(--text-secondary)'
                }
              }}
            >
              {/* Thumbnail placeholder */}
              <div
                className="w-12 h-12 rounded flex items-center justify-center shrink-0"
                style={{ backgroundColor: 'var(--bg-elevated)' }}
              >
                <Image className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.name}</p>
                <p className="text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                  {item.id}
                </p>
              </div>

              <ChevronRight
                className="w-4 h-4 shrink-0 transition-colors"
                style={{ color: isSelected ? 'var(--text-accent)' : 'var(--text-tertiary)' }}
              />
            </button>
          )
        })}
      </div>

      {/* Metadata Panel */}
      {selectedImage && (
        <div
          className="border-t px-4 py-3"
          style={{ borderColor: 'var(--border-primary)' }}
        >
          <h3
            className="text-xs font-semibold uppercase mb-2"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Metadata
          </h3>
          <dl className="space-y-1 text-xs">
            {Object.entries(selectedImage.metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <dt style={{ color: 'var(--text-tertiary)' }}>{key}</dt>
                <dd className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                  {String(value)}
                </dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt style={{ color: 'var(--text-tertiary)' }}>dimensions</dt>
              <dd className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                {selectedImage.width}x{selectedImage.height}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </aside>
  )
}
