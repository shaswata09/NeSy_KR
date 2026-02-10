import { useMemo } from 'react'
import { useGlobalState } from '../context/GlobalState'
import { DIFF_STATUS } from '../data/sampleData'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'

function DiffLegend() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: 'var(--diff-correct)' }}
        />
        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Correct</span>
      </span>
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full border border-dashed"
          style={{ borderColor: 'var(--diff-missing)' }}
        />
        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Missing</span>
      </span>
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: 'var(--diff-hallucinated)' }}
        />
        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Hallucinated</span>
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
        <div
          className="flex items-center justify-center h-full text-sm"
          style={{ color: 'var(--text-tertiary)' }}
        >
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
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--diff-correct-bg)',
                  color: 'var(--diff-correct-text)',
                }}
              >
                {stats.correct} correct
              </span>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--diff-missing-bg)',
                  color: 'var(--diff-missing-text)',
                }}
              >
                {stats.missing} missing
              </span>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--diff-hallucinated-bg)',
                  color: 'var(--diff-hallucinated-text)',
                }}
              >
                {stats.hallucinated} hallucinated
              </span>
            </div>
          )}
        </div>
      )}
    </PaneContainer>
  )
}
