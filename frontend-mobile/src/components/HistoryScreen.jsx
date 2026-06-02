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
import { fetchHistory } from '../api'

function groupByDate(items) {
  const groups = {}
  for (const item of items) {
    const date = item.swiped_at.slice(0, 10)
    if (!groups[date]) groups[date] = []
    groups[date].push(item)
  }
  return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]))
}

function formatDateFi(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('fi-FI', { weekday: 'long', day: 'numeric', month: 'long' })
}

function HistoryItem({ item }) {
  const lead = item.summary?.bullets?.slice(0, 2).join(' ') || ''
  return (
    <Pressable
      style={styles.item}
      onPress={() => Linking.openURL(item.url)}
      accessibilityRole="link"
    >
      <View style={styles.itemHeader}>
        <Text style={[styles.badge, item.is_relevant ? styles.badgeRelevant : styles.badgeDismissed]}>
          {item.is_relevant ? 'KIINNOSTAA' : 'OHITETTU'}
        </Text>
        <Text style={styles.source}>{item.source}</Text>
      </View>
      <Text style={styles.title}>{item.title}</Text>
      {lead ? <Text style={styles.lead} numberOfLines={2}>{lead}</Text> : null}
    </Pressable>
  )
}

export default function HistoryScreen({ onClose }) {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // 'all' | 'relevant' | 'dismissed'

  useEffect(() => {
    reload()
  }, [])

  function reload() {
    setError(null)
    setLoading(true)
    fetchHistory(200)
      .then((data) => {
        setGroups(groupByDate(data.items))
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }

  const filtered =
    filter === 'all'
      ? groups
      : groups.map(([date, items]) => [
          date,
          items.filter((i) => (filter === 'relevant' ? i.is_relevant : !i.is_relevant)),
        ]).filter(([, items]) => items.length > 0)

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={onClose} style={styles.closeBtn} accessibilityRole="button">
          <Text style={styles.closeBtnText}>← Takaisin</Text>
        </Pressable>
        <Text style={styles.heading}>SELAUSHISTORIA</Text>
      </View>

      {/* Filter tabs */}
      <View style={styles.tabs}>
        {['all', 'relevant', 'dismissed'].map((f) => (
          <Pressable
            key={f}
            style={[styles.tab, filter === f && styles.tabActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.tabText, filter === f && styles.tabTextActive]}>
              {f === 'all' ? 'Kaikki' : f === 'relevant' ? 'Kiinnostaa' : 'Ohitettu'}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading && <ActivityIndicator style={{ marginTop: 40 }} color="#1a1a1a" />}
      {error && (
        <View style={styles.errorWrap}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={reload}>
            <Text style={styles.retryBtnText}>↻ Yritä uudelleen</Text>
          </Pressable>
        </View>
      )}

      {!loading && !error && (
        <FlatList
          data={filtered}
          keyExtractor={([date]) => date}
          contentContainerStyle={{ paddingBottom: 40 }}
          renderItem={({ item: [date, items] }) => (
            <View>
              <View style={styles.dateHeader}>
                <Text style={styles.dateText}>{formatDateFi(date)}</Text>
                <Text style={styles.dateCount}>{items.length} artikkelia</Text>
              </View>
              {items.map((article) => (
                <HistoryItem key={article.swipe_id} item={article} />
              ))}
            </View>
          )}
        />
      )}

      {!loading && !error && filtered.length === 0 && (
        <Text style={styles.emptyText}>Ei selaushistoriaa vielä.</Text>
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
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
    paddingHorizontal: 16,
    gap: 0,
  },
  tab: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#1a1a1a',
  },
  tabText: {
    fontSize: 12,
    letterSpacing: 1,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
  },
  tabTextActive: {
    color: '#1a1a1a',
  },
  dateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 6,
    backgroundColor: '#f8f8f8',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e5e5',
  },
  dateText: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: '#1a1a1a',
  },
  dateCount: {
    fontSize: 11,
    color: '#888',
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
  badgeRelevant: {
    color: '#065f46',
    borderColor: '#065f46',
  },
  badgeDismissed: {
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
  errorWrap: {
    alignItems: 'center',
    marginTop: 48,
    paddingHorizontal: 32,
    gap: 16,
  },
  errorText: {
    textAlign: 'center',
    color: '#991b1b',
    fontSize: 14,
    lineHeight: 20,
  },
  retryBtn: {
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 2,
  },
  retryBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
})
