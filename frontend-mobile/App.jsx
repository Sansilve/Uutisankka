import { useEffect, useMemo, useState } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native'
import ArticleCard from './src/components/ArticleCard'
import HistoryScreen from './src/components/HistoryScreen'
import OnboardingScreen from './src/components/OnboardingScreen'
import PreferencesPanel from './src/components/PreferencesPanel'
import {
  fetchBriefing,
  fetchMetrics,
  fetchPreferences,
  fetchRandomBriefing,
  sendFeedback,
  triggerIngest,
} from './src/api'

const DAILY_LIMIT = 8

function Masthead({ metricsText, onOpenSettings, onOpenHistory }) {
  return (
    <View style={styles.masthead}>
      <View style={styles.mastheadTop}>
        <Text style={styles.mastheadName}>🦆 UutisAnkka</Text>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <TouchableOpacity style={styles.settingsButton} onPress={onOpenHistory}>
            <Text style={styles.settingsButtonText}>Historia</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.settingsButton} onPress={onOpenSettings}>
            <Text style={styles.settingsButtonText}>Asetukset</Text>
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.mastheadRule} />
      <View style={styles.mastheadMeta}>
        <Text style={styles.mastheadSub}>PÄIVÄN BRIEFING</Text>
        {metricsText ? <Text style={styles.mastheadMetrics}>{metricsText}</Text> : null}
      </View>
    </View>
  )
}

function CompletionScreen({ ratings, onRestart, onShowMore, onOpenSettings }) {
  const { width } = useWindowDimensions()
  const isCompact = width < 520
  const contentWidth = Math.min(width - (isCompact ? 32 : 64), 680)
  const relevantCount = ratings.filter((item) => item.isRelevant).length
  const percentage = ratings.length ? Math.round((relevantCount / ratings.length) * 100) : 0
  const barPercent = `${percentage}%`

  return (
    <ScrollView contentContainerStyle={styles.completionScroll}>
      <View style={[styles.completionInner, { width: contentWidth }]}>
        {/* Mini masthead */}
        <Text style={styles.completionBrand}>🦆 UutisAnkka</Text>
        <View style={styles.completionBrandRule} />

        {/* Check */}
        <View style={styles.completionCheckCircle}>
          <Text style={styles.completionCheckMark}>✓</Text>
        </View>

        <Text style={styles.completionTitle}>Päivä luettu!</Text>
        <Text style={styles.completionBody}>
          Luit {ratings.length} artikkelia ja pidit {relevantCount} niistä kiinnostavina.
        </Text>

        {/* Big progress bar */}
        <View style={styles.completionBarWrap}>
          <View style={styles.completionTrack}>
            <View style={[styles.completionFill, { width: barPercent }]} />
          </View>
          <Text style={styles.completionPercent}>{percentage}% relevanttia</Text>
        </View>

        {/* Stats */}
        <View style={styles.statRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{ratings.length}</Text>
            <Text style={styles.statLabel}>Käsitelty</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{relevantCount}</Text>
            <Text style={styles.statLabel}>Kiinnostaa</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{ratings.length - relevantCount}</Text>
            <Text style={styles.statLabel}>Ohitettu</Text>
          </View>
        </View>

        <View style={styles.completionRuleLight} />

        <TouchableOpacity style={styles.primaryButton} onPress={onShowMore}>
          <Text style={styles.primaryButtonText}>📰 Näytä lisää uutisia</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.secondaryButton} onPress={onRestart}>
          <Text style={styles.secondaryButtonText}>↻ Aloita alusta</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.ghostButton} onPress={onOpenSettings}>
          <Text style={styles.ghostButtonText}>Avaa asetukset</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

export default function App() {
  const { width } = useWindowDimensions()
  const isCompact = width < 560
  const [screen, setScreen] = useState('feed')
  const [onboardingDone, setOnboardingDone] = useState(null) // null = checking
  const [briefing, setBriefing] = useState([])
  const [preferences, setPreferences] = useState({ interests: [], disliked_topics: [] })
  const [metrics, setMetrics] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [ratings, setRatings] = useState([])
  const [surpriseStory, setSurpriseStory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  function applyBriefingState(briefingData, prefData, metricsData) {
    setBriefing(briefingData.stories)
    setPreferences(prefData)
    setMetrics(metricsData)
    setCurrentIndex(0)
    setRatings([])
    setSurpriseStory(null)
  }

  async function loadData() {
    try {
      const [briefingData, prefData, metricsData] = await Promise.all([
        fetchBriefing(DAILY_LIMIT),
        fetchPreferences(),
        fetchMetrics(DAILY_LIMIT),
      ])
      applyBriefingState(briefingData, prefData, metricsData)
    } catch (error) {
      setStatusMsg(`Virhe: ${error.message}`)
    }
  }

  useEffect(() => {
    AsyncStorage.getItem('onboarding_done').then((val) => {
      setOnboardingDone(val === 'true')
    })
  }, [])

  useEffect(() => {
    loadData().finally(() => setLoading(false))
  }, [])

  const activeStory = surpriseStory || briefing[currentIndex]
  const total = briefing.length || DAILY_LIMIT
  const progressCount = Math.min(currentIndex + 1, total)
  const progressRatio = total ? progressCount / total : 0
  const progressWidth = `${Math.max(progressRatio, 0.02) * 100}%`
  const isComplete = !loading && !surpriseStory && currentIndex >= briefing.length && briefing.length > 0

  async function handleDecision(isRelevant) {
    if (!activeStory) return
    setBusy(true)
    try {
      await sendFeedback({ article_id: activeStory.id, is_relevant: isRelevant })
      setRatings((prev) => [
        ...prev,
        { articleId: activeStory.id, isRelevant, surprise: Boolean(surpriseStory) },
      ])
      setStatusMsg(isRelevant ? 'Merkitty kiinnostavaksi' : 'Ohitettu')
      if (surpriseStory) {
        setSurpriseStory(null)
      } else {
        setCurrentIndex((v) => v + 1)
      }
    } catch (error) {
      setStatusMsg(`Virhe: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function handleSurprise() {
    setBusy(true)
    try {
      const result = await fetchRandomBriefing(1)
      const nextStory = result.stories[0]
      if (!nextStory) {
        setStatusMsg('Yllätysuutista ei saatu juuri nyt.')
      } else {
        setSurpriseStory(nextStory)
        setStatusMsg('Yllätysuutinen haettu.')
      }
    } catch (error) {
      setStatusMsg(`Virhe: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function handleShowMore() {
    setBusy(true)
    try {
      const ingest = await triggerIngest()
      if (ingest.inserted > 0) {
        setStatusMsg(`Haettu ${ingest.inserted} uutta uutista`)
        await loadData()
      } else {
        const [briefingData, prefData, metricsData] = await Promise.all([
          fetchRandomBriefing(DAILY_LIMIT),
          fetchPreferences(),
          fetchMetrics(DAILY_LIMIT),
        ])
        applyBriefingState(briefingData, prefData, metricsData)
        setStatusMsg('Ei uusia uutisia juuri nyt - näytetään toinen kierros valikoidusta arkistosta.')
      }
      setScreen('feed')
    } catch (error) {
      setStatusMsg(`Virhe: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  function handleRestart() {
    setCurrentIndex(0)
    setRatings([])
    setSurpriseStory(null)
    setScreen('feed')
  }

  const metricsText = useMemo(() => {
    if (!metrics) return ''
    if (metrics.positive_feedback_ratio === null) return 'Ei palautetta vielä'
    return `${Math.round(metrics.positive_feedback_ratio * 100)}% relevanttia · ${metrics.total_feedback_votes} ääntä`
  }, [metrics])

  if (loading || onboardingDone === null) {
    return (
      <SafeAreaView style={styles.loadingScreen}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <ActivityIndicator size="large" color="#1a1a1a" />
        <Text style={styles.loadingText}>Rakennetaan päivän uutiskierros...</Text>
      </SafeAreaView>
    )
  }

  if (!onboardingDone) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <OnboardingScreen
          onComplete={async () => {
            await AsyncStorage.setItem('onboarding_done', 'true')
            setOnboardingDone(true)
            await loadData()
          }}
        />
      </SafeAreaView>
    )
  }

  if (screen === 'history') {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <HistoryScreen onClose={() => setScreen('feed')} />
      </SafeAreaView>
    )
  }

  if (screen === 'settings') {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <View style={styles.sheetHeader}>
          <TouchableOpacity onPress={() => setScreen('feed')}>
            <Text style={styles.backButton}>← Takaisin</Text>
          </TouchableOpacity>
          <Text style={styles.sheetTitle}>Asetukset</Text>
          <View style={styles.sheetSpacer} />
        </View>
        <View style={styles.sheetRule} />
        <PreferencesPanel
          preferences={preferences}
          onSaved={async () => {
            await loadData()
            setScreen('feed')
          }}
        />
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />

      <Masthead metricsText={metricsText} onOpenSettings={() => setScreen('settings')} onOpenHistory={() => setScreen('history')} />

      {statusMsg ? (
        <View style={styles.statusBanner}>
          <Text style={styles.statusText}>{statusMsg}</Text>
        </View>
      ) : null}

      {isComplete ? (
        <CompletionScreen
          ratings={ratings.filter((item) => !item.surprise)}
          onRestart={handleRestart}
          onShowMore={handleShowMore}
          onOpenSettings={() => setScreen('settings')}
        />
      ) : activeStory ? (
        <ArticleCard
          story={activeStory}
          onDecision={handleDecision}
          disabled={busy}
          progressText={`${progressCount} / ${total}`}
          progressWidth={progressWidth}
          onSurprise={handleSurprise}
        />
      ) : (
        <View style={styles.emptyWrap}>
          <Text style={styles.emptyTitle}>Ei uutisia juuri nyt</Text>
          <Text style={styles.emptyBody}>
            Päivitä syötteet tai kokeile uudelleen hetken päästä.
          </Text>
          <TouchableOpacity style={styles.primaryButton} onPress={handleShowMore} disabled={busy}>
            <Text style={styles.primaryButtonText}>Päivitä uutiset</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    width: '100%',
    backgroundColor: '#ffffff',
    overflow: 'hidden',
  },
  loadingScreen: {
    flex: 1,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: '#9ca3af',
    fontSize: 15,
    marginTop: 14,
    fontFamily: 'Georgia',
  },

  // Masthead
  masthead: {
    paddingHorizontal: 18,
    paddingTop: 10,
    paddingBottom: 0,
    backgroundColor: '#ffffff',
  },
  mastheadTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  mastheadName: {
    color: '#1a1a1a',
    fontSize: 28,
    fontWeight: '900',
    fontFamily: 'Georgia',
    letterSpacing: -0.5,
  },
  mastheadRule: {
    height: 3,
    backgroundColor: '#FFB700',
    marginBottom: 6,
  },
  mastheadMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: 8,
  },
  mastheadSub: {
    color: '#9ca3af',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 2,
  },
  mastheadMetrics: {
    color: '#9ca3af',
    fontSize: 11,
  },
  settingsButton: {
    borderWidth: 1.5,
    borderColor: '#d1d5db',
    borderRadius: 2,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  settingsButtonText: {
    color: '#1a1a1a',
    fontSize: 13,
    fontWeight: '700',
  },

  // Status banner
  statusBanner: {
    backgroundColor: '#fffbeb',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#fde68a',
    paddingHorizontal: 18,
    paddingVertical: 7,
  },
  statusText: {
    color: '#92400e',
    fontSize: 12,
    fontWeight: '600',
  },

  // Settings sheet
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 10,
  },
  sheetRule: {
    height: 1,
    backgroundColor: '#e5e7eb',
  },
  backButton: {
    color: '#1a1a1a',
    fontSize: 15,
    fontWeight: '700',
  },
  sheetTitle: {
    color: '#1a1a1a',
    fontSize: 16,
    fontWeight: '800',
    fontFamily: 'Georgia',
  },
  sheetSpacer: {
    width: 60,
  },

  // Completion screen
  completionScroll: {
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 16,
  },
  completionInner: {
    alignItems: 'center',
  },
  completionBrand: {
    color: '#1a1a1a',
    fontSize: 22,
    fontWeight: '900',
    fontFamily: 'Georgia',
    marginBottom: 4,
  },
  completionBrandRule: {
    height: 2,
    backgroundColor: '#FFB700',
    width: '100%',
    marginBottom: 28,
  },
  completionCheckCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 3,
    borderColor: '#065f46',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  completionCheckMark: {
    color: '#065f46',
    fontSize: 36,
    fontWeight: '900',
    lineHeight: 42,
  },
  completionTitle: {
    color: '#1a1a1a',
    fontSize: 32,
    fontWeight: '900',
    fontFamily: 'Georgia',
    marginBottom: 10,
    textAlign: 'center',
  },
  completionBody: {
    color: '#4a4a4a',
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'center',
    fontFamily: 'Georgia',
    marginBottom: 24,
  },
  completionBarWrap: {
    width: '100%',
    marginBottom: 24,
  },
  completionTrack: {
    height: 8,
    backgroundColor: '#f3f4f6',
    borderRadius: 4,
    marginBottom: 6,
  },
  completionFill: {
    height: '100%',
    backgroundColor: '#FFB700',
    borderRadius: 4,
  },
  completionPercent: {
    color: '#4a4a4a',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'right',
  },
  statRow: {
    flexDirection: 'row',
    width: '100%',
    marginBottom: 24,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 3,
  },
  statCard: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
  },
  statDivider: {
    width: 1.5,
    backgroundColor: '#e5e7eb',
  },
  statValue: {
    color: '#1a1a1a',
    fontSize: 28,
    fontWeight: '900',
    fontFamily: 'Georgia',
  },
  statLabel: {
    color: '#9ca3af',
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
    marginTop: 2,
  },
  completionRuleLight: {
    height: 1,
    backgroundColor: '#e5e7eb',
    width: '100%',
    marginBottom: 20,
  },
  primaryButton: {
    width: '100%',
    backgroundColor: '#1a1a1a',
    borderRadius: 2,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
    marginBottom: 10,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  secondaryButton: {
    width: '100%',
    borderWidth: 2,
    borderColor: '#1a1a1a',
    borderRadius: 2,
    minHeight: 52,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
    marginBottom: 10,
  },
  secondaryButtonText: {
    color: '#1a1a1a',
    fontSize: 15,
    fontWeight: '700',
  },
  ghostButton: {
    marginTop: 4,
    paddingVertical: 10,
  },
  ghostButtonText: {
    color: '#9ca3af',
    fontSize: 13,
    fontWeight: '600',
    borderBottomWidth: 1,
    borderBottomColor: '#d1d5db',
  },

  // Empty state
  emptyWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    gap: 14,
  },
  emptyTitle: {
    color: '#1a1a1a',
    fontSize: 26,
    fontWeight: '800',
    fontFamily: 'Georgia',
    textAlign: 'center',
  },
  emptyBody: {
    color: '#4a4a4a',
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
  },
})
