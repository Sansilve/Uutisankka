import { useMemo, useState } from 'react'

export default function useBriefingState(dailyLimit) {
  const [briefing, setBriefing] = useState([])
  const [emptyReason, setEmptyReason] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [ratings, setRatings] = useState([])
  const [surpriseStory, setSurpriseStory] = useState(null)

  function applyBriefingData(briefingData, metricsData) {
    setBriefing(briefingData?.stories || [])
    setEmptyReason(briefingData?.empty_reason || null)
    setMetrics(metricsData || null)
    setCurrentIndex(0)
    setRatings([])
    setSurpriseStory(null)
    setEmptyReason(null)
  }

  function addRating(storyId, isRelevant, isSurprise) {
    setRatings((prev) => [
      ...prev,
      { articleId: storyId, isRelevant, surprise: Boolean(isSurprise) },
    ])
  }

  function moveToNextStory() {
    setCurrentIndex((value) => value + 1)
  }

  function clearSurpriseStory() {
    setSurpriseStory(null)
  }

  function resetReadingSession() {
    setCurrentIndex(0)
    setRatings([])
    setSurpriseStory(null)
  }

  const activeStory = surpriseStory || briefing[currentIndex]
  const isShowingSurprise = Boolean(surpriseStory)
  const total = briefing.length || dailyLimit
  const progressCount = Math.min(currentIndex + 1, total)
  const progressRatio = total ? progressCount / total : 0
  const progressWidth = `${Math.max(progressRatio, 0.02) * 100}%`
  const isComplete = currentIndex >= briefing.length && briefing.length > 0 && !surpriseStory

  const metricsText = useMemo(() => {
    if (!metrics) return ''
    if (metrics.positive_feedback_ratio === null) return 'Ei palautetta vielä'
    return `${Math.round(metrics.positive_feedback_ratio * 100)}% relevanttia · ${metrics.total_feedback_votes} ääntä`
  }, [metrics])

  return {
    briefing,
    emptyReason,
    metrics,
    currentIndex,
    ratings,
    surpriseStory,
    isShowingSurprise,
    activeStory,
    total,
    progressCount,
    progressWidth,
    isComplete,
    metricsText,
    applyBriefingData,
    addRating,
    moveToNextStory,
    clearSurpriseStory,
    resetReadingSession,
    setSurpriseStory,
  }
}
