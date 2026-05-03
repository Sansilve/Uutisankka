import { useEffect } from 'react'
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
import AllNewsScreen from './src/components/AllNewsScreen'
import HistoryScreen from './src/components/HistoryScreen'
import OnboardingScreen from './src/components/OnboardingScreen'
import PreferencesPanel from './src/components/PreferencesPanel'
import SwipeTutorialOverlay from './src/components/SwipeTutorialOverlay'
import useAppNavigation from './src/navigation/useAppNavigation'
import { APP_ROUTES } from './src/navigation/routes'
import useBriefingState from './src/state/useBriefingState'
import usePreferencesState from './src/state/usePreferencesState'
import useSessionUiState from './src/state/useSessionUiState'
import {
  fetchBriefing,
  fetchMetrics,
  fetchPreferences,
  fetchRandomBriefing,
  sendFeedback,
  triggerIngest,
} from './src/api'

const DAILY_LIMIT = 8

function Masthead({ metricsText, onOpenSettings, onOpenHistory, onOpenAllNews }) {
  return (
    <View style={styles.masthead}>
      <View style={styles.mastheadTop}>
        <Text style={styles.mastheadName}>🦆 UutisAnkka</Text>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <TouchableOpacity style={styles.settingsButton} onPress={onOpenAllNews}>
            <Text style={styles.settingsButtonText}>Kaikki</Text>
          </TouchableOpacity>
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

function CompletionScreen({ ratings, onRestart, onShowMore, onOpenSettings, busy }) {
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

        <TouchableOpacity
          style={[styles.primaryButton, busy && { opacity: 0.5 }]}
          onPress={onShowMore}
          disabled={busy}
        >
          {busy
            ? <ActivityIndicator color="#fff" size="small" />
            : <Text style={styles.primaryButtonText}>📰 Näytä lisää uutisia</Text>
          }
        </TouchableOpacity>
        <TouchableOpacity style={styles.secondaryButton} onPress={onRestart} disabled={busy}>
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
  useWindowDimensions()
  const { route, openFeed, openHistory, openAllNews, openSettings } = useAppNavigation()
  const { preferences, applyPreferences } = usePreferencesState()
  const {
    ratings,
    activeStory,
    isShowingSurprise,
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
  } = useBriefingState(DAILY_LIMIT)
  const {
    onboardingDone,
    swipeTutorialShown,
    loading,
    busy,
    statusMsg,
    fatalError,
    setLoading,
    setBusy,
    setStatusMsg,
    setErrorStatus,
    markFatalError,
    clearFatalError,
    completeOnboarding,
    markSwipeTutorialShown,
  } = useSessionUiState()

  async function loadData() {
    try {
      const [briefingData, prefData, metricsData] = await Promise.all([
        fetchBriefing(DAILY_LIMIT),
        fetchPreferences(),
        fetchMetrics(DAILY_LIMIT),
      ])
      applyBriefingData(briefingData, metricsData)
      applyPreferences(prefData)
      clearFatalError()
    } catch (error) {
      markFatalError(error)
    }
  }

  useEffect(() => {
    loadData().finally(() => setLoading(false))
  }, [])

  async function handleDecision(isRelevant) {
    if (!activeStory) return
    setBusy(true)
    try {
      await sendFeedback({ article_id: activeStory.id, is_relevant: isRelevant })
      addRating(activeStory.id, isRelevant, isShowingSurprise)
      setStatusMsg(isRelevant ? 'Merkitty kiinnostavaksi' : 'Ohitettu')
      if (isShowingSurprise) {
        clearSurpriseStory()
      } else {
        moveToNextStory()
      }
    } catch (error) {
      setErrorStatus(error)
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
      setErrorStatus(error)
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
        applyBriefingData(briefingData, metricsData)
        applyPreferences(prefData)
        setStatusMsg('Ei uusia uutisia juuri nyt - näytetään toinen kierros valikoidusta arkistosta.')
      }
      openFeed()
    } catch (error) {
      setErrorStatus(error)
    } finally {
      setBusy(false)
    }
  }

  function handleRestart() {
    resetReadingSession()
    openFeed()
  }

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
            await completeOnboarding()
            setLoading(true)
            await loadData()
            setLoading(false)
          }}
        />
      </SafeAreaView>
    )
  }

  if (fatalError) {
    return (
      <SafeAreaView style={styles.loadingScreen}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <Text style={styles.errorScreenTitle}>Yhteys epäonnistui</Text>
        <Text style={styles.errorScreenBody}>{fatalError}</Text>
        <TouchableOpacity
          style={styles.retryButton}
          onPress={async () => {
            setLoading(true)
            await loadData()
            setLoading(false)
          }}
        >
          <Text style={styles.retryButtonText}>↻ Yritä uudelleen</Text>
        </TouchableOpacity>
      </SafeAreaView>
    )
  }

  if (route === APP_ROUTES.HISTORY) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <HistoryScreen onClose={openFeed} />
      </SafeAreaView>
    )
  }

  if (route === APP_ROUTES.ALL_NEWS) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <AllNewsScreen onClose={openFeed} />
      </SafeAreaView>
    )
  }

  if (route === APP_ROUTES.SETTINGS) {
    return (
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
        <View style={styles.sheetHeader}>
          <TouchableOpacity onPress={openFeed}>
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
            openFeed()
          }}
        />
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />

      <Masthead
        metricsText={metricsText}
        onOpenSettings={openSettings}
        onOpenHistory={openHistory}
        onOpenAllNews={openAllNews}
      />

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
          onOpenSettings={openSettings}
          busy={busy}
        />
      ) : activeStory ? (
        <View style={{ flex: 1, position: 'relative' }}>
          <ArticleCard
            story={activeStory}
            onDecision={handleDecision}
            disabled={busy}
            progressText={`${progressCount} / ${total}`}
            progressWidth={progressWidth}
            onSurprise={handleSurprise}
          />
          {swipeTutorialShown === false ? (
            <SwipeTutorialOverlay onDismiss={markSwipeTutorialShown} />
          ) : null}
        </View>
      ) : (
        <View style={styles.emptyWrap}>
          {loading ? (
            <>
              <Text style={styles.emptyEmoji}>⏳</Text>
              <Text style={styles.emptyTitle}>Haetaan uutisia...</Text>
              <ActivityIndicator color="#FFB700" size="large" />
            </>
          ) : total === 0 ? (
            <>
              <Text style={styles.emptyEmoji}>🚫</Text>
              <Text style={styles.emptyTitle}>Ei uutisia saatavilla</Text>
              <Text style={styles.emptyBody}>
                Mitään uutisia ei vastaa nykyisiä suodattimia. Kokeile muuttaa asetuksia tai palaa myöhemmin.
              </Text>
              <TouchableOpacity style={styles.primaryButton} onPress={openSettings}>
                <Text style={styles.primaryButtonText}>Muokkaa asetuksia</Text>
              </TouchableOpacity>
            </>
          ) : isComplete ? (
            <>
              <Text style={styles.emptyEmoji}>✅</Text>
              <Text style={styles.emptyTitle}>Kaikki uutiset luettu</Text>
              <Text style={styles.emptyBody}>
                Olet käynyt läpi kaikki tämän päivän uutiset! Palaa myöhemmin, kun uusia uutisia ilmestyy.
              </Text>
              <TouchableOpacity style={styles.primaryButton} onPress={handleShowMore} disabled={busy}>
                {busy ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.primaryButtonText}>Hae lisää uutisia</Text>
                )}
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.emptyEmoji}>🤔</Text>
              <Text style={styles.emptyTitle}>Ei uutisia juuri nyt</Text>
              <Text style={styles.emptyBody}>
                Syötteessä ei ole uusia uutisia. Kokeile päivittää tai palaa hetken päästä.
              </Text>
              <TouchableOpacity style={styles.primaryButton} onPress={handleShowMore} disabled={busy}>
                {busy ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.primaryButtonText}>Päivitä uutiset</Text>
                )}
              </TouchableOpacity>
            </>
          )}
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
    paddingHorizontal: 32,
  },
  loadingText: {
    color: '#9ca3af',
    fontSize: 15,
    marginTop: 14,
    fontFamily: 'Georgia',
  },
  errorScreenTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a1a1a',
    fontFamily: 'Georgia',
    marginBottom: 8,
    textAlign: 'center',
  },
  errorScreenBody: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 28,
    paddingVertical: 12,
    borderRadius: 2,
  },
  retryButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.5,
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
  emptyEmoji: {
    fontSize: 64,
    marginBottom: 8,
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
