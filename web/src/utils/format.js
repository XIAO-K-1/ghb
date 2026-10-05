/** 通用格式化工具 */

/** 金额 → 万元/亿元 中文简写 */
export function money(v, unit = '万') {
  if (v === null || v === undefined || isNaN(v)) return '—'
  const n = Number(v)
  if (unit === '元') return `${n.toLocaleString('zh-CN')} 元`
  if (Math.abs(n) >= 100000000) return `${(n / 100000000).toFixed(2)} 亿`
  if (Math.abs(n) >= 10000) {
    const w = n / 10000
    return `${w >= 1000 ? w.toFixed(0) : w.toFixed(w % 1 === 0 ? 0 : 1)} 万`
  }
  return `${n} 元`
}

/** 数字千分位 */
export function thousands(v) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return Number(v).toLocaleString('zh-CN')
}

/** 小数 → 百分比字符串 */
export function percent(v, digits = 0) {
  if (v === null || v === undefined || isNaN(v)) return '—'
  return `${(Number(v) * 100).toFixed(digits)}%`
}

/** 风险等级 → 中文 */
export const RISK_TEXT = { red: '高风险', amber: '中风险', green: '低风险' }
export const RISK_CLASS = { red: 'risk-red', amber: 'risk-amber', green: 'risk-green' }
export const RISK_COLOR = { red: '#F53F3F', amber: '#FF7D00', green: '#00B42A' }

/** 时间戳 → MM-DD HH:mm */
export function shortTime(iso) {
  if (!iso) return '—'
  const d = new Date(String(iso).replace(' ', 'T'))
  if (isNaN(d.getTime())) return String(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 日期字符串 → 相对时间 */
export function fromNow(iso) {
  if (!iso) return '—'
  const d = new Date(String(iso).replace(' ', 'T'))
  if (isNaN(d.getTime())) return String(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

/** 简单 Markdown 渲染（仅支持标题/加粗/有序无序列表/引用），用于巡检报告 */
export function renderMarkdown(md) {
  if (!md) return ''
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = String(md).split('\n')
  let html = ''
  let listType = null
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null } }

  for (let raw of lines) {
    const line = raw.replace(/\r$/, '')
    if (!line.trim()) { closeList(); continue }
    let m
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) {
      closeList()
      const lv = m[1].length + 1
      html += `<h${lv} class="md-h">${inline(esc(m[2]))}</h${lv}>`
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      if (listType !== 'ul') { closeList(); html += '<ul class="md-ul">'; listType = 'ul' }
      html += `<li>${inline(esc(m[1]))}</li>`
    } else if ((m = line.match(/^\s*\d+[.、]\s+(.*)$/))) {
      if (listType !== 'ol') { closeList(); html += '<ol class="md-ol">'; listType = 'ol' }
      html += `<li>${inline(esc(m[1]))}</li>`
    } else if ((m = line.match(/^>\s+(.*)$/))) {
      closeList()
      html += `<blockquote class="md-quote">${inline(esc(m[1]))}</blockquote>`
    } else if (/^\s*[-—]{3,}\s*$/.test(line)) {
      closeList(); html += '<hr class="md-hr" />'
    } else {
      closeList()
      html += `<p class="md-p">${inline(esc(line))}</p>`
    }
  }
  closeList()
  return html

  function inline(s) {
    return s
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/(🔴|🟡|🟢|⚠️|📚|✅|❗)/g, '<span class="md-emo">$1</span>')
  }
}
