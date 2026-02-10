import { Image, Database, ChevronRight, Eye, GitGraph } from 'lucide-react'
import { useGlobalState } from '../context/GlobalState'
import { cn } from '../lib/cn'

export default function Sidebar({ className }) {
  const {
    dataset,
    selectedImageId,
    setSelectedImageId,
    selectedImage,
    viewMode,
    setViewMode,
  } = useGlobalState()

  return (
    <aside className={cn('flex flex-col bg-[var(--color-sidebar-bg)]', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-700">
        <Database className="w-4 h-4 text-blue-400" />
        <h2 className="text-sm font-semibold tracking-wide uppercase text-slate-300">
          Dataset Explorer
        </h2>
      </div>

      {/* View Mode Toggle */}
      <div className="flex gap-1 px-3 py-2 border-b border-slate-700/50">
        <button
          onClick={() => setViewMode('IMAGE')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs font-medium transition-colors',
            viewMode === 'IMAGE'
              ? 'bg-blue-600 text-white'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          )}
        >
          <Eye className="w-3.5 h-3.5" />
          Image
        </button>
        <button
          onClick={() => setViewMode('GRAPH')}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-xs font-medium transition-colors',
            viewMode === 'GRAPH'
              ? 'bg-blue-600 text-white'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          )}
        >
          <GitGraph className="w-3.5 h-3.5" />
          Graph
        </button>
      </div>

      {/* Image List */}
      <div className="flex-1 overflow-y-auto">
        {dataset.map((item) => (
          <button
            key={item.id}
            onClick={() => setSelectedImageId(item.id)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-3 text-left transition-colors border-l-2',
              selectedImageId === item.id
                ? 'bg-slate-800/80 border-l-blue-500 text-white'
                : 'border-l-transparent text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
            )}
          >
            {/* Thumbnail placeholder */}
            <div className="w-12 h-12 rounded bg-slate-700 flex items-center justify-center shrink-0">
              <Image className="w-5 h-5 text-slate-500" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{item.name}</p>
              <p className="text-xs text-slate-500 truncate">{item.id}</p>
            </div>

            <ChevronRight className={cn(
              'w-4 h-4 shrink-0 transition-colors',
              selectedImageId === item.id ? 'text-blue-400' : 'text-slate-600'
            )} />
          </button>
        ))}
      </div>

      {/* Metadata Panel */}
      {selectedImage && (
        <div className="border-t border-slate-700 px-4 py-3">
          <h3 className="text-xs font-semibold uppercase text-slate-500 mb-2">Metadata</h3>
          <dl className="space-y-1 text-xs">
            {Object.entries(selectedImage.metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <dt className="text-slate-500">{key}</dt>
                <dd className="text-slate-300 font-mono">{String(value)}</dd>
              </div>
            ))}
            <div className="flex justify-between">
              <dt className="text-slate-500">dimensions</dt>
              <dd className="text-slate-300 font-mono">{selectedImage.width}x{selectedImage.height}</dd>
            </div>
          </dl>
        </div>
      )}
    </aside>
  )
}
