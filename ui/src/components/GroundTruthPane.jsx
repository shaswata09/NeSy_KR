import { useState } from 'react'
import { useGlobalState } from '../context/GlobalState'
import { getAvailableModes } from '../lib/getAvailableModes'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'
import ImageViewer from './ImageViewer'
import AttributesViewer from './AttributesViewer'
import QAViewer from './QAViewer'
import ViewModeToggle from './ViewModeToggle'

export default function GroundTruthPane() {
  const { selectedImage } = useGlobalState()
  const [viewMode, setViewMode] = useState('GRAPH')

  const gt = selectedImage?.groundTruth
  const modes = gt
    ? getAvailableModes({
        imageUrl: selectedImage.imageUrl,
        nodes: gt.nodes,
        attributes: gt.attributes,
        qas: gt.qas,
      })
    : []

  const activeMode = modes.includes(viewMode) ? viewMode : (modes[0] ?? viewMode)

  if (!selectedImage) {
    return (
      <PaneContainer title="Ground Truth">
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
      title="Ground Truth"
      headerLeft={
        <ViewModeToggle modes={modes} value={activeMode} onChange={setViewMode} />
      }
    >
      {({ width, height }) =>
        activeMode === 'IMAGE' ? (
          <ImageViewer
            imageData={{ ...gt, width: selectedImage.width, height: selectedImage.height, imageUrl: selectedImage.imageUrl }}
            width={width}
            height={height}
          />
        ) : activeMode === 'GRAPH' ? (
          <GraphViewer
            graphData={gt}
            paneId="groundtruth"
            width={width}
            height={height}
          />
        ) : activeMode === 'ATTRIBUTES' ? (
          <AttributesViewer attributes={gt.attributes} nodes={gt.nodes} />
        ) : (
          <QAViewer qas={gt.qas} />
        )
      }
    </PaneContainer>
  )
}
