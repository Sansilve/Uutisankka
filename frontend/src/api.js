const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

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

export function fetchBriefing(limit = 10) {
  return request(`/api/briefing?limit=${limit}`)
}

export function triggerIngest() {
  return request('/api/ingest', { method: 'POST' })
}

export function fetchPreferences() {
  return request('/api/preferences')
}

export function updatePreferences(payload) {
  return request('/api/preferences', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function sendFeedback(payload) {
  return request('/api/feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchMetrics(limit = 10) {
  return request(`/api/metrics?limit=${limit}`)
}
