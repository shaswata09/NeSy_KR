import { MessageCircleQuestion } from 'lucide-react'

export default function QAViewer({ qas, isDiffView }) {
  if (!qas || qas.length === 0) {
    return (
      <div
        className="flex items-center justify-center h-full text-sm"
        style={{ color: 'var(--text-tertiary)' }}
      >
        No question-answers available
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto px-3 py-2 space-y-3">
      {qas.map((qa, i) => {
        const statusColor = isDiffView && qa.status
          ? `var(--diff-${qa.status})`
          : undefined
        const statusBg = isDiffView && qa.status
          ? `var(--diff-${qa.status}-bg)`
          : undefined

        return (
          <div
            key={qa.id ?? i}
            className="rounded-lg border p-3"
            style={{
              borderColor: isDiffView && qa.status
                ? statusColor
                : 'var(--border-secondary)',
              backgroundColor: 'var(--bg-elevated)',
            }}
          >
            {/* Question */}
            <div className="flex items-start gap-2 mb-1.5">
              <MessageCircleQuestion
                className="w-3.5 h-3.5 mt-0.5 shrink-0"
                style={{ color: 'var(--text-accent)' }}
              />
              <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                {qa.question}
              </p>
            </div>

            {/* Answer */}
            <div className="flex items-start gap-2 pl-5.5">
              <p
                className="text-xs"
                style={{
                  color: qa.answer ? 'var(--text-secondary)' : 'var(--text-tertiary)',
                  fontStyle: qa.answer ? 'normal' : 'italic',
                }}
              >
                {qa.answer ?? 'No answer provided'}
              </p>

              {/* Diff badge */}
              {isDiffView && qa.status && (
                <span
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0 ml-auto"
                  style={{ backgroundColor: statusBg, color: statusColor }}
                >
                  {qa.status}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
