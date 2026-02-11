import cytoscape from 'cytoscape';
import d3Force from 'cytoscape-d3-force';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, LocateFixed, Lock, Maximize2, Minimize2, Unlock, Waypoints, ZoomIn, ZoomOut } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';

cytoscape.use(d3Force);

import { useGlobalState } from '../context/GlobalState';
import { useThemeColors } from '../lib/useThemeColors';

export default function GraphViewer({
  graphData,
  isDiffView = false,
  width,
  height,
  onToggleFullscreen,
  isFullscreen,
  hiddenStatuses = [],
}) {
  const cyRef = useRef(null);
  const {
    selectedEntityId,
    setSelectedEntityId,
    selectedEdgeId,
    setSelectedEdgeId,
    hoveredEntityId,
    setHoveredEntityId
  } = useGlobalState();
  const colors = useThemeColors();
  const [locked, setLocked] = useState(false);
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, title: '', attributes: [] });




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
    },
    // Selection highlighting (from image bounding box)
    {
        selector: 'node.selected-adj',
        style: {
            'border-width': 2,
            'border-color': colors.highlightSelected,
            'opacity': 1
        }
    },
    {
        selector: 'edge.selected-edge',
        style: {
            'line-color': colors.highlightSelected,
            'width': 2.5,
            'target-arrow-color': colors.highlightSelected,
            'z-index': 5,
            'opacity': 1
        }
    },
    // Dim non-selected elements when something is selected
    {
        selector: 'node.dimmed',
        style: {
            'opacity': 0.25
        }
    },
    {
        selector: 'edge.dimmed',
        style: {
            'opacity': 0.15
        }
    },
    // Hidden status (toggled via legend)
    {
        selector: '.status-hidden',
        style: {
            'display': 'none'
        }
    }
  ], [colors]);

  // Convert graphData to Cytoscape elements (for rendering)
  const elements = useMemo(() => {
    const nodes = graphData.nodes.map((n) => ({
      data: { 
        id: n.id, 
        label: n.label || n.id,
        status: n.status,
        isDiffView
      }
    }));

    const edges = graphData.links.map((l) => {
      const source = typeof l.source === 'object' ? l.source.id : l.source;
      const target = typeof l.target === 'object' ? l.target.id : l.target;
      // Stable ID based on connection content, not list index
      const edgeId = `e-${source}-${target}-${l.label || 'rel'}`;
      
      return {
        data: {
          id: edgeId,
          source,
          target,
          label: l.label,
          status: l.status,
          isDiffView
        }
      };
    });

    return [...nodes, ...edges];
  }, [graphData, isDiffView]);

  const d3Config = useMemo(() => ({
    name: 'd3-force',
    animate: true,
    fixedAfterDragging: true,
    ungrabifyWhileSimulating: false,
    fit: false,
    padding: 50,
    linkId: (d) => d.id,
    linkDistance: 200,          // Long edges → more room, fewer crossings
    manyBodyStrength: -3000,    // Very strong repulsion → no overlap
    manyBodyDistanceMin: 1,
    manyBodyDistanceMax: 1500,
    collideRadius: 80,          // Large exclusion zone around each node
    collideStrength: 1,         // Full enforcement
    collideIterations: 4,       // Multiple passes per tick for accuracy
    alpha: 1,
    alphaMin: 0.001,
    alphaDecay: 0.1,             // Very fast cooling
    velocityDecay: 0.6,          // Heavy damping → almost no bouncing
    infinite: true,
    randomize: true
  }), []);

  // Refs for stable state access

  const setSelectedRef = useRef(setSelectedEntityId);
  setSelectedRef.current = setSelectedEntityId;
  const setSelectedEdgeRef = useRef(setSelectedEdgeId);
  setSelectedEdgeRef.current = setSelectedEdgeId;



  const setHoveredRef = useRef(setHoveredEntityId);
  setHoveredRef.current = setHoveredEntityId;

  // 1. Setup listeners (Once)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const handleSelect = (evt) => {
        setSelectedEdgeRef.current(null);
        setSelectedRef.current(evt.target.id());
    };
    const handleUnselect = () => {
        setSelectedRef.current(null);
        setSelectedEdgeRef.current(null);
    };
    
    const handleMouseOver = (evt) => {
        const node = evt.target;
        setHoveredRef.current(node.id());
        node.neighborhood().addClass('hovered-adj');
        node.connectedEdges().addClass('highlighted');
    };
    
    const handleMouseOut = (evt) => {
        setHoveredRef.current(null);
        evt.target.neighborhood().removeClass('hovered-adj');
        evt.target.connectedEdges().removeClass('highlighted');
    };

    // Sticky Logic for D3
    const handleDragFree = (evt) => {
        const node = evt.target;
        const pos = node.position();
        // Set fx/fy to fix node in place for D3
        node.data('fx', pos.x);
        node.data('fy', pos.y);
        node.addClass('sticky');
    };

    const handleGrab = (evt) => {
        const node = evt.target;
        if (node.isNode && node.isNode()) {
            // Unset fx/fy so it can move freely
            node.data('fx', null);
            node.data('fy', null);
        }
    };

    cy.on('tap', 'node', handleSelect);
    cy.on('tap', (evt) => { if (evt.target === cy) handleUnselect(); });
    cy.on('mouseover', 'node', handleMouseOver);
    cy.on('mouseout', 'node', handleMouseOut);
    cy.on('dragfree', 'node', handleDragFree);
    cy.on('grab', 'node', handleGrab);

    // Edge click → highlight connected nodes. Highlights handled by useEffect.
    const handleEdgeTap = (evt) => {
      const edge = evt.target;
      const sourceNode = edge.source();
      setSelectedRef.current(sourceNode.id());
      setSelectedEdgeRef.current(edge.id());
    };

    // Edge hover effects
    const handleEdgeMouseOver = (evt) => {
      const edge = evt.target;
      edge.addClass('highlighted');
      edge.source().addClass('hovered-adj');
      edge.target().addClass('hovered-adj');
    };
    const handleEdgeMouseOut = (evt) => {
      const edge = evt.target;
      edge.removeClass('highlighted');
      edge.source().removeClass('hovered-adj');
      edge.target().removeClass('hovered-adj');
    };

    const handleCxtTap = (evt) => {
      const target = evt.target;
      if (target === cy) {
        setContextMenu({ visible: false });
        return;
      }

      const id = target.id();
      const label = target.data('label') || id;
      const type = target.isNode() ? 'Node' : 'Edge';
      
      // Filter attributes for this entity
      const entityAttrs = (graphData.attributes || []).filter(a => a.entityId === id);

      if (entityAttrs.length > 0) {
        const pos = evt.renderedPosition;
        setContextMenu({
          visible: true,
          x: pos.x,
          y: pos.y,
          title: `${type}: ${label}`,
          attributes: entityAttrs
        });
      }
    };

    cy.on('tap', 'edge', handleEdgeTap);
    cy.on('mouseover', 'edge', handleEdgeMouseOver);
    cy.on('mouseout', 'edge', handleEdgeMouseOut);
    cy.on('cxttap', handleCxtTap);
    cy.on('tapstart', () => setContextMenu({ visible: false }));
    cy.on('dragstart', () => setContextMenu({ visible: false }));
    cy.on('zoom pan', () => setContextMenu({ visible: false }));

    return () => {
      cy.off('tap', 'node', handleSelect);
      cy.off('tap', handleUnselect);
      cy.off('mouseover', 'node', handleMouseOver);
      cy.off('mouseout', 'node', handleMouseOut);
      cy.off('dragfree', 'node', handleDragFree);
      cy.off('grab', 'node', handleGrab);
      cy.off('tap', 'edge', handleEdgeTap);
      cy.off('mouseover', 'edge', handleEdgeMouseOver);
      cy.off('mouseout', 'edge', handleEdgeMouseOut);
      cy.off('cxttap', handleCxtTap);
    };
  }, []);

  // Handle new data load: Restart simulation and fit once settled
  const hasFittedRef = useRef(false);
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || elements.length === 0) return;

    // Reset fit state for new data
    hasFittedRef.current = false;
    
    let layout;
    
    // Use requestAnimationFrame to ensure cy instance is synchronized with React props
    // This solves the issue where layout.run() would execution on old/cached elements
    const rafId = requestAnimationFrame(() => {
      if (!cy || cy.destroyed()) return;
      
      layout = cy.layout(d3Config);
      layout.run();

      const fitOnce = () => {
        if (!hasFittedRef.current) {
          hasFittedRef.current = true;
          setTimeout(() => {
            if (!cy.destroyed()) {
              cy.animate({ fit: { eles: cy.elements(), padding: 50 }, duration: 500 });
            }
          }, 1000); // Slightly more time for d3 physics to push nodes out
        }
      };
      fitOnce();
    });

    return () => {
      cancelAnimationFrame(rafId);
      if (layout) layout.stop();
    };
  }, [elements, d3Config]);

  // Handle selected entity highlight from external changes (e.g. image bounding box or other panels)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // Clear previous selection highlights
    cy.elements().removeClass('selected-adj selected-edge dimmed');
    cy.nodes().unselect();

    // Priority 1: Edge selection (comes from another panel or local edge click)
    if (selectedEdgeId) {
      let selectedEdge = cy.$(`#${selectedEdgeId}`);
      
      // Fallback: If exact ID match fails (e.g. data source slightly changed), 
      // try to find any edge connecting the same source and target if we can parse the ID
      if (selectedEdge.length === 0 && selectedEdgeId.startsWith('e-')) {
        const parts = selectedEdgeId.split('-');
        if (parts.length >= 3) {
          const src = parts[1];
          const tgt = parts[2];
          selectedEdge = cy.edges(`edge[source="${src}"][target="${tgt}"]`).first();
        }
      }

      if (selectedEdge.length > 0) {
        const sourceNode = selectedEdge.source();
        const targetNode = selectedEdge.target();
        
        sourceNode.select();
        targetNode.addClass('selected-adj');
        selectedEdge.addClass('selected-edge');
        cy.elements().not(sourceNode).not(targetNode).not(selectedEdge).addClass('dimmed');
        return;
      }
    }

    // Priority 2: Node selection
    if (selectedEntityId) {
      const selectedNode = cy.$(`#${selectedEntityId}`);
      if (selectedNode.length > 0) {
        selectedNode.select();
        // Highlight connected edges and neighbor nodes
        const connectedEdges = selectedNode.connectedEdges();
        const neighborNodes = selectedNode.neighborhood('node');
        connectedEdges.addClass('selected-edge');
        neighborNodes.addClass('selected-adj');
        // Dim everything else
        cy.elements().not(selectedNode).not(connectedEdges).not(neighborNodes).addClass('dimmed');
      }
    }
  }, [selectedEntityId, selectedEdgeId]);

  // Toggle visibility of nodes/edges based on hiddenStatuses from legend
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // Remove all status-hidden first
    cy.elements().removeClass('status-hidden');

    // Hide nodes and edges whose status is in the hidden list
    hiddenStatuses.forEach((status) => {
      cy.nodes(`[status="${status}"]`).addClass('status-hidden');
      cy.edges(`[status="${status}"]`).addClass('status-hidden');
    });
  }, [hiddenStatuses]);

  const handleToggleLock = useCallback(() => {
    setLocked((prev) => {
      const cy = cyRef.current;
      if (!cy) return prev;
      cy.autolock(!prev);
      return !prev;
    });
  }, []);

  const handleFit = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.animate({
        fit: { eles: cyRef.current.elements(), padding: 50 },
        duration: 500
      });
    }
  }, []);

  const handleAutoArrange = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    // Clear all fixed positions so nodes can move freely
    cy.nodes().forEach(n => {
      n.data('fx', null);
      n.data('fy', null);
      n.removeClass('sticky');
    });
    // Run a compact but natural layout
    const compactLayout = cy.makeLayout({
      name: 'd3-force',
      animate: true,
      fit: false,
      fixedAfterDragging: false,
      ungrabifyWhileSimulating: false,
      padding: 30,
      linkId: (d) => d.id,
      linkDistance: 120,         // Moderate edges for natural compactness
      manyBodyStrength: -1500,   // Balanced repulsion (not forced)
      manyBodyDistanceMin: 1,
      manyBodyDistanceMax: 800,
      collideRadius: 50,
      collideStrength: 1,
      collideIterations: 4,
      alpha: 1,
      alphaMin: 0.05,
      alphaDecay: 0.1,
      velocityDecay: 0.6,
      randomize: false
    });
    compactLayout.run();
    // After settling, pin all nodes and fit
    setTimeout(() => {
      cy.nodes().forEach(n => {
        const pos = n.position();
        n.data('fx', pos.x);
        n.data('fy', pos.y);
      });
      cy.animate({ fit: { eles: cy.elements(), padding: 40 }, duration: 500 });
    }, 800);
  }, []);

  const handleZoomIn = useCallback(() => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom({
        level: cy.zoom() * 1.2,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
      });
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (cyRef.current) {
      const cy = cyRef.current;
      cy.zoom({
        level: cy.zoom() / 1.2,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
      });
    }
  }, []);

  const handlePan = useCallback((dx, dy) => {
    if (cyRef.current) {
      cyRef.current.panBy({ x: dx, y: dy });
    }
  }, []);

  const btnStyle = { backgroundColor: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border-primary)' };
  const btnActiveStyle = { backgroundColor: 'var(--text-secondary)', color: 'var(--bg-pane)', border: '1px solid var(--text-secondary)' };

  return (
    <div className="relative w-full h-full">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={stylesheet}
        layout={d3Config}
        cy={(cy) => { cyRef.current = cy; }}
        className="bg-transparent"
        minZoom={0.05}
        maxZoom={10}
      />
      
      <div className="absolute bottom-2 right-2 flex items-center gap-2 pointer-events-none">
        <div className="grid grid-cols-3 gap-0.5 pointer-events-auto" style={{ gridTemplateRows: 'repeat(3, auto)' }}>
          <div />
          <button onClick={() => handlePan(0, 40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan up"><ChevronUp size={12} /></button>
          <div />
          <button onClick={() => handlePan(40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan left"><ChevronLeft size={12} /></button>
          <button onClick={handleFit} className="p-1 rounded cursor-pointer" style={btnStyle} title="Re-center"><LocateFixed size={12} /></button>
          <button onClick={() => handlePan(-40, 0)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan right"><ChevronRight size={12} /></button>
          <div />
          <button onClick={() => handlePan(0, -40)} className="p-1 rounded cursor-pointer" style={btnStyle} title="Pan down"><ChevronDown size={12} /></button>
          <div />
        </div>
        <div className="flex flex-col gap-0.5 pointer-events-auto">
          <button onClick={handleAutoArrange} className="p-1 rounded cursor-pointer" style={btnStyle} title="Auto arrange">
            <Waypoints size={12} />
          </button>
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

      {/* Context Menu Popup */}
      {contextMenu.visible && (
        <div 
          className="absolute z-[100] shadow-xl border rounded-md overflow-hidden min-w-[180px]"
          style={{ 
            left: contextMenu.x + 10, 
            top: contextMenu.y + 10,
            backgroundColor: 'var(--bg-elevated)',
            borderColor: 'var(--border-secondary)',
            backdropFilter: 'blur(8px)'
          }}
        >
          <div className="px-3 py-2 border-b bg-black/5" style={{ borderColor: 'var(--border-secondary)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
              {contextMenu.title}
            </p>
          </div>
          <div className="max-h-[200px] overflow-y-auto">
            <table className="w-full text-left text-[11px] border-collapse">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border-secondary)' }}>
                  <th className="px-3 py-1.5 font-semibold" style={{ color: 'var(--text-tertiary)' }}>Attribute</th>
                  <th className="px-3 py-1.5 font-semibold text-right" style={{ color: 'var(--text-tertiary)' }}>Value</th>
                </tr>
              </thead>
              <tbody>
                {contextMenu.attributes.map((attr, i) => (
                  <tr key={i} className="border-b last:border-0" style={{ borderColor: 'var(--border-secondary)' }}>
                    <td className="px-3 py-1.5" style={{ color: 'var(--text-secondary)' }}>{attr.attribute}</td>
                    <td className="px-3 py-1.5 text-right font-mono" style={{ color: 'var(--text-primary)' }}>{attr.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
