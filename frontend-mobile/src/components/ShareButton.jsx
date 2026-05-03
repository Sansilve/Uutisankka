import { Linking, Modal, Platform, Pressable, Share, StyleSheet, TouchableOpacity, View } from 'react-native'
import { useRef, useState } from 'react'
import { Text } from 'react-native'

const SHARE_OPTIONS = [
  { key: 'clipboard', label: 'Kopioi linkki', icon: '📋' },
  { key: 'share', label: 'Jaa', icon: '📤' },
  { key: 'telegram', label: 'Telegram', icon: '💬' },
  { key: 'email', label: 'Sähköposti', icon: '✉️' },
]

export default function ShareButton({ article }) {
  const [showMenu, setShowMenu] = useState(false)
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 })
  const buttonRef = useRef(null)

  const handleCopyLink = () => {
    // Note: Clipboard API would need react-native-clipboard or similar
    // For now, we'll use a fallback alert
    const message = `${article.title}\n${article.url}`
    console.log('Copy to clipboard:', message)
    setShowMenu(false)
  }

  const handleShare = async () => {
    try {
      await Share.share({
        message: `Lue: ${article.title}\n${article.url}`,
        title: article.title,
        url: article.url,
      })
      setShowMenu(false)
    } catch (error) {
      console.error('Share failed:', error)
    }
  }

  const handleTelegram = () => {
    const message = encodeURIComponent(`Lue: ${article.title}\n${article.url}`)
    const deepLink = `tg://msg?text=${message}`
    Linking.openURL(deepLink).catch(() => {
      // Fallback to web
      Linking.openURL('https://telegram.me/?text=' + message)
    })
    setShowMenu(false)
  }

  const handleEmail = () => {
    const subject = encodeURIComponent(`Kiinnostava uutinen: ${article.title}`)
    const body = encodeURIComponent(`Lue tämä:\n\n${article.title}\n\n${article.url}`)
    Linking.openURL(`mailto:?subject=${subject}&body=${body}`)
    setShowMenu(false)
  }

  const handleOption = (option) => {
    switch (option) {
      case 'clipboard':
        handleCopyLink()
        break
      case 'share':
        handleShare()
        break
      case 'telegram':
        handleTelegram()
        break
      case 'email':
        handleEmail()
        break
      default:
        break
    }
  }

  const openMenu = () => {
    if (buttonRef.current) {
      buttonRef.current.measureInWindow((x, y, width, height) => {
        setMenuPos({ top: y + height + 4, right: window?.innerWidth ? window.innerWidth - x - width : 16 })
        setShowMenu(true)
      })
    } else {
      setShowMenu(true)
    }
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity
        ref={buttonRef}
        style={styles.shareButton}
        onPress={openMenu}
      >
        <Text style={styles.shareButtonText}>📤 Jaa</Text>
      </TouchableOpacity>

      <Modal
        visible={showMenu}
        transparent
        animationType="none"
        onRequestClose={() => setShowMenu(false)}
      >
        <Pressable style={styles.backdrop} onPress={() => setShowMenu(false)}>
          <Pressable style={[styles.menu, { position: 'absolute', top: menuPos.top, right: menuPos.right }]} onPress={() => {}}>
            {SHARE_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.key}
                style={styles.menuItem}
                onPress={() => handleOption(option.key)}
              >
                <Text style={styles.menuItemIcon}>{option.icon}</Text>
                <Text style={styles.menuItemLabel}>{option.label}</Text>
              </TouchableOpacity>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
  },
  shareButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f3f4f6',
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  shareButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  menu: {
    backgroundColor: '#ffffff',
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#d1d5db',
    minWidth: 150,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    gap: 8,
  },
  menuItemIcon: {
    fontSize: 16,
  },
  menuItemLabel: {
    fontSize: 13,
    color: '#374151',
    fontWeight: '500',
  },
})
