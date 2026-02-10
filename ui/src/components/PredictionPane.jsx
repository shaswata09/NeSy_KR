import { useMemo } from 'react'
import { useGlobalState } from '../context/GlobalState'
import { DIFF_STATUS } from '../data/sampleData'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'

function DiffLegend() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-[10px] text-slate-400">Correct</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full border border-slate-400 border-dashed" />
        <span className="text-[10px] text-slate-400">Missing</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        <span className="text-[10px] text-slate-400">Hallucinated</span>
      </span>
    </div>
  )
}

export default function PredictionPane() {
  const { selectedImage } = useGlobalState()

  const stats = useMemo(() => {
    if (!selectedImage) return null
    const nodes = selectedImage.prediction.nodes
    return {
      correct: nodes.filter((n) => n.status === DIFF_STATUS.CORRECT).length,
      missing: nodes.filter((n) => n.status === DIFF_STATUS.MISSING).length,
      hallucinated: nodes.filter((n) => n.status === DIFF_STATUS.HALLUCINATED).length,
    }
  }, [selectedImage])

  if (!selectedImage) {
    return (
      <PaneContainer title="Model Prediction">
        <div className="flex items-center justify-center h-full text-slate-500 text-sm">
          No data selected
        </div>
      </PaneContainer>
    )
  }

  return (
    <PaneContainer
      title="Model Prediction"
      headerRight={<DiffLegend />}
    >
      {({ width, height }) => (
        <div className="relative" style={{ width, height }}>
          <GraphViewer
            graphData={selectedImage.prediction}
            isDiffView={true}
            paneId="prediction"
            width={width}
            height={height}
          />

          {/* Stats overlay */}
          {stats && (
            <div className="absolute bottom-2 left-2 flex gap-2 pointer-events-none">
              <span className="bg-green-500/20 text-green-400 text-[10px] font-mono px-1.5 py-0.5 rounded">
                {stats.correct} correct
              </span>
              <span className="bg-slate-500/20 text-slate-400 text-[10px] font-mono px-1.5 py-0.5 rounded">
                {stats.missing} missing
              </span>
              <span className="bg-red-500/20 text-red-400 text-[10px] font-mono px-1.5 py-0.5 rounded">
                {stats.hallucinated} hallucinated
              </span>
            </div>
          )}
        </div>
      )}
    </PaneContainer>
  )
}
