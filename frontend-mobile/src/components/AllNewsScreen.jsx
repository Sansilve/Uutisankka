import React, { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
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
  const [includePaywall, setIncludePaywall] = useState(true)
  const [paywallFilter, setPaywallFilter] = useState('all') // all | open | paywall
  const [sourceQuery, setSourceQuery] = useState('')
  const [regionQuery, setRegionQuery] = useState('')

  function loadItems(withPaywall) {
    setLoading(true)
    fetchAllArticles(500, withPaywall)
      .then((data) => {
        setItems(data.items || [])
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }

  useEffect(() => {
    loadItems(true)
  }, [])

  const sourceNorm = sourceQuery.trim().toLowerCase()
  const regionNorm = regionQuery.trim().toLowerCase()

  const filteredItems = items.filter((item) => {
    if (paywallFilter === 'open' && item.is_paywall) return false
    if (paywallFilter === 'paywall' && !item.is_paywall) return false

    if (sourceNorm && !String(item.source || '').toLowerCase().includes(sourceNorm)) return false
    if (regionNorm && !String(item.region || '').toLowerCase().includes(regionNorm)) return false

    return true
  })

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
          data={filteredItems}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingBottom: 40 }}
          renderItem={({ item }) => <AllNewsItem item={item} />}
          ListHeaderComponent={(
            <>
              <View style={styles.metaBar}>
                <Text style={styles.metaText}>{filteredItems.length} / {items.length} artikkelia</Text>
                <Text style={styles.metaHint}>Uusin ensin, avaa artikkeli painamalla riviä.</Text>
              </View>

              <View style={styles.filtersWrap}>
                <View style={styles.toggleRow}>
                  <Pressable
                    style={[styles.toggleBtn, includePaywall && styles.toggleBtnActive]}
                    onPress={() => {
                      const next = !includePaywall
                      setIncludePaywall(next)
                      loadItems(next)
                    }}
                  >
                    <Text style={[styles.toggleText, includePaywall && styles.toggleTextActive]}>
                      {includePaywall ? 'Paywall mukana: ON' : 'Paywall mukana: OFF'}
                    </Text>
                  </Pressable>
                </View>

                <View style={styles.tabs}>
                  {[
                    { id: 'all', label: 'Kaikki' },
                    { id: 'open', label: 'Avoimet' },
                    { id: 'paywall', label: 'Paywall' },
                  ].map((f) => (
                    <Pressable
                      key={f.id}
                      style={[styles.tab, paywallFilter === f.id && styles.tabActive]}
                      onPress={() => setPaywallFilter(f.id)}
                    >
                      <Text style={[styles.tabText, paywallFilter === f.id && styles.tabTextActive]}>{f.label}</Text>
                    </Pressable>
                  ))}
                </View>

                <TextInput
                  value={sourceQuery}
                  onChangeText={setSourceQuery}
                  placeholder="Suodata lähteen mukaan (esim. Guardian)"
                  placeholderTextColor="#9ca3af"
                  style={styles.input}
                />
                <TextInput
                  value={regionQuery}
                  onChangeText={setRegionQuery}
                  placeholder="Suodata alueen mukaan (esim. maailma, suomi, paikalliset:helsinki)"
                  placeholderTextColor="#9ca3af"
                  style={styles.input}
                />
              </View>
            </>
          )}
        />
      )}

      {!loading && !error && filteredItems.length === 0 && (
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
  filtersWrap: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#efefef',
    gap: 8,
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  toggleBtn: {
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    backgroundColor: '#f8f8f8',
  },
  toggleBtnActive: {
    backgroundColor: '#111827',
    borderColor: '#111827',
  },
  toggleText: {
    fontSize: 12,
    color: '#111827',
    fontWeight: '600',
  },
  toggleTextActive: {
    color: '#ffffff',
  },
  tabs: {
    flexDirection: 'row',
    gap: 8,
  },
  tab: {
    paddingVertical: 7,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 999,
  },
  tabActive: {
    borderColor: '#1a1a1a',
    backgroundColor: '#1a1a1a',
  },
  tabText: {
    fontSize: 12,
    color: '#666',
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#fff',
  },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 13,
    color: '#111827',
    backgroundColor: '#fff',
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
