const RATING_ORDER = ['VERY HIGH', 'HIGH', 'MOSTLY FACTUAL', 'MIXED', 'LOW', 'VERY LOW', 'FAKE NEWS']
const RATING_COLOR = {
  'VERY HIGH':     '#15803d',
  'HIGH':          '#16a34a',
  'MOSTLY FACTUAL':'#ca8a04',
  'MIXED':         '#d97706',
  'LOW':           '#dc2626',
  'VERY LOW':      '#b91c1c',
  'FAKE NEWS':     '#7f1d1d',
}
const RATING_FI = {
  'VERY HIGH':     'Erittäin korkea',
  'HIGH':          'Korkea',
  'MOSTLY FACTUAL':'Pääosin asiapitoinen',
  'MIXED':         'Vaihteleva',
  'LOW':           'Heikko',
  'VERY LOW':      'Erittäin heikko',
  'FAKE NEWS':     'Fake news',
}

const BIAS_LABELS = {
  '-3': 'Ääriv. vasen',
  '-2': 'Vasen',
  '-1': 'Vasen-keskusta',
   '0': 'Keskusta',
   '1': 'Oikea-keskusta',
   '2': 'Oikea',
   '3': 'Ääriv. oikea',
}
const BIAS_COLOR = {
  '-3': '#7c3aed',
  '-2': '#2563eb',
  '-1': '#0ea5e9',
   '0': '#16a34a',
   '1': '#f59e0b',
   '2': '#ea580c',
   '3': '#dc2626',
}

export default function TrustBiasDashboard({ metrics = {} }) {
  const trustStats      = metrics.trust_stats || {}
  const biasDistrib     = metrics.bias_distribution || []

  // Total articles with trust data
  const trustTotal = Object.values(trustStats).reduce((s, v) => s + (v.count || 0), 0)
  const biasTotal  = biasDistrib.reduce((s, v) => s + (v.count || 0), 0)

  // Group into high/ok/low for summary
  const highTrust = (trustStats['VERY HIGH']?.count || 0) + (trustStats['HIGH']?.count || 0)
  const lowTrust  = (trustStats['LOW']?.count || 0) + (trustStats['VERY LOW']?.count || 0) + (trustStats['FAKE NEWS']?.count || 0)

  return (
    <div style={s.container}>
      <h3 style={s.title}>🛡️ Lähdetiedot — luotettavuus &amp; poliittinen suuntaus</h3>

      {/* Summary row */}
      <div style={s.summaryRow}>
        <div style={{ ...s.summaryCard, borderColor: '#16a34a' }}>
          <span style={{ ...s.summaryNum, color: '#16a34a' }}>{trustTotal > 0 ? Math.round((highTrust / trustTotal) * 100) : 0}%</span>
          <span style={s.summaryLabel}>Luotettavia lähteitä</span>
        </div>
        <div style={{ ...s.summaryCard, borderColor: '#6b7280' }}>
          <span style={{ ...s.summaryNum, color: '#111' }}>{trustTotal}</span>
          <span style={s.summaryLabel}>Artikkelia yhteensä</span>
        </div>
        <div style={{ ...s.summaryCard, borderColor: '#dc2626' }}>
          <span style={{ ...s.summaryNum, color: '#dc2626' }}>{trustTotal > 0 ? Math.round((lowTrust / trustTotal) * 100) : 0}%</span>
          <span style={s.summaryLabel}>Heikot lähteet</span>
        </div>
      </div>

      {/* Factual rating bars */}
      <h4 style={s.sectionTitle}>Faktuaalisuusjakauma</h4>
      <div style={s.barChart}>
        {RATING_ORDER.map((rating) => {
          const data = trustStats[rating]
          if (!data) return null
          const pct = trustTotal > 0 ? (data.count / trustTotal) * 100 : 0
          return (
            <div key={rating} style={s.barRow}>
              <div style={s.barLabel}>{RATING_FI[rating]}</div>
              <div style={s.barTrack}>
                <div
                  style={{
                    ...s.barFill,
                    width: `${pct}%`,
                    backgroundColor: RATING_COLOR[rating],
                  }}
                />
              </div>
              <div style={s.barCount}>{data.count} ({pct.toFixed(1)}%)</div>
            </div>
          )
        })}
      </div>

      {/* Bias distribution */}
      <h4 style={s.sectionTitle}>Poliittinen suuntaus (bias-jakauma)</h4>
      <div style={s.biasChart}>
        {biasDistrib.map(({ bias_score, count }) => {
          const key = String(bias_score)
          const pct = biasTotal > 0 ? (count / biasTotal) * 100 : 0
          return (
            <div key={key} style={s.biasCol}>
              <div style={s.biasBarWrap}>
                <div
                  style={{
                    ...s.biasBar,
                    height: `${Math.max(pct * 2, 4)}px`,
                    backgroundColor: BIAS_COLOR[key] || '#9ca3af',
                  }}
                />
              </div>
              <div style={s.biasScore}>{bias_score > 0 ? `+${bias_score}` : bias_score}</div>
              <div style={s.biasLabelSmall}>{BIAS_LABELS[key] || key}</div>
              <div style={s.biasCount}>{count}</div>
            </div>
          )
        })}
      </div>
      <div style={s.biasAxis}>
        <span>← Vasen</span>
        <span>Oikea →</span>
      </div>

      <p style={s.credit}>Lähdeluokitukset perustuvat MediaBiasFactCheck.com-yhteisödataan.</p>
    </div>
  )
}

// ── Styles (inline, no deps) ────────────────────────────────────────────────
const s = {
  container: {
    fontFamily: 'system-ui, sans-serif',
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 12,
    padding: 24,
    marginBottom: 24,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
    margin: '0 0 16px',
    color: '#111',
  },
  summaryRow: {
    display: 'flex',
    gap: 12,
    marginBottom: 24,
  },
  summaryCard: {
    flex: 1,
    border: '2px solid',
    borderRadius: 10,
    padding: '12px 16px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
  },
  summaryNum: {
    fontSize: 28,
    fontWeight: 800,
    lineHeight: 1,
  },
  summaryLabel: {
    fontSize: 11,
    color: '#6b7280',
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#374151',
    margin: '0 0 10px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  barChart: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    marginBottom: 24,
  },
  barRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  barLabel: {
    width: 160,
    fontSize: 12,
    color: '#374151',
    textAlign: 'right',
    flexShrink: 0,
  },
  barTrack: {
    flex: 1,
    height: 18,
    background: '#f3f4f6',
    borderRadius: 4,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    minWidth: 2,
    transition: 'width 0.4s ease',
  },
  barCount: {
    width: 100,
    fontSize: 11,
    color: '#6b7280',
    flexShrink: 0,
  },
  biasChart: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 6,
    marginBottom: 4,
    minHeight: 120,
  },
  biasCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
  },
  biasBarWrap: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'flex-end',
    height: 100,
  },
  biasBar: {
    width: '80%',
    margin: '0 auto',
    borderRadius: '3px 3px 0 0',
    minHeight: 4,
  },
  biasScore: {
    fontSize: 12,
    fontWeight: 700,
    color: '#374151',
  },
  biasLabelSmall: {
    fontSize: 9,
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 1.2,
  },
  biasCount: {
    fontSize: 10,
    color: '#6b7280',
  },
  biasAxis: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 11,
    color: '#9ca3af',
    marginBottom: 16,
    marginTop: 4,
  },
  credit: {
    fontSize: 11,
    color: '#9ca3af',
    margin: 0,
  },
}
