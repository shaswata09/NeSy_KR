import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, LocateFixed, Lock, Maximize2, Minimize2, Unlock, ZoomIn, ZoomOut } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';

cytoscape.use(cola);

import { useGlobalState } from '../context/GlobalState';
import { useThemeColors } from '../lib/useThemeColors';

export default function GraphViewer({
  graphData,
  isDiffView = false,
  width,
  height,
  onToggleFullscreen,
  isFullscreen,
}) {
  const cyRef = useRef(null);
  const {
    setSelectedEntityId,
    hoveredEntityId,
    setHoveredEntityId,
    selectedEntityId
  } = useGlobalState();
  const colors = useThemeColors();
  const [locked, setLocked] = useState(false);

  // Convert graphData to Cytoscape elements
  const elements = useMemo(() => {
    const nodes = graphData.nodes.map((n) => ({
      data: { 
        id: n.id, 
        label: n.label || n.id,
        status: n.status,
        isDiffView
      }
    }));

    const edges = graphData.links.map((l, i) => ({
      data: {
        id: `e-${i}`,
        source: typeof l.source === 'object' ? l.source.id : l.source,
        target: typeof l.target === 'object' ? l.target.id : l.target,
        label: l.label,
        status: l.status,
        isDiffView
      }
    }));

    return [...nodes, ...edges];
  }, [graphData, isDiffView]);

  const stylesheet = useMemo(() => [
    {
      selector: 'node',
      style: {
        'width': 16,
        'height': 16,
        'label': 'data(label)',
        'background-color': colors.canvasNodeDefault,
        'color': colors.canvasText,
        'font-size': '10px',
        'font-family': 'Inter, system-ui, sans-serif',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 4,
        'transition-property': 'background-color, line-color, width, height, border-width, border-color, shadow-blur, shadow-color',
        'transition-duration': '0.2s',
        'z-index': 1
      }
    },
    {
      selector: 'node:hover',
      style: {
        'width': 20,
        'height': 20,
        'border-width': 3,
        'border-color': colors.highlightHover,
        'z-index': 10
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': colors.highlightSelected,
        'z-index': 10
      }
    },
    // Status colors
    {
      selector: 'node[status="correct"]',
      style: { 'background-color': colors.diffCorrect }
    },
    {
      selector: 'node[status="hallucinated"]',
      style: { 
        'background-color': colors.diffHallucinated,
        'border-width': 2,
        'border-color': colors.diffHallucinated
      }
    },
    {
      selector: 'node[status="missing"]',
      style: { 
        'background-color': 'transparent',
        'border-width': 2,
        'border-color': colors.diffMissing,
        'border-style': 'dashed'
      }
    },
    // Edges
    {
      selector: 'edge',
      style: {
        'width': 1.5,
        'line-color': colors.canvasLinkDefault,
        'label': 'data(label)',
        'font-size': '8px',
        'color': colors.canvasTextMuted,
        'text-background-opacity': 0.8,
        'text-background-color': 'var(--bg-elevated)',
        'text-background-padding': '2px',
        'text-background-shape': 'roundrectangle',
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        'target-arrow-color': colors.canvasLinkDefault,
        'arrow-scale': 0.8
      }
    },
    {
      selector: 'edge[status="correct"]',
      style: {
        'line-color': colors.diffCorrect,
        'target-arrow-color': colors.diffCorrect
      }
    },
    {
      selector: 'edge[status="hallucinated"]',
      style: {
        'line-color': colors.diffHallucinated,
        'target-arrow-color': colors.diffHallucinated,
        'width': 2.5
      }
    },
    {
      selector: 'edge[status="missing"]',
      style: {
        'line-color': colors.diffMissing,
        'target-arrow-color': colors.diffMissing,
        'line-style': 'dashed'
      }
    },
    {
        selector: 'node.hovered-adj',
        style: {
            'border-width': 2,
            'border-color': colors.highlightHover
        }
    },
    {
        selector: 'edge.highlighted',
        style: {
            'line-color': colors.highlightHover,
            'width': 2,
            'target-arrow-color': colors.highlightHover,
            'z-index': 5
        }
    }
  ], [colors]);

  const layout = {
    name: 'cola',
    animate: true,
    refresh: 1,
    maxSimulationTime: 4000,
    ungrabifyWhileSimulating: false,
    fit: true,
    padding: 30,
    randomize: false,
    avoidOverlap: true,
    handleDisconnected: true,
    convergenceThreshold: 0.01,
    nodeSpacing: 40,
    edgeLength: 100,
    infinite: true // Keep it reactive to dragging
  };

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const handleSelect = (evt) => setSelectedEntityId(evt.target.id());
    const handleUnselect = () => setSelectedEntityId(null);
    const handleMouseOver = (evt) => {
        const node = evt.target;
        setHoveredEntityId(node.id());
        node.neighborhood().addClass('hovered-adj');
        node.connectedEdges().addClass('highlighted');
    };
    const handleMouseOut = (evt) => {
        setHoveredEntityId(null);
        evt.target.neighborhood().removeClass('hovered-adj');
        evt.target.connectedEdges().removeClass('highlighted');
    };

    // Sticky behavior: set node to fixed (locked) after drag
    const handleDragFree = (evt) => {
        evt.target.lock();
        evt.target.addClass('sticky');
    };

    cy.on('tap', 'node', handleSelect);
    cy.on('tap', (evt) => { if (evt.target === cy) handleUnselect(); });
    cy.on('mouseover', 'node', handleMouseOver);
    cy.on('mouseout', 'node', handleMouseOut);
    cy.on('dragfree', 'node', handleDragFree);

    return () => {
      cy.off('tap', 'node', handleSelect);
      cy.off('tap', handleUnselect);
      cy.off('mouseover', 'node', handleMouseOver);
      cy.off('mouseout', 'node', handleMouseOut);
      cy.off('dragfree', 'node', handleDragFree);
    };
  }, [setSelectedEntityId, setHoveredEntityId]);

  // Handle selected entity highlight from external changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedEntityId) {
      cy.$(`#${selectedEntityId}`).select();
    }
  }, [selectedEntityId]);

  const handleToggleLock = useCallback(() => {
    setLocked((prev) => {
      const cy = cyRef.current;
      if (!cy) return prev;
      cy.autolock(!prev);
      return !prev;
    });
  }, []);

  const handleFit = useCallback(() => {
    if (cyRef.current) cyRef.current.fit(null, 50);
  }, []);

  const handleZoomIn = useCallback(() => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 1.2);
  }, []);

  const handleZoomOut = useCallback(() => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() / 1.2);
  }, []);

  const handlePan = (dx, dy) => {
    if (cyRef.current) cyRef.current.panBy({ x: dx, y: dy });
  };

  const btnStyle = { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border-primary)' };
  const btnActiveStyle = { backgroundColor: 'var(--text-secondary)', color: 'var(--bg-pane)', border: '1px solid var(--text-secondary)' };

  return (
    <div className="relative w-full h-full">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={stylesheet}
        layout={layout}
        cy={(cy) => { cyRef.current = cy; }}
        className="bg-transparent"
        zoom={1}
        pan={{ x: 0, y: 0 }}
        minZoom={0.1}
        maxZoom={5}
      />
      
      <div className="absolute bottom-2 right-2 flex items-center gap-2 pointer-events-none">
        <div className="grid grid-cols-3 gap-0.5 pointer-events-auto" style={{ gridTemplateRows: 'repeat(3, auto)' }}>
          <div />
          <button onClick={() => handlePan(0, -40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan up"><ChevronUp size={12} /></button>
          <div />
          <button onClick={() => handlePan(-40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan left"><ChevronLeft size={12} /></button>
          <button onClick={handleFit} className="p-1 rounded cursor-pointer" style={btnStyle} title="Re-center"><LocateFixed size={12} /></button>
          <button onClick={() => handlePan(40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan right"><ChevronRight size={12} /></button>
          <div />
          <button onClick={() => handlePan(0, 40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan down"><ChevronDown size={12} /></button>
          <div />
        </div>
        <div className="flex flex-col gap-0.5 pointer-events-auto">
          <button onClick={handleToggleLock} className="p-1 rounded cursor-pointer" style={locked ? btnActiveStyle : btnStyle} title={locked ? 'Unlock layout' : 'Lock layout'}>
            {locked ? <Lock size={12} /> : <Unlock size={12} />}
          </button>
          <button onClick={handleZoomIn} className="p-1 rounded cursor-pointer" style={btnStyle} title="Zoom in"><ZoomIn size={12} /></button>
          <button onClick={handleZoomOut} className="p-1 rounded cursor-pointer" style={btnStyle} title="Zoom out"><ZoomOut size={12} /></button>
          {onToggleFullscreen && (
            <button onClick={onToggleFullscreen} className="p-1 rounded cursor-pointer" style={btnStyle} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
              {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
