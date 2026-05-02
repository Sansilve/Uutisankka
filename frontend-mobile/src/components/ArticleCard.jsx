import { useMemo, useRef, useState } from 'react'
import {
  Animated,
  Linking,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native'

// Dark, muted newspaper-style topic colors
const TOPIC_COLORS = {
  technology:    '#1e3a8a',
  teknologia:    '#1e3a8a',
  science:       '#3b0764',
  tiede:         '#3b0764',
  politics:      '#991b1b',
  politiikka:    '#991b1b',
  economy:       '#065f46',
  talous:        '#065f46',
  health:        '#064e3b',
  terveys:       '#064e3b',
  culture:       '#831843',
  kulttuuri:     '#831843',
  sports:        '#14532d',
  urheilu:       '#14532d',
  environment:   '#052e16',
  celebrity:     '#581c87',
  weather:       '#0c4a6e',
  crime:         '#450a0a',
  transportation:'#1e3a5f',
  military:      '#1c1917',
  education:     '#1e1b4b',
}

const TOPIC_LABELS = {
  politics:      'Politiikka',
  politiikka:    'Politiikka',
  economy:       'Talous',
  talous:        'Talous',
  technology:    'Teknologia',
  teknologia:    'Teknologia',
  science:       'Tiede',
  tiede:         'Tiede',
  sports:        'Urheilu',
  urheilu:       'Urheilu',
  health:        'Terveys',
  terveys:       'Terveys',
  environment:   'Ympäristö',
  culture:       'Kulttuuri',
  kulttuuri:     'Kulttuuri',
  celebrity:     'Viihde',
  weather:       'Sää',
  crime:         'Rikos',
  transportation:'Liikenne',
  military:      'Puolustus',
  education:     'Koulutus',
}

function topicColor(topic) {
  return TOPIC_COLORS[topic] || '#374151'
}

function topicLabel(topic) {
  return TOPIC_LABELS[topic] || topic.charAt(0).toUpperCase() + topic.slice(1)
}

function todayFi() {
  return new Date().toLocaleDateString('fi-FI', {
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
  })
}


const SOURCE_NAMES = {
  'MT RSS feed': 'Maaseudun Tulevaisuus',
  'Iltalehti.fi tuoreimmat uutiset - Uutiset': 'Iltalehti',
  'Uutiset - Helsingin Sanomat': 'Helsingin Sanomat',
  'Uutiset - Ilta-Sanomat': 'Ilta-Sanomat',
  'Pääuutiset | Kauppalehti.fi': 'Kauppalehti',
  'Latest News From Euronews | Euronews RSS': 'Euronews',
  'Al Jazeera – Breaking News, World News and Video from Al Jazeera': 'Al Jazeera',
  'Al Jazeera â€“ Breaking News, World News and Video from Al Jazeera': 'Al Jazeera',
  'Yle Uutiset | Tuoreimmat': 'Yle Uutiset',
  'Yle Uutiset | Pääuutiset': 'Yle Uutiset',
  'Yle Urheilu | Tuoreimmat': 'Yle Urheilu',
  'NYT > World News': 'New York Times',
  'World news | The Guardian': 'The Guardian',
  'World | Deutsche Welle': 'Deutsche Welle',
  'NPR Topics: World': 'NPR',
  'TalouselÃ¤mÃ¤': 'Talouselämä',
  'PÃ¤Ã¤uutiset | Kauppalehti.fi': 'Kauppalehti',
  'Yle Uutiset | PÃ¤Ã¤uutiset': 'Yle Uutiset',
  ': World': 'Reuters',
}

function cleanSource(raw) {
  return SOURCE_NAMES[raw] || raw
}

function formatPubDate(isoStr) {
  if (!isoStr) return todayFi()
  const d = new Date(isoStr)
  const today = new Date()
  const isToday = d.toDateString() === today.toDateString()
  if (isToday) {
    return 'Tänään klo ' + d.toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('fi-FI', { day: 'numeric', month: 'numeric' }) +
    ' klo ' + d.toLocaleTimeString('fi-FI', { hour: '2-digit', minute: '2-digit' })
}

function bulletsToLead(bullets) {
  if (!bullets || bullets.length === 0) return ''
  return bullets.slice(0, 3).join(' ')
}

export default function ArticleCard({
  story,
  onDecision,
  disabled,
  progressText,
  progressWidth,
  onSurprise,
}) {
  const { width } = useWindowDimensions()
  const isCompact = width < 520
  const cardWidth = Math.min(width - (isCompact ? 16 : 32), 760)
  const swipeThreshold = width * 0.24
  const [expanded, setExpanded] = useState(false)
  const pan = useRef(new Animated.ValueXY()).current

  const rotate = pan.x.interpolate({
    inputRange: [-width, 0, width],
    outputRange: ['-10deg', '0deg', '10deg'],
  })

  const relevantOpacity = pan.x.interpolate({
    inputRange: [0, swipeThreshold],
    outputRange: [0, 1],
    extrapolate: 'clamp',
  })

  const dismissOpacity = pan.x.interpolate({
    inputRange: [-swipeThreshold, 0],
    outputRange: [1, 0],
    extrapolate: 'clamp',
  })

  const totalScore = useMemo(
    () => story.score_breakdown.items.reduce((sum, item) => sum + item.points, 0),
    [story.score_breakdown.items],
  )

  function settleCard(isRelevant) {
    const toX = isRelevant ? width * 1.2 : -width * 1.2
    Animated.timing(pan, {
      toValue: { x: toX, y: 0 },
      duration: 200,
      useNativeDriver: false,
    }).start(() => {
      pan.setValue({ x: 0, y: 0 })
      setExpanded(false)
      onDecision(isRelevant)
    })
  }

  const responder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, gesture) =>
          !disabled && (Math.abs(gesture.dx) > 8 || Math.abs(gesture.dy) > 8),
        onPanResponderMove: (_, gesture) => {
          pan.setValue({ x: gesture.dx, y: gesture.dy * 0.1 })
        },
        onPanResponderRelease: (_, gesture) => {
          if (gesture.dx > swipeThreshold) {
            settleCard(true)
            return
          }
          if (gesture.dx < -swipeThreshold) {
            settleCard(false)
            return
          }
          Animated.spring(pan, {
            toValue: { x: 0, y: 0 },
            friction: 5,
            useNativeDriver: false,
          }).start()
        },
      }),
    [disabled, pan, swipeThreshold],
  )

  const lead = bulletsToLead(story.summary.bullets) || 'Artikkeli on maksumuurin takana. Lue koko juttu lähteestä.'
  const scorePercent = `${Math.min(Math.max((totalScore / 20) * 100, 0), 100)}%`

  return (
    <View style={[styles.screen, { paddingHorizontal: isCompact ? 8 : 16 }]}>
      <View style={styles.topRow}>
        <View>
          <Text style={styles.eyebrow}>PÄIVÄN BRIEFING</Text>
          <Text style={[styles.progressLabel, isCompact && styles.progressLabelCompact]}>
            {progressText}
          </Text>
        </View>
        <TouchableOpacity style={styles.surpriseButton} onPress={onSurprise} disabled={disabled}>
          <Text style={styles.surpriseText}>✨ Yllätä minut</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: progressWidth }]} />
      </View>

      <View style={styles.cardStage}>
        <Animated.View
          style={[
            styles.card,
            { width: cardWidth },
            {
              transform: [
                { translateX: pan.x },
                { translateY: pan.y },
                { rotate },
              ],
            },
          ]}
          {...responder.panHandlers}
        >
          <Animated.View
            style={[styles.overlay, styles.overlayRelevant, { opacity: relevantOpacity }]}
          >
            <Text style={styles.overlayTextRelevant}>KIINNOSTAA</Text>
          </Animated.View>
          <Animated.View
            style={[styles.overlay, styles.overlayDismiss, { opacity: dismissOpacity }]}
          >
            <Text style={styles.overlayTextDismiss}>OHITAN</Text>
          </Animated.View>

          <View style={styles.metaRow}>
            <View style={styles.topicRow}>
              {story.topics.slice(0, 3).map((topic) => (
                <View key={topic} style={[styles.topicBadge, { borderColor: topicColor(topic) }]}>
                  <Text style={[styles.topicText, { color: topicColor(topic) }]}>
                    {topicLabel(topic)}
                  </Text>
                </View>
              ))}
              {story.is_paywall && (
                <View style={styles.paywallBadge}>
                  <Text style={styles.paywallBadgeText}>🔒 Maksumuuri</Text>
                </View>
              )}
            </View>
            <Text style={styles.dateText}>{formatPubDate(story.published_at)}</Text>
          </View>

          <Text style={[styles.title, isCompact && styles.titleCompact]}>{story.title}</Text>

          <View style={styles.titleRule} />

          <Text style={styles.sourceText}>📰 {cleanSource(story.source)}</Text>

          <Text style={[styles.lead, isCompact && styles.leadCompact]}>{lead}</Text>

          <Pressable style={styles.whyToggle} onPress={() => setExpanded((v) => !v)}>
            <Text style={styles.whyLabel}>💡 Miksi suosittelemme?</Text>
            <Text style={styles.whyCaret}>{expanded ? '▲' : '▼'}</Text>
          </Pressable>

          {expanded ? (
            <View style={styles.breakdownPanel}>
              {story.score_breakdown.items.length ? (
                story.score_breakdown.items.map((item, index) => (
                  <View key={`${item.reason}-${index}`} style={styles.breakdownRow}>
                    <Text style={styles.breakdownCheck}>✓</Text>
                    <Text style={styles.breakdownReason}>{item.reason}</Text>
                    <Text
                      style={[
                        styles.breakdownPoints,
                        item.points >= 0 ? styles.pointsPos : styles.pointsNeg,
                      ]}
                    >
                      {item.points > 0 ? '+' : ''}
                      {item.points.toFixed(1)}
                    </Text>
                  </View>
                ))
              ) : (
                <Text style={styles.emptyBreakdown}>Ei piste-erittelyä saatavilla.</Text>
              )}
              <View style={styles.breakdownDivider} />
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>YHTEENSÄ</Text>
                <Text style={styles.totalValue}>{totalScore.toFixed(1)}</Text>
              </View>
              <View style={styles.scoreTrack}>
                <View style={[styles.scoreFill, { width: scorePercent }]} />
              </View>
            </View>
          ) : null}

          <View style={styles.footer}>
            <TouchableOpacity
              style={[styles.actionButton, styles.dismissButton]}
              onPress={() => settleCard(false)}
              disabled={disabled}
            >
              <Text style={styles.dismissText}>👎  Ohita</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionButton, styles.relevantButton]}
              onPress={() => settleCard(true)}
              disabled={disabled}
            >
              <Text style={styles.relevantText}>Kiinnostaa  👍</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.linkButton} onPress={() => Linking.openURL(story.url)}>
            <Text style={styles.linkText}>Lue alkuperäinen →</Text>
          </TouchableOpacity>
        </Animated.View>
      </View>

      <Text style={styles.hint}>← Ohita · swipe · Kiinnostaa →</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    width: '100%',
    backgroundColor: '#ffffff',
    paddingTop: 10,
    paddingBottom: 10,
    overflow: 'hidden',
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
    paddingHorizontal: 2,
  },
  eyebrow: {
    color: '#9ca3af',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 2,
  },
  progressLabel: {
    color: '#1a1a1a',
    fontSize: 19,
    fontWeight: '800',
    fontFamily: 'Georgia',
    marginTop: 1,
  },
  progressLabelCompact: {
    fontSize: 15,
  },
  surpriseButton: {
    borderWidth: 1.5,
    borderColor: '#FFB700',
    borderRadius: 2,
    paddingHorizontal: 11,
    paddingVertical: 7,
    backgroundColor: '#fff',
  },
  surpriseText: {
    color: '#1a1a1a',
    fontSize: 12,
    fontWeight: '700',
  },
  progressTrack: {
    height: 3,
    backgroundColor: '#f3f4f6',
    marginBottom: 10,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#FFB700',
  },
  cardStage: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1.5,
    borderColor: '#d1d5db',
    borderRadius: 3,
    padding: 20,
    maxWidth: 760,
    shadowColor: '#000',
    shadowOpacity: 0.07,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  overlay: {
    position: 'absolute',
    top: 22,
    zIndex: 10,
    borderWidth: 3,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 2,
    transform: [{ rotate: '-12deg' }],
  },
  overlayRelevant: {
    right: 14,
    borderColor: '#065f46',
    backgroundColor: 'rgba(6,95,70,0.05)',
  },
  overlayDismiss: {
    left: 14,
    borderColor: '#991b1b',
    backgroundColor: 'rgba(153,27,27,0.05)',
  },
  overlayTextRelevant: {
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
    color: '#065f46',
    fontFamily: 'Georgia',
  },
  overlayTextDismiss: {
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 2,
    color: '#991b1b',
    fontFamily: 'Georgia',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  topicRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    flex: 1,
    gap: 6,
  },
  topicBadge: {
    borderWidth: 1,
    borderRadius: 2,
    paddingHorizontal: 7,
    paddingVertical: 3,
  },
  topicText: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  paywallBadge: {
    borderWidth: 1,
    borderColor: '#9ca3af',
    borderRadius: 2,
    paddingHorizontal: 7,
    paddingVertical: 3,
    backgroundColor: '#f3f4f6',
  },
  paywallBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#6b7280',
    letterSpacing: 0.5,
  },
  dateText: {
    color: '#9ca3af',
    fontSize: 11,
    marginLeft: 8,
    flexShrink: 0,
  },
  title: {
    color: '#1a1a1a',
    fontSize: 29,
    lineHeight: 36,
    fontWeight: '800',
    fontFamily: 'Georgia',
    marginBottom: 14,
  },
  titleCompact: {
    fontSize: 21,
    lineHeight: 27,
    marginBottom: 10,
  },
  titleRule: {
    height: 2,
    backgroundColor: '#1a1a1a',
    marginBottom: 14,
  },
  sourceText: {
    color: '#6b7280',
    fontSize: 11,
    fontWeight: '500',
    marginBottom: 12,
    letterSpacing: 0.3,
  },
  lead: {
    color: '#1a1a1a',
    fontSize: 16,
    lineHeight: 26,
    fontFamily: 'Georgia',
    marginBottom: 16,
  },
  leadCompact: {
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 12,
  },
  whyToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    paddingTop: 12,
    marginTop: 2,
  },
  whyLabel: {
    color: '#1a1a1a',
    fontSize: 13,
    fontWeight: '700',
  },
  whyCaret: {
    color: '#FFB700',
    fontSize: 12,
    fontWeight: '700',
  },
  breakdownPanel: {
    marginTop: 12,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
  },
  breakdownRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 9,
    gap: 8,
  },
  breakdownCheck: {
    color: '#065f46',
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
    width: 16,
  },
  breakdownReason: {
    flex: 1,
    color: '#4a4a4a',
    fontSize: 13,
    lineHeight: 19,
  },
  breakdownPoints: {
    fontSize: 13,
    fontWeight: '800',
  },
  pointsPos: { color: '#065f46' },
  pointsNeg: { color: '#991b1b' },
  emptyBreakdown: {
    color: '#9ca3af',
    fontSize: 13,
  },
  breakdownDivider: {
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    marginVertical: 10,
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  totalLabel: {
    color: '#4a4a4a',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  totalValue: {
    color: '#1a1a1a',
    fontSize: 24,
    fontWeight: '900',
    fontFamily: 'Georgia',
  },
  scoreTrack: {
    height: 4,
    backgroundColor: '#f3f4f6',
    borderRadius: 2,
    marginBottom: 4,
  },
  scoreFill: {
    height: '100%',
    backgroundColor: '#FFB700',
    borderRadius: 2,
  },
  footer: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 14,
  },
  actionButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderRadius: 2,
    minHeight: 46,
    paddingHorizontal: 10,
  },
  dismissButton: {
    borderColor: '#991b1b',
    backgroundColor: '#fff',
  },
  relevantButton: {
    borderColor: '#065f46',
    backgroundColor: '#fff',
  },
  dismissText: {
    color: '#991b1b',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  relevantText: {
    color: '#065f46',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  linkButton: {
    alignSelf: 'center',
    marginTop: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#FFB700',
    paddingBottom: 1,
  },
  linkText: {
    color: '#4a4a4a',
    fontSize: 11,
    fontWeight: '600',
  },
  hint: {
    textAlign: 'center',
    color: '#d1d5db',
    fontSize: 11,
    marginTop: 8,
    letterSpacing: 0.5,
  },
})
