import { useEffect, useMemo, useState } from 'react'
import {
  fetchBriefing,
  fetchMetrics,
  fetchPreferences,
  sendFeedback,
  triggerIngest,
  updatePreferences,
} from './api'
import './App.css'

function App() {
  const [briefing, setBriefing] = useState({ stories: [], generated_at: null })
  const [preferences, setPreferences] = useState({
    interests: ['technology', 'politics', 'economy'],
    disliked_topics: ['celebrity', 'entertainment'],
  })
  const [interestInput, setInterestInput] = useState('technology, politics, economy')
  const [dislikedInput, setDislikedInput] = useState('celebrity, entertainment')
  const [status, setStatus] = useState('Loading briefing...')
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
        fetchBriefing(10),
        fetchPreferences(),
        fetchMetrics(10),
      ])
      setBriefing(briefingData)
      setPreferences(prefData)
      setMetrics(metricsData)
      setInterestInput(prefData.interests.join(', '))
      setDislikedInput(prefData.disliked_topics.join(', '))
      setStatus(`Loaded ${briefingData.total} stories`)
    } catch (error) {
      setStatus(`Error: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  async function refreshIngest() {
    setBusy(true)
    setStatus('Refreshing feeds...')
    try {
      const result = await triggerIngest()
      await loadAll()
      setStatus(`Ingested ${result.inserted} new stories, skipped ${result.duplicates} duplicates`)
    } catch (error) {
      setStatus(`Error: ${error.message}`)
      setBusy(false)
    }
  }

  function normalizeList(input) {
    return input
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  }

  async function savePreferences() {
    setBusy(true)
    try {
      const payload = {
        interests: normalizeList(interestInput),
        disliked_topics: normalizeList(dislikedInput),
      }
      const updated = await updatePreferences(payload)
      setPreferences(updated)
      await loadAll()
      setStatus('Preferences saved and briefing re-ranked')
    } catch (error) {
      setStatus(`Error: ${error.message}`)
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
        `Feedback saved: ${result.feedback_positive} relevant, ${result.feedback_negative} not relevant`
      )
    } catch (error) {
      setStatus(`Error: ${error.message}`)
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
    if (!briefing.stories.length) {
      return
    }
    const payload = briefing.stories
      .slice(0, 5)
      .map((story, index) => `Story ${index + 1}. ${story.title}. ${story.summary.bullets[0] ?? ''}`)
      .join('. ')
    speak(payload)
  }

  return (
    <main className="page">
      <header className="topbar">
        <div>
          <p className="kicker">UutisAnkka</p>
          <h1>No-BS Morning Briefing</h1>
          <p className="meta">Updated: {updatedAt}</p>
          <p className="meta">
            Top {metrics.top_limit} acceptance:{' '}
            {metrics.positive_feedback_ratio === null
              ? 'No feedback yet'
              : `${Math.round(metrics.positive_feedback_ratio * 100)}%`} ({metrics.total_feedback_votes} votes)
          </p>
        </div>
        <div className="actions">
          <button onClick={refreshIngest} disabled={busy}>Refresh Feeds</button>
          <button onClick={speakTopStories} disabled={!briefing.stories.length}>Listen Top 5</button>
        </div>
      </header>

      <section className="panel prefs">
        <h2>Personalization</h2>
        <p className="panel-copy">Tune relevance scoring with comma-separated topics.</p>
        <label>
          Interests
          <input
            value={interestInput}
            onChange={(e) => setInterestInput(e.target.value)}
            placeholder="technology, politics, economy"
          />
        </label>
        <label>
          Disliked Topics
          <input
            value={dislikedInput}
            onChange={(e) => setDislikedInput(e.target.value)}
            placeholder="celebrity, entertainment"
          />
        </label>
        <div className="prefs-actions">
          <button onClick={savePreferences} disabled={busy}>Save Preferences</button>
          <span>{status}</span>
        </div>
        <p className="current">Current profile: {preferences.interests.join(', ')} | avoid {preferences.disliked_topics.join(', ')}</p>
      </section>

      <section className="stories">
        {briefing.stories.map((story) => (
          <article className="story" key={story.id}>
            <div className="story-header">
              <h3>{story.title}</h3>
              <div className="story-meta">
                <span>{story.source}</span>
                <span>Total {story.score.toFixed(2)}</span>
                <span>Base {story.base_score.toFixed(2)}</span>
                <span>Feedback {story.feedback_score.toFixed(2)}</span>
              </div>
            </div>
            <ul>
              {story.summary.bullets.slice(0, 5).map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
            <details className="score-breakdown">
              <summary>Why this score</summary>
              <ul>
                {story.score_breakdown.items.map((item, idx) => (
                  <li key={`${item.reason}-${idx}`}>
                    {item.reason}: {item.points > 0 ? '+' : ''}
                    {item.points.toFixed(2)}
                  </li>
                ))}
                {story.score_breakdown.items.length === 0 && (
                  <li>No breakdown available</li>
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
                <button onClick={() => rateStory(story.id, true)} disabled={busy}>Relevant</button>
                <button onClick={() => rateStory(story.id, false)} disabled={busy}>Not relevant</button>
                <span className="feedback-counts">
                  Positive {story.feedback_positive} | Negative {story.feedback_negative}
                </span>
                <button onClick={() => speakStory(story)}>Listen</button>
                <a href={story.url} target="_blank" rel="noreferrer">Open source</a>
              </div>
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}

export default App
