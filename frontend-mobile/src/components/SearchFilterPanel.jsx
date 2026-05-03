import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native'

const TOPIC_CHIPS = [
  { key: 'technology', label: 'Teknologia', emoji: '💻' },
  { key: 'politics', label: 'Politiikka', emoji: '🏛️' },
  { key: 'economy', label: 'Talous', emoji: '💰' },
  { key: 'science', label: 'Tiede', emoji: '🔬' },
  { key: 'sports', label: 'Urheilu', emoji: '⚽' },
  { key: 'health', label: 'Terveys', emoji: '🏥' },
  { key: 'culture', label: 'Kulttuuri', emoji: '🎨' },
  { key: 'environment', label: 'Ympäristö', emoji: '🌱' },
  { key: 'crime', label: 'Rikos', emoji: '⚠️' },
  { key: 'weather', label: 'Sää', emoji: '⛅' },
]

export default function SearchFilterPanel({ selectedTopics = [], onToggleTopic, onClose }) {
  const handleToggle = (topic) => {
    onToggleTopic?.(topic)
  }

  const clearAll = () => {
    selectedTopics.forEach((topic) => onToggleTopic?.(topic))
  }

  const selectAll = () => {
    TOPIC_CHIPS.forEach((chip) => {
      if (!selectedTopics.includes(chip.key)) {
        onToggleTopic?.(chip.key)
      }
    })
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Suodata aiheittain</Text>
        <TouchableOpacity onPress={onClose}>
          <Text style={styles.closeButton}>✕</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionButton, selectedTopics.length === TOPIC_CHIPS.length && styles.actionButtonActive]}
          onPress={selectAll}
        >
          <Text style={styles.actionButtonText}>Valitse kaikki</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, selectedTopics.length === 0 && styles.actionButtonActive]}
          onPress={clearAll}
        >
          <Text style={styles.actionButtonText}>Tyhjennä</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.chipContainer} showsVerticalScrollIndicator={false}>
        {TOPIC_CHIPS.map((chip) => {
          const isSelected = selectedTopics.includes(chip.key)
          return (
            <TouchableOpacity
              key={chip.key}
              style={[styles.chip, isSelected && styles.chipSelected]}
              onPress={() => handleToggle(chip.key)}
            >
              <Text style={styles.chipEmoji}>{chip.emoji}</Text>
              <Text style={[styles.chipLabel, isSelected && styles.chipLabelSelected]}>
                {chip.label}
              </Text>
              {isSelected && <Text style={styles.chipCheck}>✓</Text>}
            </TouchableOpacity>
          )
        })}
      </ScrollView>

      {selectedTopics.length > 0 && (
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Näytetään: {selectedTopics.length} / {TOPIC_CHIPS.length} aihetta
          </Text>
        </View>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: '85%',
    maxWidth: 320,
    backgroundColor: '#ffffff',
    borderLeftWidth: 1,
    borderLeftColor: '#e5e7eb',
    zIndex: 50,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: -2, height: 0 },
    elevation: 6,
    flexDirection: 'column',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1a1a1a',
  },
  closeButton: {
    fontSize: 20,
    color: '#9ca3af',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#f9fafb',
  },
  actionButton: {
    flex: 1,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#d1d5db',
    backgroundColor: '#ffffff',
  },
  actionButtonActive: {
    backgroundColor: '#FFB700',
    borderColor: '#FFB700',
  },
  actionButtonText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#4b5563',
    textAlign: 'center',
  },
  chipContainer: {
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    backgroundColor: '#ffffff',
  },
  chipSelected: {
    borderColor: '#FFB700',
    backgroundColor: '#fffbf0',
  },
  chipEmoji: {
    fontSize: 18,
    marginRight: 8,
  },
  chipLabel: {
    flex: 1,
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
  },
  chipLabelSelected: {
    color: '#1a1a1a',
    fontWeight: '700',
  },
  chipCheck: {
    fontSize: 16,
    color: '#FFB700',
    marginLeft: 8,
  },
  footer: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    backgroundColor: '#f9fafb',
  },
  footerText: {
    fontSize: 12,
    color: '#6b7280',
    textAlign: 'center',
  },
})
