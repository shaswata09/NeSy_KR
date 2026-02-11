import { useEffect, useMemo, useState } from "react";
import { useGlobalState } from "../context/GlobalState";
import { DIFF_STATUS } from "../data/sampleData";
import { getAvailableModes } from "../lib/getAvailableModes";
import AttributesViewer from "./AttributesViewer";
import GraphViewer from "./GraphViewer";
import ImageViewer from "./ImageViewer";
import PaneContainer from "./PaneContainer";
import ViewModeToggle from "./ViewModeToggle";

function DiffLegend() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: "var(--diff-correct)" }}
        />
        <span
          className="text-[10px]"
          style={{ color: "var(--text-secondary)" }}
        >
          Correct
        </span>
      </span>
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full border border-dashed"
          style={{ borderColor: "var(--diff-missing)" }}
        />
        <span
          className="text-[10px]"
          style={{ color: "var(--text-secondary)" }}
        >
          Missing
        </span>
      </span>
      <span className="flex items-center gap-1">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: "var(--diff-hallucinated)" }}
        />
        <span
          className="text-[10px]"
          style={{ color: "var(--text-secondary)" }}
        >
          Hallucinated
        </span>
      </span>
    </div>
  );
}

export default function PredictionPane() {
  const { selectedImage } = useGlobalState();
  const [viewMode, setViewMode] = useState("GRAPH");

  const pred = selectedImage?.prediction;
  const modes = useMemo(
    () =>
      pred
        ? getAvailableModes({
            // Prediction IMAGE mode only if prediction nodes have bboxes
            imageUrl: selectedImage.imageUrl,
            nodes: pred.nodes,
            attributes: pred.attributes,
          })
        : [],
    [pred, selectedImage?.imageUrl],
  );

  // Auto-correct if current mode is no longer available
  useEffect(() => {
    if (modes.length > 0 && !modes.includes(viewMode)) {
      setViewMode(modes[0]);
    }
  }, [modes, viewMode]);

  const stats = useMemo(() => {
    if (!pred) return null;
    const nodes = pred.nodes;
    return {
      correct: nodes.filter((n) => n.status === DIFF_STATUS.CORRECT).length,
      missing: nodes.filter((n) => n.status === DIFF_STATUS.MISSING).length,
      hallucinated: nodes.filter((n) => n.status === DIFF_STATUS.HALLUCINATED)
        .length,
    };
  }, [pred]);

  if (!selectedImage) {
    return (
      <PaneContainer title="Prediction">
        <div
          className="flex items-center justify-center h-full text-sm"
          style={{ color: "var(--text-tertiary)" }}
        >
          No data selected
        </div>
      </PaneContainer>
    );
  }

  return (
    <PaneContainer
      title="Prediction"
      headerLeft={
        <ViewModeToggle modes={modes} value={viewMode} onChange={setViewMode} />
      }
      headerRight={<DiffLegend />}
    >
      {({ width, height }) => (
        <div className="relative" style={{ width, height }}>
          {viewMode === "IMAGE" ? (
            <ImageViewer
              imageData={{
                ...pred,
                width: selectedImage.width,
                height: selectedImage.height,
                imageUrl: selectedImage.imageUrl,
              }}
              width={width}
              height={height}
            />
          ) : viewMode === "GRAPH" ? (
            <GraphViewer
              graphData={pred}
              isDiffView={true}
              paneId="prediction"
              width={width}
              height={height}
            />
          ) : (
            <AttributesViewer
              attributes={pred.attributes}
              nodes={pred.nodes}
              isDiffView={true}
            />
          )}

          {/* Stats overlay */}
          {stats && (
            <div className="absolute bottom-2 left-2 flex gap-2 pointer-events-none">
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: "var(--diff-correct-bg)",
                  color: "var(--diff-correct-text)",
                }}
              >
                {stats.correct} correct
              </span>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: "var(--diff-missing-bg)",
                  color: "var(--diff-missing-text)",
                }}
              >
                {stats.missing} missing
              </span>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: "var(--diff-hallucinated-bg)",
                  color: "var(--diff-hallucinated-text)",
                }}
              >
                {stats.hallucinated} hallucinated
              </span>
            </div>
          )}
        </div>
      )}
    </PaneContainer>
  );
}
