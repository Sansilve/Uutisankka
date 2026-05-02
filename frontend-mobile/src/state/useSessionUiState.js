import { useEffect, useState } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'

export default function useSessionUiState() {
  const [onboardingDone, setOnboardingDone] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

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

  return {
    onboardingDone,
    loading,
    busy,
    statusMsg,
    setOnboardingDone,
    setLoading,
    setBusy,
    setStatusMsg,
    setErrorStatus,
    completeOnboarding,
  }
}
