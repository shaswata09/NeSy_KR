import Sidebar from './Sidebar'
import InputPane from './InputPane'
import GroundTruthPane from './GroundTruthPane'
import PredictionPane from './PredictionPane'

export default function ComparisonWorkspace() {
  return (
    <div
      className="h-screen w-screen overflow-hidden transition-colors duration-200"
      style={{
        display: 'grid',
        gridTemplateColumns: '280px 1fr 1fr 1fr',
        gap: '0',
        backgroundColor: 'var(--bg-app)',
        color: 'var(--text-primary)',
      }}
    >
      {/* Column 1: Sidebar / DatasetExplorer */}
      <Sidebar className="border-r" style={{ borderColor: 'var(--border-primary)' }} />

      {/* Columns 2-4: Three comparison panes with gap */}
      <div className="col-span-3 grid grid-cols-3 gap-2 p-2 min-h-0">
        {/* Column 2: Input Source */}
        <InputPane />

        {/* Column 3: Ground Truth */}
        <GroundTruthPane />

        {/* Column 4: Model Prediction with Diff Overlay */}
        <PredictionPane />
      </div>
    </div>
  )
}
