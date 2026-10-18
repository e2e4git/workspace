import { Component } from 'react'

/**
 * Граница ошибок (Error Boundary).
 * Перехватывает исключения рендера React и показывает понятное сообщение
 * вместо «белого экрана», что упрощает диагностику.
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Дублируем ошибку в консоль для быстрой отладки
    console.error('React render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            background: '#0b0420',
            color: '#e2e8f0',
            fontFamily: 'system-ui, sans-serif',
            textAlign: 'center',
          }}
        >
          <h1 style={{ margin: 0, fontSize: '1.25rem' }}>
            Ошибка рендера приложения
          </h1>
          <pre
            style={{
              maxWidth: '90vw',
              overflow: 'auto',
              padding: '1rem',
              background: '#1b0733',
              border: '1px solid #ff2d95',
              borderRadius: '12px',
              color: '#ff6b9d',
              fontSize: '0.85rem',
            }}
          >
            {String(this.state.error?.message || this.state.error)}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}
