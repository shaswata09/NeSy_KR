import { useState } from "react";
import { useGlobalState } from "../context/GlobalState";
import { DIFF_STATUS } from "../lib/diffStatus";
import { getAvailableModes } from "../lib/getAvailableModes";
import AttributesViewer from "./AttributesViewer";
import GraphViewer from "./GraphViewer";
import ImageViewer from "./ImageViewer";
import PaneContainer from "./PaneContainer";
import QAViewer from "./QAViewer";
import ViewModeToggle from "./ViewModeToggle";

function DiffLegend({ visibility, onToggle }) {
  const items = [
    {
      key: "correct",
      label: "Correct",
      dot: (
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: "var(--diff-correct)" }}
        />
      ),
    },
    {
      key: "missing",
      label: "Missing",
      dot: (
        <span
          className="w-2 h-2 rounded-full border border-dashed"
          style={{ borderColor: "var(--diff-missing)" }}
        />
      ),
    },
    {
      key: "hallucinated",
      label: "Hallucinated",
      dot: (
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: "var(--diff-hallucinated)" }}
        />
      ),
    },
  ];

  return (
    <div className="flex items-center gap-3">
      {items.map((item) => {
        const active = visibility[item.key];
        return (
          <button
            key={item.key}
            onClick={() => onToggle(item.key)}
            className="flex items-center gap-1 cursor-pointer transition-opacity"
            style={{ opacity: active ? 1 : 0.35 }}
            title={active ? `Hide ${item.label.toLowerCase()}` : `Show ${item.label.toLowerCase()}`}
          >
            {item.dot}
            <span
              className="text-[10px]"
              style={{
                color: "var(--text-secondary)",
                textDecoration: active ? "none" : "line-through",
              }}
            >
              {item.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function PredictionPane() {
  const { selectedImage } = useGlobalState();
  const [viewMode, setViewMode] = useState("GRAPH");
  const [statusVisibility, setStatusVisibility] = useState({
    correct: true,
    missing: true,
    hallucinated: true,
  });

  const toggleStatus = (key) =>
    setStatusVisibility((prev) => ({ ...prev, [key]: !prev[key] }));

  const pred = selectedImage?.prediction;
  const modes = pred
    ? getAvailableModes({
        imageUrl: selectedImage.imageUrl,
        nodes: pred.nodes,
        attributes: pred.attributes,
        qas: pred.qas,
      })
    : [];

  // Auto-correct: if current mode is unavailable, fall back to first available
  const activeMode = modes.includes(viewMode) ? viewMode : (modes[0] ?? viewMode);

  const stats = pred
    ? {
        correct: pred.nodes.filter((n) => n.status === DIFF_STATUS.CORRECT).length,
        missing: pred.nodes.filter((n) => n.status === DIFF_STATUS.MISSING).length,
        hallucinated: pred.nodes.filter((n) => n.status === DIFF_STATUS.HALLUCINATED).length,
      }
    : null;

  if (!selectedImage || !pred) {
    return (
      <PaneContainer title="Prediction">
        <div
          className="flex items-center justify-center h-full text-sm"
          style={{ color: "var(--text-tertiary)" }}
        >
          {selectedImage ? "No prediction available" : "No data selected"}
        </div>
      </PaneContainer>
    );
  }

  return (
    <PaneContainer
      title="Prediction"
      headerLeft={
        <ViewModeToggle modes={modes} value={activeMode} onChange={setViewMode} />
      }
      headerRight={null}
    >
      {({ width, height, toggleFullscreen, isFullscreen }) => (
        <div className="relative" style={{ width, height }}>
          {/* Diff legend overlay - only for GRAPH mode */}
          {activeMode === "GRAPH" && (
            <div className="absolute top-2 left-2 z-10 flex items-center gap-3">
              <DiffLegend visibility={statusVisibility} onToggle={toggleStatus} />
            </div>
          )}
          {activeMode === "IMAGE" ? (
            <ImageViewer
              imageData={{
                ...pred,
                width: selectedImage.width,
                height: selectedImage.height,
                imageUrl: selectedImage.imageUrl,
              }}
              width={width}
              height={height}
              onToggleFullscreen={toggleFullscreen}
              isFullscreen={isFullscreen}
            />
          ) : activeMode === "GRAPH" ? (
            <GraphViewer
              graphData={pred}
              isDiffView={true}
              paneId="prediction"
              width={width}
              height={height}
              onToggleFullscreen={toggleFullscreen}
              isFullscreen={isFullscreen}
              hiddenStatuses={Object.entries(statusVisibility)
                .filter(([, v]) => !v)
                .map(([k]) => k)}
            />
          ) : activeMode === "ATTRIBUTES" ? (
            <AttributesViewer
              attributes={pred.attributes}
              nodes={pred.nodes}
              isDiffView={true}
            />
          ) : (
            <QAViewer qas={pred.qas} isDiffView={true} />
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
