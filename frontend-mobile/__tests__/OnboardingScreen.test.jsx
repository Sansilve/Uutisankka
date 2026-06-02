/**
 * Component tests for OnboardingScreen (Issue #16)
 *
 * Covers:
 *  - Renders welcome step without crashing
 *  - "Seuraava" button advances to next step
 *  - onComplete callback is invoked after saving preferences
 */
import React from 'react'
import { fireEvent, render, waitFor } from '@testing-library/react-native'

import OnboardingScreen from '../src/components/OnboardingScreen'

// Mock the API module so no real HTTP calls are made.
jest.mock('../src/api', () => ({
  updatePreferences: jest.fn().mockResolvedValue({}),
}))

const { updatePreferences } = require('../src/api')

describe('OnboardingScreen', () => {
  beforeEach(() => {
    updatePreferences.mockClear()
  })

  it('renders without crashing', () => {
    render(<OnboardingScreen onComplete={jest.fn()} />)
  })

  it('shows welcome step content on first render', () => {
    const { getAllByText } = render(<OnboardingScreen onComplete={jest.fn()} />)
    // The welcome step contains "TERVETULOA" heading
    expect(getAllByText(/tervetuloa/i).length).toBeGreaterThan(0)
  })

  it('advances to next step when Aloita is pressed on welcome step', () => {
    const { getByText, queryByText } = render(
      <OnboardingScreen onComplete={jest.fn()} />,
    )
    // Step 0 (welcome) uses "Aloita →" as the primary button
    const btn = getByText(/aloita/i)
    fireEvent.press(btn)
    // After step 0 → step 1, the welcome text should be gone
    expect(queryByText(/tervetuloa/i)).toBeNull()
  })

  it('calls onComplete after finishing all steps and saving', async () => {
    const onComplete = jest.fn()
    const { getAllByText } = render(
      <OnboardingScreen onComplete={onComplete} />,
    )

    // Step 0: welcome → press "Aloita →"
    fireEvent.press(getAllByText(/aloita/i)[0])
    // Step 1: scope → press "Seuraava →"
    fireEvent.press(getAllByText(/seuraava/i)[0])
    // Step 2: interests → press "Seuraava →"
    fireEvent.press(getAllByText(/seuraava/i)[0])
    // Step 3: dislikes/finish → press "Aloita lukeminen →"
    fireEvent.press(getAllByText(/aloita lukeminen/i)[0])

    await waitFor(() => expect(updatePreferences).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1))
  })
})
