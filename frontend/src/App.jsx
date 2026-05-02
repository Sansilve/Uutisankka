import { useEffect, useMemo, useState } from 'react'
import {
  fetchBriefing,
  fetchHistory,
  fetchMetrics,
  fetchPreferences,
  fetchReenrichStatus,
  sendFeedback,
  triggerIngest,
  triggerReenrich,
  updatePreferences,
} from './api'
import './App.css'

// ── Topic config (mirrored from mobile) ──────────────────────────────────────
const TOPIC_COLORS = {
  teknologia: '#1e3a8a', tiede: '#3b0764', politiikka: '#991b1b',
  talous: '#065f46', terveys: '#064e3b', kulttuuri: '#831843',
  urheilu: '#14532d', ympäristö: '#052e16', celebrity: '#581c87',
  sää: '#0c4a6e', rikokset: '#450a0a', koulutus: '#1e1b4b',
  turvallisuus: '#1c1917', kansainväliset: '#7c2d12', viihde: '#4a044e',
}

const TOPIC_LABELS = {
  politiikka: 'Politiikka', talous: 'Talous', teknologia: 'Teknologia',
  tiede: 'Tiede', urheilu: 'Urheilu', terveys: 'Terveys',
  ympäristö: 'Ympäristö', kulttuuri: 'Kulttuuri', celebrity: 'Viihde/julkkis',
  sää: 'Sää', rikokset: 'Rikos', koulutus: 'Koulutus',
  turvallisuus: 'Turvallisuus', kansainväliset: 'Kansainväliset', viihde: 'Viihde',
}

const INTEREST_CATEGORIES = [
  'politiikka', 'talous', 'teknologia', 'urheilu', 'kulttuuri',
  'terveys', 'ympäristö', 'tiede', 'turvallisuus', 'koulutus', 'kansainväliset',
]

const DISLIKE_CATEGORIES = [
  'viihde', 'celebrity', 'urheilu', 'rikokset', 'onnettomuudet', 'sää',
]

function topicColor(t) { return TOPIC_COLORS[t] || '#374151' }
function topicLabel(t) { return TOPIC_LABELS[t] || (t.charAt(0).toUpperCase() + t.slice(1)) }

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
        <span className="card-score">{story.score.toFixed(1)} pts</span>
        {story.is_paywall && <span className="paywall-badge">🔒 Maksumuurin takana</span>}
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

      <button
        className="why-toggle"
        onClick={() => setExpanded(e => !e)}
      >
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

      <div className="card-actions">
        <button
          className={`btn-ohita${voted === 'no' ? ' btn--active' : ''}`}
          onClick={() => handleRate(false)}
          disabled={voted !== null || busy}
        >
          👎 Ohita
        </button>
        <div className="feedback-count">
          <span className="count-pos">+{story.feedback_positive}</span>
          {' / '}
          <span className="count-neg">−{story.feedback_negative}</span>
        </div>
        <button
          className={`btn-kiinnostaa${voted === 'yes' ? ' btn--active' : ''}`}
          onClick={() => handleRate(true)}
          disabled={voted !== null || busy}
        >
          Kiinnostaa 👍
        </button>
      </div>
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

function PrefsPanel({ selectedCategories, setSelectedCategories, dislikedCategories, setDislikedCategories, unsaved, busy, onSave, status }) {
  function toggleInterest(id) {
    const next = new Set(selectedCategories)
    if (next.has(id)) { next.delete(id) } else { next.add(id); const d = new Set(dislikedCategories); d.delete(id); setDislikedCategories(d) }
    setSelectedCategories(next)
  }
  function toggleDislike(id) {
    const next = new Set(dislikedCategories)
    if (next.has(id)) { next.delete(id) } else { next.add(id); const s = new Set(selectedCategories); s.delete(id); setSelectedCategories(s) }
    setDislikedCategories(next)
  }

  return (
    <section className="panel prefs">
      <h2>Omat kiinnostukset</h2>
      {unsaved && (
        <div className="unsaved-banner">
          Tallentamattomat muutokset – paina Tallenna niin briefing päivittyy.
        </div>
      )}
      <div className="pref-row">
        <p className="pref-label">👍 Kiinnostaa</p>
        <div className="cat-chips">
          {INTEREST_CATEGORIES.map(id => (
            <button key={id}
              className={`chip${selectedCategories.has(id) ? ' chip--on' : ''}`}
              onClick={toggleInterest.bind(null, id)}
            >{topicLabel(id)}</button>
          ))}
        </div>
      </div>
      <div className="pref-row">
        <p className="pref-label">👎 Ei kiinnosta</p>
        <div className="cat-chips">
          {DISLIKE_CATEGORIES.map(id => (
            <button key={id}
              className={`chip chip--dislike${dislikedCategories.has(id) ? ' chip--on' : ''}`}
              onClick={toggleDislike.bind(null, id)}
            >{topicLabel(id)}</button>
          ))}
        </div>
      </div>
      <div className="prefs-actions">
        <button
          className={unsaved ? 'btn-primary' : ''}
          onClick={onSave}
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
  { kicker: 'VAIHE 1', title: 'Valitse aiheet', body: 'Valitse mitkä aiheet kiinnostavat sinua eniten.' },
  { kicker: 'VAIHE 2', title: 'Suodata pois', body: 'Merkitse aiheet joita et halua nähdä.' },
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
            {INTEREST_CATEGORIES.map(id => (
              <button key={id} className={`chip${interests.has(id) ? ' chip--on' : ''}`} onClick={() => toggleI(id)}>
                {topicLabel(id)}
              </button>
            ))}
          </div>
        )}
        {step === 2 && (
          <div className="cat-chips" style={{ justifyContent: 'center', margin: '1rem 0' }}>
            {DISLIKE_CATEGORIES.map(id => (
              <button key={id} className={`chip chip--dislike${dislikes.has(id) ? ' chip--on' : ''}`} onClick={() => toggleD(id)}>
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
  const [selectedCategories, setSelectedCategories] = useState(new Set())
  const [dislikedCategories, setDislikedCategories] = useState(new Set())
  const [activeTab, setActiveTab] = useState('briefing')
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
        fetchBriefing(briefingLimit),
        fetchPreferences(),
        fetchMetrics(briefingLimit),
      ])
      setBriefing(bd)
      setMetrics(md)
      setSelectedCategories(new Set(pd.interests))
      setDislikedCategories(new Set(pd.disliked_topics))
      setStatus('')
    } catch (e) {
      setStatus(`Virhe: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { if (onboarded) loadAll() }, [onboarded])

  async function pollReenrich() {
    const MAX_WAIT = 60_000; const start = Date.now()
    while (Date.now() - start < MAX_WAIT) {
      await new Promise(r => setTimeout(r, 300))
      try {
        const s = await fetchReenrichStatus()
        const done = s.state === 'done'
        setStatus(`Pisteytetty ${s.enriched ?? 0}${done ? ' – valmis!' : '...'}`)
        if (done) { await loadAll(); setBusy(false); return }
      } catch (_) { /* ignore */ }
    }
    setStatus('Pisteytys kesti liian kauan.'); setBusy(false)
  }

  async function savePreferences() {
    setBusy(true); setStatus('Tallennetaan...')
    try {
      await updatePreferences({ interests: [...selectedCategories], disliked_topics: [...dislikedCategories] })
      setUnsaved(false); setStatus('Tallennettu – pisteytetään...')
      pollReenrich()
    } catch (e) { setStatus(`Virhe: ${e.message}`); setBusy(false) }
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

  function markUnsaved(setter) {
    return (...args) => { setter(...args); setUnsaved(true) }
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
          <button onClick={() => { setBusy(true); triggerReenrich().then(() => { setStatus('Pisteytetään...'); pollReenrich() }).catch(e => { setStatus(e.message); setBusy(false) }) }} disabled={busy}>↻ Pisteytä</button>
        </div>
      </header>

      {status && <div className="status-bar">{status}</div>}

      <nav className="tab-bar">
        {[
          { key: 'briefing', label: '📰 Briefing' },
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
          {unsaved && (
            <div className="unsaved-banner">
              Preferensseissä tallentamattomia muutoksia – mene <button className="link-btn" onClick={() => setActiveTab('prefs')}>Asetuksiin</button> tallentamaan.
            </div>
          )}
          {busy && briefing.stories.length === 0 && <p className="empty">Ladataan...</p>}
          {!busy && briefing.stories.length === 0 && <p className="empty">Ei uutisia – paina Päivitä.</p>}
          {briefing.stories.map(story => (
            <StoryCard key={story.id} story={story} onRate={rateStory} busy={false} />
          ))}
        </section>
      )}

      {activeTab === 'history' && <HistoryView />}

      {activeTab === 'prefs' && (
        <PrefsPanel
          selectedCategories={selectedCategories}
          setSelectedCategories={markUnsaved(setSelectedCategories)}
          dislikedCategories={dislikedCategories}
          setDislikedCategories={markUnsaved(setDislikedCategories)}
          unsaved={unsaved}
          busy={busy}
          onSave={savePreferences}
          status={status}
        />
      )}
    </div>
  )
}
