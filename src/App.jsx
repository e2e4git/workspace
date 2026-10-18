import { useCallback, useEffect, useRef, useState } from 'react'
import { SynthwaveEngine, TOTAL_DURATION } from './audio/SynthwaveEngine'
import { Visualizer } from './visualizer/Visualizer'
import './App.css'

/** Форматирование секунд в строку mm:ss. */
function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/**
 * Корневой компонент — плеер Synthwave-клипа.
 * Связывает аудио-движок (Web Audio API), визуализатор (Canvas) и интерфейс управления.
 */
function App() {
  const canvasRef = useRef(null)
  const stageRef = useRef(null)
  const sliderRef = useRef(null)
  const timeRef = useRef(null)
  const engineRef = useRef(null)
  const visualizerRef = useRef(null)
  const rafRef = useRef(0)
  const scrubbingRef = useRef(false)

  const [isPlaying, setIsPlaying] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Инициализация движка и визуализатора + цикл обновления таймлайна
  useEffect(() => {
    const engine = new SynthwaveEngine()
    engineRef.current = engine

    const visualizer = new Visualizer(canvasRef.current, engine)
    visualizerRef.current = visualizer
    visualizer.start()

    // Единый цикл: обновляем позицию ползунка и метку времени напрямую в DOM
    const tick = () => {
      const pos = engine.getPositionSeconds()
      const slider = sliderRef.current
      if (slider && !scrubbingRef.current) {
        slider.value = String(pos)
        slider.style.setProperty('--progress', `${(pos / TOTAL_DURATION) * 100}%`)
      }
      if (timeRef.current) {
        timeRef.current.textContent = `${formatTime(pos)} / ${formatTime(TOTAL_DURATION)}`
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)

    // Отслеживаем выход из полноэкранного режима
    const onFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement))
      // Даём браузеру применить новый размер и пересчитываем холст
      requestAnimationFrame(() => visualizerRef.current?.resize())
    }
    document.addEventListener('fullscreenchange', onFsChange)

    return () => {
      cancelAnimationFrame(rafRef.current)
      document.removeEventListener('fullscreenchange', onFsChange)
      visualizer.dispose()
      engine.dispose()
    }
  }, [])

  /** Переключение воспроизведения (Play/Pause). */
  const togglePlay = useCallback(async () => {
    const engine = engineRef.current
    if (engine.isPlaying) {
      engine.pause()
      setIsPlaying(false)
    } else {
      await engine.play()
      setIsPlaying(true)
    }
  }, [])

  /** Скраббинг таймлайна: перемотка по позиции ползунка. */
  const handleSeek = useCallback((event) => {
    const value = Number(event.target.value)
    const engine = engineRef.current
    engine.seek(value)
    // Мгновенно синхронизируем визуальные элементы
    event.target.style.setProperty('--progress', `${(value / TOTAL_DURATION) * 100}%`)
    if (timeRef.current) {
      timeRef.current.textContent = `${formatTime(value)} / ${formatTime(TOTAL_DURATION)}`
    }
  }, [])

  /** Переключение полноэкранного режима для сцены. */
  const toggleFullscreen = useCallback(async () => {
    const stage = stageRef.current
    if (!stage) return
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen()
      } else {
        await stage.requestFullscreen()
      }
    } catch {
      // Полноэкранный режим может быть недоступен в некоторых браузерах
    }
  }, [])

  return (
    <main className="app">
      {/* Сцена: холст визуализации + кнопка Fullscreen */}
      <div className="stage" ref={stageRef}>
        <canvas className="stage__canvas" ref={canvasRef} />

        <button
          type="button"
          className="stage__fullscreen"
          onClick={toggleFullscreen}
          aria-label={isFullscreen ? 'Выйти из полноэкранного режима' : 'Полноэкранный режим'}
          title={isFullscreen ? 'Выйти из полноэкранного режима' : 'Полноэкранный режим'}
        >
          {isFullscreen ? '⤢' : '⛶'}
        </button>
      </div>

      {/* Панель управления */}
      <div className="controls">
        <button
          type="button"
          className="controls__play"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Пауза' : 'Воспроизвести'}
        >
          {isPlaying ? '❚❚' : '▶'}
        </button>

        <div className="controls__timeline">
          <input
            ref={sliderRef}
            type="range"
            className="controls__range"
            min="0"
            max={TOTAL_DURATION}
            step="0.05"
            defaultValue="0"
            onPointerDown={() => { scrubbingRef.current = true }}
            onPointerUp={() => { scrubbingRef.current = false }}
            onPointerCancel={() => { scrubbingRef.current = false }}
            onChange={handleSeek}
            aria-label="Позиция трека"
          />
          <span className="controls__time" ref={timeRef}>
            00:00 / {formatTime(TOTAL_DURATION)}
          </span>
        </div>
      </div>
    </main>
  )
}

export default App
