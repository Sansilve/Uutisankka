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
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }
  return response.json()
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
export const fetchAllArticles = (limit = 300, includePaywall = false) =>
  request(`/api/articles?limit=${limit}&include_paywall=${includePaywall ? 'true' : 'false'}`)
export const triggerIngest = () => request('/api/ingest', { method: 'POST' })
export const triggerReenrich = () => request('/api/admin/reenrich', { method: 'POST' })
export const fetchReenrichStatus = () => request('/api/admin/reenrich/status')
