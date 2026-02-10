import { useGlobalState } from '../context/GlobalState'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'
import ImageViewer from './ImageViewer'

export default function InputPane() {
  const { viewMode, selectedImage } = useGlobalState()

  if (!selectedImage) {
    return (
      <PaneContainer title="Input Source">
        <div
          className="flex items-center justify-center h-full text-sm"
          style={{ color: 'var(--text-tertiary)' }}
        >
          Select an image from the sidebar
        </div>
      </PaneContainer>
    )
  }

  const gt = selectedImage.groundTruth

  return (
    <PaneContainer
      title="Input Source"
      headerRight={
        <span
          className="text-[10px] font-mono px-1.5 py-0.5 rounded"
          style={{ color: 'var(--text-tertiary)', backgroundColor: 'var(--bg-elevated)' }}
        >
          {viewMode}
        </span>
      }
    >
      {({ width, height }) =>
        viewMode === 'IMAGE' ? (
          <ImageViewer
            imageData={{ ...gt, width: selectedImage.width, height: selectedImage.height }}
            width={width}
            height={height}
          />
        ) : (
          <GraphViewer
            graphData={gt}
            paneId="input"
            width={width}
            height={height}
          />
        )
      }
    </PaneContainer>
  )
}
