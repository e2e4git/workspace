import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Конфигурация сборщика Vite для React-приложения.
// Плагин react обеспечивает поддержку JSX и Fast Refresh в режиме разработки.
export default defineConfig({
  plugins: [react()],
  server: {
    // Слушаем все сетевые интерфейсы (доступ извне контейнера/по проброшенному порту)
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
  },
})