/**
 * Component tests for ArticleCard (Issue #16)
 *
 * Covers:
 *  - Renders with required story data
 *  - Displays article title and source
 *  - Renders topic badges
 *  - "Kiinnostaa" / "Ohita" action buttons exist and trigger onDecision
 */
import React from 'react'
import { fireEvent, render } from '@testing-library/react-native'

import ArticleCard from '../src/components/ArticleCard'

const STORY = {
  id: 1,
  title: 'Testi: Suomen teknologiasektori kasvaa',
  source: 'yle.fi',
  published_at: '2026-05-02T10:00:00',
  url: 'https://yle.fi/uutiset/testi',
  score: 7.5,
  base_score: 7.5,
  feedback_score: 0,
  feedback_positive: 0,
  feedback_negative: 0,
  topics: ['teknologia', 'talous'],
  summary: {
    bullets: ['Ensimmäinen tietopiste tähän.', 'Toinen kohta tähän.'],
  },
  score_breakdown: {
    items: [{ reason: 'Kiinnostava aihe', points: 2.5 }],
  },
  is_paywall: false,
}

function renderCard(overrides = {}) {
  const props = {
    story: { ...STORY, ...overrides },
    onDecision: jest.fn(),
    disabled: false,
    progressText: '1 / 10',
    progressWidth: '10%',
    onSurprise: jest.fn(),
  }
  return { ...render(<ArticleCard {...props} />), props }
}

describe('ArticleCard', () => {
  // Patch Animated.timing to call its callback synchronously so the
  // settleCard animation resolves immediately in tests.
  let timingSpy
  beforeAll(() => {
    const { Animated } = require('react-native')
    timingSpy = jest
      .spyOn(Animated, 'timing')
      .mockImplementation((_value, _config) => ({
        start: (cb) => { if (cb) cb({ finished: true }) },
      }))
  })
  afterAll(() => {
    if (timingSpy) timingSpy.mockRestore()
  })
  it('renders without crashing', () => {
    renderCard()
  })

  it('displays the article title', () => {
    const { getByText } = renderCard()
    expect(getByText('Testi: Suomen teknologiasektori kasvaa')).toBeTruthy()
  })

  it('displays the source name', () => {
    const { getByText } = renderCard()
    expect(getByText(/yle\.fi/i)).toBeTruthy()
  })

  it('renders topic badges for provided topics', () => {
    const { getByText } = renderCard()
    expect(getByText('Teknologia')).toBeTruthy()
    expect(getByText('Talous')).toBeTruthy()
  })

  it('renders the Kiinnostaa action button', () => {
    const { getAllByText } = renderCard()
    expect(getAllByText(/kiinnostaa/i).length).toBeGreaterThan(0)
  })

  it('renders the Ohita action button', () => {
    const { getAllByText } = renderCard()
    expect(getAllByText(/ohita/i).length).toBeGreaterThan(0)
  })

  it('calls onDecision(true) when Kiinnostaa is pressed', () => {
    const { getByText, props } = renderCard()
    // Exact button label from the component source
    fireEvent.press(getByText('Kiinnostaa  👍'))
    expect(props.onDecision).toHaveBeenCalledWith(true)
  })

  it('calls onDecision(false) when Ohita is pressed', () => {
    const { getByText, props } = renderCard()
    fireEvent.press(getByText('👎  Ohita'))
    expect(props.onDecision).toHaveBeenCalledWith(false)
  })

  it('shows paywall badge when is_paywall is true', () => {
    const { getByText } = renderCard({ is_paywall: true })
    expect(getByText(/maksumuuri/i)).toBeTruthy()
  })

  it('expands score breakdown when why-toggle is pressed', () => {
    const { getByText } = renderCard()
    const toggle = getByText(/miksi suosittelemme/i)
    fireEvent.press(toggle)
    // Breakdown reason should now be visible
    expect(getByText('Kiinnostava aihe')).toBeTruthy()
  })

  it('displays progress text', () => {
    const { getByText } = renderCard()
    expect(getByText('1 / 10')).toBeTruthy()
  })
})
