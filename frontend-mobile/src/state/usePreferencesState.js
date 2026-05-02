import { useState } from 'react'

const EMPTY_PREFERENCES = { interests: [], disliked_topics: [] }

export default function usePreferencesState() {
  const [preferences, setPreferences] = useState(EMPTY_PREFERENCES)

  function applyPreferences(nextPreferences) {
    setPreferences(nextPreferences || EMPTY_PREFERENCES)
  }

  return {
    preferences,
    setPreferences,
    applyPreferences,
  }
}
