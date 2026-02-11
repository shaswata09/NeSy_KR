import { useState, useEffect, useMemo } from 'react'
import { useGlobalState } from '../context/GlobalState'
import { getAvailableModes } from '../lib/getAvailableModes'
import PaneContainer from './PaneContainer'
import GraphViewer from './GraphViewer'
import ImageViewer from './ImageViewer'
import AttributesViewer from './AttributesViewer'
import ViewModeToggle from './ViewModeToggle'

export default function GroundTruthPane() {
  const { selectedImage } = useGlobalState()
  const [viewMode, setViewMode] = useState('GRAPH')

  const gt = selectedImage?.groundTruth
  const modes = useMemo(
    () =>
      gt
        ? getAvailableModes({
            imageUrl: selectedImage.imageUrl,
            nodes: gt.nodes,
            attributes: gt.attributes,
          })
        : [],
    [gt, selectedImage?.imageUrl]
  )

  // Auto-correct if current mode is no longer available
  useEffect(() => {
    if (modes.length > 0 && !modes.includes(viewMode)) {
      setViewMode(modes[0])
    }
  }, [modes, viewMode])

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
        <ViewModeToggle modes={modes} value={viewMode} onChange={setViewMode} />
      }
    >
      {({ width, height }) =>
        viewMode === 'IMAGE' ? (
          <ImageViewer
            imageData={{ ...gt, width: selectedImage.width, height: selectedImage.height, imageUrl: selectedImage.imageUrl }}
            width={width}
            height={height}
          />
        ) : viewMode === 'GRAPH' ? (
          <GraphViewer
            graphData={gt}
            paneId="groundtruth"
            width={width}
            height={height}
          />
        ) : (
          <AttributesViewer attributes={gt.attributes} nodes={gt.nodes} />
        )
      }
    </PaneContainer>
  )
}
