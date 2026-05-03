import { useState } from 'react'
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native'
import { updatePreferences, fetchReenrichStatus } from '../api'

// Single source of truth for all categories — used in both lists
export const ALL_TOPICS = [
  { id: 'politiikka',    label: 'Politiikka' },
  { id: 'talous',        label: 'Talous' },
  { id: 'teknologia',    label: 'Teknologia' },
  { id: 'urheilu',       label: 'Urheilu' },
  { id: 'kulttuuri',     label: 'Kulttuuri' },
  { id: 'terveys',       label: 'Terveys' },
  { id: 'ympäristö',     label: 'Ympäristö' },
  { id: 'tiede',         label: 'Tiede' },
  { id: 'turvallisuus',  label: 'Turvallisuus' },
  { id: 'koulutus',      label: 'Koulutus' },
  { id: 'kansainväliset',label: 'Kansainväliset' },
  { id: 'viihde',        label: 'Viihde' },
  { id: 'celebrity',     label: 'Julkkikset' },
  { id: 'rikokset',      label: 'Rikokset' },
  { id: 'onnettomuudet', label: 'Onnettomuudet' },
  { id: 'sää',           label: 'Sää' },
]

export const LOCAL_CITIES = {
  tampere: 'Tampere',
  oulu: 'Oulu',
  turku: 'Turku',
  helsinki: 'Helsinki',
  jyvaskyla: 'Jyväskylä',
  kuopio: 'Kuopio',
  hameenlinna: 'Hämeenlinna',
  lappeenranta: 'Lappeenranta',
}

export const ALL_SOURCES = [
  'yle.fi',
  'hs.fi',
  'iltalehti.fi',
  'is.fi',
  'verkkouutiset.fi',
  'uusisuomi.fi',
  'maaseuduntulevaisuus.fi',
  'kauppalehti.fi',
  'talouselama.fi',
  'arvopaperi.fi',
  'mikrobitti.fi',
  'tekniikkatalous.fi',
  'aamulehti.fi',
  'kaleva.fi',
  'satakunnankansa.fi',
  'bbc.co.uk',
  'nytimes.com',
  'theguardian.com',
  'washingtonpost.com',
  'aljazeera.com',
  'reutersagency.com',
]

const NEWS_SCOPES = [
  { id: 'suomi',       label: 'Suomi' },
  { id: 'maailma',     label: 'Maailma' },
  { id: 'paikalliset', label: 'Paikalliset' },
]

const TONE_OPTIONS = [
  { id: 'all',             icon: '🌤',  label: 'Kaikki uutiset',       desc: 'Näytä kaikki' },
  { id: 'neutral_positive', icon: '⛅', label: 'Ei raskaita',           desc: 'Piilota negatiiviset' },
  { id: 'positive',        icon: '☀️',  label: 'Vain hyvät uutiset',   desc: 'Vain positiiviset' },
]

export default function PreferencesPanel({ preferences, onSaved }) {
  const { width } = useWindowDimensions()
  const panelWidth = Math.min(width - (width < 520 ? 24 : 40), 760)

  const [interests, setInterests] = useState(new Set(preferences.interests || []))
  const [dislikes, setDislikes]   = useState(new Set(preferences.disliked_topics || []))
  const [scope, setScope]         = useState(new Set(preferences.news_scope || ['suomi', 'maailma']))
  const [city, setCity]           = useState(preferences.local_city || '')
  const [hidePaywall, setHidePaywall] = useState(preferences.hide_paywall !== false)
  const [excludedSources, setExcludedSources] = useState(new Set(preferences.excluded_sources || []))
  const [toneFilter, setToneFilter] = useState(preferences.tone_filter || 'all')
  const [saving, setSaving]       = useState(false)
  const [status, setStatus]       = useState('')
  const [unsaved, setUnsaved]     = useState(false)

  function toggleInterest(id) {
    const next = new Set(interests)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
      const nd = new Set(dislikes)
      nd.delete(id)
      setDislikes(nd)
    }
    setInterests(next)
    setUnsaved(true)
  }

  function toggleDislike(id) {
    const next = new Set(dislikes)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
      const ni = new Set(interests)
      ni.delete(id)
      setInterests(ni)
    }
    setDislikes(next)
    setUnsaved(true)
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
    setUnsaved(true)
  }

  function toggleSource(id) {
    const next = new Set(excludedSources)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setExcludedSources(next)
    setUnsaved(true)
  }

  async function pollReenrich() {
    const MAX_WAIT = 60_000
    const start = Date.now()
    let first = true
    while (Date.now() - start < MAX_WAIT) {
      await new Promise((r) => setTimeout(r, first ? 200 : 500))
      first = false
      try {
        const s = await fetchReenrichStatus()
        if (s.state === 'done') {
          setStatus(`Valmis – ${s.enriched} artikkelia pisteytetty`)
          setSaving(false)
          onSaved?.()
          return
        }
        setStatus(`Pisteytetään... (${s.enriched ?? 0})`)
      } catch (_) {}
    }
    setStatus('Pisteytys kesti liian kauan')
    setSaving(false)
  }

  async function save() {
    setSaving(true)
    setStatus('Tallennetaan...')
    try {
      await updatePreferences({
        interests: [...interests],
        disliked_topics: [...dislikes],
        news_scope: [...scope],
        local_city: city,
        hide_paywall: hidePaywall,
        excluded_sources: [...excludedSources],
        tone_filter: toneFilter,
      })
      setUnsaved(false)
      setStatus('Tallennettu – pisteytetään...')
      pollReenrich()
    } catch (e) {
      setStatus(`Virhe: ${e.message}`)
      setSaving(false)
    }
  }

  const showCityPicker = scope.has('paikalliset')

  return (
    <ScrollView style={styles.panel} contentContainerStyle={styles.outerContent}>
      <View style={[styles.content, { width: panelWidth }]}>

        <Text style={styles.sectionLabel}>Uutisalue</Text>
        <View style={styles.chips}>
          {NEWS_SCOPES.map((s) => (
            <TouchableOpacity
              key={s.id}
              style={[styles.chip, scope.has(s.id) && styles.chipScope]}
              onPress={() => toggleScope(s.id)}
            >
              <Text style={[styles.chipText, scope.has(s.id) && styles.chipTextActive]}>
                {s.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {showCityPicker && (
          <View>
            <Text style={styles.subLabel}>Valitse kaupunki</Text>
            <View style={styles.chips}>
              {Object.entries(LOCAL_CITIES).map(([id, label]) => (
                <TouchableOpacity
                  key={id}
                  style={[styles.chip, city === id && styles.chipScope]}
                  onPress={() => { setCity(id); setUnsaved(true) }}
                >
                  <Text style={[styles.chipText, city === id && styles.chipTextActive]}>
                    {label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        <Text style={styles.sectionLabel}>Kiinnostaa</Text>
        <Text style={styles.hint}>Valitseminen poistaa aiheen automaattisesti ei-kiinnosta-listalta</Text>
        <View style={styles.chips}>
          {ALL_TOPICS.map((c) => {
            const active  = interests.has(c.id)
            const blocked = dislikes.has(c.id)
            return (
              <TouchableOpacity
                key={c.id}
                style={[styles.chip, active && styles.chipActive, blocked && styles.chipBlocked]}
                onPress={() => !blocked && toggleInterest(c.id)}
                disabled={blocked}
              >
                <Text style={[styles.chipText, active && styles.chipTextActive, blocked && styles.chipTextBlocked]}>
                  {c.label}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <Text style={styles.sectionLabel}>Ei kiinnosta</Text>
        <Text style={styles.hint}>Valitseminen poistaa aiheen kiinnostaa-listalta ja laskee aiheen pisteitä, mutta ei piilota artikkeleita</Text>
        <View style={styles.chips}>
          {ALL_TOPICS.map((c) => {
            const active  = dislikes.has(c.id)
            const blocked = interests.has(c.id)
            return (
              <TouchableOpacity
                key={c.id}
                style={[styles.chip, styles.chipDislikeBase, active && styles.chipDislikeActive, blocked && styles.chipBlocked]}
                onPress={() => !blocked && toggleDislike(c.id)}
                disabled={blocked}
              >
                <Text style={[styles.chipText, active && styles.chipTextActive, blocked && styles.chipTextBlocked]}>
                  {c.label}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        {unsaved && <Text style={styles.unsaved}>Tallentamattomat muutokset</Text>}

        <Text style={styles.sectionLabel}>Uutisten tunnelma</Text>
        <Text style={styles.hint}>Vaikuttaa siihen, minkälaiset uutiset nousevat briefingiin</Text>
        <View style={styles.toneRow}>
          {TONE_OPTIONS.map((opt) => {
            const active = toneFilter === opt.id
            return (
              <TouchableOpacity
                key={opt.id}
                style={[styles.toneBtn, active && styles.toneBtnActive]}
                onPress={() => { setToneFilter(opt.id); setUnsaved(true) }}
                activeOpacity={0.7}
              >
                <Text style={styles.toneIcon}>{opt.icon}</Text>
                <Text style={[styles.toneBtnLabel, active && styles.toneBtnLabelActive]}>{opt.label}</Text>
                <Text style={[styles.toneBtnDesc, active && styles.toneBtnDescActive]}>{opt.desc}</Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <Text style={styles.sectionLabel}>Muut asetukset</Text>
        <TouchableOpacity
          style={styles.toggleRow}
          onPress={() => { setHidePaywall((v) => !v); setUnsaved(true) }}
          activeOpacity={0.7}
        >
          <View style={styles.toggleInfo}>
            <Text style={styles.toggleLabel}>Piilota maksumuuriartikkelit</Text>
            <Text style={styles.toggleDesc}>Artikkelit joita ei voi lukea ilmaiseksi piilotetaan</Text>
          </View>
          <View style={[styles.toggleSwitch, hidePaywall && styles.toggleSwitchOn]}>
            <View style={[styles.toggleThumb, hidePaywall && styles.toggleThumbOn]} />
          </View>
        </TouchableOpacity>

        <Text style={styles.sectionLabel}>Uutislähteet</Text>
        <Text style={styles.hint}>Valitsemasi lähteet piilotetaan – poista valinta näyttääksesi kaikki</Text>
        <View style={styles.chips}>
          {ALL_SOURCES.map((src) => {
            const excluded = excludedSources.has(src)
            return (
              <TouchableOpacity
                key={src}
                style={[styles.chip, excluded && styles.chipDislikeActive]}
                onPress={() => toggleSource(src)}
              >
                <Text style={[styles.chipText, excluded && styles.chipTextActive]}>
                  {src}
                </Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <TouchableOpacity
          style={[styles.saveBtn, (!unsaved || saving) && styles.saveBtnDisabled]}
          onPress={save}
          disabled={!unsaved || saving}
        >
          {saving ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.saveBtnText}>Tallenna asetukset</Text>
          )}
        </TouchableOpacity>

        {status ? <Text style={styles.status}>{status}</Text> : null}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  panel: { flex: 1, width: '100%', backgroundColor: '#ffffff' },
  outerContent: { alignItems: 'center', paddingVertical: 12, paddingBottom: 40 },
  content: { padding: 16, paddingBottom: 40, width: '100%', maxWidth: 760 },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#9ca3af',
    textTransform: 'uppercase',
    letterSpacing: 2,
    marginTop: 20,
    marginBottom: 4,
  },
  subLabel: { fontSize: 10, color: '#9ca3af', letterSpacing: 1, marginBottom: 6, marginTop: 8 },
  hint: { fontSize: 11, color: '#c4c4c4', marginBottom: 8, fontStyle: 'italic' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: {
    borderRadius: 2,
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#ffffff',
    borderWidth: 1.5,
    borderColor: '#d1d5db',
  },
  chipActive:        { backgroundColor: '#1e3a8a', borderColor: '#1e3a8a' },
  chipScope:         { backgroundColor: '#1a1a1a', borderColor: '#1a1a1a' },
  chipDislikeBase:   { borderColor: '#d1d5db' },
  chipDislikeActive: { backgroundColor: '#991b1b', borderColor: '#991b1b' },
  chipBlocked:       { borderColor: '#f0f0f0', backgroundColor: '#f9f9f9', opacity: 0.45 },
  chipText:          { fontSize: 13, color: '#4a4a4a', fontWeight: '600' },
  chipTextActive:    { color: '#fff', fontWeight: '700' },
  chipTextBlocked:   { color: '#bbb' },
  unsaved: {
    marginTop: 12, fontSize: 12, color: '#92400e',
    textAlign: 'center', fontWeight: '600', letterSpacing: 0.3,
  },
  toggleRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    marginTop: 12, paddingVertical: 12, paddingHorizontal: 12,
    borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 4,
  },
  toggleInfo: { flex: 1, marginRight: 16 },
  toggleLabel: { fontSize: 14, fontWeight: '600', color: '#1a1a1a' },
  toggleDesc: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  toggleSwitch: {
    width: 44, height: 24, borderRadius: 12, backgroundColor: '#d1d5db',
    justifyContent: 'center', paddingHorizontal: 2,
  },
  toggleSwitchOn: { backgroundColor: '#1a1a1a' },
  toggleThumb: {
    width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 2, shadowOffset: { width: 0, height: 1 },
  },
  toggleThumbOn: { alignSelf: 'flex-end' },
  saveBtn: { marginTop: 20, backgroundColor: '#1a1a1a', borderRadius: 2, paddingVertical: 14, alignItems: 'center' },
  saveBtnDisabled: { backgroundColor: '#d1d5db' },
  saveBtnText: { color: '#fff', fontSize: 15, fontWeight: '700', letterSpacing: 0.3 },
  status: { marginTop: 10, fontSize: 13, color: '#9ca3af', textAlign: 'center' },
  toneRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  toneBtn: {
    flex: 1, borderWidth: 1.5, borderColor: '#d1d5db', borderRadius: 4,
    paddingVertical: 10, paddingHorizontal: 8, alignItems: 'center',
  },
  toneBtnActive: { borderColor: '#1a1a1a', backgroundColor: '#1a1a1a' },
  toneIcon: { fontSize: 20, marginBottom: 4 },
  toneBtnLabel: { fontSize: 12, fontWeight: '700', color: '#1a1a1a', textAlign: 'center' },
  toneBtnLabelActive: { color: '#fff' },
  toneBtnDesc: { fontSize: 10, color: '#9ca3af', textAlign: 'center', marginTop: 2 },
  toneBtnDescActive: { color: '#d1d5db' },
})
