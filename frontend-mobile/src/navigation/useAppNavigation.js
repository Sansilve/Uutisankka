import { useState } from 'react'
import { APP_ROUTES } from './routes'

export default function useAppNavigation() {
  const [route, setRoute] = useState(APP_ROUTES.FEED)

  return {
    route,
    openFeed: () => setRoute(APP_ROUTES.FEED),
    openHistory: () => setRoute(APP_ROUTES.HISTORY),
    openAllNews: () => setRoute(APP_ROUTES.ALL_NEWS),
    openSettings: () => setRoute(APP_ROUTES.SETTINGS),
  }
}
