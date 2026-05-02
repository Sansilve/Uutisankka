import React, { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { fetchAllArticles } from '../api'

function AllNewsItem({ item }) {
  const lead = item.summary?.bullets?.slice(0, 2).join(' ') || ''
  return (
    <Pressable
      style={styles.item}
      onPress={() => Linking.openURL(item.url)}
      accessibilityRole="link"
    >
      <View style={styles.itemHeader}>
        <Text style={[styles.badge, item.is_paywall ? styles.badgePaywall : styles.badgeOpen]}>
          {item.is_paywall ? 'PAYWALL' : 'AVOIN'}
        </Text>
        <Text style={styles.source}>{item.source}</Text>
      </View>
      <Text style={styles.title}>{item.title}</Text>
      {lead ? <Text style={styles.lead} numberOfLines={2}>{lead}</Text> : null}
    </Pressable>
  )
}

export default function AllNewsScreen({ onClose }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAllArticles(500)
      .then((data) => {
        setItems(data.items || [])
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [])

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable onPress={onClose} style={styles.closeBtn} accessibilityRole="button">
          <Text style={styles.closeBtnText}>← Takaisin</Text>
        </Pressable>
        <Text style={styles.heading}>KAIKKI UUTISET (DEV)</Text>
      </View>

      {loading && <ActivityIndicator style={{ marginTop: 40 }} color="#1a1a1a" />}
      {error && <Text style={styles.errorText}>{error}</Text>}

      {!loading && !error && (
        <FlatList
          data={items}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingBottom: 40 }}
          renderItem={({ item }) => <AllNewsItem item={item} />}
          ListHeaderComponent={(
            <View style={styles.metaBar}>
              <Text style={styles.metaText}>{items.length} artikkelia</Text>
              <Text style={styles.metaHint}>Uusin ensin, avaa artikkeli painamalla riviä.</Text>
            </View>
          )}
        />
      )}

      {!loading && !error && items.length === 0 && (
        <Text style={styles.emptyText}>Ei artikkeleita juuri nyt.</Text>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  header: {
    paddingTop: 56,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 3,
    borderBottomColor: '#FFB700',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  closeBtn: {
    paddingVertical: 4,
  },
  closeBtnText: {
    fontSize: 14,
    color: '#1a1a1a',
    fontFamily: 'Georgia',
  },
  heading: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 2,
    color: '#1a1a1a',
  },
  metaBar: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#efefef',
  },
  metaText: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    color: '#1a1a1a',
    textTransform: 'uppercase',
  },
  metaHint: {
    marginTop: 4,
    fontSize: 12,
    color: '#666',
  },
  item: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  itemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  badge: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 1,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderWidth: 1,
    textTransform: 'uppercase',
  },
  badgeOpen: {
    color: '#065f46',
    borderColor: '#065f46',
  },
  badgePaywall: {
    color: '#991b1b',
    borderColor: '#991b1b',
  },
  source: {
    fontSize: 10,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  title: {
    fontSize: 15,
    fontWeight: '700',
    fontFamily: 'Georgia',
    color: '#1a1a1a',
    lineHeight: 20,
  },
  lead: {
    fontSize: 13,
    color: '#4a4a4a',
    marginTop: 3,
    lineHeight: 18,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 60,
    color: '#888',
    fontSize: 15,
    fontFamily: 'Georgia',
  },
  errorText: {
    textAlign: 'center',
    marginTop: 24,
    color: '#991b1b',
    fontSize: 14,
  },
})
