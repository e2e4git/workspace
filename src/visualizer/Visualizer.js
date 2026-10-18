/**
 * Visualizer — отрисовка клипа на HTML5 Canvas.
 *
 * Слои сцены:
 *  1. Синтвейв-фон: градиентное небо, полосатое «солнце», перспективная сетка.
 *  2. Система частиц, реагирующая на частотные диапазоны (низы/середины/верха).
 *  3. Процедурный 2D-персонаж по центру: масштаб и движение зависят от бита (бас).
 *  4. Кинетическая типографика: слово меняется на каждую долю такта.
 *  5. Тряска экрана на фазе дропа (кульминация).
 *
 * Три фазы сцены синхронизированы с движком:
 *  - intro (такты 1–8), drop (такты 9–24), outro (такты 25–32).
 */

// Слова кинетической типографики по фазам (индексируются долей такта)
const PHASE_WORDS = {
  intro: ['SYNTH', 'NIGHT', 'DRIVE', 'NEON'],
  drop: ['DROP', 'PULSE', 'FIRE', 'IMPACT'],
  outro: ['FADE', 'DREAM', 'ECHO', 'HOME'],
}

// Неоновая палитра (hue в градусах HSL)
const HUE_BASS = 320 // маджента
const HUE_MID = 190  // циан
const HUE_HIGH = 50  // жёлтый

export class Visualizer {
  constructor(canvas, engine) {
    this.canvas = canvas
    this.c = canvas.getContext('2d')
    this.engine = engine
    this.particles = []
    this.running = false
    this.raf = 0
    this.dpr = Math.min(window.devicePixelRatio || 1, 2)
    this.w = 0
    this.h = 0

    this._onResize = () => this.resize()
    window.addEventListener('resize', this._onResize)
    this.resize()
  }

  /** Пересчёт размеров холста под CSS-размер контейнера с учётом DPR. */
  resize() {
    const rect = this.canvas.getBoundingClientRect()
    const w = rect.width || this.canvas.clientWidth || 360
    const h = rect.height || this.canvas.clientHeight || 240
    this.w = w
    this.h = h
    this.canvas.width = Math.round(w * this.dpr)
    this.canvas.height = Math.round(h * this.dpr)
    // После изменения width/height трансформация сбрасывается — задаём заново.
    this.c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
  }

  start() {
    if (this.running) return
    this.running = true
    this._frame()
  }

  stop() {
    this.running = false
    if (this.raf) cancelAnimationFrame(this.raf)
  }

  dispose() {
    this.stop()
    window.removeEventListener('resize', this._onResize)
  }

  _frame = () => {
    if (!this.running) return
    this.draw()
    this.raf = requestAnimationFrame(this._frame)
  }

  /** Расчёт энергии по частотным диапазонам (нормировано 0..1). */
  _bands() {
    const data = this.engine.getFrequencyData()
    const res = { bass: 0, mid: 0, high: 0, overall: 0 }
    if (!data) return res
    const n = data.length
    const avg = (a, b) => {
      let s = 0
      for (let i = a; i < b; i++) s += data[i]
      return s / ((b - a) * 255)
    }
    res.bass = Math.min(1, avg(1, Math.floor(n * 0.02)) * 1.5)
    res.mid = Math.min(1, avg(Math.floor(n * 0.02), Math.floor(n * 0.15)) * 1.6)
    res.high = Math.min(1, avg(Math.floor(n * 0.15), Math.floor(n * 0.5)) * 1.8)
    res.overall = Math.min(1, (res.bass * 1.5 + res.mid + res.high * 0.8) / 3)
    return res
  }

  draw() {
    const { c, w, h } = this
    const t = performance.now()
    const bands = this._bands()

    // Музыкальная позиция
    const steps = this.engine.getPositionSteps()
    const bar = Math.floor(steps / 16) + 1
    const stepInBar = Math.floor(steps % 16)
    const beat = Math.floor(stepInBar / 4)
    const fracBeat = (steps % 4) / 4
    const beatPulse = Math.pow(1 - fracBeat, 4) // всплеск в начале каждой доли
    const phase = this.engine.getPhase(bar)

    // Тряска экрана: активна на дропе, усиливается басом и ударом доли
    const shake =
      phase === 'drop' ? 1.5 + bands.overall * 7 + beatPulse * 9 : 0
    const sx = (Math.random() * 2 - 1) * shake
    const sy = (Math.random() * 2 - 1) * shake

    c.save()
    c.translate(sx, sy)

    this._drawBackground(w, h, t)
    this._updateParticles(bands, w, h, phase)
    this._drawCharacter(w / 2, h * 0.46, bands, beatPulse, phase, t)
    this._drawTypography(w, h, bands, beatPulse, phase, bar, beat)

    c.restore()

    this._drawVignette(w, h, bands)
  }

  // ---------------------------------------------------------------------------
  // Фон
  // ---------------------------------------------------------------------------

  _drawBackground(w, h, t) {
    const c = this.c

    // Небо: градиент от глубокого фиолетового к тёмному
    const sky = c.createLinearGradient(0, 0, 0, h)
    sky.addColorStop(0, '#0b0420')
    sky.addColorStop(0.45, '#1b0733')
    sky.addColorStop(0.75, '#2a0a44')
    sky.addColorStop(1, '#0b0420')
    c.fillStyle = sky
    c.fillRect(0, 0, w, h)

    // Солнце с горизонтальными полосами
    const sunR = Math.min(w, h) * 0.22
    const sunX = w / 2
    const sunY = h * 0.44

    const glow = c.createRadialGradient(sunX, sunY, 0, sunX, sunY, sunR * 2.2)
    glow.addColorStop(0, 'rgba(255,45,149,0.85)')
    glow.addColorStop(0.4, 'rgba(255,120,80,0.30)')
    glow.addColorStop(1, 'rgba(0,0,0,0)')
    c.fillStyle = glow
    c.beginPath()
    c.arc(sunX, sunY, sunR * 2.2, 0, Math.PI * 2)
    c.fill()

    c.save()
    c.beginPath()
    c.arc(sunX, sunY, sunR, 0, Math.PI * 2)
    c.clip()
    const sunGrad = c.createLinearGradient(0, sunY - sunR, 0, sunY + sunR)
    sunGrad.addColorStop(0, '#ffe14d')
    sunGrad.addColorStop(0.5, '#ff6b9d')
    sunGrad.addColorStop(1, '#b16cea')
    c.fillStyle = sunGrad
    c.fillRect(sunX - sunR, sunY - sunR, sunR * 2, sunR * 2)
    // Полосы на нижней половине солнца
    c.fillStyle = 'rgba(11,4,32,0.85)'
    const lines = 8
    for (let i = 0; i < lines; i++) {
      const p = i / (lines - 1)
      const y = sunY + p * sunR - sunR * 0.05
      c.fillRect(sunX - sunR, y, sunR * 2, 1.5 + i * 2.2)
    }
    c.restore()

    // Перспективная сетка
    const horizon = h * 0.62
    const scroll = (t * 0.00004) % 1 // бегущая анимация линий

    c.lineWidth = 1
    c.strokeStyle = 'rgba(0,229,255,0.30)'
    for (let i = 0; i < 12; i++) {
      const p = (i + scroll) / 12
      const y = horizon + Math.pow(p, 2.4) * (h - horizon)
      c.beginPath()
      c.moveTo(0, y)
      c.lineTo(w, y)
      c.stroke()
    }

    const cx = w / 2
    for (let i = -12; i <= 12; i++) {
      c.beginPath()
      c.moveTo(cx, horizon)
      c.lineTo(cx + i * (w / 9), h)
      c.stroke()
    }

    // Линия горизонта
    c.strokeStyle = 'rgba(255,45,149,0.5)'
    c.lineWidth = 2
    c.beginPath()
    c.moveTo(0, horizon)
    c.lineTo(w, horizon)
    c.stroke()
  }

  // ---------------------------------------------------------------------------
  // Частицы
  // ---------------------------------------------------------------------------

  _updateParticles(bands, w, h, phase) {
    const cx = w / 2
    const cy = h * 0.5

    // Количество спавна зависит от энергии диапазонов
    let spawn = Math.floor(bands.bass * 9 + bands.mid * 7 + bands.high * 6)
    if (phase === 'drop') spawn += 2

    for (let i = 0; i < spawn; i++) {
      if (this.particles.length > 340) break
      const angle = Math.random() * Math.PI * 2
      const speed = 0.7 + Math.random() * 2.2 + bands.overall * 4.5
      // Цвет выбирается по доминирующему диапазону
      let hue = HUE_MID
      const r = Math.random()
      if (r < bands.bass / (bands.bass + bands.mid + bands.high + 0.001)) hue = HUE_BASS
      else if (r < 0.85) hue = HUE_MID
      else hue = HUE_HIGH

      this.particles.push({
        x: cx + (Math.random() * 2 - 1) * 20,
        y: cy + (Math.random() * 2 - 1) * 20,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.6,
        life: 1,
        decay: 0.006 + Math.random() * 0.018,
        size: 1 + Math.random() * 2.6,
        hue,
      })
    }

    const c = this.c
    c.save()
    c.globalCompositeOperation = 'lighter'
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i]
      p.x += p.vx
      p.y += p.vy
      p.vx *= 0.985
      p.vy = p.vy * 0.985 - 0.02
      p.life -= p.decay
      if (p.life <= 0) {
        this.particles.splice(i, 1)
        continue
      }
      const alpha = Math.max(0, p.life)
      c.beginPath()
      c.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2)
      c.fillStyle = `hsla(${p.hue}, 100%, 65%, ${alpha})`
      c.shadowBlur = 12
      c.shadowColor = `hsla(${p.hue}, 100%, 60%, ${alpha})`
      c.fill()
    }
    c.restore()
  }

  // ---------------------------------------------------------------------------
  // Персонаж
  // ---------------------------------------------------------------------------

  _drawCharacter(cx, cy, bands, beatPulse, phase, t) {
    const c = this.c
    const { w, h } = this
    // Базовый масштаб фигуры относительно размера сцены
    const charScale = Math.min(w, h) / 520
    // Музыкальное масштабирование: бас + удар доли + дыхание
    const musicScale = 1 + bands.bass * 0.28 + beatPulse * 0.12
    const u = 100 * charScale * musicScale

    const bob = Math.sin(t * 0.004) * 5 * charScale
    const sway = Math.sin(t * 0.0016) * 0.05

    c.save()
    c.translate(cx, cy + bob)
    c.rotate(sway)

    // Аура вокруг персонажа
    const aura = c.createRadialGradient(0, 0, 0, 0, 0, 2.3 * u)
    aura.addColorStop(0, `rgba(255,45,149,${0.22 + bands.bass * 0.4})`)
    aura.addColorStop(0.5, 'rgba(177,108,234,0.10)')
    aura.addColorStop(1, 'rgba(0,0,0,0)')
    c.fillStyle = aura
    c.beginPath()
    c.arc(0, 0, 2.3 * u, 0, Math.PI * 2)
    c.fill()

    c.lineCap = 'round'
    c.lineJoin = 'round'

    // Ноги
    c.strokeStyle = '#7c3aed'
    c.lineWidth = 0.13 * u
    c.shadowBlur = 16
    c.shadowColor = 'rgba(124,58,237,0.8)'
    const legSpread = 0.15 * u
    c.beginPath()
    c.moveTo(-legSpread, 0.12 * u)
    c.lineTo(-legSpread - 0.05 * u, 0.74 * u)
    c.stroke()
    c.beginPath()
    c.moveTo(legSpread, 0.12 * u)
    c.lineTo(legSpread + 0.05 * u, 0.74 * u)
    c.stroke()

    // Торс (трапеция с градиентом)
    const torsoGrad = c.createLinearGradient(0, -0.7 * u, 0, 0.25 * u)
    torsoGrad.addColorStop(0, '#00e5ff')
    torsoGrad.addColorStop(1, '#ff2d95')
    c.fillStyle = torsoGrad
    c.shadowBlur = 22
    c.shadowColor = 'rgba(0,229,255,0.85)'
    c.beginPath()
    c.moveTo(-0.22 * u, -0.6 * u)
    c.lineTo(0.22 * u, -0.6 * u)
    c.lineTo(0.3 * u, 0.2 * u)
    c.lineTo(-0.3 * u, 0.2 * u)
    c.closePath()
    c.fill()

    // Руки: на дропе подняты (танцующий силуэт), в остальных фазах — опущены
    const armLift = phase === 'drop' ? Math.min(1, 0.55 + beatPulse * 1.0) : 0.15
    c.strokeStyle = '#ff2d95'
    c.lineWidth = 0.1 * u
    c.shadowBlur = 18
    c.shadowColor = 'rgba(255,45,149,0.9)'
    for (const side of [-1, 1]) {
      const shx = side * 0.22 * u
      const shy = -0.55 * u
      const hx = side * (0.36 * u + 0.24 * u * armLift)
      const hy = 0.34 * u * (1 - armLift) + -1.24 * u * armLift
      const ex = side * 0.42 * u
      const ey = -0.12 * u + (hy + 0.12 * u) * 0.35
      c.beginPath()
      c.moveTo(shx, shy)
      c.quadraticCurveTo(ex, ey, hx, hy)
      c.stroke()
    }

    // Голова
    c.shadowColor = 'rgba(255,225,77,0.9)'
    c.shadowBlur = 24
    c.fillStyle = '#ffe14d'
    c.beginPath()
    c.arc(0, -0.85 * u, 0.2 * u, 0, Math.PI * 2)
    c.fill()

    // Визор (кибер-очки)
    c.shadowColor = 'rgba(0,229,255,0.9)'
    c.fillStyle = '#00e5ff'
    c.fillRect(-0.16 * u, -0.9 * u, 0.32 * u, 0.09 * u)

    c.restore()
  }

  // ---------------------------------------------------------------------------
  // Кинетическая типографика
  // ---------------------------------------------------------------------------

  _drawTypography(w, h, bands, beatPulse, phase, bar, beat) {
    const c = this.c
    const words = PHASE_WORDS[phase] || PHASE_WORDS.intro
    const word = words[beat % words.length]

    const baseSize = Math.min(w, h) * (phase === 'drop' ? 0.17 : 0.13)
    const fontSize = baseSize * (1 + beatPulse * 0.16 + bands.overall * 0.06)

    c.save()
    c.textAlign = 'center'
    c.textBaseline = 'middle'

    // Крупное кинетическое слово
    c.font = `900 ${fontSize}px "Segoe UI", system-ui, sans-serif`
    const grad = c.createLinearGradient(0, h * 0.75, 0, h * 0.92)
    grad.addColorStop(0, '#00e5ff')
    grad.addColorStop(1, '#ff2d95')
    c.fillStyle = grad
    c.shadowBlur = 34
    c.shadowColor = 'rgba(255,45,149,0.9)'
    c.fillText(word, w / 2, h * 0.84)

    // Верхняя строка-статус: фаза и номер такта
    const label = `${phase.toUpperCase()}  •  BAR ${String(bar).padStart(2, '0')}/32`
    c.font = `600 ${Math.min(w, h) * 0.035}px "Segoe UI", system-ui, sans-serif`
    c.fillStyle = 'rgba(226,232,240,0.85)'
    c.shadowBlur = 12
    c.shadowColor = 'rgba(0,229,255,0.8)'
    c.fillText(label, w / 2, h * 0.08)

    c.restore()
  }

  // ---------------------------------------------------------------------------
  // Виньетка
  // ---------------------------------------------------------------------------

  _drawVignette(w, h, bands) {
    const c = this.c
    const vig = c.createRadialGradient(
      w / 2, h / 2, Math.min(w, h) * 0.3,
      w / 2, h / 2, Math.max(w, h) * 0.75,
    )
    vig.addColorStop(0, 'rgba(0,0,0,0)')
    vig.addColorStop(1, `rgba(0,0,0,${0.55 + bands.overall * 0.1})`)
    c.fillStyle = vig
    c.fillRect(0, 0, w, h)
  }
}
