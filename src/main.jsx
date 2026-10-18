import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ErrorBoundary } from './components/ErrorBoundary.jsx'
import './index.css'

// Точка входа приложения: монтируем корневой компонент App
// в DOM-элемент с идентификатором "root".
// ErrorBoundary гарантирует видимое сообщение об ошибке вместо белого экрана.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)