import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'

// ── Bias scale ─────────────────────────────────────────────────────────────
const BIAS_STEPS = [
  { score: -3, label: 'Ääriv.\nvasen', short: 'ÄV' },
  { score: -2, label: 'Vasen', short: 'V' },
  { score: -1, label: 'Vasen-\nkeskusta', short: 'VK' },
  { score:  0, label: 'Keskusta', short: 'K' },
  { score:  1, label: 'Oikea-\nkeskusta', short: 'OK' },
  { score:  2, label: 'Oikea', short: 'O' },
  { score:  3, label: 'Ääriv.\noikea', short: 'ÄO' },
]

function biasColor(score) {
  if (score <= -3) return '#7c3aed'
  if (score === -2) return '#2563eb'
  if (score === -1) return '#0ea5e9'
  if (score === 0)  return '#16a34a'
  if (score === 1)  return '#f59e0b'
  if (score === 2)  return '#ea580c'
  return '#dc2626'
}

// ── Factual rating ──────────────────────────────────────────────────────────
const RATING_META = {
  'VERY HIGH':     { color: '#15803d', bg: '#dcfce7', fi: 'Erittäin korkea', icon: '✅' },
  'HIGH':          { color: '#16a34a', bg: '#dcfce7', fi: 'Korkea',          icon: '✅' },
  'MOSTLY FACTUAL':{ color: '#ca8a04', bg: '#fef9c3', fi: 'Pääosin asiat.',  icon: '⚠️' },
  'MIXED':         { color: '#d97706', bg: '#fef3c7', fi: 'Vaihteleva',      icon: '⚠️' },
  'LOW':           { color: '#dc2626', bg: '#fee2e2', fi: 'Heikko',          icon: '🚫' },
  'VERY LOW':      { color: '#b91c1c', bg: '#fee2e2', fi: 'Erittäin heikko', icon: '🚫' },
  'FAKE NEWS':     { color: '#7f1d1d', bg: '#fca5a5', fi: 'Fake news',       icon: '❌' },
}

function getRatingMeta(rating) {
  return RATING_META[(rating || '').toUpperCase()] || { color: '#6b7280', bg: '#f3f4f6', fi: 'Tuntematon', icon: '❓' }
}

// ── Component ───────────────────────────────────────────────────────────────
export default function SourceTrustModal({ visible, onClose, story }) {
  if (!story) return null

  const biasScore  = story.bias_score  ?? 0
  const factual    = (story.factual_rating || '').toUpperCase()
  const trustScore = story.trust_score ?? null
  const source     = story.source || ''
  const ratingMeta = getRatingMeta(factual)

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>

          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Lähteen luotettavuus</Text>
            <Pressable onPress={onClose} style={styles.closeBtn} hitSlop={12}>
              <Text style={styles.closeBtnText}>✕</Text>
            </Pressable>
          </View>

          <Text style={styles.sourceName} numberOfLines={2}>{source}</Text>

          {/* Factual rating pill */}
          <View style={[styles.ratingPill, { backgroundColor: ratingMeta.bg }]}>
            <Text style={[styles.ratingIcon]}>{ratingMeta.icon}</Text>
            <View>
              <Text style={styles.ratingLabel}>Faktuaalisuus</Text>
              <Text style={[styles.ratingValue, { color: ratingMeta.color }]}>
                {ratingMeta.fi}
              </Text>
            </View>
            {trustScore !== null && (
              <Text style={[styles.trustBadge, { color: ratingMeta.color }]}>
                {trustScore}/100
              </Text>
            )}
          </View>

          {/* Bias scale */}
          <Text style={styles.sectionLabel}>Poliittinen suuntaus</Text>
          <View style={styles.biasScale}>
            {BIAS_STEPS.map((step) => {
              const active = step.score === biasScore
              return (
                <View key={step.score} style={styles.biasStep}>
                  <View
                    style={[
                      styles.biasNode,
                      { backgroundColor: active ? biasColor(biasScore) : '#e5e7eb' },
                      active && styles.biasNodeActive,
                    ]}
                  >
                    <Text style={[styles.biasNodeText, active && styles.biasNodeTextActive]}>
                      {step.short}
                    </Text>
                  </View>
                  {active && (
                    <Text style={[styles.biasActiveLabel, { color: biasColor(biasScore) }]}>
                      {step.label}
                    </Text>
                  )}
                </View>
              )
            })}
          </View>
          <View style={styles.biasBar}>
            <Text style={styles.biasBarLeft}>← Vasen</Text>
            <Text style={styles.biasBarRight}>Oikea →</Text>
          </View>

          {/* MBFC credit */}
          <Text style={styles.credit}>
            Lähdearviointi perustuu MediaBiasFactCheck.com-yhteisödataan.
            Arviot ovat suuntaa-antavia.
          </Text>

          <Pressable style={styles.doneBtn} onPress={onClose}>
            <Text style={styles.doneBtnText}>Sulje</Text>
          </Pressable>

        </Pressable>
      </Pressable>
    </Modal>
  )
}

// ── Styles ──────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 1,
    color: '#6b7280',
    textTransform: 'uppercase',
  },
  closeBtn: {
    padding: 4,
  },
  closeBtnText: {
    fontSize: 18,
    color: '#9ca3af',
  },
  sourceName: {
    fontSize: 17,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  ratingPill: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 12,
    padding: 14,
    gap: 12,
    marginBottom: 20,
  },
  ratingIcon: {
    fontSize: 24,
  },
  ratingLabel: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  ratingValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  trustBadge: {
    marginLeft: 'auto',
    fontSize: 20,
    fontWeight: '800',
  },
  sectionLabel: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  biasScale: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  biasStep: {
    alignItems: 'center',
    flex: 1,
  },
  biasNode: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  biasNodeActive: {
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  biasNodeText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#9ca3af',
  },
  biasNodeTextActive: {
    color: '#fff',
  },
  biasActiveLabel: {
    fontSize: 9,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 4,
  },
  biasBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  biasBarLeft: {
    fontSize: 10,
    color: '#9ca3af',
  },
  biasBarRight: {
    fontSize: 10,
    color: '#9ca3af',
  },
  credit: {
    fontSize: 11,
    color: '#9ca3af',
    textAlign: 'center',
    lineHeight: 16,
    marginBottom: 16,
  },
  doneBtn: {
    backgroundColor: '#111827',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  doneBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
})
