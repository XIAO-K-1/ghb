import { reactive } from 'vue'
import api from '@/api'

/**
 * 全局轻量状态（模块级单例，路由切换不丢失）
 * 银行端与老板端共享同一份数据视图，实现真正的“双屏联动”。
 */
export const store = reactive({
  ready: false,
  loading: false,
  error: '',

  homestays: [],
  dashboard: null,
  warnings: [],
  warningSummary: { red: 0, amber: 0, pending: 0 },
  currentHomestayId: 'LY001',

  llmMode: 'unknown',
  vectorMode: 'unknown',

  /** 老板端当前登录用户 */
  user: JSON.parse(localStorage.getItem('ysx:user') || 'null'),
  token: localStorage.getItem('ysx:token') || '',

  /** 老板端收到的实时预警（双屏联动） */
  inbox: JSON.parse(localStorage.getItem('ysx:inbox') || '[]'),

  /** AI 巡检报告全屏遮罩状态 */
  report: {
    visible: false,
    phase: 'idle', // idle | thinking | done | error
    content: '',
    homestay: null,
    generatedAt: '',
    error: ''
  }
})

/** 首次加载基础数据 */
export async function bootstrap(force = false) {
  if (store.ready && !force) return
  store.loading = true
  store.error = ''
  try {
    const [hs, dash, warns, health] = await Promise.all([
      api.homestays().catch(() => ({ list: [] })),
      api.dashboard().catch(() => null),
      api.warnings().catch(() => ({ list: [], summary: {} })),
      api.health().catch(() => null)
    ])
    store.homestays = hs?.list || []
    store.dashboard = dash
    store.warnings = warns?.list || []
    store.warningSummary = warns?.summary || { red: 0, amber: 0, pending: 0 }
    if (health) {
      store.llmMode = health.llm || 'offline'
      store.vectorMode = health.vector || 'builtin'
    }
    store.ready = true
  } catch (e) {
    store.error = e?.message || '后端服务未启动'
  } finally {
    store.loading = false
  }
}

/** 触发规则引擎并刷新 */
export async function runRuleEngine() {
  const res = await api.triggerWarnings()
  store.warnings = res?.all || []
  store.warningSummary = res?.summary || store.warningSummary
  await refreshDashboard()
  return res
}

export async function refreshWarnings() {
  const warns = await api.warnings()
  store.warnings = warns?.list || []
  store.warningSummary = warns?.summary || store.warningSummary
  return store.warnings
}

export async function refreshDashboard() {
  try {
    store.dashboard = await api.dashboard()
  } catch { /* ignore */ }
  return store.dashboard
}

/** 依据 id 取民宿 */
export function homestayById(id) {
  return store.homestays.find((h) => h.id === id) || null
}

export function persistUser(user, token) {
  store.user = user
  store.token = token || ''
  if (user) localStorage.setItem('ysx:user', JSON.stringify(user))
  else localStorage.removeItem('ysx:user')
  if (token) localStorage.setItem('ysx:token', token)
  else localStorage.removeItem('ysx:token')
}

export function pushInbox(item) {
  store.inbox = [item, ...store.inbox].slice(0, 20)
  localStorage.setItem('ysx:inbox', JSON.stringify(store.inbox))
}

export function clearInbox() {
  store.inbox = []
  localStorage.removeItem('ysx:inbox')
}

/** 按时间戳标记单条消息为已读 */
export function markInboxRead(at) {
  const idx = store.inbox.findIndex((i) => i.at === at)
  if (idx < 0) return
  store.inbox = store.inbox.map((i, n) => (n === idx ? { ...i, read: true } : i))
  localStorage.setItem('ysx:inbox', JSON.stringify(store.inbox))
}

/** 全部标记已读 */
export function markAllInboxRead() {
  store.inbox = store.inbox.map((i) => ({ ...i, read: true }))
  localStorage.setItem('ysx:inbox', JSON.stringify(store.inbox))
}

/** ============ AI 巡检报告：全屏遮罩状态机 ============ */
export async function openReport(homestayId) {
  const hs = homestayById(homestayId)
  store.report = {
    visible: true,
    phase: 'thinking',
    content: '',
    homestay: hs,
    generatedAt: '',
    error: ''
  }
  try {
    const res = await api.generateReport(homestayId)
    // 让「AI 粒子大脑」动画至少停留 1.6s，保证仪式感
    await new Promise((r) => setTimeout(r, 1600))
    store.report.content = res?.report_content || '（未返回报告内容）'
    store.report.generatedAt = res?.generated_at || new Date().toISOString()
    store.report.phase = 'done'
    // 报告生成后，向老板端推送整改建议 —— 双屏联动
    return res
  } catch (e) {
    store.report.phase = 'error'
    store.report.error = e?.message || '报告生成失败，请确认后端服务已启动'
    return null
  }
}

export function closeReport() {
  store.report.visible = false
  store.report.phase = 'idle'
}
