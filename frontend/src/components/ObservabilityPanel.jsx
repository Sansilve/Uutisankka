export default function ObservabilityPanel({ metrics = {} }) {
  const {
    ingest_stats = {},
    llm_stats = {},
    timestamp,
    scoring_version = 'unknown',
    adaptive_scoring_enabled = false,
  } = metrics

  const llmProviders = Object.entries(llm_stats).map(([name, stats]) => ({
    name,
    ...stats,
  }))

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>🔧 Observability Panel</h3>

      {timestamp && (
        <p style={styles.timestamp}>
          Last updated: {new Date(timestamp).toLocaleTimeString()}
        </p>
      )}

      {/* Ingest Stats */}
      <div style={styles.section}>
        <h4 style={styles.sectionTitle}>📥 Ingest Statistics</h4>
        <table style={styles.table}>
          <tbody>
            <tr>
              <td>Articles ingested (today)</td>
              <td style={styles.value}>{ingest_stats.total_ingested || 0}</td>
            </tr>
            <tr>
              <td>New articles</td>
              <td style={styles.value}>{ingest_stats.new_articles || 0}</td>
            </tr>
            <tr>
              <td>Updated articles</td>
              <td style={styles.value}>{ingest_stats.updated_articles || 0}</td>
            </tr>
            <tr>
              <td>Summaries generated</td>
              <td style={styles.value}>{ingest_stats.summaries_generated || 0}</td>
            </tr>
            <tr>
              <td>Last ingest status</td>
              <td style={styles.value}>
                {ingest_stats.last_status === 'success' ? '✅' : '❌'}{' '}
                {ingest_stats.last_status || 'Unknown'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* LLM Provider Metrics */}
      <div style={styles.section}>
        <h4 style={styles.sectionTitle}>🤖 LLM Provider Metrics</h4>
        {llmProviders.length > 0 ? (
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Calls</th>
                <th>Errors</th>
                <th>P50 (ms)</th>
                <th>P95 (ms)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {llmProviders.map((provider) => (
                <tr key={provider.name}>
                  <td style={styles.providerName}>{provider.name}</td>
                  <td>{provider.call_count || 0}</td>
                  <td>{provider.error_count || 0}</td>
                  <td>{provider.p50_ms?.toFixed(0) || 'N/A'}</td>
                  <td style={{
                    color: provider.p95_ms > 10000 ? '#ef4444' : '#374151',
                    fontWeight: provider.p95_ms > 10000 ? '600' : 'normal',
                  }}>
                    {provider.p95_ms?.toFixed(0) || 'N/A'}
                  </td>
                  <td>
                    {provider.error_count === 0 ? '✅ OK' : '⚠️ Errors'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={styles.emptyMessage}>No LLM provider metrics available yet.</p>
        )}
      </div>

      {/* Scoring Configuration */}
      <div style={styles.section}>
        <h4 style={styles.sectionTitle}>🎯 Scoring Configuration</h4>
        <table style={styles.table}>
          <tbody>
            <tr>
              <td>Scoring version</td>
              <td style={styles.value}>{scoring_version}</td>
            </tr>
            <tr>
              <td>Adaptive scoring</td>
              <td style={styles.value}>
                {adaptive_scoring_enabled ? '✅ Enabled' : '❌ Disabled'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style={styles.footer}>
        <p>💡 Use this panel to monitor system health and LLM provider performance.</p>
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
  section: {
    marginBottom: '16px',
  },
  sectionTitle: {
    margin: '0 0 8px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#4b5563',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: '#ffffff',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  thead: {
    backgroundColor: '#f3f4f6',
  },
  th: {
    padding: '8px',
    textAlign: 'left',
    fontSize: '12px',
    fontWeight: '600',
    color: '#6b7280',
    borderBottom: '1px solid #e5e7eb',
  },
  td: {
    padding: '8px',
    fontSize: '13px',
    color: '#374151',
    borderBottom: '1px solid #e5e7eb',
  },
  value: {
    fontWeight: '600',
    color: '#1a1a1a',
  },
  providerName: {
    fontWeight: '600',
    color: '#1a1a1a',
  },
  emptyMessage: {
    padding: '12px',
    backgroundColor: '#ffffff',
    borderRadius: '4px',
    color: '#9ca3af',
    fontSize: '13px',
    margin: 0,
  },
  footer: {
    paddingTop: '12px',
    borderTop: '1px solid #e5e7eb',
    fontSize: '12px',
    color: '#9ca3af',
    margin: 0,
  },
}
