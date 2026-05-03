import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { fetchAllArticleFacets, fetchAllArticles } from '../api'

const PAGE_SIZE = 50
const TOPIC_COLORS = {
  teknologia: '#1e3a8a',
  tiede: '#3b0764',
  politiikka: '#991b1b',
  talous: '#065f46',
  terveys: '#064e3b',
  kulttuuri: '#831843',
  urheilu: '#14532d',
  ymparisto: '#052e16',
  celebrity: '#581c87',
  saa: '#0c4a6e',
  rikos: '#450a0a',
  koulutus: '#1e1b4b',
  turvallisuus: '#1c1917',
  kansainvaliset: '#7c2d12',
  viihde: '#4a044e',
  onnettomuudet: '#7f1d1d',
  all: '#111827',
}

const CATEGORY_OPTIONS = [
  { id: 'teknologia', label: 'Teknologia' },
  { id: 'politiikka', label: 'Politiikka' },
  { id: 'talous', label: 'Talous' },
  { id: 'tiede', label: 'Tiede' },
  { id: 'urheilu', label: 'Urheilu' },
  { id: 'terveys', label: 'Terveys' },
  { id: 'kulttuuri', label: 'Kulttuuri' },
  { id: 'ymparisto', label: 'Ympäristö' },
  { id: 'rikos', label: 'Rikos' },
  { id: 'saa', label: 'Sää' },
]
const SCOPE_OPTIONS = [
  { id: 'maailma', label: 'Maailma' },
  { id: 'suomi', label: 'Suomi' },
  { id: 'paikalliset', label: 'Paikallisuutiset' },
]
const TONE_OPTIONS = [
  { id: 'all', label: 'Kaikki' },
  { id: 'neutral_positive', label: 'Ei raskaita' },
  { id: 'positive', label: 'Vain positiiviset' },
  { id: 'neutral', label: 'Vain neutraalit' },
]

const normalizeCategory = (value) =>
  String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

const canonicalCategoryKey = (value) => {
  const key = normalizeCategory(value)
  const aliases = {
    rikokset: 'rikos',
    saa: 'saa',
    ymparisto: 'ymparisto',
    turvallisuus: 'turvallisuus',
    kansainvaliset: 'kansainvaliset',
  }
  return aliases[key] || key
}

const categoryLabel = (key) => {
  const found = CATEGORY_OPTIONS.find((c) => c.id === key)
  if (found) return found.label
  if (!key) return ''
  return key.charAt(0).toUpperCase() + key.slice(1)
}

const scopeLabel = (key) => {
  const found = SCOPE_OPTIONS.find((x) => x.id === key)
  return found ? found.label : key
}

const collectItemCategories = (item) => {
  const candidates = [item.category, item.category_secondary, ...(item.topics || [])]
  const unique = new Set()
  for (const value of candidates) {
    const key = canonicalCategoryKey(value)
    if (key && key !== 'all') unique.add(key)
  }
  return Array.from(unique)
}

const itemHasCategory = (item, selected) => {
  if (selected === 'all') return true
  const target = canonicalCategoryKey(selected)
  return collectItemCategories(item).includes(target)
}

function AllNewsItem({ item, onOpen }) {
  const lead = item.summary?.bullets?.slice(0, 2).join(' ') || ''
  const categories = collectItemCategories(item)
  return (
    <Pressable
      style={styles.item}
      onPress={() => onOpen(item)}
      accessibilityRole="button"
    >
      <View style={styles.itemHeader}>
        <Text style={[styles.badge, item.is_paywall ? styles.badgePaywall : styles.badgeOpen]}>
          {item.is_paywall ? 'Maksumuuri' : 'Avoin'}
        </Text>
        <Text style={styles.scoreBadge}>Pisteet {Number(item.score || 0).toFixed(1)}</Text>
        <Text style={styles.source}>{item.source}</Text>
      </View>
      <Text style={styles.title}>{item.title}</Text>
      {lead ? <Text style={styles.lead} numberOfLines={2}>{lead}</Text> : null}
      {categories.length > 0 && (
        <View style={styles.itemCategories}>
          {categories.map((key) => (
            <View
              key={`${item.id}-${key}`}
              style={[styles.itemCategoryChip, { borderColor: TOPIC_COLORS[key] || '#6b7280' }]}
            >
              <Text style={[styles.itemCategoryText, { color: TOPIC_COLORS[key] || '#6b7280' }]}>
                {categoryLabel(key)}
              </Text>
            </View>
          ))}
        </View>
      )}
    </Pressable>
  )
}

function AllNewsDetail({ item, onBack }) {
  const categories = collectItemCategories(item)
  const bullets = item.summary?.bullets || []

  return (
    <View style={styles.detailContainer}>
      <View style={styles.detailHeader}>
        <Pressable onPress={onBack} style={styles.closeBtn} accessibilityRole="button">
          <Text style={styles.closeBtnText}>← Takaisin listaan</Text>
        </Pressable>
        <Text style={styles.heading}>UUTISKORTTI</Text>
      </View>

      <ScrollView contentContainerStyle={styles.detailContent}>
        <View style={styles.detailMetaRow}>
          <Text style={[styles.badge, item.is_paywall ? styles.badgePaywall : styles.badgeOpen]}>
            {item.is_paywall ? 'Maksumuuri' : 'Avoin'}
          </Text>
          <Text style={styles.scoreBadge}>Pisteet {Number(item.score || 0).toFixed(1)}</Text>
        </View>

        <Text style={styles.detailSource}>{item.source}</Text>
        <Text style={styles.detailTitle}>{item.title}</Text>

        {categories.length > 0 && (
          <View style={styles.detailCategories}>
            {categories.map((key) => (
              <View
                key={`detail-${item.id}-${key}`}
                style={[styles.itemCategoryChip, { borderColor: TOPIC_COLORS[key] || '#6b7280' }]}
              >
                <Text style={[styles.itemCategoryText, { color: TOPIC_COLORS[key] || '#6b7280' }]}>
                  {categoryLabel(key)}
                </Text>
              </View>
            ))}
          </View>
        )}

        <Text style={styles.detailSectionTitle}>Tiivistelmä</Text>
        {bullets.length > 0 ? (
          bullets.map((bullet, idx) => (
            <Text key={`${item.id}-b-${idx}`} style={styles.detailBullet}>• {bullet}</Text>
          ))
        ) : (
          <Text style={styles.detailBullet}>Ei tiivistelmää saatavilla.</Text>
        )}

        <Pressable style={styles.openLinkBtn} onPress={() => Linking.openURL(item.url)}>
          <Text style={styles.openLinkText}>Avaa alkuperäinen juttu</Text>
        </Pressable>
      </ScrollView>
    </View>
  )
}

export default function AllNewsScreen({ onClose }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [loadingFacets, setLoadingFacets] = useState(false)
  const [error, setError] = useState(null)
  const [includePaywall, setIncludePaywall] = useState(true)
  const [scopeFilters, setScopeFilters] = useState(['maailma', 'suomi', 'paikalliset'])
  const [localCityFilters, setLocalCityFilters] = useState([])
  const [categoryFilters, setCategoryFilters] = useState([])
  const [sourceFilters, setSourceFilters] = useState([])
  const [toneFilter, setToneFilter] = useState('all')
  const [showSources, setShowSources] = useState(false)
  const [showCities, setShowCities] = useState(false)
  const [facets, setFacets] = useState({
    total: 0,
    categories: {},
    sources: {},
    tones: { positive: 0, neutral: 0, negative: 0 },
    scopes: { maailma: 0, suomi: 0, paikalliset: 0 },
    cities: {},
  })
  const [selectedItem, setSelectedItem] = useState(null)

  const offsetRef = useRef(0)
  const hasMoreRef = useRef(true)

  const scopeKey = useMemo(() => [...scopeFilters].sort().join('|'), [scopeFilters])
  const cityKey = useMemo(() => [...localCityFilters].sort().join('|'), [localCityFilters])
  const categoryKey = useMemo(() => [...categoryFilters].sort().join('|'), [categoryFilters])
  const sourceKey = useMemo(() => [...sourceFilters].sort().join('|'), [sourceFilters])

  const toggleMulti = (value, setter, current) => {
    if (current.includes(value)) {
      setter(current.filter((x) => x !== value))
    } else {
      setter([...current, value])
    }
  }

  const load = useCallback((reset = false) => {
    if (reset) {
      offsetRef.current = 0
      hasMoreRef.current = true
      setItems([])
      setTotal(null)
      setError(null)
      setLoading(true)
    } else {
      if (!hasMoreRef.current) return
      setLoadingMore(true)
    }
    fetchAllArticles({
      limit: PAGE_SIZE,
      offset: offsetRef.current,
      includePaywall,
      scopes: scopeFilters,
      localCities: localCityFilters,
      categories: categoryFilters,
      sources: sourceFilters,
      tones: toneFilter === 'all' ? [] : [toneFilter],
    })
      .then((data) => {
        const newItems = data.items || []
        offsetRef.current += newItems.length
        if (newItems.length < PAGE_SIZE) hasMoreRef.current = false
        setTotal(data.total ?? null)
        setItems((prev) => reset ? newItems : [...prev, ...newItems])
      })
      .catch((e) => setError(e.message))
      .finally(() => { setLoading(false); setLoadingMore(false) })
  }, [includePaywall, scopeKey, cityKey, categoryKey, sourceKey, toneFilter])

  const loadFacets = useCallback(() => {
    setLoadingFacets(true)
    fetchAllArticleFacets({
      includePaywall,
      scopes: scopeFilters,
      localCities: localCityFilters,
    })
      .then((data) => setFacets(data))
      .catch(() => {})
      .finally(() => setLoadingFacets(false))
  }, [includePaywall, scopeKey, cityKey])

  useEffect(() => {
    load(true)
  }, [includePaywall, scopeKey, cityKey, categoryKey, sourceKey, toneFilter])

  useEffect(() => {
    if (!scopeFilters.includes('paikalliset') && localCityFilters.length > 0) {
      setLocalCityFilters([])
    }
    if (!scopeFilters.includes('paikalliset')) {
      setShowCities(false)
    }
  }, [scopeKey])

  useEffect(() => {
    loadFacets()
  }, [includePaywall, scopeKey, cityKey])

  const categoryOptionsFromData = useMemo(() => {
    const keys = new Set(CATEGORY_OPTIONS.map((x) => x.id))
    for (const key of Object.keys(facets.categories || {})) {
      keys.add(canonicalCategoryKey(key))
    }
    return Array.from(keys)
      .filter(Boolean)
      .sort((a, b) => categoryLabel(a).localeCompare(categoryLabel(b), 'fi'))
      .map((key) => ({ id: key, label: categoryLabel(key) }))
  }, [facets])

  const sourceOptions = useMemo(
    () => Object.entries(facets.sources || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 40)
      .map(([name, count]) => ({ name, count })),
    [facets],
  )

  const cityOptions = useMemo(
    () => Object.entries(facets.cities || {})
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count })),
    [facets],
  )

  const toneCounts = {
    all: facets.total || 0,
    neutral_positive: (facets.tones?.neutral || 0) + (facets.tones?.positive || 0),
    positive: facets.tones?.positive || 0,
    neutral: facets.tones?.neutral || 0,
  }

  const filteredItems = items

  const loadMore = () => {
    if (!loadingMore && !loading && hasMoreRef.current) load(false)
  }

  if (selectedItem) {
    return <AllNewsDetail item={selectedItem} onBack={() => setSelectedItem(null)} />
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable onPress={onClose} style={styles.closeBtn} accessibilityRole="button">
          <Text style={styles.closeBtnText}>← Takaisin</Text>
        </Pressable>
        <Text style={styles.heading}>KAIKKI UUTISET</Text>
      </View>

      {loading && <ActivityIndicator style={{ marginTop: 40 }} color="#1a1a1a" />}
      {error && (
        <View style={styles.errorWrap}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryBtn} onPress={() => load(true)}>
            <Text style={styles.retryBtnText}>↻ Yritä uudelleen</Text>
          </Pressable>
        </View>
      )}

      {!loading && !error && (
        <FlatList
          data={filteredItems}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={{ paddingBottom: 40 }}
          renderItem={({ item }) => <AllNewsItem item={item} onOpen={setSelectedItem} />}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListHeaderComponent={(
            <>
              <View style={styles.metaBar}>
                <Text style={styles.metaText}>
                  {filteredItems.length} artikkelia ladattu{total !== null ? ` · ${total} yhteensä` : ''}
                </Text>
                {loadingFacets ? <Text style={styles.metaHint}>Päivitetään koko aineiston laskureita…</Text> : null}
              </View>

              <View style={styles.filtersWrap}>
                <View style={styles.toggleRow}>
                  <Pressable
                    style={[styles.toggleBtn, includePaywall && styles.toggleBtnActive]}
                    onPress={() => setIncludePaywall((prev) => !prev)}
                  >
                    <Text style={[styles.toggleText, includePaywall && styles.toggleTextActive]}>
                      {includePaywall ? '🔒 Maksumuuri mukana' : '🔓 Vain avoimet'}
                    </Text>
                  </Pressable>
                </View>

                <Text style={styles.sectionLabel}>Alue</Text>
                <View style={styles.categoryRow}>
                  {SCOPE_OPTIONS.map((option) => {
                    const active = scopeFilters.includes(option.id)
                    return (
                      <Pressable
                        key={option.id}
                        style={[styles.filterChip, active && styles.filterChipActive]}
                        onPress={() => {
                          if (active && scopeFilters.length === 1) return
                          if (!active && option.id === 'paikalliset') {
                            setShowCities(true)
                          }
                          toggleMulti(option.id, setScopeFilters, scopeFilters)
                        }}
                      >
                        <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                          {scopeLabel(option.id)} ({facets.scopes?.[option.id] || 0})
                        </Text>
                      </Pressable>
                    )
                  })}
                </View>

                {scopeFilters.includes('paikalliset') && cityOptions.length > 0 && (
                  <>
                    <Pressable style={styles.sectionToggle} onPress={() => setShowCities((prev) => !prev)}>
                      <Text style={styles.sectionLabel}>Paikalliskaupungit</Text>
                      <Text style={styles.sectionToggleText}>{showCities ? 'Piilota' : 'Näytä'}</Text>
                    </Pressable>
                    {showCities && (
                      <View style={styles.categoryRow}>
                        {cityOptions.map((city) => {
                          const active = localCityFilters.includes(city.name)
                          return (
                            <Pressable
                              key={city.name}
                              style={[styles.filterChip, active && styles.filterChipActive]}
                              onPress={() => toggleMulti(city.name, setLocalCityFilters, localCityFilters)}
                            >
                              <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                                {city.name} ({city.count})
                              </Text>
                            </Pressable>
                          )
                        })}
                      </View>
                    )}
                  </>
                )}

                <Text style={styles.sectionLabel}>Uutisten tunnelma</Text>
                <View style={styles.categoryRow}>
                  {TONE_OPTIONS.map((option) => {
                    const active = toneFilter === option.id
                    return (
                      <Pressable
                        key={option.id}
                        style={[styles.filterChip, active && styles.filterChipActive]}
                        onPress={() => setToneFilter(option.id)}
                      >
                        <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                          {option.label} ({toneCounts[option.id] || 0})
                        </Text>
                      </Pressable>
                    )
                  })}
                </View>

                <Text style={styles.sectionLabel}>Kategoriat</Text>
                <View style={styles.categoryRow}>
                  {categoryOptionsFromData.map((option) => {
                    const color = TOPIC_COLORS[option.id] || '#374151'
                    const active = categoryFilters.includes(option.id)
                    return (
                      <Pressable
                        key={option.id}
                        style={[
                          styles.categoryChip,
                          { borderColor: color },
                          active && { backgroundColor: color, borderColor: color },
                        ]}
                        onPress={() => toggleMulti(option.id, setCategoryFilters, categoryFilters)}
                      >
                        <Text style={[styles.categoryChipText, active ? { color: '#ffffff' } : { color }]}>
                          {option.label} ({facets.categories?.[option.id] || 0})
                        </Text>
                      </Pressable>
                    )
                  })}
                </View>

                <Pressable style={styles.sectionToggle} onPress={() => setShowSources((prev) => !prev)}>
                  <Text style={styles.sectionLabel}>Lähteet</Text>
                  <Text style={styles.sectionToggleText}>{showSources ? 'Piilota' : 'Näytä'}</Text>
                </Pressable>
                {showSources && (
                  <View style={styles.categoryRow}>
                    {sourceOptions.map((option) => {
                      const active = sourceFilters.includes(option.name)
                      return (
                        <Pressable
                          key={option.name}
                          style={[styles.filterChip, active && styles.filterChipActive]}
                          onPress={() => toggleMulti(option.name, setSourceFilters, sourceFilters)}
                        >
                          <Text style={[styles.filterChipText, active && styles.filterChipTextActive]}>
                            {option.name} ({option.count})
                          </Text>
                        </Pressable>
                      )
                    })}
                  </View>
                )}
              </View>
            </>
          )}
          ListFooterComponent={
            loadingMore
              ? <ActivityIndicator style={{ marginVertical: 16 }} color="#1a1a1a" />
              : !hasMoreRef.current && items.length > 0
                ? <Text style={styles.endText}>— Kaikki ladattu —</Text>
                : hasMoreRef.current && items.length > 0
                  ? (
                    <Pressable style={styles.loadMoreBtn} onPress={loadMore}>
                      <Text style={styles.loadMoreText}>Lataa lisää ({PAGE_SIZE} kerrallaan)</Text>
                    </Pressable>
                  )
                  : null
          }
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
  detailContainer: {
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
  detailHeader: {
    paddingTop: 56,
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 3,
    borderBottomColor: '#FFB700',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  detailContent: {
    padding: 16,
    gap: 10,
  },
  detailMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailSource: {
    fontSize: 11,
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginTop: 4,
  },
  detailTitle: {
    fontSize: 25,
    lineHeight: 34,
    fontFamily: 'Georgia',
    color: '#111827',
    marginTop: 6,
  },
  detailCategories: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  detailSectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#111827',
    marginTop: 14,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  detailBullet: {
    fontSize: 15,
    lineHeight: 24,
    color: '#1f2937',
  },
  openLinkBtn: {
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#111827',
    borderRadius: 2,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: '#111827',
  },
  openLinkText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
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
    color: '#6b7280',
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
  sectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginTop: 4,
  },
  sectionToggle: {
    marginTop: 4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionToggleText: {
    fontSize: 12,
    color: '#6b7280',
    fontWeight: '600',
  },
  categoryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  categoryChip: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 999,
    backgroundColor: '#ffffff',
  },
  categoryChipText: {
    fontSize: 12,
    color: '#4b5563',
    fontWeight: '600',
  },
  filterChip: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 999,
    backgroundColor: '#ffffff',
  },
  filterChipActive: {
    backgroundColor: '#111827',
    borderColor: '#111827',
  },
  filterChipText: {
    fontSize: 12,
    color: '#374151',
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: '#ffffff',
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
    flexShrink: 1,
  },
  scoreBadge: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1f2937',
    backgroundColor: '#f3f4f6',
    borderWidth: 1,
    borderColor: '#d1d5db',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 999,
  },
  itemCategories: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  itemCategoryChip: {
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderWidth: 1,
    borderRadius: 999,
    backgroundColor: '#ffffff',
  },
  itemCategoryText: {
    fontSize: 11,
    fontWeight: '600',
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
  loadMoreBtn: {
    margin: 16,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#1a1a1a',
    borderRadius: 2,
  },
  loadMoreText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1a1a1a',
    letterSpacing: 0.5,
  },
  endText: {
    textAlign: 'center',
    marginVertical: 20,
    color: '#999',
    fontSize: 12,
    letterSpacing: 1,
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
