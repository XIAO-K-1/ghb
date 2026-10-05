/**
 * 跨窗口事件总线 —— 支撑「双屏联动」演示
 * 银行端 Web 触发预警后，老板端 App（另一个窗口 / 同一窗口）实时收到整改建议。
 * 优先使用 BroadcastChannel，不支持时降级为 localStorage storage 事件。
 */
const CHANNEL = 'ysx-bus'
const LS_KEY = 'ysx-bus-msg'

let channel = null
try {
  channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL) : null
} catch {
  channel = null
}

const listeners = new Map()

function dispatch(type, payload) {
  const handlers = listeners.get(type) || []
  handlers.forEach((fn) => {
    try { fn(payload) } catch (e) { console.warn('[bus] handler error', e) }
  })
  const all = listeners.get('*') || []
  all.forEach((fn) => {
    try { fn({ type, payload }) } catch (e) { /* ignore */ }
  })
}

if (channel) {
  channel.onmessage = (e) => {
    const { type, payload } = e.data || {}
    if (type) dispatch(type, payload)
  }
}

window.addEventListener('storage', (e) => {
  if (e.key !== LS_KEY || !e.newValue) return
  try {
    const { type, payload, ts } = JSON.parse(e.newValue)
    // 忽略自己发出的（同窗口不会触发 storage，此处仅双保险）
    if (Date.now() - ts < 50) return
    dispatch(type, payload)
  } catch { /* ignore */ }
})

export const bus = {
  /** 发送事件 */
  emit(type, payload) {
    const msg = { type, payload, ts: Date.now() }
    if (channel) channel.postMessage(msg)
    try { localStorage.setItem(LS_KEY, JSON.stringify(msg)) } catch { /* ignore */ }
    // 本窗口立即响应
    dispatch(type, payload)
  },
  /** 订阅事件，返回取消订阅函数 */
  on(type, fn) {
    if (!listeners.has(type)) listeners.set(type, [])
    listeners.get(type).push(fn)
    return () => {
      const arr = listeners.get(type) || []
      const i = arr.indexOf(fn)
      if (i > -1) arr.splice(i, 1)
    }
  }
}

export default bus
