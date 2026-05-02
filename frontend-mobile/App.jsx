import { useEffect, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native'
import ArticleCard from './src/components/ArticleCard'
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

function CompletionScreen({ ratings, onRestart, onShowMore, onOpenSettings }) {
  const { width } = useWindowDimensions()
  const isCompact = width < 520
  const contentWidth = Math.min(width - (isCompact ? 32 : 48), 720)
  const relevantCount = ratings.filter((item) => item.isRelevant).length
  const percentage = ratings.length ? Math.round((relevantCount / ratings.length) * 100) : 0

  return (
    <View style={styles.completionWrap}>
      <View style={[styles.completionInner, { width: contentWidth }]}> 
      <Text style={styles.completionCheck}>Valmis!</Text>
      <Text style={styles.completionTitle}>Paivan kierros paketissa</Text>
      <Text style={styles.completionBody}>
        Luit {ratings.length} uutista ja merkitsit {relevantCount} relevanteiksi ({percentage}%).
      </Text>

      <View style={[styles.statRow, isCompact && styles.statRowCompact]}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{ratings.length}</Text>
          <Text style={styles.statLabel}>Kasitelty</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{relevantCount}</Text>
          <Text style={styles.statLabel}>Relevantti</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{ratings.length - relevantCount}</Text>
          <Text style={styles.statLabel}>Ohitettu</Text>
        </View>
      </View>

      <TouchableOpacity style={[styles.primaryButton, styles.fullWidth]}>
        <Text style={styles.primaryButtonText}>Kuuntele yhteenveto</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.secondaryButton, styles.fullWidth]} onPress={onShowMore}>
        <Text style={styles.secondaryButtonText}>Nayta lisaa</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.secondaryButton, styles.fullWidth]} onPress={onRestart}>
        <Text style={styles.secondaryButtonText}>Aloita alusta</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.settingsLink} onPress={onOpenSettings}>
        <Text style={styles.settingsLinkText}>Avaa asetukset</Text>
      </TouchableOpacity>
      </View>
    </View>
  )
}

export default function App() {
  const { width } = useWindowDimensions()
  const isCompact = width < 560
  const contentWidth = Math.min(width - (isCompact ? 24 : 40), 980)
  const [screen, setScreen] = useState('feed')
  const [briefing, setBriefing] = useState([])
  const [preferences, setPreferences] = useState({ interests: [], disliked_topics: [] })
  const [metrics, setMetrics] = useState(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [ratings, setRatings] = useState([])
  const [surpriseStory, setSurpriseStory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  async function loadData() {
    try {
      const [briefingData, prefData, metricsData] = await Promise.all([
        fetchBriefing(DAILY_LIMIT),
        fetchPreferences(),
        fetchMetrics(DAILY_LIMIT),
      ])
      setBriefing(briefingData.stories)
      setPreferences(prefData)
      setMetrics(metricsData)
      setCurrentIndex(0)
      setRatings([])
      setSurpriseStory(null)
    } catch (error) {
      setStatusMsg(`Virhe: ${error.message}`)
    }
  }

  useEffect(() => {
    loadData().finally(() => setLoading(false))
  }, [])

  const activeStory = surpriseStory || briefing[currentIndex]
  const total = briefing.length || DAILY_LIMIT
  const completedMainStories = currentIndex
  const progressCount = Math.min(completedMainStories + 1, total)
  const progressRatio = total ? progressCount / total : 0
  const progressWidth = `${Math.max(progressRatio, 0.02) * 100}%`
  const isComplete = !loading && !surpriseStory && currentIndex >= briefing.length && briefing.length > 0

  async function handleDecision(isRelevant) {
    if (!activeStory) {
      return
    }
    setBusy(true)
    try {
      await sendFeedback({ article_id: activeStory.id, is_relevant: isRelevant })
      setRatings((prev) => [...prev, { articleId: activeStory.id, isRelevant, surprise: Boolean(surpriseStory) }])
      setStatusMsg(isRelevant ? 'Merkittu relevantiksi' : 'Merkittu ei-kiinnostavaksi')
      if (surpriseStory) {
        setSurpriseStory(null)
      } else {
        setCurrentIndex((value) => value + 1)
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
        setStatusMsg('Yllatysuutista ei saatu juuri nyt.')
      } else {
        setSurpriseStory(nextStory)
        setStatusMsg('Yllatysuutinen haettu.')
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
      setStatusMsg(`Haettu ${ingest.inserted} uutta uutista`)
      await loadData()
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
    if (!metrics) {
      return ''
    }
    if (metrics.positive_feedback_ratio === null) {
      return 'Ei palautetta viela'
    }
    return `${Math.round(metrics.positive_feedback_ratio * 100)}% relevanttia · ${metrics.total_feedback_votes} aanta`
  }, [metrics])

  if (loading) {
    return (
      <SafeAreaView style={styles.loadingScreen}>
        <StatusBar barStyle="dark-content" backgroundColor="#f6f7fb" />
        <ActivityIndicator size="large" color="#111827" />
        <Text style={styles.loadingText}>Rakennetaan paivan uutiskierros...</Text>
      </SafeAreaView>
    )
  }

  if (screen === 'settings') {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#f6f7fb" />
        <View style={styles.sheetHeader}>
          <TouchableOpacity onPress={() => setScreen('feed')}>
            <Text style={styles.backButton}>Takaisin</Text>
          </TouchableOpacity>
          <Text style={styles.sheetTitle}>Asetukset</Text>
          <View style={styles.sheetSpacer} />
        </View>
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
      <StatusBar barStyle="dark-content" backgroundColor="#f6f7fb" />

      <View style={[styles.appHeader, { paddingHorizontal: isCompact ? 12 : 18, width: contentWidth, alignSelf: 'center' }]}>
        <View>
          <Text style={styles.appName}>UutisAnkka</Text>
          <Text style={styles.metricsLine}>{metricsText}</Text>
        </View>
        <TouchableOpacity style={styles.settingsButton} onPress={() => setScreen('settings')}>
          <Text style={styles.settingsButtonText}>Asetukset</Text>
        </TouchableOpacity>
      </View>

      {statusMsg ? (
        <View style={[styles.statusBanner, { width: contentWidth, alignSelf: 'center', paddingHorizontal: isCompact ? 12 : 18 }]}>
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
          <Text style={styles.emptyBody}>Paeivita syotteet tai kokeile uudelleen hetken paasta.</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={handleShowMore} disabled={busy}>
            <Text style={styles.primaryButtonText}>Paivita uutiset</Text>
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
    backgroundColor: '#f6f7fb',
    overflow: 'hidden',
  },
  loadingScreen: {
    flex: 1,
    backgroundColor: '#f6f7fb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: '#6b7280',
    fontSize: 15,
    marginTop: 14,
  },
  appHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 6,
  },
  appName: {
    color: '#111827',
    fontSize: 24,
    fontWeight: '800',
  },
  metricsLine: {
    color: '#6b7280',
    fontSize: 13,
    marginTop: 4,
  },
  settingsButton: {
    borderRadius: 12,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#d7d9e1',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  settingsButtonText: {
    color: '#111827',
    fontSize: 14,
    fontWeight: '700',
  },
  statusBanner: {
    backgroundColor: '#eef2ff',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#dbe3ff',
    paddingHorizontal: 18,
    paddingVertical: 8,
  },
  statusText: {
    color: '#374151',
    fontSize: 13,
  },
  completionWrap: {
    flex: 1,
    width: '100%',
    paddingHorizontal: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  completionInner: {
    maxWidth: 720,
  },
  completionCheck: {
    color: '#08a045',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 12,
  },
  completionTitle: {
    color: '#111827',
    fontSize: 34,
    lineHeight: 40,
    fontWeight: '800',
    marginBottom: 10,
  },
  completionBody: {
    color: '#4b5563',
    fontSize: 17,
    lineHeight: 25,
  },
  statRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 24,
    marginBottom: 24,
  },
  statRowCompact: {
    flexDirection: 'column',
  },
  statCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: '#000000',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  statValue: {
    color: '#111827',
    fontSize: 24,
    fontWeight: '800',
  },
  statLabel: {
    color: '#6b7280',
    fontSize: 12,
    marginTop: 4,
  },
  fullWidth: {
    width: '100%',
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#111827',
    borderRadius: 14,
    minHeight: 54,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    backgroundColor: '#ffffff',
    borderRadius: 14,
    minHeight: 54,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#d7d9e1',
    paddingHorizontal: 18,
  },
  secondaryButtonText: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '700',
  },
  settingsLink: {
    alignItems: 'center',
    marginTop: 6,
  },
  settingsLinkText: {
    color: '#6b7280',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 28,
    gap: 14,
    alignSelf: 'center',
    width: '100%',
    maxWidth: 720,
  },
  emptyTitle: {
    color: '#111827',
    fontSize: 28,
    fontWeight: '800',
  },
  emptyBody: {
    color: '#6b7280',
    fontSize: 16,
    lineHeight: 24,
    textAlign: 'center',
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 8,
  },
  backButton: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '700',
  },
  sheetTitle: {
    color: '#111827',
    fontSize: 18,
    fontWeight: '800',
  },
  sheetSpacer: {
    width: 60,
  },
})
