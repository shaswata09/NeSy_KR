import { ChevronDown, ChevronRight, Image, LayoutGrid, Moon, ScanEye, Sun } from 'lucide-react'
import { useGlobalState } from '../context/GlobalState'
import { cn } from '../lib/cn'

export default function Sidebar({ className, style, onResetLayout }) {
  const {
    dataset,
    datasetLoading,
    availableDatasets,
    activeDatasetId,
    switchDataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,
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

        <div className="flex items-center gap-1">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-md transition-colors cursor-pointer"
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

          {/* Reset Layout */}
          {onResetLayout && (
            <button
              onClick={onResetLayout}
              className="p-1.5 rounded-md transition-colors cursor-pointer"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent'
                e.currentTarget.style.color = 'var(--text-tertiary)'
              }}
              title="Reset panel layout"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Dataset Selector */}
      {availableDatasets.length > 1 && (
        <div
          className="px-3 py-2 border-b"
          style={{ borderColor: 'var(--border-primary)' }}
        >
          <label
            className="block text-[10px] font-semibold uppercase mb-1 tracking-wide"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Dataset
          </label>
          <div className="relative">
            <select
              value={activeDatasetId}
              onChange={(e) => switchDataset(e.target.value)}
              className="w-full appearance-none text-xs font-medium rounded-md px-2.5 py-1.5 pr-7 cursor-pointer outline-none transition-colors"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-primary)',
              }}
            >
              {availableDatasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.label}
                </option>
              ))}
            </select>
            <ChevronDown
              className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none"
              style={{ color: 'var(--text-tertiary)' }}
            />
          </div>
        </div>
      )}

      {/* Image List */}
      <div className="flex-1 overflow-y-auto">
        {datasetLoading && (
          <div
            className="flex items-center justify-center py-8 text-xs"
            style={{ color: 'var(--text-tertiary)' }}
          >
            Loading dataset…
          </div>
        )}
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
              {/* Thumbnail */}
              <div
                className="w-12 h-12 rounded overflow-hidden flex items-center justify-center shrink-0"
                style={{ backgroundColor: 'var(--bg-elevated)' }}
              >
                {item.imageUrl ? (
                  <img
                    src={item.imageUrl}
                    alt={item.name}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <Image className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
                )}
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
