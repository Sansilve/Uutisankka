import { Platform } from 'react-native'

const LAN_API_BASE = 'http://192.168.10.50:8000'

function normalizeApiBase(url) {
  if (!url || typeof url !== 'string') return ''
  return url.trim().replace(/\/+$/, '')
}

function getApiBase() {
  const envApiBase = normalizeApiBase(process?.env?.EXPO_PUBLIC_API_BASE)
  if (envApiBase) {
    return envApiBase
  }

  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000'
    }
    return `http://${hostname}:8000`
  }
  return LAN_API_BASE
}

const API_BASE = getApiBase()

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    let message = ''
    try {
      const payload = await response.json()
      message = payload?.detail || payload?.message || ''
    } catch {
      const text = await response.text()
      message = text || ''
    }
    throw new Error(message || `Request failed: ${response.status}`)
  }
  return response.json()
}

function buildAllArticlesQuery(params = {}) {
  const query = new URLSearchParams()
  query.set('limit', String(params.limit ?? 50))
  query.set('offset', String(params.offset ?? 0))
  query.set('include_paywall', params.includePaywall ? 'true' : 'false')

  for (const scope of params.scopes || []) query.append('scopes', scope)
  for (const city of params.localCities || []) query.append('local_cities', city)
  for (const category of params.categories || []) query.append('categories', category)
  for (const source of params.sources || []) query.append('sources', source)
  for (const tone of params.tones || []) query.append('tones', tone)

  return query.toString()
}

function buildFacetsQuery(params = {}) {
  const query = new URLSearchParams()
  query.set('include_paywall', params.includePaywall ? 'true' : 'false')
  for (const scope of params.scopes || []) query.append('scopes', scope)
  for (const city of params.localCities || []) query.append('local_cities', city)
  return query.toString()
}

export const fetchBriefing = (limit = 10) => request(`/api/briefing?limit=${limit}`)
export const fetchRandomBriefing = (limit = 10) => request(`/api/briefing/random?limit=${limit}`)
export const fetchPreferences = () => request('/api/preferences')
export const updatePreferences = (payload) =>
  request('/api/preferences', { method: 'PUT', body: JSON.stringify(payload) })
export const sendFeedback = (payload) =>
  request('/api/feedback', { method: 'POST', body: JSON.stringify(payload) })
export const fetchMetrics = (limit = 10) => request(`/api/metrics?limit=${limit}`)
export const fetchHistory = (limit = 100) => request(`/api/history?limit=${limit}`)
export const fetchAllArticles = (params = {}) =>
  request(`/api/articles?${buildAllArticlesQuery(params)}`)
export const fetchAllArticleFacets = (params = {}) =>
  request(`/api/articles/facets?${buildFacetsQuery(params)}`)
export const triggerIngest = () => request('/api/ingest', { method: 'POST' })
export const triggerReenrich = () => request('/api/admin/reenrich', { method: 'POST' })
export const fetchReenrichStatus = () => request('/api/admin/reenrich/status')
