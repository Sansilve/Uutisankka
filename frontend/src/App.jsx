import { useEffect, useMemo, useState } from 'react'
import {
  fetchArticles,
  fetchBriefing,
  fetchHistory,
  fetchMetrics,
  fetchPreferences,
  fetchRandomBriefing,
  fetchReenrichStatus,
  sendFeedback,
  triggerIngest,
  triggerReenrich,
  updatePreferences,
} from './api'
import './App.css'

// ── Topic & source config (mirrored from mobile) ──────────────────────────────
const TOPIC_COLORS = {
  teknologia: '#1e3a8a', tiede: '#3b0764', politiikka: '#991b1b',
  talous: '#065f46', terveys: '#064e3b', kulttuuri: '#831843',
  urheilu: '#14532d', ympäristö: '#052e16', celebrity: '#581c87',
  sää: '#0c4a6e', rikokset: '#450a0a', koulutus: '#1e1b4b',
  turvallisuus: '#1c1917', kansainväliset: '#7c2d12', viihde: '#4a044e',
  onnettomuudet: '#7f1d1d',
}

const ALL_TOPICS = [
  { id: 'politiikka', label: 'Politiikka' },
  { id: 'talous', label: 'Talous' },
  { id: 'teknologia', label: 'Teknologia' },
  { id: 'urheilu', label: 'Urheilu' },
  { id: 'kulttuuri', label: 'Kulttuuri' },
  { id: 'terveys', label: 'Terveys' },
  { id: 'ympäristö', label: 'Ympäristö' },
  { id: 'tiede', label: 'Tiede' },
  { id: 'turvallisuus', label: 'Turvallisuus' },
  { id: 'koulutus', label: 'Koulutus' },
  { id: 'kansainväliset', label: 'Kansainväliset' },
  { id: 'viihde', label: 'Viihde' },
  { id: 'celebrity', label: 'Julkkikset' },
  { id: 'rikokset', label: 'Rikokset' },
  { id: 'onnettomuudet', label: 'Onnettomuudet' },
  { id: 'sää', label: 'Sää' },
]

const NEWS_SCOPES = [
  { id: 'suomi', label: '🇫🇮 Suomi' },
  { id: 'maailma', label: '🌍 Maailma' },
  { id: 'paikalliset', label: '📍 Paikalliset' },
]

const LOCAL_CITIES = {
  helsinki: 'Helsinki', tampere: 'Tampere', oulu: 'Oulu',
  turku: 'Turku', jyvaskyla: 'Jyväskylä', kuopio: 'Kuopio',
  hameenlinna: 'Hämeenlinna', lappeenranta: 'Lappeenranta',
}

const ALL_SOURCES = [
  'yle.fi', 'hs.fi', 'iltalehti.fi', 'is.fi', 'verkkouutiset.fi',
  'uusisuomi.fi', 'maaseuduntulevaisuus.fi', 'kauppalehti.fi',
  'talouselama.fi', 'arvopaperi.fi', 'mikrobitti.fi', 'tekniikkatalous.fi',
  'aamulehti.fi', 'kaleva.fi', 'satakunnankansa.fi',
  'bbc.co.uk', 'nytimes.com', 'theguardian.com', 'washingtonpost.com',
  'aljazeera.com', 'reutersagency.com',
]

function topicColor(t) { return TOPIC_COLORS[t] || '#374151' }
function topicLabel(t) {
  const found = ALL_TOPICS.find(x => x.id === t)
  return found ? found.label : (t.charAt(0).toUpperCase() + t.slice(1))
}

function groupByDate(items) {
  const groups = {}
  for (const item of items) {
    const date = (item.swiped_at || '').slice(0, 10)
    if (!groups[date]) groups[date] = []
    groups[date].push(item)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

function formatDateFi(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('fi-FI', { weekday: 'long', day: 'numeric', month: 'long' })
}

// ── Sub-components ────────────────────────────────────────────────────────────
function TopicBadge({ topic }) {
  return (
    <span className="topic-badge" style={{ background: topicColor(topic) }}>
      {topicLabel(topic)}
    </span>
  )
}

function StoryCard({ story, onRate, busy }) {
  const [expanded, setExpanded] = useState(false)
  const [voted, setVoted] = useState(null)

  async function handleRate(isRelevant) {
    if (voted !== null || busy) return
    setVoted(isRelevant ? 'yes' : 'no')
    await onRate(story.id, isRelevant)
  }

  return (
    <article className={`card${voted ? ' card--voted' : ''}`}>
      <div className="card-meta">
        <span className="card-source">{story.source}</span>
        {story.score != null && <span className="card-score">{story.score.toFixed(1)} pts</span>}
        {story.is_paywall && <span className="paywall-badge">🔒 Maksumuuri</span>}
      </div>
      <h2 className="card-title">
        <a href={story.url} target="_blank" rel="noreferrer">{story.title}</a>
      </h2>
      <ul className="card-bullets">
        {(story.summary?.bullets || []).slice(0, 4).map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>
      {story.topics?.length > 0 && (
        <div className="card-topics">
          {story.topics.map(t => <TopicBadge key={t} topic={t} />)}
        </div>
      )}
      {story.score_breakdown && (
        <>
          <button className="why-toggle" onClick={() => setExpanded(e => !e)}>
            {expanded ? '▲ Piilota pisteet' : '▼ Miksi nämä pisteet?'}
          </button>
          {expanded && (
            <ul className="breakdown-list">
              {(story.score_breakdown?.items || []).map((item, i) => (
                <li key={i} className={item.points >= 0 ? 'pos' : 'neg'}>
                  <span>{item.reason}</span>
                  <span>{item.points > 0 ? '+' : ''}{item.points.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {onRate && (
        <div className="card-actions">
          <button
            className={`btn-ohita${voted === 'no' ? ' btn--active' : ''}`}
            onClick={() => handleRate(false)}
            disabled={voted !== null || busy}
          >
            👎 Ohita
          </button>
          <div className="feedback-count">
            <span className="count-pos">+{story.feedback_positive ?? 0}</span>
            {' / '}
            <span className="count-neg">−{story.feedback_negative ?? 0}</span>
          </div>
          <button
            className={`btn-kiinnostaa${voted === 'yes' ? ' btn--active' : ''}`}
            onClick={() => handleRate(true)}
            disabled={voted !== null || busy}
          >
            Kiinnostaa 👍
          </button>
        </div>
      )}
    </article>
  )
}

function HistoryView() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchHistory(200)
      .then(data => { setGroups(groupByDate(data.items || [])); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = filter === 'all'
    ? groups
    : groups
        .map(([date, items]) => [date, items.filter(i => filter === 'relevant' ? i.is_relevant : !i.is_relevant)])
        .filter(([, items]) => items.length > 0)

  if (loading) return <p className="empty">Ladataan historiaa...</p>

  return (
    <div className="history-view">
      <div className="history-filter">
        {[
          { key: 'all', label: 'Kaikki' },
          { key: 'relevant', label: '👍 Kiinnostaa' },
          { key: 'dismissed', label: '👎 Ohitettu' },
        ].map(({ key, label }) => (
          <button
            key={key}
            className={`chip${filter === key ? ' chip--on' : ''}`}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {filtered.length === 0 && <p className="empty">Ei swaipattuja uutisia.</p>}
      {filtered.map(([date, items]) => (
        <div key={date} className="history-group">
          <h3 className="history-date">{formatDateFi(date)}</h3>
          {items.map(item => (
            <a
              key={item.swipe_id}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="history-item"
            >
              <span className={`history-badge${item.is_relevant ? ' history-badge--yes' : ' history-badge--no'}`}>
                {item.is_relevant ? 'KIINNOSTAA' : 'OHITETTU'}
              </span>
              <span className="history-source">{item.source}</span>
              <span className="history-title">{item.title}</span>
              {item.summary?.bullets?.[0] && (
                <span className="history-lead">{item.summary.bullets[0]}</span>
              )}
            </a>
          ))}
        </div>
      ))}
    </div>
  )
}

function AllArticlesView() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [topicFilter, setTopicFilter] = useState('all')
  const [regionFilter, setRegionFilter] = useState('all')

  useEffect(() => {
    fetchArticles(100, true)
      .then(data => { setArticles(data.items || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = articles
    .filter(a => topicFilter === 'all' || (a.topics || []).includes(topicFilter))
    .filter(a => regionFilter === 'all' || a.region === regionFilter)

  // Stats
  const topicCounts = {}
  for (const a of articles) {
    for (const t of (a.topics || [])) {
      topicCounts[t] = (topicCounts[t] || 0) + 1
    }
  }
  const topTopics = Object.entries(topicCounts).sort((a, b) => b[1] - a[1]).slice(0, 8)
  const paywallCount = articles.filter(a => a.is_paywall).length
  const regions = { suomi: 0, maailma: 0 }
  for (const a of articles) { if (regions[a.region] !== undefined) regions[a.region]++ }

  if (loading) return <p className="empty">Ladataan artikkeleita...</p>

  return (
    <div>
      <div className="data-stats">
        <div className="stat-card">
          <div className="stat-num">{articles.length}</div>
          <div className="stat-label">Artikkelia</div>
        </div>
        <div className="stat-card">
          <div className="stat-num">{regions.suomi}</div>
          <div className="stat-label">🇫🇮 Suomi</div>
        </div>
        <div className="stat-card">
          <div className="stat-num">{regions.maailma}</div>
          <div className="stat-label">🌍 Maailma</div>
        </div>
        <div className="stat-card">
          <div className="stat-num">{paywallCount}</div>
          <div className="stat-label">🔒 Maksumuuri</div>
        </div>
      </div>

      <div className="topic-bar">
        {topTopics.map(([t, n]) => (
          <button
            key={t}
            className={`chip${topicFilter === t ? ' chip--on' : ''}`}
            style={topicFilter === t ? { background: topicColor(t), borderColor: topicColor(t) } : {}}
            onClick={() => setTopicFilter(topicFilter === t ? 'all' : t)}
          >
            {topicLabel(t)} <span className="chip-count">{n}</span>
          </button>
        ))}
        {topicFilter !== 'all' && (
          <button className="chip btn-ghost" onClick={() => setTopicFilter('all')}>× Kaikki</button>
        )}
      </div>

      <div className="region-tabs">
        {[['all', 'Kaikki'], ['suomi', '🇫🇮 Suomi'], ['maailma', '🌍 Maailma']].map(([k, l]) => (
          <button
            key={k}
            className={`chip${regionFilter === k ? ' chip--on' : ''}`}
            onClick={() => setRegionFilter(k)}
          >{l}</button>
        ))}
      </div>

      <div className="stories">
        {filtered.length === 0 && <p className="empty">Ei artikkeleita valituilla suodattimilla.</p>}
        {filtered.map(a => (
          <StoryCard key={a.id} story={a} onRate={null} busy={false} />
        ))}
      </div>
    </div>
  )
}

function PrefsPanel({ prefs, onSaved, setStatusGlobal }) {
  const [interests, setInterests] = useState(new Set(prefs.interests || []))
  const [dislikes, setDislikes] = useState(new Set(prefs.disliked_topics || []))
  const [scope, setScope] = useState(new Set(prefs.news_scope || ['suomi', 'maailma']))
  const [city, setCity] = useState(prefs.local_city || '')
  const [hidePaywall, setHidePaywall] = useState(prefs.hide_paywall !== false)
  const [excludedSources, setExcludedSources] = useState(new Set(prefs.excluded_sources || []))
  const [unsaved, setUnsaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')

  function mark(fn) { return (...a) => { fn(...a); setUnsaved(true) } }

  function toggleInterest(id) {
    const next = new Set(interests)
    if (next.has(id)) { next.delete(id) } else { next.add(id); const d = new Set(dislikes); d.delete(id); setDislikes(d) }
    setInterests(next); setUnsaved(true)
  }
  function toggleDislike(id) {
    const next = new Set(dislikes)
    if (next.has(id)) { next.delete(id) } else { next.add(id); const s = new Set(interests); s.delete(id); setInterests(s) }
    setDislikes(next); setUnsaved(true)
  }
  function toggleScope(id) {
    const next = new Set(scope)
    if (next.has(id)) { if (next.size > 1) { next.delete(id); if (id === 'paikalliset') setCity('') } }
    else { next.add(id) }
    setScope(next); setUnsaved(true)
  }
  function toggleSource(id) {
    const next = new Set(excludedSources)
    next.has(id) ? next.delete(id) : next.add(id)
    setExcludedSources(next); setUnsaved(true)
  }

  async function pollReenrich() {
    const start = Date.now()
    while (Date.now() - start < 60_000) {
      await new Promise(r => setTimeout(r, 500))
      try {
        const s = await fetchReenrichStatus()
        if (s.state === 'done') {
          setStatus(`Valmis – ${s.enriched} artikkelia pisteytetty`)
          setBusy(false); onSaved?.(); return
        }
        setStatus(`Pisteytetään... (${s.enriched ?? 0})`)
      } catch (_) {}
    }
    setStatus('Pisteytys kesti liian kauan'); setBusy(false)
  }

  async function save() {
    setBusy(true); setStatus('Tallennetaan...')
    try {
      await updatePreferences({
        interests: [...interests],
        disliked_topics: [...dislikes],
        news_scope: [...scope],
        local_city: city,
        hide_paywall: hidePaywall,
        excluded_sources: [...excludedSources],
      })
      setUnsaved(false); setStatus('Tallennettu – pisteytetään...'); pollReenrich()
    } catch (e) { setStatus(`Virhe: ${e.message}`); setBusy(false) }
  }

  return (
    <section className="panel prefs">
      {unsaved && (
        <div className="unsaved-banner">
          Tallentamattomat muutokset – tallenna niin briefing päivittyy.
        </div>
      )}

      <div className="pref-section">
        <p className="pref-label">🗺️ Uutisalue</p>
        <p className="pref-hint">Valitse mitkä alueet näkyvät briefingissä</p>
        <div className="cat-chips">
          {NEWS_SCOPES.map(s => (
            <button
              key={s.id}
              className={`chip chip--scope${scope.has(s.id) ? ' chip--on' : ''}`}
              onClick={() => toggleScope(s.id)}
            >{s.label}</button>
          ))}
        </div>
        {scope.has('paikalliset') && (
          <div className="cat-chips" style={{ marginTop: '0.4rem' }}>
            {Object.entries(LOCAL_CITIES).map(([id, label]) => (
              <button
                key={id}
                className={`chip${city === id ? ' chip--on' : ''}`}
                onClick={() => { setCity(id); setUnsaved(true) }}
              >{label}</button>
            ))}
          </div>
        )}
      </div>

      <div className="pref-section">
        <p className="pref-label">👍 Kiinnostaa</p>
        <p className="pref-hint">Valitseminen poistaa aiheen automaattisesti ei-kiinnosta-listalta</p>
        <div className="cat-chips">
          {ALL_TOPICS.map(({ id }) => {
            const active = interests.has(id)
            const blocked = dislikes.has(id)
            return (
              <button
                key={id}
                className={`chip${active ? ' chip--on' : ''}${blocked ? ' chip--blocked' : ''}`}
                onClick={() => !blocked && toggleInterest(id)}
                disabled={blocked}
              >{topicLabel(id)}</button>
            )
          })}
        </div>
      </div>

      <div className="pref-section">
        <p className="pref-label">👎 Ei kiinnosta</p>
        <p className="pref-hint">Valitseminen poistaa aiheen automaattisesti kiinnostaa-listalta</p>
        <div className="cat-chips">
          {ALL_TOPICS.map(({ id }) => {
            const active = dislikes.has(id)
            const blocked = interests.has(id)
            return (
              <button
                key={id}
                className={`chip chip--dislike${active ? ' chip--on' : ''}${blocked ? ' chip--blocked' : ''}`}
                onClick={() => !blocked && toggleDislike(id)}
                disabled={blocked}
              >{topicLabel(id)}</button>
            )
          })}
        </div>
      </div>

      <div className="pref-section">
        <p className="pref-label">⚙️ Muut asetukset</p>
        <label className="toggle-row" onClick={() => { setHidePaywall(v => !v); setUnsaved(true) }}>
          <div className="toggle-info">
            <span className="toggle-label">Piilota maksumuuriartikkelit</span>
            <span className="toggle-desc">Artikkelit joita ei voi lukea ilmaiseksi piilotetaan</span>
          </div>
          <div className={`toggle-switch${hidePaywall ? ' toggle-switch--on' : ''}`}>
            <div className={`toggle-thumb${hidePaywall ? ' toggle-thumb--on' : ''}`} />
          </div>
        </label>
      </div>

      <div className="pref-section">
        <p className="pref-label">📰 Uutislähteet</p>
        <p className="pref-hint">Valitut lähteet suljetaan pois briefingistä</p>
        <div className="cat-chips">
          {ALL_SOURCES.map(src => (
            <button
              key={src}
              className={`chip chip--source${excludedSources.has(src) ? ' chip--excluded' : ''}`}
              onClick={() => toggleSource(src)}
            >
              {excludedSources.has(src) ? '✕ ' : ''}{src}
            </button>
          ))}
        </div>
      </div>

      <div className="prefs-actions">
        <button
          className={unsaved ? 'btn-primary' : ''}
          onClick={save}
          disabled={busy || !unsaved}
        >
          {busy ? 'Tallennetaan...' : 'Tallenna asetukset'}
        </button>
        {status && <span className="status-text">{status}</span>}
      </div>
    </section>
  )
}

// ── Onboarding ────────────────────────────────────────────────────────────────
const OB_STEPS = [
  { kicker: 'TERVETULOA', title: '🦆 UutisAnkka', body: 'Älykäs uutisbriefing – vain se, mikä sinua oikeasti kiinnostaa. Merkitse kiinnostavat, niin se oppii.' },
  { kicker: 'VAIHE 1 / 3', title: 'Valitse aiheet', body: 'Valitse mitkä aiheet kiinnostavat sinua eniten.' },
  { kicker: 'VAIHE 2 / 3', title: 'Suodata pois', body: 'Merkitse aiheet joita et halua nähdä.' },
  { kicker: 'VALMIS', title: 'Aloita lukeminen', body: 'Klikkaa "Kiinnostaa" tai "Ohita" joka uutisessa – UutisAnkka oppii.' },
]

function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0)
  const [interests, setInterests] = useState(new Set(['politiikka', 'talous', 'teknologia']))
  const [dislikes, setDislikes] = useState(new Set(['viihde', 'celebrity']))

  function toggleI(id) {
    const n = new Set(interests)
    if (n.has(id)) { n.delete(id) } else { n.add(id); const d = new Set(dislikes); d.delete(id); setDislikes(d) }
    setInterests(n)
  }
  function toggleD(id) {
    const n = new Set(dislikes)
    if (n.has(id)) { n.delete(id) } else { n.add(id); const s = new Set(interests); s.delete(id); setInterests(s) }
    setDislikes(n)
  }

  async function finish() {
    await updatePreferences({ interests: [...interests], disliked_topics: [...dislikes] })
    onComplete()
  }

  const s = OB_STEPS[step]
  const isLast = step === OB_STEPS.length - 1

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <p className="onboarding-kicker">{s.kicker}</p>
        <h1 className="onboarding-title">{s.title}</h1>
        <p className="onboarding-body">{s.body}</p>
        {step === 1 && (
          <div className="cat-chips" style={{ justifyContent: 'center', margin: '1rem 0' }}>
            {ALL_TOPICS.map(({ id }) => (
              <button key={id} className={`chip${interests.has(id) ? ' chip--on' : ''}${dislikes.has(id) ? ' chip--blocked' : ''}`}
                onClick={() => !dislikes.has(id) && toggleI(id)} disabled={dislikes.has(id)}>
                {topicLabel(id)}
              </button>
            ))}
          </div>
        )}
        {step === 2 && (
          <div className="cat-chips" style={{ justifyContent: 'center', margin: '1rem 0' }}>
            {ALL_TOPICS.map(({ id }) => (
              <button key={id} className={`chip chip--dislike${dislikes.has(id) ? ' chip--on' : ''}${interests.has(id) ? ' chip--blocked' : ''}`}
                onClick={() => !interests.has(id) && toggleD(id)} disabled={interests.has(id)}>
                {topicLabel(id)}
              </button>
            ))}
          </div>
        )}
        <div className="onboarding-actions">
          {step > 0 && <button className="btn-ghost" onClick={() => setStep(s => s - 1)}>← Takaisin</button>}
          {isLast
            ? <button className="btn-primary" onClick={finish}>Aloita lukeminen →</button>
            : <button className="btn-primary" onClick={() => setStep(s => s + 1)}>
                {step === 0 ? 'Aloita →' : 'Seuraava →'}
              </button>
          }
        </div>
        <div className="onboarding-dots">
          {OB_STEPS.map((_, i) => <span key={i} className={`dot${i === step ? ' dot--active' : ''}`} />)}
        </div>
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [onboarded, setOnboarded] = useState(() => !!localStorage.getItem('ua_onboarded'))
  const [briefing, setBriefing] = useState({ stories: [], generated_at: null, total: 0 })
  const [prefs, setPrefs] = useState(null)
  const [activeTab, setActiveTab] = useState('briefing')
  const [briefingMode, setBriefingMode] = useState('top') // 'top' | 'random'
  const [status, setStatus] = useState('')
  const [unsaved, setUnsaved] = useState(false)
  const [metrics, setMetrics] = useState({ total_feedback_votes: 0, positive_feedback_ratio: null })
  const [busy, setBusy] = useState(false)
  const [briefingLimit] = useState(() => {
    const s = localStorage.getItem('ua_limit'); return s ? parseInt(s, 10) : 10
  })

  const updatedAt = useMemo(() => {
    if (!briefing.generated_at) return null
    return new Date(briefing.generated_at).toLocaleString('fi-FI')
  }, [briefing.generated_at])

  async function loadAll() {
    setBusy(true)
    try {
      const [bd, pd, md] = await Promise.all([
        briefingMode === 'random' ? fetchRandomBriefing(briefingLimit) : fetchBriefing(briefingLimit),
        fetchPreferences(),
        fetchMetrics(10),
      ])
      setBriefing(bd)
      setMetrics(md)
      setPrefs(pd)
      setStatus('')
    } catch (e) {
      setStatus(`Virhe: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { if (onboarded) loadAll() }, [onboarded, briefingMode])

  async function pollReenrich() {
    const start = Date.now()
    while (Date.now() - start < 60_000) {
      await new Promise(r => setTimeout(r, 400))
      try {
        const s = await fetchReenrichStatus()
        const done = s.state === 'done'
        setStatus(`Pisteytetty ${s.enriched ?? 0}${done ? ' – valmis!' : '...'}`)
        if (done) { await loadAll(); setBusy(false); return }
      } catch (_) {}
    }
    setStatus('Pisteytys kesti liian kauan.'); setBusy(false)
  }

  async function refreshIngest() {
    setBusy(true); setStatus('Haetaan uutisia...')
    try {
      const r = await triggerIngest()
      await loadAll()
      setStatus(`Haettu ${r.inserted} uutta, ${r.duplicates} duplikaattia`)
    } catch (e) { setStatus(`Virhe: ${e.message}`); setBusy(false) }
  }

  async function rateStory(articleId, isRelevant) {
    try {
      await sendFeedback({ article_id: articleId, is_relevant: isRelevant })
    } catch (e) { setStatus(`Virhe: ${e.message}`) }
  }

  if (!onboarded) {
    return <Onboarding onComplete={() => { localStorage.setItem('ua_onboarded', '1'); setOnboarded(true) }} />
  }

  const voteStr = metrics.positive_feedback_ratio === null
    ? 'Ei palautetta vielä'
    : `${Math.round(metrics.positive_feedback_ratio * 100)}% kiinnostavia (${metrics.total_feedback_votes} ääntä)`

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="kicker">🦆 UutisAnkka</span>
          <h1>Morning Briefing</h1>
          {updatedAt && <p className="meta">Päivitetty {updatedAt} · {voteStr}</p>}
        </div>
        <div className="topbar-actions">
          <button onClick={refreshIngest} disabled={busy}>↓ Päivitä</button>
          <button
            onClick={() => { setBusy(true); triggerReenrich().then(() => { setStatus('Pisteytetään...'); pollReenrich() }).catch(e => { setStatus(e.message); setBusy(false) }) }}
            disabled={busy}
          >↻ Pisteytä</button>
        </div>
      </header>

      {status && <div className="status-bar">{status}</div>}

      <nav className="tab-bar">
        {[
          { key: 'briefing', label: '📰 Briefing' },
          { key: 'all', label: '📋 Kaikki' },
          { key: 'history', label: '🕐 Historia' },
          { key: 'prefs', label: '⚙️ Asetukset' },
        ].map(({ key, label }) => (
          <button key={key} className={`tab${activeTab === key ? ' tab--active' : ''}`} onClick={() => setActiveTab(key)}>
            {label}
          </button>
        ))}
      </nav>

      {activeTab === 'briefing' && (
        <section className="stories">
          <div className="briefing-toolbar">
            <div className="mode-chips">
              <button
                className={`chip${briefingMode === 'top' ? ' chip--on' : ''}`}
                onClick={() => setBriefingMode('top')}
              >⭐ Top-uutiset</button>
              <button
                className={`chip${briefingMode === 'random' ? ' chip--on' : ''}`}
                onClick={() => setBriefingMode('random')}
              >🎲 Satunnainen</button>
            </div>
            {unsaved && (
              <span className="unsaved-inline">
                Tallentamattomia preferenssejä –{' '}
                <button className="link-btn" onClick={() => setActiveTab('prefs')}>Asetuksiin</button>
              </span>
            )}
          </div>
          {busy && briefing.stories.length === 0 && <p className="empty">Ladataan...</p>}
          {!busy && briefing.stories.length === 0 && <p className="empty">Ei uutisia – paina Päivitä.</p>}
          {briefing.stories.map(story => (
            <StoryCard key={story.id} story={story} onRate={rateStory} busy={false} />
          ))}
        </section>
      )}

      {activeTab === 'all' && <AllArticlesView />}
      {activeTab === 'history' && <HistoryView />}
      {activeTab === 'prefs' && prefs && (
        <PrefsPanel
          prefs={prefs}
          onSaved={() => loadAll()}
          setStatusGlobal={setStatus}
        />
      )}
      {activeTab === 'prefs' && !prefs && <p className="empty">Ladataan asetuksia...</p>}
    </div>
  )
}
