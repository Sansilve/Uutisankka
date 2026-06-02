import { useEffect, useState } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'

export default function useSessionUiState() {
  const [onboardingDone, setOnboardingDone] = useState(null)
  const [swipeTutorialShown, setSwipeTutorialShown] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [fatalError, setFatalError] = useState(null)

  useEffect(() => {
    let isMounted = true
    Promise.all([
      AsyncStorage.getItem('onboarding_done'),
      AsyncStorage.getItem('swipe_tutorial_shown'),
    ]).then(([onboardingValue, tutorialValue]) => {
      if (!isMounted) return
      setOnboardingDone(onboardingValue === 'true')
      setSwipeTutorialShown(tutorialValue === 'true')
    })
    return () => {
      isMounted = false
    }
  }, [])

  async function completeOnboarding() {
    await AsyncStorage.setItem('onboarding_done', 'true')
    setOnboardingDone(true)
  }

  async function markSwipeTutorialShown() {
    await AsyncStorage.setItem('swipe_tutorial_shown', 'true')
    setSwipeTutorialShown(true)
  }

  function setErrorStatus(error) {
    const detail = error?.message ? ` (${error.message})` : ''
    const message = `Uutisia ei voitu ladata. Tarkista yhteys.${detail}`
    setStatusMsg(`Virhe: ${message}`)
  }

  function markFatalError(error) {
    const detail = error?.message ? ` (${error.message})` : ''
    const message = `Uutisia ei voitu ladata. Tarkista yhteys.${detail}`
    setFatalError(message)
  }

  function clearFatalError() {
    setFatalError(null)
  }

  return {
    onboardingDone,
    swipeTutorialShown,
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
    markSwipeTutorialShown,
  }
}
