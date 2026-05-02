import { Component, StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '2rem', fontFamily: 'monospace', color: '#b91c1c', background: '#fff0f0', margin: '2rem', borderRadius: '0.5rem', border: '1px solid #fca5a5' }}>
          <strong>Render error:</strong>
          <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem' }}>{this.state.error?.message}{'\n'}{this.state.error?.stack}</pre>
        </div>
      )
    }
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
