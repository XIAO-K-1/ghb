<template>
  <div class="warn-page">
    <!-- ========== 概览条 ========== -->
    <section class="summary stagger">
      <div v-for="s in summaryCards" :key="s.key" class="sm-card glass" :class="'risk-' + s.risk">
        <span class="sm-bar" />
        <div class="sm-body">
          <span class="sm-label">{{ s.label }}</span>
          <span class="num num-lg">{{ s.value }}</span>
        </div>
        <span class="sm-ico" v-html="s.icon" />
      </div>
    </section>

    <!-- ========== 工具栏 ========== -->
    <section class="toolbar glass">
      <div class="segmented">
        <button v-for="f in filters" :key="f.key" :class="{ 'is-active': activeFilter === f.key }" @click="activeFilter = f.key">
          {{ f.label }}<em v-if="f.count !== undefined" class="fc num">{{ f.count }}</em>
        </button>
      </div>
      <div class="tb-search">
        <svg viewBox="0 0 24 24" width="15" height="15"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="m20 20-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input v-model="keyword" placeholder="搜索民宿名称 / 规则编号 / 风险原因" />
      </div>
      <button class="btn btn-primary" :disabled="running" @click="scan">
        {{ running ? '扫描中…' : '⚡ 触发规则引擎扫描' }}
      </button>
    </section>

    <!-- ========== 预警列表 ========== -->
    <section class="list">
      <div v-if="!filtered.length" class="empty glass">
        <div class="empty-ico">✓</div>
        <h4>当前筛选条件下暂无预警</h4>
        <p>点击「触发规则引擎扫描」，依据 R001–R004 规则重新评估在管民宿</p>
      </div>

      <article v-for="(w, i) in filtered" :key="w.id" class="wcard glass rise-in" :class="'risk-' + w.level"
        :style="{ animationDelay: Math.min(i * 0.04, 0.3) + 's' }">
        <span class="w-bar" />

        <div class="w-main">
          <header class="w-head">
            <span class="w-ico">
              <svg viewBox="0 0 24 24" width="17" height="17"><path d="M12 3 2 20h20L12 3z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M12 9v5M12 17.4v.3" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"/></svg>
            </span>
            <div class="w-title">
              <b>{{ w.homestay_name || w.homestay_id }}</b>
              <span class="w-city">{{ w.city }}</span>
            </div>
            <span class="rule-chip">{{ w.rule_id }} · {{ w.rule_name }}</span>
            <span class="level-tag" :class="'risk-' + w.level">{{ riskText[w.level] }}</span>
          </header>

          <p class="w-reason">{{ w.reason }}</p>

          <div v-if="w.suggestion" class="w-suggest">
            <span class="ws-tag">AI 整改建议</span>
            <span class="ws-text">{{ w.suggestion }}</span>
          </div>

          <div v-if="metricsOf(w).length" class="w-metrics">
            <span v-for="m in metricsOf(w)" :key="m.k">{{ m.k }}<em class="num">{{ m.v }}</em></span>
          </div>

          <footer class="w-foot">
            <span class="w-time">触发时间 {{ shortTime(w.created_at) }}</span>
            <span class="w-status" :class="'st-' + w.status">{{ statusText[w.status] || w.status }}</span>
            <div class="w-actions">
              <button class="wa-btn" @click="generateReport(w.homestay_id)">
                <svg viewBox="0 0 24 24" width="14" height="14"><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 0 6v2a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-2a3 3 0 0 1 0-6V7a4 4 0 0 1 4-4z" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
                AI巡检报告
              </button>
              <button class="wa-btn" :disabled="w.status !== 'pending'" @click="setStatus(w, 'processing')">标记处理中</button>
              <button class="wa-btn" :disabled="w.status === 'closed'" @click="setStatus(w, 'closed')">关闭预警</button>
              <button class="wa-btn ghost" @click="openArchive(w.homestay_id)">数字档案 →</button>
            </div>
          </footer>
        </div>
      </article>
    </section>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store, runRuleEngine, refreshWarnings, openReport } from '@/store'
import { shortTime, percent, RISK_TEXT } from '@/utils/format'

const router = useRouter()
const riskText = RISK_TEXT
const statusText = { pending: '待处理', processing: '处理中', closed: '已关闭' }

const running = ref(false)
const keyword = ref('')
const activeFilter = ref('all')
const toast = ref('')

const warnings = computed(() => store.warnings)

const filters = computed(() => [
  { key: 'all', label: '全部', count: warnings.value.length },
  { key: 'red', label: '高风险', count: warnings.value.filter((w) => w.level === 'red').length },
  { key: 'amber', label: '中风险', count: warnings.value.filter((w) => w.level === 'amber').length },
  { key: 'pending', label: '待处理', count: warnings.value.filter((w) => w.status === 'pending').length },
  { key: 'closed', label: '已关闭', count: warnings.value.filter((w) => w.status === 'closed').length }
])

const summaryCards = computed(() => [
  { key: 'total', label: '预警总数', value: warnings.value.length, risk: 'blue', icon: iconBell },
  { key: 'red', label: '红色预警', value: warnings.value.filter((w) => w.level === 'red').length, risk: 'red', icon: iconAlert },
  { key: 'amber', label: '黄色预警', value: warnings.value.filter((w) => w.level === 'amber').length, risk: 'amber', icon: iconClock },
  { key: 'pending', label: '待处理', value: warnings.value.filter((w) => w.status === 'pending').length, risk: 'green', icon: iconCheck }
])

const iconBell = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>'
const iconAlert = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3 2 20h20L12 3z"/><path d="M12 9v5M12 17.5v.4"/></svg>'
const iconClock = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/></svg>'
const iconCheck = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>'

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return warnings.value.filter((w) => {
    if (activeFilter.value === 'red' && w.level !== 'red') return false
    if (activeFilter.value === 'amber' && w.level !== 'amber') return false
    if (activeFilter.value === 'pending' && w.status !== 'pending') return false
    if (activeFilter.value === 'closed' && w.status !== 'closed') return false
    if (kw) {
      const hay = `${w.homestay_name || ''}${w.homestay_id || ''}${w.rule_id || ''}${w.rule_name || ''}${w.reason || ''}`.toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
})

function metricsOf(w) {
  const m = w.metrics || {}
  const out = []
  if (m.ota_score !== undefined) out.push({ k: 'OTA评分', v: Number(m.ota_score).toFixed(1) })
  if (m.bad_7d !== undefined) out.push({ k: '近7日差评', v: `${m.bad_7d} 条` })
  if (m.occupancy !== undefined) out.push({ k: '入住率', v: percent(m.occupancy, 0) })
  if (m.used_ratio !== undefined) out.push({ k: '额度使用率', v: percent(m.used_ratio, 0) })
  if (m.flow_drop_30d !== undefined) out.push({ k: '30日流水降幅', v: percent(m.flow_drop_30d, 0) })
  if (m.keyword !== undefined) out.push({ k: '关键词', v: m.keyword })
  return out.slice(0, 4)
}

async function scan() {
  running.value = true
  try {
    const res = await runRuleEngine()
    const n = res?.created?.length || 0
    show(n ? `扫描完成，新增 ${n} 条预警` : '扫描完成，暂无新增预警')
  } catch (e) {
    show(e?.message || '规则引擎调用失败')
  } finally {
    running.value = false
  }
}

async function setStatus(w, status) {
  try {
    await (await import('@/api')).default.updateWarning(w.id, status)
    await refreshWarnings()
    show(status === 'closed' ? '预警已关闭' : '已标记为处理中')
  } catch (e) {
    show(e?.message || '状态更新失败')
  }
}

function generateReport(id) {
  openReport(id)
}

function openArchive(id) {
  store.currentHomestayId = id
  router.push({ name: 'bank-archive', query: { id } })
}

let t = null
function show(msg) {
  toast.value = msg
  clearTimeout(t)
  t = setTimeout(() => (toast.value = ''), 2800)
}
</script>

<style scoped>
.warn-page { display: flex; flex-direction: column; gap: 16px; }

/* 概览 */
.summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.sm-card { position: relative; display: flex; align-items: center; gap: 13px; padding: 15px 16px; border-radius: var(--r-md); overflow: hidden; }
.sm-bar { width: 3px; align-self: stretch; border-radius: 3px; background: var(--risk, var(--brand-blue)); box-shadow: 0 0 12px var(--risk-glow, var(--accent-glow)); }
.sm-body { display: flex; flex-direction: column; gap: 2px; }
.sm-label { font-size: 12.5px; color: var(--text-2); }
.sm-body .num { color: #fff; }
.sm-ico { margin-left: auto; color: var(--risk, var(--brand-blue-400)); opacity: .6; }
.sm-card.risk-blue { --risk: #165dff; --risk-glow: rgba(22, 93, 255, .5); }

/* 工具栏 */
.toolbar { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-radius: var(--r-md); flex-wrap: wrap; }
.toolbar .segmented { flex: 0 0 auto; }
.fc { font-style: normal; margin-left: 6px; font-family: var(--font-num); opacity: .7; font-size: 11.5px; }
.tb-search {
  flex: 1; min-width: 200px; display: flex; align-items: center; gap: 9px;
  height: 38px; padding: 0 14px; border-radius: 9px;
  background: rgba(255, 255, 255, .03); border: 1px solid var(--line); color: var(--text-3);
}
.tb-search input { flex: 1; background: none; border: 0; outline: none; color: var(--text-1); font-size: 13px; font-family: inherit; }
.tb-search input::placeholder { color: var(--text-3); }

/* 列表 */
.list { display: flex; flex-direction: column; gap: 13px; }
.empty { padding: 60px 20px; text-align: center; border-radius: var(--r-md); }
.empty-ico {
  width: 52px; height: 52px; margin: 0 auto 14px; border-radius: 50%; display: grid; place-items: center;
  font-size: 24px; color: var(--risk-green); background: rgba(0, 180, 42, .12); border: 1px solid rgba(0, 180, 42, .3);
}
.empty h4 { color: var(--text-1); font-size: 15px; }
.empty p { color: var(--text-3); font-size: 12.5px; margin-top: 7px; }

.wcard { position: relative; display: flex; gap: 14px; padding: 16px 18px; border-radius: var(--r-md); overflow: hidden; }
.w-bar { width: 4px; border-radius: 4px; flex: 0 0 4px; background: var(--risk); box-shadow: 0 0 14px var(--risk-glow); }
.wcard.risk-red { border-color: rgba(245, 63, 63, .34); background: linear-gradient(120deg, rgba(245, 63, 63, .07), rgba(17, 34, 61, .7)); }
.w-main { flex: 1; min-width: 0; }
.w-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.w-ico { color: var(--risk); display: inline-flex; }
.w-title { display: flex; align-items: baseline; gap: 9px; flex: 1; min-width: 0; }
.w-title b { font-size: 15px; color: #fff; }
.w-city { font-size: 11.5px; color: var(--text-3); padding: 1px 8px; border-radius: 5px; background: rgba(255, 255, 255, .05); }
.rule-chip {
  font-family: var(--font-num); font-size: 11px; letter-spacing: .08em;
  color: var(--text-2); padding: 3px 9px; border-radius: 6px;
  background: rgba(22, 93, 255, .12); border: 1px solid rgba(22, 93, 255, .26);
}
.w-reason { margin-top: 10px; font-size: 13.5px; color: #d6e3fa; line-height: 1.75; }
.wcard.risk-red .w-reason { color: #ffd4d4; }

.w-suggest {
  display: flex; gap: 10px; margin-top: 11px; padding: 10px 13px;
  border-radius: 9px; background: var(--gold-soft); border: 1px solid rgba(255, 184, 0, .26);
}
.ws-tag { flex: 0 0 auto; font-size: 11px; font-weight: 700; color: var(--brand-gold); letter-spacing: .06em; }
.ws-text { font-size: 12.5px; color: #f0dcae; line-height: 1.65; }

.w-metrics { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 11px; }
.w-metrics span { font-size: 11.5px; color: var(--text-3); }
.w-metrics em { font-style: normal; color: var(--text-1); font-size: 13.5px; margin-left: 5px; }

.w-foot { display: flex; align-items: center; gap: 14px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); flex-wrap: wrap; }
.w-time { font-size: 11.5px; color: var(--text-3); font-family: var(--font-num); }
.w-status { font-size: 11.5px; padding: 2px 10px; border-radius: 5px; }
.st-pending { color: var(--risk-amber); background: rgba(255, 125, 0, .13); }
.st-processing { color: var(--brand-blue-400); background: rgba(22, 93, 255, .15); }
.st-closed { color: var(--text-3); background: rgba(255, 255, 255, .06); }
.w-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.wa-btn {
  display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px;
  border-radius: 8px; font-size: 12.5px; color: var(--text-2);
  background: rgba(255, 255, 255, .04); border: 1px solid var(--line);
  transition: all .25s var(--ease-out);
}
.wa-btn:hover:not(:disabled) { color: #fff; background: rgba(22, 93, 255, .2); border-color: rgba(22, 93, 255, .4); transform: translateY(-1px); }
.wa-btn:disabled { opacity: .4; cursor: not-allowed; }
.wa-btn.ghost { color: var(--brand-gold); background: var(--gold-soft); border-color: rgba(255, 184, 0, .28); }
.wa-btn.ghost:hover { background: rgba(255, 184, 0, .22); border-color: rgba(255, 184, 0, .5); }

.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 11px; font-size: 13.5px; z-index: 99;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong); color: var(--text-1);
  box-shadow: var(--shadow-lift);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

@media (max-width: 900px) { .summary { grid-template-columns: repeat(2, 1fr); } }
</style>
