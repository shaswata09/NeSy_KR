import { useGlobalState } from '../context/GlobalState'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'

export default function GroundTruthPane() {
  const { selectedImage } = useGlobalState()

  if (!selectedImage) {
    return (
      <PaneContainer title="Ground Truth">
        <div className="flex items-center justify-center h-full text-slate-500 text-sm">
          No data selected
        </div>
      </PaneContainer>
    )
  }

  return (
    <PaneContainer
      title="Ground Truth"
      headerRight={
        <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
          {selectedImage.groundTruth.nodes.length} nodes
        </span>
      }
    >
      {({ width, height }) => (
        <GraphViewer
          graphData={selectedImage.groundTruth}
          paneId="groundtruth"
          width={width}
          height={height}
        />
      )}
    </PaneContainer>
  )
}
