# Augmenter UI

React + Vite application for visualizing and comparing ground truth vs. model predictions across scene graphs, images, attributes, and question-answers.

## Getting Started

```bash
npm install
npm run dev      # development server at http://localhost:5173
npm run build    # production build
npm run preview  # preview production build
```

## Architecture

```
src/
  components/
    ComparisonWorkspace.jsx   CSS Grid layout (sidebar + 3 panes)
    Sidebar.jsx               Dataset list, theme toggle
    PaneContainer.jsx         Reusable pane wrapper with ResizeObserver
    InputPane.jsx             Input source viewer (ground truth data)
    GroundTruthPane.jsx       Ground truth viewer
    PredictionPane.jsx        Prediction viewer with diff overlay
    ImageViewer.jsx           Canvas-based image + bounding box renderer
    GraphViewer.jsx           Force-directed graph (react-force-graph-2d)
    AttributesViewer.jsx      Scrollable entity attribute table
    QAViewer.jsx              Question-answer card list
    ViewModeToggle.jsx        Per-pane dropdown for switching view modes
  context/
    GlobalState.jsx           React Context for shared state
  data/
    sampleData.js             Sample Visual Genome data (images 1, 2, 3)
  lib/
    cn.js                     clsx + tailwind-merge utility
    getAvailableModes.js      Computes available view modes from data
    useThemeColors.js         Resolves CSS vars for canvas rendering
```

## Dataset Format

See [`../dataset-template.json`](../dataset-template.json) and the [project README](../README.md) for the full dataset schema specification.

To use your own data, replace or extend `src/data/sampleData.js` following the template format.

## Tech Stack

- React 19 + Vite 7
- Tailwind CSS v4
- react-force-graph-2d + d3-force
- lucide-react (icons)
- CSS custom properties for light/dark theming
