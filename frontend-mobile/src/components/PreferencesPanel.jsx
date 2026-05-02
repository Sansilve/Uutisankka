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

const INTERESTS = [
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

const DISLIKES = [
  { id: 'viihde', label: 'Viihde' },
  { id: 'celebrity', label: 'Julkkikset' },
  { id: 'urheilu', label: 'Urheilu' },
  { id: 'rikokset', label: 'Rikokset' },
  { id: 'onnettomuudet', label: 'Onnettomuudet' },
  { id: 'sää', label: 'Sää' },
]

export default function PreferencesPanel({ preferences, onSaved }) {
  const { width } = useWindowDimensions()
  const panelWidth = Math.min(width - (width < 520 ? 24 : 40), 760)
  const [interests, setInterests] = useState(new Set(preferences.interests))
  const [dislikes, setDislikes] = useState(new Set(preferences.disliked_topics))
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')
  const [unsaved, setUnsaved] = useState(false)

  function toggle(id, set, setFn) {
    const next = new Set(set)
    next.has(id) ? next.delete(id) : next.add(id)
    setFn(next)
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
      })
      setUnsaved(false)
      setStatus('Tallennettu – pisteytetään...')
      pollReenrich()
    } catch (e) {
      setStatus(`Virhe: ${e.message}`)
      setSaving(false)
    }
  }

  return (
    <ScrollView style={styles.panel} contentContainerStyle={styles.outerContent}>
      <View style={[styles.content, { width: panelWidth }]}> 
      <Text style={styles.sectionLabel}>Kiinnostaa</Text>
      <View style={styles.chips}>
        {INTERESTS.map((c) => (
          <TouchableOpacity
            key={c.id}
            style={[styles.chip, interests.has(c.id) && styles.chipActive]}
            onPress={() => toggle(c.id, interests, setInterests)}
          >
            <Text style={[styles.chipText, interests.has(c.id) && styles.chipTextActive]}>
              {c.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.sectionLabel}>Ei kiinnosta</Text>
      <View style={styles.chips}>
        {DISLIKES.map((c) => (
          <TouchableOpacity
            key={c.id}
            style={[styles.chip, styles.chipDislike, dislikes.has(c.id) && styles.chipDislikeActive]}
            onPress={() => toggle(c.id, dislikes, setDislikes)}
          >
            <Text style={[styles.chipText, dislikes.has(c.id) && styles.chipTextActive]}>
              {c.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {unsaved && (
        <Text style={styles.unsaved}>Tallentamattomat muutokset</Text>
      )}

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
  panel: { flex: 1, width: '100%', backgroundColor: '#141420', overflow: 'hidden' },
  outerContent: { alignItems: 'center', paddingVertical: 12, paddingBottom: 40 },
  content: { padding: 16, paddingBottom: 40, width: '100%', maxWidth: 760 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 16,
    marginBottom: 8,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  chip: {
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#252538',
    borderWidth: 1,
    borderColor: '#3a3a58',
  },
  chipActive: { backgroundColor: '#7c3aed', borderColor: '#7c3aed' },
  chipDislike: { borderColor: '#7f1d1d' },
  chipDislikeActive: { backgroundColor: '#7f1d1d', borderColor: '#7f1d1d' },
  chipText: { fontSize: 13, color: '#a0a0c0' },
  chipTextActive: { color: '#fff', fontWeight: '600' },
  unsaved: {
    marginTop: 12,
    fontSize: 13,
    color: '#f59e0b',
    textAlign: 'center',
  },
  saveBtn: {
    marginTop: 16,
    backgroundColor: '#7c3aed',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnDisabled: { backgroundColor: '#3a3a58' },
  saveBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  status: {
    marginTop: 10,
    fontSize: 13,
    color: '#888',
    textAlign: 'center',
  },
})
