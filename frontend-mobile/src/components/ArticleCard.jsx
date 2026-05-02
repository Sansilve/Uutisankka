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

const TOPIC_STYLES = {
  technology: { bg: '#d9ecff', text: '#165ec9' },
  teknologia: { bg: '#d9ecff', text: '#165ec9' },
  science: { bg: '#efe0ff', text: '#8a2be2' },
  tiede: { bg: '#efe0ff', text: '#8a2be2' },
  politics: { bg: '#ffe0df', text: '#d63031' },
  politiikka: { bg: '#ffe0df', text: '#d63031' },
  economy: { bg: '#fff2d6', text: '#b7791f' },
  talous: { bg: '#fff2d6', text: '#b7791f' },
  health: { bg: '#ddfff0', text: '#0e9f6e' },
  terveys: { bg: '#ddfff0', text: '#0e9f6e' },
  culture: { bg: '#ffe1f0', text: '#d63384' },
  kulttuuri: { bg: '#ffe1f0', text: '#d63384' },
  sports: { bg: '#e6f7db', text: '#2f855a' },
  urheilu: { bg: '#e6f7db', text: '#2f855a' },
  environment: { bg: '#e3f7e7', text: '#2b8a3e' },
  ympäristö: { bg: '#e3f7e7', text: '#2b8a3e' },
}

function topicStyle(topic) {
  return TOPIC_STYLES[topic] || { bg: '#ececf3', text: '#495057' }
}

function topicLabel(topic) {
  const labels = {
    politics: 'Politics',
    economy: 'Economy',
    technology: 'Technology',
    science: 'Science',
    sports: 'Sports',
    health: 'Health',
    environment: 'Environment',
    culture: 'Culture',
    celebrity: 'Celebrity',
    weather: 'Weather',
    crime: 'Crime',
    transportation: 'Transport',
    military: 'Military',
    education: 'Education',
  }
  return labels[topic] || topic.charAt(0).toUpperCase() + topic.slice(1)
}

export default function ArticleCard({
  story,
  onDecision,
  disabled,
  progressText,
  progressWidth,
  onSurprise,
}) {
  const { width, height } = useWindowDimensions()
  const isCompact = width < 520
  const isShort = height < 780
  const cardWidth = Math.min(width - (isCompact ? 24 : 40), 760)
  const swipeThreshold = width * 0.24
  const [expanded, setExpanded] = useState(false)
  const pan = useRef(new Animated.ValueXY()).current

  const rotate = pan.x.interpolate({
    inputRange: [-width, 0, width],
    outputRange: ['-14deg', '0deg', '14deg'],
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
      duration: 190,
      useNativeDriver: false,
    }).start(() => {
      pan.setValue({ x: 0, y: 0 })
      setExpanded(false)
      onDecision(isRelevant)
    })
  }

  const responder = useMemo(
    () => PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) =>
        !disabled && (Math.abs(gesture.dx) > 8 || Math.abs(gesture.dy) > 8),
      onPanResponderMove: (_, gesture) => {
        pan.setValue({ x: gesture.dx, y: gesture.dy * 0.12 })
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

  return (
    <View style={[styles.screen, { paddingHorizontal: isCompact ? 10 : 18, paddingBottom: isCompact ? 10 : 22 }] }>
      <View style={styles.topRow}>
        <View>
          <Text style={styles.eyebrow}>Tanaan sinulle</Text>
          <Text style={[styles.progressLabel, isCompact && styles.progressLabelCompact]}>{progressText}</Text>
        </View>
        <TouchableOpacity style={styles.surpriseButton} onPress={onSurprise} disabled={disabled}>
          <Text style={styles.surpriseText}>Yllata minut</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: progressWidth }]} />
      </View>

      <View style={styles.cardStage}>
        <Animated.View
          style={[
            styles.card,
            {
              width: cardWidth,
              padding: isCompact ? 14 : 20,
            },
            isShort && styles.cardShort,
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
          <Animated.View style={[styles.overlay, styles.overlayRelevant, { opacity: relevantOpacity }]}>
            <Text style={styles.overlayText}>RELEVANTTI</Text>
          </Animated.View>
          <Animated.View style={[styles.overlay, styles.overlayDismiss, { opacity: dismissOpacity }]}>
            <Text style={styles.overlayText}>EI KIINNOSTA</Text>
          </Animated.View>

          <View style={styles.topicRow}>
            {story.topics.slice(0, 3).map((topic) => {
              const color = topicStyle(topic)
              return (
                <View key={topic} style={[styles.topicBadge, { backgroundColor: color.bg }]}>
                  <Text style={[styles.topicText, { color: color.text }]}>{topicLabel(topic)}</Text>
                </View>
              )
            })}
          </View>

          <Text style={[styles.title, isCompact && styles.titleCompact, isShort && styles.titleShort]}>{story.title}</Text>

          <View style={[styles.summaryWrap, isShort && styles.summaryWrapShort]}>
            {story.summary.bullets.slice(0, isCompact ? 3 : 5).map((bullet, index) => (
              <Text key={`${story.id}-${index}`} style={[styles.bullet, isCompact && styles.bulletCompact, isShort && styles.bulletShort]}>
                {'\u2022'} {bullet}
              </Text>
            ))}
          </View>

          <Pressable style={styles.whyToggle} onPress={() => setExpanded((value) => !value)}>
            <Text style={styles.whyLabel}>Miksi tama sinulle?</Text>
            <Text style={styles.whyCaret}>{expanded ? '^' : 'v'}</Text>
          </Pressable>

          {expanded ? (
            <View style={styles.breakdownPanel}>
              {story.score_breakdown.items.length ? (
                story.score_breakdown.items.map((item, index) => (
                  <View key={`${item.reason}-${index}`} style={styles.breakdownRow}>
                    <Text style={styles.breakdownReason}>{item.reason}</Text>
                    <Text style={styles.breakdownPoints}>
                      {item.points > 0 ? '+' : ''}
                      {item.points.toFixed(1)}
                    </Text>
                  </View>
                ))
              ) : (
                <Text style={styles.emptyBreakdown}>Ei piste-erittelya saatavilla.</Text>
              )}
              <View style={styles.divider} />
              <View style={styles.breakdownRow}>
                <Text style={styles.totalLabel}>Pisteet</Text>
                <Text style={styles.totalValue}>{totalScore.toFixed(1)}</Text>
              </View>
            </View>
          ) : null}

          <View style={[styles.footer, isCompact && styles.footerCompact]}>
            <TouchableOpacity
              style={[styles.actionButton, styles.dismissButton]}
              onPress={() => settleCard(false)}
              disabled={disabled}
            >
              <Text style={styles.dismissText}>Ei kiinnosta</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionButton, styles.relevantButton]}
              onPress={() => settleCard(true)}
              disabled={disabled}
            >
              <Text style={styles.relevantText}>Relevantti</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.linkButton} onPress={() => Linking.openURL(story.url)}>
            <Text style={styles.linkText}>Lue lahde</Text>
          </TouchableOpacity>
        </Animated.View>
      </View>

      <Text style={styles.hint}>Swipe oikealle = relevantti · Swipe vasemmalle = ei kiinnosta</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    width: '100%',
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 22,
    overflow: 'hidden',
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  eyebrow: {
    color: '#6b7280',
    fontSize: 14,
    fontWeight: '600',
  },
  progressLabel: {
    color: '#111827',
    fontSize: 24,
    fontWeight: '800',
    marginTop: 2,
  },
  progressLabelCompact: {
    fontSize: 17,
  },
  surpriseButton: {
    borderWidth: 1,
    borderColor: '#d7d9e1',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#ffffff',
  },
  surpriseText: {
    color: '#1f2937',
    fontSize: 14,
    fontWeight: '700',
  },
  progressTrack: {
    height: 6,
    backgroundColor: '#d1d5db',
    borderRadius: 999,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#111827',
    borderRadius: 999,
  },
  cardStage: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 20,
    padding: 20,
    width: '100%',
    maxWidth: 760,
    shadowColor: '#000000',
    shadowOpacity: 0.12,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
  cardShort: {
    borderRadius: 18,
  },
  overlay: {
    position: 'absolute',
    top: 18,
    zIndex: 2,
    borderWidth: 2,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  overlayRelevant: {
    right: 18,
    borderColor: '#08a045',
    backgroundColor: 'rgba(8,160,69,0.08)',
  },
  overlayDismiss: {
    left: 18,
    borderColor: '#e11d48',
    backgroundColor: 'rgba(225,29,72,0.08)',
  },
  overlayText: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1,
    color: '#111827',
  },
  topicRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 10,
  },
  topicBadge: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginRight: 8,
    marginBottom: 8,
  },
  topicText: {
    fontSize: 12,
    fontWeight: '700',
  },
  title: {
    color: '#111827',
    fontSize: 31,
    lineHeight: 38,
    fontWeight: '800',
    marginBottom: 18,
  },
  titleCompact: {
    fontSize: 20,
    lineHeight: 26,
    marginBottom: 10,
  },
  titleShort: {
    fontSize: 19,
    lineHeight: 24,
    marginBottom: 8,
  },
  summaryWrap: {
    gap: 12,
    marginBottom: 18,
  },
  summaryWrapShort: {
    gap: 6,
    marginBottom: 10,
  },
  bullet: {
    color: '#4b5563',
    fontSize: 17,
    lineHeight: 26,
  },
  bulletCompact: {
    fontSize: 14,
    lineHeight: 20,
  },
  bulletShort: {
    fontSize: 13,
    lineHeight: 18,
  },
  whyToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    paddingTop: 16,
    marginTop: 4,
  },
  whyLabel: {
    color: '#374151',
    fontSize: 15,
    fontWeight: '700',
  },
  whyCaret: {
    color: '#6b7280',
    fontSize: 16,
    fontWeight: '700',
  },
  breakdownPanel: {
    marginTop: 14,
    paddingTop: 6,
    paddingBottom: 6,
  },
  breakdownRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 9,
    gap: 12,
  },
  breakdownReason: {
    flex: 1,
    color: '#374151',
    fontSize: 15,
    lineHeight: 21,
  },
  breakdownPoints: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '700',
  },
  emptyBreakdown: {
    color: '#6b7280',
    fontSize: 14,
  },
  divider: {
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    marginTop: 6,
    paddingTop: 10,
  },
  totalLabel: {
    color: '#111827',
    fontSize: 15,
    fontWeight: '800',
  },
  totalValue: {
    color: '#111827',
    fontSize: 18,
    fontWeight: '800',
  },
  footer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 14,
  },
  footerCompact: {
    flexDirection: 'column-reverse',
  },
  actionButton: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    minHeight: 52,
    paddingHorizontal: 12,
  },
  dismissButton: {
    borderWidth: 1,
    borderColor: '#fca5a5',
    backgroundColor: '#fffafb',
  },
  relevantButton: {
    backgroundColor: '#08a045',
  },
  dismissText: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '700',
  },
  relevantText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  linkButton: {
    alignSelf: 'center',
    marginTop: 14,
  },
  linkText: {
    color: '#6b7280',
    fontSize: 13,
    fontWeight: '700',
  },
  hint: {
    textAlign: 'center',
    color: '#6b7280',
    fontSize: 13,
    marginTop: 18,
  },
})
