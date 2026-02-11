import { useCallback, useRef, useState } from "react";
import GroundTruthPane from "./GroundTruthPane";
import InputPane from "./InputPane";
import PredictionPane from "./PredictionPane";
import Sidebar from "./Sidebar";

function DragHandle({ onDrag }) {
  const draggingRef = useRef(false);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    draggingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMouseMove = (e) => {
      if (draggingRef.current) {
        onDrag(e.clientX);
      }
    };

    const handleMouseUp = () => {
      draggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [onDrag]);

  return (
    <div
      onMouseDown={handleMouseDown}
      className="flex-shrink-0 flex items-center justify-center cursor-col-resize"
      style={{ width: 8 }}
      onMouseEnter={(e) => {
        e.currentTarget.querySelector('.drag-pill').style.backgroundColor = 'var(--text-secondary)';
        e.currentTarget.querySelector('.drag-pill').style.width = '5px';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.querySelector('.drag-pill').style.backgroundColor = 'var(--border-primary)';
        e.currentTarget.querySelector('.drag-pill').style.width = '4px';
      }}
    >
      <div
        className="drag-pill rounded-full transition-all duration-150"
        style={{
          width: 4,
          height: 40,
          backgroundColor: 'var(--border-primary)',
        }}
      />
    </div>
  );
}

export default function ComparisonWorkspace() {
  // Panel fractions (must sum to 1)
  const [fractions, setFractions] = useState([1 / 3, 1 / 3, 1 / 3]);
  const containerRef = useRef(null);

  const handleDrag1 = useCallback((clientX) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const totalWidth = rect.width - 16; // 16px for two drag handles
    const pos = clientX - rect.left;
    const newFrac1 = Math.max(0.1, Math.min(0.8, pos / totalWidth));
    setFractions(prev => {
      const remaining = 1 - newFrac1;
      // Keep the ratio of panel 2 and 3 the same
      const ratio = prev[2] / (prev[1] + prev[2]) || 0.5;
      const frac2 = remaining * (1 - ratio);
      const frac3 = remaining * ratio;
      return [newFrac1, Math.max(0.1, frac2), Math.max(0.1, frac3)];
    });
  }, []);

  const handleDrag2 = useCallback((clientX) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const totalWidth = rect.width - 16;
    const pos = clientX - rect.left;
    setFractions(prev => {
      const frac1 = prev[0];
      const newFrac2 = Math.max(0.1, Math.min(0.8 - frac1, pos / totalWidth - frac1));
      const frac3 = Math.max(0.1, 1 - frac1 - newFrac2);
      return [frac1, newFrac2, frac3];
    });
  }, []);

  const handleResetLayout = useCallback(() => {
    setFractions([1 / 3, 1 / 3, 1 / 3]);
  }, []);

  return (
    <div
      className="h-screen w-screen overflow-hidden transition-colors duration-200"
      style={{
        display: "grid",
        gridTemplateColumns: "280px 1fr",
        gridTemplateRows: "100vh",
        gap: "0",
        backgroundColor: "var(--bg-app)",
        color: "var(--text-primary)",
      }}
    >
      {/* Column 1: Sidebar / DatasetExplorer */}
      <Sidebar
        className="border-r"
        style={{ borderColor: "var(--border-primary)" }}
        onResetLayout={handleResetLayout}
      />

      {/* Columns 2-4: Three comparison panes with drag dividers */}
      <div ref={containerRef} className="flex p-2 overflow-hidden" style={{ height: 'calc(100vh - 0px)' }}>
        {/* "INPUT SOURCE" (12 chars) + dropdown + margins */}
        <div className="h-full" style={{ flex: `${fractions[0]} 1 0%`, minWidth: 210 }}>
          <InputPane />
        </div>

        <DragHandle onDrag={handleDrag1} />

        {/* "GROUND TRUTH" (12 chars) + dropdown + margins */}
        <div className="h-full" style={{ flex: `${fractions[1]} 1 0%`, minWidth: 220 }}>
          <GroundTruthPane />
        </div>

        <DragHandle onDrag={handleDrag2} />

        {/* "PREDICTION" (10 chars) + dropdown + margins */}
        <div className="h-full" style={{ flex: `${fractions[2]} 1 0%`, minWidth: 200 }}>
          <PredictionPane />
        </div>
      </div>
    </div>
  );
}
