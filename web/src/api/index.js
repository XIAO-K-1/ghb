/**
 * 豫宿巡 · API 客户端
 * - 统一走 /api 前缀（开发环境由 Vite 代理到 FastAPI:8000）
 * - 内置 localStorage 缓存：后端未启动时回退到最近一次成功的数据，保证演示不白屏
 */

const BASE = '/api'
const CACHE_PREFIX = 'ysx:cache:'

export const apiState = {
  online: true,
  llm: 'unknown',
  vector: 'unknown'
}

/** 读取缓存 */
function readCache(key) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/** 写入缓存 */
function writeCache(key, data) {
  try {
    localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(data))
  } catch {
    /* 超出配额时忽略 */
  }
}

async function request(path, { method = 'GET', body, cache = true, timeout = 90000 } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const res = await fetch(BASE + path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal
    })
    if (!res.ok) {
      let detail = `请求失败（HTTP ${res.status}）`
      try {
        const j = await res.json()
        if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
      } catch { /* ignore */ }
      throw new Error(detail)
    }
    const data = await res.json()
    apiState.online = true
    if (cache && method === 'GET') writeCache(path, data)
    return data
  } catch (err) {
    if (method === 'GET' && cache) {
      const cached = readCache(path)
      if (cached) {
        apiState.online = false
        return cached
      }
    }
    if (method === 'GET') apiState.online = false
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export const api = {
  health: () => request('/health', { cache: false, timeout: 4000 }),

  // ---------- 民宿 ----------
  homestays: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
    return request(`/homestays${q ? `?${q}` : ''}`)
  },
  homestay: (id) => request(`/homestays/${id}`),
  archive: (id) => request(`/homestays/${id}/archive`),

  // ---------- 驾驶舱 ----------
  dashboard: () => request('/dashboard'),

  // ---------- 预警 ----------
  warnings: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
    return request(`/warnings${q ? `?${q}` : ''}`)
  },
  triggerWarnings: () => request('/warnings/trigger', { method: 'POST' }),
  updateWarning: (id, status) => request(`/warnings/${id}`, { method: 'PATCH', body: { status }, cache: false }),
  aiGenerateWarning: (homestay_id) => request('/warnings/ai-generate', { method: 'POST', body: { homestay_id } }),
  pushWarning: (id) => request(`/warnings/${id}/push`, { method: 'POST' }),

  // ---------- RAG 系统管理 ----------
  ragDocuments: (homestay_id) => request(`/rag/documents?homestay_id=${encodeURIComponent(homestay_id)}`),
  ragAddDocument: (payload) => request('/rag/documents', { method: 'POST', body: payload, cache: false }),
  ragUpdateDocument: (doc_id, patch) => request(`/rag/documents/${doc_id}`, { method: 'PATCH', body: patch, cache: false }),
  ragDeleteDocument: (doc_id) => request(`/rag/documents/${doc_id}`, { method: 'DELETE', cache: false }),
  ragCrawl: (homestay_id = '') => request('/rag/crawl', { method: 'POST', body: { homestay_id }, cache: false }),

  // ---------- 模型管理 ----------
  models: () => request('/models', { cache: false }),
  saveModels: (scenes) => request('/models', { method: 'POST', body: { scenes }, cache: false }),
  testModel: (scene) => request('/models/test', { method: 'POST', body: { scene }, cache: false, timeout: 60000 }),
  availableModels: (scene, keyword = '') =>
    request('/models/available', { method: 'POST', body: { scene, keyword }, cache: false, timeout: 60000 }),

  // ---------- 消息中心（老板 ⇄ 银行） ----------
  messages: (homestay_id = '') => request(`/messages${homestay_id ? `?homestay_id=${homestay_id}` : ''}`),
  sendMessage: (homestay_id, sender, text) => request('/messages', { method: 'POST', body: { homestay_id, sender, text }, cache: false }),
  bankUnread: () => request('/messages/bank/unread', { cache: false }),
  markMessagesRead: (homestay_id = '') => request('/messages/read', { method: 'POST', body: { homestay_id }, cache: false }),

  // ---------- AI 能力 ----------
  chat: (homestay_id, question) => request('/chat', { method: 'POST', body: { homestay_id, question }, cache: false }),
  generateReport: (homestay_id) => request('/report/generate', { method: 'POST', body: { homestay_id }, cache: false }),
  reports: (homestay_id) => request(`/reports${homestay_id ? `?homestay_id=${homestay_id}` : ''}`),
  reportDetail: (report_id) => request(`/reports/${report_id}`),
  pushReport: (report_id) => request('/reports/push', { method: 'POST', body: { report_id }, cache: false }),
  // 样式墙为公共数据，禁用缓存：切换账号 / 重新进入时必须拿到最新样式，避免旧账号残留或空白
  creativeStyles: (homestay_id) => request(`/creative/styles${homestay_id ? `?homestay_id=${homestay_id}` : ''}`, { cache: false }),
  styleGenerate: (homestay_id, style_key, count = 1, image_url = '') =>
    request('/creative/style-generate', { method: 'POST', body: { homestay_id, style_key, count, image_url }, cache: false }),
  copywriting: (homestay_id, requirement = '', style = 'xiaohongshu') =>
    request('/creative/copywriting', { method: 'POST', body: { homestay_id, requirement, style }, cache: false }),
  generateCreative: (homestay_id, theme, count = 1) =>
    request('/creative/generate', { method: 'POST', body: { homestay_id, theme, count }, cache: false }),
  vectorize: (image_url) => request('/creative/vectorize', { method: 'POST', body: { image_url }, cache: false }),
  creativeWorks: (homestay_id) =>
    request(`/creative/works${homestay_id ? `?homestay_id=${homestay_id}` : ''}`, { cache: false }),

  // ---------- 鉴权 ----------
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password }, cache: false }),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, cache: false })
}

export default api
