/**
 * SynthwaveEngine — генератор электронного Synthwave-трека (120 BPM) на Web Audio API.
 *
 * Ключевые особенности:
 *  - Опережающий планировщик (Lookahead Scheduler): таймер setInterval каждые 25мс
 *    просматривает окно вперёд (100мс) и заранее планирует ноты с точными аудио-таймингами.
 *  - Синтез «на лету» без внешних медиафайлов: Kick, Snare, Hi-hat (шум), Bass, Lead-арпеджио.
 *  - Выход сведён в AnalyserNode — источник данных для визуализации спектра.
 *  - Структура: интро (такты 1–8), кульминация/дроп (такты 9–24), аутро (такты 25–32).
 */

// Музыкальные константы времени
const BPM = 120                    // темп
const BEAT = 60 / BPM              // длительность доли, сек (0.5с)
const STEP = BEAT / 4              // длительность 16-й ноты, сек (0.125с)
const STEPS_PER_BAR = 16           // 16-е шаги в такте (4/4)
const TOTAL_BARS = 32              // всего тактов в треке
const TOTAL_STEPS = TOTAL_BARS * STEPS_PER_BAR

// Параметры планировщика
const LOOKAHEAD = 0.1              // окно опережающего планирования, сек
const SCHED_INTERVAL = 25          // период таймера планировщика, мс

// Аккордовая прогрессия synthwave: Am — F — C — G (по одному такту на аккорд).
// root — нота баса (MIDI), chord — ноты аккорда для арпеджио (MIDI).
const PROGRESSION = [
  { root: 33, chord: [57, 60, 64, 69] }, // Am
  { root: 29, chord: [53, 57, 60, 65] }, // F
  { root: 36, chord: [48, 52, 55, 60] }, // C
  { root: 31, chord: [55, 59, 62, 67] }, // G
]

/** Перевод MIDI-ноты в частоту в герцах. */
const midiToFreq = (midi) => 440 * Math.pow(2, (midi - 69) / 12)

/** Полная длительность трека в секундах. */
export const TOTAL_DURATION = TOTAL_STEPS * STEP

export class SynthwaveEngine {
  constructor() {
    this.ctx = null
    this.master = null
    this.analyser = null
    this.freqData = null

    // Узлы-шины (маршрутизация инструментов)
    this.drumBus = null
    this.bassBus = null
    this.leadDelay = null

    this.noiseBuffer = null

    // Состояние воспроизведения
    this.isPlaying = false
    this.startTime = 0          // аудио-время старта текущего «запуска»
    this.positionAtStart = 0    // позиция (в шагах) на момент старта
    this.pausedStep = 0         // позиция на паузе (в шагах)
    this.stepCursor = 0         // индекс следующего шага для планирования
    this.nextNoteTime = 0       // аудио-время следующей ноты
    this.timerId = null
    this.activeNodes = new Set()
  }

  /** Ленивая инициализация аудио-графа (требует пользовательского жеста). */
  init() {
    if (this.ctx) return
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    this.ctx = new AudioCtx()

    // Главный гейн микса
    this.master = this.ctx.createGain()
    this.master.gain.value = 0.85

    // Компрессор для плотного «клубного» звучания
    const comp = this.ctx.createDynamicsCompressor()
    comp.threshold.value = -14
    comp.knee.value = 24
    comp.ratio.value = 3.5
    comp.attack.value = 0.004
    comp.release.value = 0.18

    // Анализатор спектра — отдаёт данные визуализатору
    this.analyser = this.ctx.createAnalyser()
    this.analyser.fftSize = 2048
    this.analyser.smoothingTimeConstant = 0.8
    this.freqData = new Uint8Array(this.analyser.frequencyBinCount)

    this.master.connect(comp)
    comp.connect(this.analyser)
    this.analyser.connect(this.ctx.destination)

    // Шины инструментов -> master
    this.drumBus = this.ctx.createGain()
    this.drumBus.gain.value = 1.0
    this.drumBus.connect(this.master)

    this.bassBus = this.ctx.createGain()
    this.bassBus.gain.value = 0.9
    this.bassBus.connect(this.master)

    // Лид-шина с delay-эффектом (dotted 8-я нота)
    this.leadDelay = this.ctx.createGain()
    const delay = this.ctx.createDelay(1.0)
    delay.delayTime.value = STEP * 6 // ≈ 0.375с — dotted eighth
    const feedback = this.ctx.createGain()
    feedback.gain.value = 0.35
    const wet = this.ctx.createGain()
    wet.gain.value = 0.3
    this.leadDelay.connect(delay)
    delay.connect(feedback)
    feedback.connect(delay)
    delay.connect(wet)
    wet.connect(this.master)

    // Буфер белого шума для ударных и хэтов
    this.noiseBuffer = this._createNoiseBuffer(1)
  }

  /** Создание моно-буфера белого шума заданной длительности. */
  _createNoiseBuffer(seconds) {
    const length = Math.floor(this.ctx.sampleRate * seconds)
    const buffer = this.ctx.createBuffer(1, length, this.ctx.sampleRate)
    const data = buffer.getChannelData(0)
    for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1
    return buffer
  }

  /** Регистрация источника для последующей остановки (при pause/seek). */
  _track(node) {
    this.activeNodes.add(node)
    node.onended = () => this.activeNodes.delete(node)
  }

  /** Немедленная остановка всех запланированных источников. */
  _stopAllActive() {
    for (const node of this.activeNodes) {
      try { node.stop() } catch { /* узел уже остановлен */ }
      try { node.disconnect() } catch { /* безопасно игнорируем */ }
    }
    this.activeNodes.clear()
  }

  // ---------------------------------------------------------------------------
  // Синтезаторы ударных
  // ---------------------------------------------------------------------------

  /** Kick — синусоида с быстрым падением частоты (punchy). */
  kick(time, loud = 1.0) {
    const osc = this.ctx.createOscillator()
    const gain = this.ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(160, time)
    osc.frequency.exponentialRampToValueAtTime(45, time + 0.13)
    gain.gain.setValueAtTime(0.0001, time)
    gain.gain.linearRampToValueAtTime(loud, time + 0.005)
    gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.42)
    osc.connect(gain).connect(this.drumBus)
    osc.start(time)
    osc.stop(time + 0.45)
    this._track(osc)
  }

  /** Snare — высокочастотный шум + короткий тон корпуса. */
  snare(time, loud = 0.8) {
    const noise = this.ctx.createBufferSource()
    noise.buffer = this.noiseBuffer
    const hp = this.ctx.createBiquadFilter()
    hp.type = 'highpass'
    hp.frequency.value = 1200
    const ng = this.ctx.createGain()
    ng.gain.setValueAtTime(loud, time)
    ng.gain.exponentialRampToValueAtTime(0.0001, time + 0.2)
    noise.connect(hp).connect(ng).connect(this.drumBus)
    noise.start(time)
    noise.stop(time + 0.22)
    this._track(noise)

    const body = this.ctx.createOscillator()
    body.type = 'triangle'
    body.frequency.value = 180
    const bg = this.ctx.createGain()
    bg.gain.setValueAtTime(loud * 0.6, time)
    bg.gain.exponentialRampToValueAtTime(0.0001, time + 0.1)
    body.connect(bg).connect(this.drumBus)
    body.start(time)
    body.stop(time + 0.12)
    this._track(body)
  }

  /** Hi-hat — короткий срез высокочастотного шума. */
  hat(time, loud = 0.25) {
    const noise = this.ctx.createBufferSource()
    noise.buffer = this.noiseBuffer
    const hp = this.ctx.createBiquadFilter()
    hp.type = 'highpass'
    hp.frequency.value = 7500
    const g = this.ctx.createGain()
    g.gain.setValueAtTime(loud, time)
    g.gain.exponentialRampToValueAtTime(0.0001, time + 0.05)
    noise.connect(hp).connect(g).connect(this.drumBus)
    noise.start(time)
    noise.stop(time + 0.06)
    this._track(noise)
  }

  // ---------------------------------------------------------------------------
  // Синтезаторы мелодии
  // ---------------------------------------------------------------------------

  /** Bass — пилообразная волна с суб-осциллятором и огибающим фильтром. */
  bass(time, midi, dur, loud = 0.5) {
    const osc = this.ctx.createOscillator()
    osc.type = 'sawtooth'
    osc.frequency.value = midiToFreq(midi)

    const sub = this.ctx.createOscillator()
    sub.type = 'sine'
    sub.frequency.value = midiToFreq(midi - 12)

    const filter = this.ctx.createBiquadFilter()
    filter.type = 'lowpass'
    filter.Q.value = 9
    filter.frequency.setValueAtTime(1400, time)
    filter.frequency.exponentialRampToValueAtTime(320, time + dur)

    const g = this.ctx.createGain()
    g.gain.setValueAtTime(0.0001, time)
    g.gain.linearRampToValueAtTime(loud, time + 0.012)
    g.gain.setValueAtTime(loud, time + dur * 0.7)
    g.gain.exponentialRampToValueAtTime(0.0001, time + dur)

    osc.connect(filter)
    sub.connect(filter)
    filter.connect(g).connect(this.bassBus)
    osc.start(time)
    sub.start(time)
    osc.stop(time + dur + 0.02)
    sub.stop(time + dur + 0.02)
    this._track(osc)
    this._track(sub)
  }

  /** Lead — квадратная волна с фильтром и отправкой в delay (dry + wet). */
  lead(time, midi, dur, loud = 0.22) {
    const osc = this.ctx.createOscillator()
    osc.type = 'square'
    osc.frequency.value = midiToFreq(midi)

    const filter = this.ctx.createBiquadFilter()
    filter.type = 'lowpass'
    filter.frequency.value = 3800
    filter.Q.value = 1

    const g = this.ctx.createGain()
    g.gain.setValueAtTime(0.0001, time)
    g.gain.linearRampToValueAtTime(loud, time + 0.005)
    g.gain.setValueAtTime(loud, time + dur * 0.5)
    g.gain.exponentialRampToValueAtTime(0.0001, time + dur)

    osc.connect(filter).connect(g)
    g.connect(this.master)      // сухой сигнал
    g.connect(this.leadDelay)   // отправка в delay
    osc.start(time)
    osc.stop(time + dur + 0.02)
    this._track(osc)
  }

  // ---------------------------------------------------------------------------
  // Секвенсор
  // ---------------------------------------------------------------------------

  /** Определение фазы сцены по номеру такта (1-based). */
  getPhase(bar) {
    if (bar <= 8) return 'intro'
    if (bar <= 24) return 'drop'
    return 'outro'
  }

  /** Планирование всех нот для одного 16-го шага. */
  scheduleStep(step, time) {
    const bar = Math.floor(step / STEPS_PER_BAR)          // 0..31
    const stepInBar = step % STEPS_PER_BAR                // 0..15
    const beatInBar = Math.floor(stepInBar / 4)           // 0..3
    const phase = this.getPhase(bar + 1)
    const prog = PROGRESSION[bar % PROGRESSION.length]

    // --- Ударные ---
    if (phase === 'drop') {
      if (stepInBar % 4 === 0) this.kick(time, 1.0)       // four-on-the-floor
      if (stepInBar % 2 === 1) this.hat(time, 0.22)
    } else if (phase === 'intro') {
      if (stepInBar === 0 || stepInBar === 8) this.kick(time, 0.85)
    } else {
      if (stepInBar === 0) this.kick(time, 0.8)
      if (stepInBar === 8) this.kick(time, 0.6)
    }

    // Snare на 2-й и 4-й долях такта
    if (stepInBar === 4 || stepInBar === 12) {
      this.snare(time, phase === 'drop' ? 0.9 : 0.6)
    }

    // --- Бас ---
    if (phase === 'drop') {
      if (stepInBar % 2 === 0) this.bass(time, prog.root, STEP * 2 * 0.9, 0.5)
    } else if (phase === 'intro') {
      if (stepInBar === 0 || stepInBar === 8) this.bass(time, prog.root, STEP * 8 * 0.9, 0.4)
    } else {
      if (stepInBar === 0) this.bass(time, prog.root, STEP * 16 * 0.95, 0.35)
    }

    // --- Лид-арпеджио ---
    const arpActive =
      phase === 'drop' ||
      (phase === 'intro' && bar >= 4) ||   // лёгкий намёк во 2-й половине интро
      (phase === 'outro' && bar < 29)      // затухание арпеджио в аутро
    if (arpActive) {
      const notes = prog.chord
      let note = notes[stepInBar % notes.length]
      // Октавный «взлёт» в конце каждой 4-й доли на дропе — драйв
      if (phase === 'drop' && beatInBar === 3 && stepInBar % 2 === 0) note += 12
      this.lead(time, note, STEP * 1.2, phase === 'drop' ? 0.22 : 0.16)
    }
  }

  /** Цикл опережающего планирования: наполняет буфер нот на LOOKAHEAD вперёд. */
  _scheduler() {
    while (this.nextNoteTime < this.ctx.currentTime + LOOKAHEAD) {
      this.scheduleStep(this.stepCursor, this.nextNoteTime)
      this.nextNoteTime += STEP
      this.stepCursor = (this.stepCursor + 1) % TOTAL_STEPS
    }
  }

  // ---------------------------------------------------------------------------
  // Управление транспортом
  // ---------------------------------------------------------------------------

  /** Запуск/возобновление воспроизведения. */
  async play() {
    this.init()
    if (this.ctx.state === 'suspended') await this.ctx.resume()
    if (this.isPlaying) return
    this.isPlaying = true
    this.startTime = this.ctx.currentTime
    this.positionAtStart = this.pausedStep
    this.stepCursor = Math.floor(this.pausedStep)
    this.nextNoteTime = this.ctx.currentTime + 0.05
    this.timerId = setInterval(() => this._scheduler(), SCHED_INTERVAL)
  }

  /** Пауза с сохранением текущей позиции. */
  pause() {
    if (!this.isPlaying) return
    this.pausedStep = this.getPositionSteps()
    this.isPlaying = false
    clearInterval(this.timerId)
    this.timerId = null
    this._stopAllActive()
  }

  /** Перемотка в позицию (в секундах). */
  seek(seconds) {
    const clamped = Math.max(0, Math.min(TOTAL_DURATION - 0.01, seconds))
    const step = clamped / STEP
    this.pausedStep = step % TOTAL_STEPS
    if (this.isPlaying) {
      this._stopAllActive()
      this.startTime = this.ctx.currentTime
      this.positionAtStart = this.pausedStep
      this.stepCursor = Math.floor(this.pausedStep)
      this.nextNoteTime = this.ctx.currentTime + 0.05
    }
  }

  /** Текущая позиция в шагах (с учётом зацикливания трека). */
  getPositionSteps() {
    if (!this.ctx) return this.pausedStep
    if (!this.isPlaying) return this.pausedStep
    const elapsed = this.ctx.currentTime - this.startTime
    return (this.positionAtStart + elapsed / STEP) % TOTAL_STEPS
  }

  /** Текущая позиция в секундах. */
  getPositionSeconds() {
    return this.getPositionSteps() * STEP
  }

  /** Текущие данные спектра (Uint8Array), диапазон 0..255. */
  getFrequencyData() {
    if (!this.analyser) return null
    this.analyser.getByteFrequencyData(this.freqData)
    return this.freqData
  }

  /** Сброс аудио-графа (при размонтировании компонента). */
  dispose() {
    this.pause()
    if (this.ctx) this.ctx.close()
    this.ctx = null
  }
}
