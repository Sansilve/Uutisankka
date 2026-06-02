export default function ToneDashboard({ metrics = {} }) {
  const { tone_stats = {}, timestamp } = metrics

  const toneData = {
    positive: tone_stats.positive_count || 0,
    neutral: tone_stats.neutral_count || 0,
    negative: tone_stats.negative_count || 0,
  }

  const total = Object.values(toneData).reduce((a, b) => a + b, 0)

  const toneEmojis = {
    positive: '😊',
    neutral: '😐',
    negative: '😔',
  }

  const toneLabels = {
    positive: 'Positiivinen',
    neutral: 'Neutraali',
    negative: 'Negatiivinen',
  }

  const tonePercentages = {
    positive: total > 0 ? ((toneData.positive / total) * 100).toFixed(1) : 0,
    neutral: total > 0 ? ((toneData.neutral / total) * 100).toFixed(1) : 0,
    negative: total > 0 ? ((toneData.negative / total) * 100).toFixed(1) : 0,
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>📊 Tone Sentiment Dashboard</h3>
      
      {timestamp && (
        <p style={styles.timestamp}>
          Last updated: {new Date(timestamp).toLocaleTimeString()}
        </p>
      )}

      <div style={styles.chartContainer}>
        <div style={styles.pieChart}>
          {/* Simplified pie chart using CSS */}
          <svg width="200" height="200" viewBox="0 0 100 100" style={styles.svg}>
            {/* Positive (green) */}
            {tonePercentages.positive > 0 && (
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#22c55e"
                strokeWidth="15"
                strokeDasharray={`${(tonePercentages.positive / 100) * 282.6} 282.6`}
              />
            )}
            {/* Neutral (blue) */}
            {tonePercentages.neutral > 0 && (
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#6366f1"
                strokeWidth="15"
                strokeDasharray={`${(tonePercentages.neutral / 100) * 282.6} 282.6`}
                strokeDashoffset={-((tonePercentages.positive / 100) * 282.6)}
              />
            )}
            {/* Negative (red) */}
            {tonePercentages.negative > 0 && (
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="#ef4444"
                strokeWidth="15"
                strokeDasharray={`${(tonePercentages.negative / 100) * 282.6} 282.6`}
                strokeDashoffset={-(((tonePercentages.positive + tonePercentages.neutral) / 100) * 282.6)}
              />
            )}
          </svg>
        </div>

        <div style={styles.legend}>
          <div style={styles.legendItem}>
            <span style={styles.legendEmoji}>{toneEmojis.positive}</span>
            <span style={styles.legendLabel}>{toneLabels.positive}</span>
            <span style={styles.legendValue}>
              {toneData.positive} ({tonePercentages.positive}%)
            </span>
          </div>
          <div style={styles.legendItem}>
            <span style={styles.legendEmoji}>{toneEmojis.neutral}</span>
            <span style={styles.legendLabel}>{toneLabels.neutral}</span>
            <span style={styles.legendValue}>
              {toneData.neutral} ({tonePercentages.neutral}%)
            </span>
          </div>
          <div style={styles.legendItem}>
            <span style={styles.legendEmoji}>{toneEmojis.negative}</span>
            <span style={styles.legendLabel}>{toneLabels.negative}</span>
            <span style={styles.legendValue}>
              {toneData.negative} ({tonePercentages.negative}%)
            </span>
          </div>
        </div>
      </div>

      <div style={styles.stats}>
        <p style={styles.statRow}>
          <strong>Total articles analyzed:</strong> {total}
        </p>
        <p style={styles.statRow}>
          <strong>Tone confidence:</strong>{' '}
          {tone_stats.avg_confidence
            ? (tone_stats.avg_confidence * 100).toFixed(1) + '%'
            : 'N/A'}
        </p>
      </div>
    </div>
  )
}

const styles = {
  container: {
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '16px',
    backgroundColor: '#f9fafb',
    marginBottom: '20px',
  },
  title: {
    margin: '0 0 12px 0',
    fontSize: '18px',
    fontWeight: '600',
    color: '#1a1a1a',
  },
  timestamp: {
    margin: '0 0 16px 0',
    fontSize: '12px',
    color: '#9ca3af',
  },
  chartContainer: {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
    marginBottom: '16px',
  },
  pieChart: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  svg: {
    transform: 'rotate(-90deg)',
  },
  legend: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
  },
  legendEmoji: {
    fontSize: '18px',
    width: '24px',
  },
  legendLabel: {
    fontWeight: '500',
    color: '#4b5563',
    minWidth: '80px',
  },
  legendValue: {
    color: '#9ca3af',
    fontSize: '12px',
  },
  stats: {
    backgroundColor: '#ffffff',
    borderRadius: '4px',
    padding: '12px',
    borderLeft: '4px solid #FFB700',
  },
  statRow: {
    margin: '6px 0',
    fontSize: '13px',
    color: '#374151',
  },
}
