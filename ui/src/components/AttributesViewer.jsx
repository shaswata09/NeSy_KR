import { useGlobalState } from '../context/GlobalState'

export default function AttributesViewer({ attributes, nodes, isDiffView }) {
  const { hoveredEntityId, selectedEntityId, setHoveredEntityId, setSelectedEntityId, setSelectedEdgeId } = useGlobalState()

  if (!attributes || attributes.length === 0) {
    return (
      <div
        className="flex items-center justify-center h-full text-sm"
        style={{ color: 'var(--text-tertiary)' }}
      >
        No attributes available
      </div>
    )
  }

  // Build a label lookup from nodes
  const labelMap = {}
  for (const n of nodes ?? []) {
    labelMap[n.id] = n.label
  }

  return (
    <div className="h-full overflow-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr
            className="sticky top-0"
            style={{ backgroundColor: 'var(--bg-pane)' }}
          >
            <th
              className="text-left px-3 py-2 font-semibold border-b"
              style={{ color: 'var(--text-tertiary)', borderColor: 'var(--border-secondary)' }}
            >
              Entity
            </th>
            <th
              className="text-left px-3 py-2 font-semibold border-b"
              style={{ color: 'var(--text-tertiary)', borderColor: 'var(--border-secondary)' }}
            >
              Attribute
            </th>
            <th
              className="text-left px-3 py-2 font-semibold border-b"
              style={{ color: 'var(--text-tertiary)', borderColor: 'var(--border-secondary)' }}
            >
              Value
            </th>
            {isDiffView && (
              <th
                className="text-left px-3 py-2 font-semibold border-b"
                style={{ color: 'var(--text-tertiary)', borderColor: 'var(--border-secondary)' }}
              >
                Status
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {attributes.map((attr, i) => {
            const isHovered = hoveredEntityId === attr.entityId
            const isSelected = selectedEntityId === attr.entityId

            const rowBg = isSelected
              ? 'var(--bg-active)'
              : isHovered
                ? 'var(--bg-hover)'
                : 'transparent'

            const statusColor = isDiffView && attr.status
              ? `var(--diff-${attr.status})`
              : undefined

            const statusBg = isDiffView && attr.status
              ? `var(--diff-${attr.status}-bg)`
              : undefined

            return (
              <tr
                key={`${attr.entityId}-${attr.attribute}-${i}`}
                className="cursor-pointer transition-colors"
                style={{ backgroundColor: rowBg }}
                onClick={() => {
                  const nextId = attr.entityId === selectedEntityId ? null : attr.entityId;
                  setSelectedEntityId(nextId);
                  setSelectedEdgeId(null);
                }}
                onMouseEnter={() => setHoveredEntityId(attr.entityId)}
                onMouseLeave={() => setHoveredEntityId(null)}
              >
                <td
                  className="px-3 py-1.5 border-b font-medium"
                  style={{ color: 'var(--text-primary)', borderColor: 'var(--border-secondary)' }}
                >
                  {labelMap[attr.entityId] ?? attr.entityId}
                </td>
                <td
                  className="px-3 py-1.5 border-b"
                  style={{ color: 'var(--text-secondary)', borderColor: 'var(--border-secondary)' }}
                >
                  {attr.attribute}
                </td>
                <td
                  className="px-3 py-1.5 border-b font-mono"
                  style={{ color: 'var(--text-secondary)', borderColor: 'var(--border-secondary)' }}
                >
                  {attr.value}
                </td>
                {isDiffView && (
                  <td
                    className="px-3 py-1.5 border-b"
                    style={{ borderColor: 'var(--border-secondary)' }}
                  >
                    {attr.status && (
                      <span
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                        style={{ backgroundColor: statusBg, color: statusColor }}
                      >
                        {attr.status}
                      </span>
                    )}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
