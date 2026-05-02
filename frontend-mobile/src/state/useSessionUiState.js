import { useEffect, useState } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'

export default function useSessionUiState() {
  const [onboardingDone, setOnboardingDone] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [fatalError, setFatalError] = useState(null)

  useEffect(() => {
    let isMounted = true
    AsyncStorage.getItem('onboarding_done').then((value) => {
      if (!isMounted) return
      setOnboardingDone(value === 'true')
    })
    return () => {
      isMounted = false
    }
  }, [])

  async function completeOnboarding() {
    await AsyncStorage.setItem('onboarding_done', 'true')
    setOnboardingDone(true)
  }

  function setErrorStatus(error) {
    const message = error?.message || 'Tuntematon virhe'
    setStatusMsg(`Virhe: ${message}`)
  }

  function markFatalError(error) {
    const message = error?.message || 'Tuntematon virhe'
    setFatalError(message)
  }

  function clearFatalError() {
    setFatalError(null)
  }

  return {
    onboardingDone,
    loading,
    busy,
    statusMsg,
    fatalError,
    setOnboardingDone,
    setLoading,
    setBusy,
    setStatusMsg,
    setErrorStatus,
    markFatalError,
    clearFatalError,
    completeOnboarding,
  }
}
