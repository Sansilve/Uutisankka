import { useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native'
import { updatePreferences } from '../api'
import { ALL_TOPICS, LOCAL_CITIES } from './PreferencesPanel'

const NEWS_SCOPES = [
  { id: 'suomi',       label: 'Suomi',       desc: 'Kotimaiset uutiset' },
  { id: 'maailma',     label: 'Maailma',     desc: 'Kansainväliset uutiset' },
  { id: 'paikalliset', label: 'Paikalliset', desc: 'Oman kaupungin uutiset' },
]

const STEPS = ['welcome', 'scope', 'interests', 'dislikes']

export default function OnboardingScreen({ onComplete }) {
  const { width } = useWindowDimensions()
  const contentWidth = Math.min(width - 32, 560)

  const [step, setStep]           = useState(0)
  const [interests, setInterests] = useState(new Set(['politiikka', 'talous', 'teknologia']))
  const [dislikes, setDislikes]   = useState(new Set())
  const [scope, setScope]         = useState(new Set(['suomi', 'maailma']))
  const [city, setCity]           = useState('')
  const [saving, setSaving]       = useState(false)
  const [saveError, setSaveError] = useState(null)

  function toggleInterest(id) {
    const next = new Set(interests)
    next.has(id) ? next.delete(id) : next.add(id)
    if (next.has(id)) {
      const nd = new Set(dislikes)
      nd.delete(id)
      setDislikes(nd)
    }
    setInterests(next)
  }

  function toggleDislike(id) {
    const next = new Set(dislikes)
    next.has(id) ? next.delete(id) : next.add(id)
    if (next.has(id)) {
      const ni = new Set(interests)
      ni.delete(id)
      setInterests(ni)
    }
    setDislikes(next)
  }

  function toggleScope(id) {
    const next = new Set(scope)
    if (next.has(id)) {
      if (next.size > 1) {
        next.delete(id)
        if (id === 'paikalliset') setCity('')
      }
    } else {
      next.add(id)
    }
    setScope(next)
  }

  async function finish() {
    setSaving(true)
    setSaveError(null)
    try {
      await updatePreferences({
        interests: [...interests],
        disliked_topics: [...dislikes],
        news_scope: [...scope],
        local_city: city,
      })
      onComplete()
    } catch (e) {
      setSaveError(e?.message || 'Tallennus epäonnistui. Yritä uudelleen.')
      setSaving(false)
    }
  }

  const currentStep = STEPS[step]
  const totalSteps = STEPS.length - 1 // exclude welcome

  return (
    <View style={styles.root}>
      <ScrollView contentContainerStyle={[styles.scroll, { paddingHorizontal: (width - contentWidth) / 2 }]}>

        {/* Masthead */}
        <Text style={styles.brand}>🦆 UutisAnkka</Text>
        <View style={styles.brandRule} />

        {/* Step indicator (dots for steps 1-3, hidden on welcome) */}
        <View style={styles.stepDots}>
          {step > 0 && STEPS.slice(1).map((_, i) => (
            <View key={i} style={[styles.dot, step - 1 >= i && styles.dotActive]} />
          ))}
        </View>

        {/* ── Step 0: Welcome ── */}
        {currentStep === 'welcome' && (
          <View style={styles.stepContent}>
            <Text style={styles.eyebrow}>TERVETULOA</Text>
            <Text style={styles.heading}>Päivittäinen{'\n'}uutiskierros{'\n'}sinulle.</Text>
            <Text style={styles.body}>
              UutisAnkka kokoaa joka päivä parhaat uutiset kiinnostustesi mukaan.
              Käydään läpi muutama kysymys niin päästään heti asiaan.
            </Text>
            <Pressable style={styles.primaryBtn} onPress={() => setStep(1)}>
              <Text style={styles.primaryBtnText}>Aloita →</Text>
            </Pressable>
          </View>
        )}

        {/* ── Step 1: Scope ── */}
        {currentStep === 'scope' && (
          <View style={styles.stepContent}>
            <Text style={styles.eyebrow}>VAIHE 1 / {totalSteps}</Text>
            <Text style={styles.heading}>Mistä uutiset?</Text>
            <Text style={styles.body}>Valitse alueet joista haluat uutisia.</Text>

            <View style={styles.scopeRow}>
              {NEWS_SCOPES.map((s) => (
                <Pressable
                  key={s.id}
                  style={[styles.scopeCard, scope.has(s.id) && styles.scopeCardActive]}
                  onPress={() => toggleScope(s.id)}
                >
                  <Text style={[styles.scopeLabel, scope.has(s.id) && styles.scopeLabelActive]}>
                    {s.label}
                  </Text>
                  <Text style={[styles.scopeDesc, scope.has(s.id) && styles.scopeDescActive]}>
                    {s.desc}
                  </Text>
                </Pressable>
              ))}
            </View>

            {scope.has('paikalliset') && (
              <View>
                <Text style={styles.sectionLabel}>Kaupunki</Text>
                <View style={styles.chips}>
                  {Object.entries(LOCAL_CITIES).map(([id, label]) => (
                    <Pressable
                      key={id}
                      style={[styles.chip, city === id && styles.chipActive]}
                      onPress={() => setCity(id)}
                    >
                      <Text style={[styles.chipText, city === id && styles.chipTextActive]}>
                        {label}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            )}

            <View style={styles.navRow}>
              <Pressable style={styles.secondaryBtn} onPress={() => setStep(0)}>
                <Text style={styles.secondaryBtnText}>← Takaisin</Text>
              </Pressable>
              <Pressable style={styles.primaryBtn} onPress={() => setStep(2)}>
                <Text style={styles.primaryBtnText}>Seuraava →</Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* ── Step 2: Interests ── */}
        {currentStep === 'interests' && (
          <View style={styles.stepContent}>
            <Text style={styles.eyebrow}>VAIHE 2 / {totalSteps}</Text>
            <Text style={styles.heading}>Mistä aiheista{'\n'}pidät?</Text>
            <Text style={styles.body}>Valitse vähintään yksi aihe. Voit muuttaa valintoja myöhemmin.</Text>
            <View style={styles.chips}>
              {ALL_TOPICS.map((c) => {
                const active  = interests.has(c.id)
                const blocked = dislikes.has(c.id)
                return (
                  <Pressable
                    key={c.id}
                    style={[styles.chip, active && styles.chipActive, blocked && styles.chipBlocked]}
                    onPress={() => !blocked && toggleInterest(c.id)}
                  >
                    <Text style={[styles.chipText, active && styles.chipTextActive]}>
                      {c.label}
                    </Text>
                  </Pressable>
                )
              })}
            </View>
            <View style={styles.navRow}>
              <Pressable style={styles.secondaryBtn} onPress={() => setStep(1)}>
                <Text style={styles.secondaryBtnText}>← Takaisin</Text>
              </Pressable>
              <Pressable
                style={[styles.primaryBtn, interests.size === 0 && styles.primaryBtnDisabled]}
                onPress={() => interests.size > 0 && setStep(3)}
              >
                <Text style={styles.primaryBtnText}>Seuraava →</Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* ── Step 3: Dislikes ── */}
        {currentStep === 'dislikes' && (
          <View style={styles.stepContent}>
            <Text style={styles.eyebrow}>VAIHE 3 / {totalSteps}</Text>
            <Text style={styles.heading}>Mitä haluat{'\n'}välttää?</Text>
            <Text style={styles.body}>
              Valinnaiset. Kiinnostaa-listalla olevat aiheet eivät ole valittavissa.
            </Text>
            <View style={styles.chips}>
              {ALL_TOPICS.map((c) => {
                const active  = dislikes.has(c.id)
                const blocked = interests.has(c.id)
                return (
                  <Pressable
                    key={c.id}
                    style={[styles.chip, styles.chipDislikeBase, active && styles.chipDislikeActive, blocked && styles.chipBlocked]}
                    onPress={() => !blocked && toggleDislike(c.id)}
                  >
                    <Text style={[styles.chipText, active && styles.chipTextActive]}>
                      {c.label}
                    </Text>
                  </Pressable>
                )
              })}
            </View>

            <View style={styles.navRow}>
              <Pressable style={styles.secondaryBtn} onPress={() => setStep(2)}>
                <Text style={styles.secondaryBtnText}>← Takaisin</Text>
              </Pressable>
              <Pressable
                style={[styles.primaryBtn, saving && styles.primaryBtnDisabled]}
                onPress={finish}
                disabled={saving}
              >
                {saving
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.primaryBtnText}>Aloita lukeminen →</Text>
                }
              </Pressable>
            </View>
            {saveError ? (
              <Text style={styles.saveError}>{saveError}</Text>
            ) : null}
          </View>
        )}

      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#ffffff' },
  scroll: { paddingTop: 60, paddingBottom: 60 },
  brand: { fontSize: 28, fontFamily: 'Georgia', fontWeight: '700', color: '#1a1a1a', textAlign: 'center' },
  brandRule: { height: 3, backgroundColor: '#FFB700', marginVertical: 16, marginHorizontal: 0 },
  stepDots: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginBottom: 32 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#e5e5e5' },
  dotActive: { backgroundColor: '#1a1a1a' },
  stepContent: { gap: 0 },
  eyebrow: {
    fontSize: 10, fontWeight: '700', letterSpacing: 2,
    textTransform: 'uppercase', color: '#FFB700', marginBottom: 8,
  },
  heading: {
    fontSize: 36, fontFamily: 'Georgia', fontWeight: '700',
    color: '#1a1a1a', lineHeight: 42, marginBottom: 16,
  },
  body: { fontSize: 15, color: '#4a4a4a', lineHeight: 22, marginBottom: 24 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 24 },
  chip: {
    borderRadius: 2, paddingHorizontal: 12, paddingVertical: 7,
    backgroundColor: '#ffffff', borderWidth: 1.5, borderColor: '#d1d5db',
  },
  chipActive:        { backgroundColor: '#1e3a8a', borderColor: '#1e3a8a' },
  chipDislikeBase:   { borderColor: '#d1d5db' },
  chipDislikeActive: { backgroundColor: '#991b1b', borderColor: '#991b1b' },
  chipBlocked:       { borderColor: '#f0f0f0', backgroundColor: '#f9f9f9', opacity: 0.4 },
  chipText:          { fontSize: 13, color: '#4a4a4a', fontWeight: '600' },
  chipTextActive:    { color: '#fff', fontWeight: '700' },
  sectionLabel: {
    fontSize: 10, fontWeight: '700', color: '#9ca3af',
    textTransform: 'uppercase', letterSpacing: 2, marginBottom: 10,
  },
  scopeRow: { flexDirection: 'row', gap: 8, marginBottom: 24, flexWrap: 'wrap' },
  scopeCard: {
    flex: 1, minWidth: 100, borderWidth: 1.5, borderColor: '#d1d5db',
    borderRadius: 2, padding: 12,
  },
  scopeCardActive: { borderColor: '#1a1a1a', backgroundColor: '#1a1a1a' },
  scopeLabel:      { fontSize: 14, fontWeight: '700', color: '#1a1a1a' },
  scopeLabelActive:{ color: '#fff' },
  scopeDesc:       { fontSize: 11, color: '#9ca3af', marginTop: 2 },
  scopeDescActive: { color: '#ccc' },
  navRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8, gap: 12 },
  primaryBtn: {
    flex: 1, backgroundColor: '#1a1a1a', borderRadius: 2,
    paddingVertical: 14, alignItems: 'center',
  },
  primaryBtnDisabled: { backgroundColor: '#d1d5db' },
  primaryBtnText: { color: '#fff', fontSize: 15, fontWeight: '700', letterSpacing: 0.3 },
  secondaryBtn: {
    borderWidth: 1.5, borderColor: '#1a1a1a', borderRadius: 2,
    paddingVertical: 14, paddingHorizontal: 20, alignItems: 'center',
  },
  secondaryBtnText: { color: '#1a1a1a', fontSize: 14, fontWeight: '600' },
  saveError: {
    marginTop: 12, color: '#b91c1c', fontSize: 13, textAlign: 'center', lineHeight: 18,
  },
})
