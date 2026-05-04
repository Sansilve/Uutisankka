import * as Clipboard from 'expo-clipboard'
import { useState } from 'react'
import { Share, StyleSheet, Text, TouchableOpacity, View } from 'react-native'

export default function ShareButton({ article }) {
  const [copyNotice, setCopyNotice] = useState('')

  const handleCopyLink = async () => {
    try {
      await Clipboard.setStringAsync(article?.url ?? '')
      setCopyNotice('Linkki kopioitu')
      setTimeout(() => setCopyNotice(''), 1600)
    } catch (error) {
      console.error('Copy to clipboard failed:', error)
      setCopyNotice('Kopiointi epaonnistui')
      setTimeout(() => setCopyNotice(''), 1600)
    }
  }

  const handleShare = async () => {
    try {
      await Share.share({
        message: `Lue: ${article.title}\n${article.url}`,
        title: article.title,
        url: article.url,
      })
    } catch (error) {
      console.error('Share failed:', error)
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.actionsRow}>
        <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
          <Text style={styles.actionButtonText}>📤 Jaa</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionButton} onPress={handleCopyLink}>
          <Text style={styles.actionButtonText}>📋 Kopioi linkki</Text>
        </TouchableOpacity>
      </View>
      {copyNotice ? <Text style={styles.copyNotice}>{copyNotice}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f3f4f6',
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  actionButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  copyNotice: {
    marginTop: 6,
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '600',
  },
})
