import { useState, useLayoutEffect } from 'react'
import { useGlobalState } from '../context/GlobalState'

/**
 * Returns resolved CSS custom property values for use in <canvas> drawing code.
 * Canvas APIs cannot read CSS variables, so we resolve them into a plain object
 * that updates whenever the theme changes.
 *
 * Uses useLayoutEffect to guarantee CSS values are read AFTER the data-theme
 * attribute has been applied to the DOM.
 */
function resolveColors() {
  const style = getComputedStyle(document.documentElement)
  const get = (prop) => style.getPropertyValue(prop).trim()

  return {
    canvasBg: get('--canvas-bg'),
    canvasGrid: get('--canvas-grid'),
    canvasNodeDefault: get('--canvas-node-default'),
    canvasLinkDefault: get('--canvas-link-default'),
    canvasText: get('--canvas-text'),
    canvasTextMuted: get('--canvas-text-muted'),
    canvasTextHighlight: get('--canvas-text-highlight'),
    canvasLabelBg: get('--canvas-label-bg'),
    canvasLabelBgHover: get('--canvas-label-bg-hover'),
    canvasLabelText: get('--canvas-label-text'),
    canvasHoverFill: get('--canvas-hover-fill'),
    canvasHallucinatedLabel: get('--canvas-hallucinated-label'),
    diffCorrect: get('--diff-correct'),
    diffMissing: get('--diff-missing'),
    diffHallucinated: get('--diff-hallucinated'),
    highlightHover: get('--highlight-hover'),
    highlightSelected: get('--highlight-selected'),
  }
}

export function useThemeColors() {
  const { theme } = useGlobalState()
  const [colors, setColors] = useState(resolveColors)

  useLayoutEffect(() => {
    setColors(resolveColors())
  }, [theme])

  return colors
}
