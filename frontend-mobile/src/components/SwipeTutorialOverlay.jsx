import { Pressable, StyleSheet, Text, View } from 'react-native'

export default function SwipeTutorialOverlay({ onDismiss }) {
  return (
    <Pressable style={styles.backdrop} onPress={onDismiss}>
      <View style={styles.modal}>
        <Text style={styles.emoji}>👋</Text>
        <Text style={styles.title}>Tervetuloa!</Text>
        <Text style={styles.subtitle}>Opimme mieltymyksistäsi</Text>
        
        <View style={styles.content}>
          <Text style={styles.instruction}>
            👍 <Text style={styles.highlight}>Swipe oikealle</Text> jos juttu kiinnostaa
          </Text>
          <Text style={styles.instruction}>
            👎 <Text style={styles.highlight}>Swipe vasemmalle</Text> jos et ole kiinnostunut
          </Text>
        </View>
        
        <Text style={styles.explanation}>
          Jokainen valinta auttaa meitä ymmärtämään paremmin, mistä olet kiinnostunut.
        </Text>
        
        <Pressable style={styles.button} onPress={onDismiss}>
          <Text style={styles.buttonText}>Ymmärretty!</Text>
        </Pressable>
      </View>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  modal: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 24,
    maxWidth: 320,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  emoji: {
    fontSize: 48,
    marginBottom: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 20,
  },
  content: {
    backgroundColor: '#f9fafb',
    borderRadius: 4,
    padding: 12,
    marginBottom: 16,
    width: '100%',
  },
  instruction: {
    fontSize: 13,
    color: '#374151',
    marginBottom: 10,
    lineHeight: 18,
  },
  highlight: {
    fontWeight: '700',
    color: '#1a1a1a',
  },
  explanation: {
    fontSize: 12,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 16,
  },
  button: {
    backgroundColor: '#FFB700',
    borderRadius: 4,
    paddingVertical: 10,
    paddingHorizontal: 24,
    minWidth: 120,
  },
  buttonText: {
    color: '#1a1a1a',
    fontWeight: '700',
    fontSize: 14,
    textAlign: 'center',
  },
})
