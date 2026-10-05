<template>
  <canvas ref="cv" class="ai-brain" />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  size: { type: Number, default: 240 },
  speed: { type: Number, default: 1 }
})

const cv = ref(null)
let raf = null
let ro = null
let pts = []
let W = 0
let H = 0
const dpr = Math.min(window.devicePixelRatio || 1, 2)
let t = 0

/** 斐波那契球面均匀撒点 */
function buildSphere(n) {
  const arr = []
  const phi = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2
    const r = Math.sqrt(1 - y * y)
    const th = phi * i
    arr.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r })
  }
  return arr
}

function resize() {
  if (!cv.value) return
  const rect = cv.value.getBoundingClientRect()
  W = rect.width
  H = rect.height
  cv.value.width = W * dpr
  cv.value.height = H * dpr
}

function draw() {
  const ctx = cv.value?.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, W, H)

  const cx = W / 2
  const cy = H / 2
  const R = Math.min(W, H) * 0.34
  t += 0.006 * props.speed

  const cosT = Math.cos(t)
  const sinT = Math.sin(t)
  const tilt = 0.42
  const cosX = Math.cos(tilt)
  const sinX = Math.sin(tilt)

  // 外圈轨道
  ctx.save()
  ctx.strokeStyle = 'rgba(22,93,255,.22)'
  ctx.lineWidth = 1
  for (let k = 0; k < 2; k++) {
    ctx.beginPath()
    ctx.ellipse(cx, cy, R * (1.22 + k * 0.2), R * (1.22 + k * 0.2) * 0.42, t * 0.3 + k, 0, Math.PI * 2)
    ctx.stroke()
  }
  ctx.restore()

  // 项目点
  const proj = pts.map((p) => {
    const x1 = p.x * cosT - p.z * sinT
    const z1 = p.x * sinT + p.z * cosT
    const y1 = p.y * cosX - z1 * sinX
    const z2 = p.y * sinX + z1 * cosX
    return { sx: cx + x1 * R, sy: cy + y1 * R, z: z2 }
  })

  // 近邻连线
  ctx.lineWidth = 0.6
  for (let i = 0; i < proj.length; i++) {
    for (let j = i + 1; j < proj.length; j++) {
      const a = proj[i]
      const b = proj[j]
      const d = Math.hypot(a.sx - b.sx, a.sy - b.sy)
      if (d < R * 0.34) {
        const alpha = (1 - d / (R * 0.34)) * 0.24 * ((a.z + b.z) / 2 + 1)
        ctx.strokeStyle = `rgba(80,150,255,${alpha.toFixed(3)})`
        ctx.beginPath()
        ctx.moveTo(a.sx, a.sy)
        ctx.lineTo(b.sx, b.sy)
        ctx.stroke()
      }
    }
  }

  // 粒子
  proj.forEach((p, i) => {
    const depth = (p.z + 1) / 2 // 0..1
    const warm = i % 11 === 0
    const r = 0.7 + depth * 1.9
    ctx.beginPath()
    ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2)
    const c = warm ? '255,184,0' : '110,175,255'
    ctx.fillStyle = `rgba(${c},${(0.25 + depth * 0.75).toFixed(3)})`
    ctx.fill()
    if (depth > 0.92) {
      ctx.beginPath()
      ctx.arc(p.sx, p.sy, r * 3.4, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${c},.09)`
      ctx.fill()
    }
  })

  // 核心光晕
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.85)
  g.addColorStop(0, 'rgba(22,93,255,.34)')
  g.addColorStop(0.55, 'rgba(22,93,255,.08)')
  g.addColorStop(1, 'rgba(22,93,255,0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(cx, cy, R * 0.85, 0, Math.PI * 2)
  ctx.fill()

  raf = requestAnimationFrame(draw)
}

onMounted(() => {
  pts = buildSphere(190)
  resize()
  draw()
  ro = new ResizeObserver(resize)
  ro.observe(cv.value)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  ro && ro.disconnect()
})
</script>

<style scoped>
.ai-brain { width: 100%; height: 100%; display: block; }
</style>
