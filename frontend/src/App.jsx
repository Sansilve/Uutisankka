import { useEffect, useMemo, useState } from 'react'
import {
  fetchBriefing,
  fetchMetrics,
  fetchPreferences,
  fetchRandomBriefing,
  sendFeedback,
  triggerIngest,
  updatePreferences,
} from './api'
import './App.css'

const CATEGORIES = [
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
]

const DISLIKED_CATEGORIES = [
  { id: 'viihde', label: 'Viihde' },
  { id: 'celebrity', label: 'Julkkikset' },
  { id: 'urheilu', label: 'Urheilu' },
  { id: 'rikokset', label: 'Rikokset' },
  { id: 'onnettomuudet', label: 'Onnettomuudet' },
  { id: 'sää', label: 'Sää' },
]

const LIMIT_OPTIONS = [5, 10, 15, 20, 25]

function App() {
  const [briefing, setBriefing] = useState({ stories: [], generated_at: null })
  const [randomBriefing, setRandomBriefing] = useState({ stories: [], generated_at: null })
  const [preferences, setPreferences] = useState({
    interests: ['politiikka', 'talous', 'teknologia'],
    disliked_topics: ['viihde', 'celebrity'],
  })
  const [selectedCategories, setSelectedCategories] = useState(new Set(['politiikka', 'talous', 'teknologia']))
  const [dislikedCategories, setDislikedCategories] = useState(new Set(['viihde', 'celebrity']))
  const [briefingLimit, setBriefingLimit] = useState(() => {
    const saved = localStorage.getItem('uutisankka_limit')
    return saved ? parseInt(saved, 10) : 10
  })
  const [activeTab, setActiveTab] = useState('top')
  const [status, setStatus] = useState('Ladataan...')
  const [metrics, setMetrics] = useState({
    top_limit: 10,
    total_feedback_votes: 0,
    positive_feedback_ratio: null,
  })
  const [busy, setBusy] = useState(false)

  const updatedAt = useMemo(() => {
    if (!briefing.generated_at) {
      return 'Not generated yet'
    }
    return new Date(briefing.generated_at).toLocaleString()
  }, [briefing.generated_at])

  async function loadAll() {
    setBusy(true)
    try {
      const [briefingData, prefData, metricsData] = await Promise.all([
        fetchBriefing(briefingLimit),
        fetchPreferences(),
        fetchMetrics(briefingLimit),
      ])
      setBriefing(briefingData)
      setPreferences(prefData)
      setMetrics(metricsData)
      setSelectedCategories(new Set(prefData.interests))
      setDislikedCategories(new Set(prefData.disliked_topics))
      setStatus(`Ladattu ${briefingData.total} uutista`)
    } catch (error) {
      setStatus(`Virhe: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  async function refreshIngest() {
    setBusy(true)
    setStatus('Päivitetään syötteitä...')
    try {
      const result = await triggerIngest()
      await loadAll()
      setStatus(`Haettu ${result.inserted} uutta uutista, ohitettu ${result.duplicates} duplikaattia`)
    } catch (error) {
      setStatus(`Virhe: ${error.message}`)
      setBusy(false)
    }
  }

  function toggleCategory(id, set, setFn) {
    const next = new Set(set)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setFn(next)
  }

  async function savePreferences() {
    setBusy(true)
    try {
      const payload = {
        interests: [...selectedCategories],
        disliked_topics: [...dislikedCategories],
      }
      const updated = await updatePreferences(payload)
      setPreferences(updated)
      await loadAll()
      setStatus('Asetukset tallennettu ja uutiset järjestetty uudelleen')
    } catch (error) {
      setStatus(`Virhe: ${error.message}`)
      setBusy(false)
    }
  }

  function changeLimit(limit) {
    setBriefingLimit(limit)
    localStorage.setItem('uutisankka_limit', String(limit))
  }

  async function switchToRandom() {
    setActiveTab('random')
    if (randomBriefing.stories.length === 0) {
      setBusy(true)
      try {
        const data = await fetchRandomBriefing(briefingLimit)
        setRandomBriefing(data)
      } catch (error) {
        setStatus(`Virhe: ${error.message}`)
      } finally {
        setBusy(false)
      }
    }
  }

  async function refreshRandom() {
    setBusy(true)
    try {
      const data = await fetchRandomBriefing(briefingLimit)
      setRandomBriefing(data)
      setStatus(`${data.total} satunnaista uutista poimittu`)
    } catch (error) {
      setStatus(`Virhe: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function rateStory(articleId, isRelevant) {
    setBusy(true)
    try {
      const result = await sendFeedback({
        article_id: articleId,
        is_relevant: isRelevant,
      })
      await loadAll()
      setStatus(
        `Palaute tallennettu: ${result.feedback_positive} relevanttia, ${result.feedback_negative} ei relevanttia`
      )
    } catch (error) {
      setStatus(`Virhe: ${error.message}`)
      setBusy(false)
    }
  }

  function speak(text) {
    const synth = window.speechSynthesis
    if (!synth) {
      setStatus('Speech synthesis is not supported in this browser')
      return
    }
    synth.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.02
    utterance.pitch = 1
    synth.speak(utterance)
  }

  function speakStory(story) {
    const body = [story.title, ...story.summary.bullets].join('. ')
    speak(body)
  }

  function speakTopStories() {
    const source = activeTab === 'random' ? randomBriefing : briefing
    if (!source.stories.length) return
    const payload = source.stories
      .slice(0, 5)
      .map((story, index) => `Uutinen ${index + 1}. ${story.title}. ${story.summary.bullets[0] ?? ''}`)
      .join('. ')
    speak(payload)
  }

  const activeStories = activeTab === 'top' ? briefing.stories : randomBriefing.stories

  return (
    <main className="page">
      <header className="topbar">
        <div>
          <p className="kicker">UutisAnkka</p>
          <h1>No-BS Morning Briefing</h1>
          <p className="meta">Päivitetty: {updatedAt}</p>
          <p className="meta">
            Top {metrics.top_limit} hyväksymisaste:{' '}
            {metrics.positive_feedback_ratio === null
              ? 'Ei palautetta vielä'
              : `${Math.round(metrics.positive_feedback_ratio * 100)}%`} ({metrics.total_feedback_votes} ääntä)
          </p>
        </div>
        <div className="actions">
          <button onClick={refreshIngest} disabled={busy}>Päivitä syötteet</button>
          <button onClick={speakTopStories} disabled={!activeStories.length}>Kuuntele top 5</button>
        </div>
      </header>

      <section className="panel prefs">
        <h2>Mukauta</h2>

        <div className="pref-row">
          <p className="pref-label">Kiinnostaa</p>
          <div className="cat-chips">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                className={`chip${selectedCategories.has(cat.id) ? ' chip--on' : ''}`}
                onClick={() => toggleCategory(cat.id, selectedCategories, setSelectedCategories)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        <div className="pref-row">
          <p className="pref-label">Ei kiinnosta</p>
          <div className="cat-chips">
            {DISLIKED_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                className={`chip chip--dislike${dislikedCategories.has(cat.id) ? ' chip--on' : ''}`}
                onClick={() => toggleCategory(cat.id, dislikedCategories, setDislikedCategories)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        <div className="pref-row">
          <p className="pref-label">Uutisia etusivulle</p>
          <div className="limit-picker">
            {LIMIT_OPTIONS.map((n) => (
              <button
                key={n}
                className={`chip${briefingLimit === n ? ' chip--on' : ''}`}
                onClick={() => changeLimit(n)}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <div className="prefs-actions">
          <button onClick={savePreferences} disabled={busy}>Tallenna asetukset</button>
          <span>{status}</span>
        </div>
      </section>

      <div className="tab-bar">
        <button
          className={`tab${activeTab === 'top' ? ' tab--active' : ''}`}
          onClick={() => setActiveTab('top')}
        >
          Top-uutiset
        </button>
        <button
          className={`tab${activeTab === 'random' ? ' tab--active' : ''}`}
          onClick={switchToRandom}
        >
          Satunnaiset poiminnat
        </button>
        {activeTab === 'random' && (
          <button className="tab-refresh" onClick={refreshRandom} disabled={busy}>
            ↻ Arvo uudet
          </button>
        )}
      </div>

      <section className="stories">
        {activeStories.map((story) => (
          <article className="story" key={story.id}>
            <div className="story-header">
              <h3>{story.title}</h3>
              <div className="story-meta">
                <span>{story.source}</span>
                <span>Yhteensä {story.score.toFixed(2)}</span>
                <span>Pohja {story.base_score.toFixed(2)}</span>
                <span>Palaute {story.feedback_score.toFixed(2)}</span>
              </div>
            </div>
            <ul>
              {story.summary.bullets.slice(0, 5).map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
            <details className="score-breakdown">
              <summary>Miksi tämä pisteet</summary>
              <ul>
                {story.score_breakdown.items.map((item, idx) => (
                  <li key={`${item.reason}-${idx}`}>
                    {item.reason}: {item.points > 0 ? '+' : ''}
                    {item.points.toFixed(2)}
                  </li>
                ))}
                {story.score_breakdown.items.length === 0 && (
                  <li>Ei pisteitystietoja saatavilla</li>
                )}
              </ul>
            </details>
            <div className="story-footer">
              <div className="chips">
                {story.topics.map((topic) => (
                  <span key={topic}>{topic}</span>
                ))}
              </div>
              <div className="story-actions">
                <button onClick={() => rateStory(story.id, true)} disabled={busy}>Relevantti</button>
                <button onClick={() => rateStory(story.id, false)} disabled={busy}>Ei relevantti</button>
                <span className="feedback-counts">
                  + {story.feedback_positive} / − {story.feedback_negative}
                </span>
                <button onClick={() => speakStory(story)}>Kuuntele</button>
                <a href={story.url} target="_blank" rel="noreferrer">Avaa lähde</a>
              </div>
            </div>
          </article>
        ))}
        {activeStories.length === 0 && !busy && (
          <p className="empty">Ei uutisia – käynnistä päivitys yllä.</p>
        )}
      </section>
    </main>
  )
}

export default App
