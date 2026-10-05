<template>
  <div class="rc">
    <!-- ========== 左：民宿清单 ========== -->
    <aside class="rc-side glass">
      <div class="rs-head">
        <h4>巡检对象</h4>
        <span class="mono-label">{{ sorted.length }} 户在管</span>
      </div>
      <div class="rs-list no-scrollbar">
        <button v-for="h in sorted" :key="h.id" class="rs-item" :class="[{ active: h.id === id }, 'risk-' + h.risk_level]" @click="id = h.id">
          <span class="rs-bar" />
          <div class="rs-body">
            <div class="rs-name">{{ h.name }}</div>
            <div class="rs-meta">
              <span>{{ h.city }}</span>
              <span>OTA {{ (h.ota_score ?? 0).toFixed(1) }}</span>
              <span>入住 {{ percent(h.current_occupancy, 0) }}</span>
            </div>
          </div>
          <span class="level-tag" :class="'risk-' + h.risk_level">{{ riskText[h.risk_level] }}</span>
        </button>
      </div>
    </aside>

    <!-- ========== 右：报告工作区 ========== -->
    <section class="rc-main">
      <header class="rc-toolbar glass">
        <div class="rt-left">
          <span class="mono-label">当前巡检对象</span>
          <b>{{ current?.name || '—' }}</b>
          <span v-if="current" class="level-tag" :class="'risk-' + current.risk_level">{{ riskText[current.risk_level] }}</span>
        </div>
        <div class="rt-right">
          <span class="rt-hint">
            <i /> 大模型：{{ llmLabel }} · 向量检索：{{ vectorLabel }}
          </span>
          <button class="btn btn-primary" :disabled="busy" @click="generate">
            {{ busy ? '生成中…' : '⚡ 生成 AI 巡检报告' }}
          </button>
        </div>
      </header>

      <!-- 空态 -->
      <div v-if="!report && !busy" class="rc-empty glass">
        <div class="re-vis">
          <div class="re-brain"><AiBrain /></div>
          <div class="re-copy">
            <h3 class="title-serif">AI 贷后风险巡检报告</h3>
            <p>后端将执行：<b>LangChain 检索该民宿私有知识库 → 拼接经营与贷款上下文 → 调用大模型 → 输出五段式结构化报告</b></p>
            <ul class="re-steps">
              <li>一、基础信息 · 二、风险摘要 · 三、AI 分析 · 四、建议措施 · 五、巡检历史</li>
              <li>RAG 多租户隔离：仅检索本店 collection，A 店数据不会出现在 B 店报告中</li>
              <li>生成后一键同步至老板端 App，形成「预警 → 报告 → 整改 → 改善」闭环</li>
            </ul>
            <button class="btn btn-gold" @click="generate">立即生成报告</button>
          </div>
        </div>
      </div>

      <!-- 生成中 -->
      <div v-else-if="busy" class="rc-thinking glass">
        <div class="th-brain"><AiBrain /></div>
        <h3>大模型正在分析经营数据…</h3>
        <p class="th-sub">{{ current?.name }} · RAG 私有知识库检索中</p>
        <ul class="steps">
          <li v-for="(s, i) in steps" :key="i" :class="{ on: i <= stepIndex }"><span class="sp" />{{ s }}</li>
        </ul>
      </div>

      <!-- 报告纸 -->
      <div v-else class="rc-paper-wrap">
        <div class="report-paper rise-in">
          <div class="paper-grid" />
          <div class="stamp">
            <svg viewBox="0 0 140 140" width="116" height="116">
              <defs><path id="rc-arc" d="M70,70 m-52,0 a52,52 0 1,1 104,0 a52,52 0 1,1 -104,0" /></defs>
              <circle cx="70" cy="70" r="62" fill="none" stroke="#C8102E" stroke-width="2.6" />
              <circle cx="70" cy="70" r="52" fill="none" stroke="#C8102E" stroke-width="1" />
              <text class="stamp-arc"><textPath href="#rc-arc" startOffset="0%">中国工商银行 · 贷后风控中心 · 豫宿巡</textPath></text>
              <path d="M70 46l5.6 11.4 12.6 1.8-9.1 8.9 2.1 12.5L70 74.7 58.8 80.6l2.1-12.5-9.1-8.9 12.6-1.8z" fill="#C8102E" />
              <text x="70" y="102" text-anchor="middle" class="stamp-txt">贷后风控</text>
            </svg>
          </div>

          <header class="rp-head">
            <div class="rp-org">中国工商银行 · 豫宿巡贷后风控中心</div>
            <h1 class="rp-title title-serif">贷后风险巡检报告</h1>
            <div class="rp-meta">
              <span>报告编号：<em class="num">{{ reportId || reportNo }}</em></span>
              <span>生成时间：<em class="num">{{ shortTime(generatedAt) }}</em></span>
              <span>巡检对象：<em>{{ current?.name || '—' }}</em></span>
              <span>数据来源：<em>合规沙盒数据 · 仅用于学术研究</em></span>
            </div>
          </header>
          <div class="rp-rule" />
          <article class="rp-body" v-html="html" />
          <footer class="rp-foot">
            <div class="rp-note">本报告由「豫宿巡」AI 引擎自动生成，仅供贷后管理辅助参考，不构成授信决策依据。</div>
            <div class="rp-sign"><div>客户经理：<span class="sign-line" /></div><div>复核人：<span class="sign-line" /></div></div>
          </footer>
        </div>

        <div class="rc-actions">
          <button class="btn btn-ghost" @click="download">下载报告</button>
          <button class="btn btn-ghost" @click="generate">重新生成</button>
          <button class="btn btn-gold" :disabled="pushed" @click="sync">
            {{ pushed ? '✅ 已下发老板端' : '📲 同步整改建议至老板端' }}
          </button>
        </div>
      </div>

      <!-- ========== 已保存报告 ========== -->
      <section v-if="history.length" class="rc-history glass">
        <div class="rh-head">
          <h4>已保存巡检报告</h4>
          <span class="mono-label">{{ history.length }} 份 · 生成即入库</span>
        </div>
        <div class="rh-list no-scrollbar">
          <div v-for="rp in history" :key="rp.report_id" class="rh-item" :class="{ current: rp.report_id === (reportId || reportNo) }">
            <span class="level-tag" :class="'risk-' + rp.risk_level">{{ riskText[rp.risk_level] }}</span>
            <div class="rh-body">
              <div class="rh-top">
                <b class="num">{{ rp.report_id }}</b>
                <span class="rh-badge" :class="rp.mode === 'llm' ? 'llm' : 'off'">{{ rp.mode === 'llm' ? '大模型' : '离线模板' }}</span>
                <span v-if="rp.pushed_to_app" class="rh-pushed">已下发</span>
              </div>
              <p class="rh-sub">{{ shortTime(rp.generated_at) }} · {{ (rp.report_content || '').replace(/[#*\n]/g, ' ').slice(0, 56) }}…</p>
            </div>
            <div class="rh-ops">
              <button class="op" @click="viewHistory(rp)">查看</button>
              <button class="op gold" :disabled="rp.pushed_to_app" @click="pushReport(rp)">
                {{ rp.pushed_to_app ? '已下发' : '下发' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </section>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import AiBrain from '@/components/bank/AiBrain.vue'
import { store } from '@/store'
import api from '@/api'
import { renderMarkdown, shortTime, percent, RISK_TEXT } from '@/utils/format'
import { bus } from '@/utils/bus'

const riskText = RISK_TEXT
const id = ref(store.currentHomestayId || 'LY001')
const busy = ref(false)
const report = ref('')
const reportId = ref('')
const pushed = ref(false)
const history = ref([])
const generatedAt = ref('')
const toast = ref('')
const stepIndex = ref(0)
let stepTimer = null
let toastTimer = null

const steps = [
  '抽取该民宿经营与贷款数据',
  'RAG 检索私有知识库（本店 SOP / 贷后管理办法）',
  '大模型生成风险分析与建议措施',
  '排版输出结构化巡检报告'
]

const sorted = computed(() => {
  const order = { red: 0, amber: 1, green: 2 }
  return [...store.homestays].sort((a, b) => (order[a.risk_level] ?? 3) - (order[b.risk_level] ?? 3))
})
const current = computed(() => store.homestays.find((h) => h.id === id.value))
const html = computed(() => renderMarkdown(report.value))
const llmLabel = computed(() => ({ qwen: '通义千问', deepseek: 'DeepSeek', offline: '离线兜底' }[store.llmMode] || '检测中'))
const vectorLabel = computed(() => ({ chromadb: 'ChromaDB', offline: '内置检索', builtin: '内置检索' }[store.vectorMode] || '检测中'))
const reportNo = computed(() => {
  const d = new Date(generatedAt.value || Date.now())
  const p = (n) => String(n).padStart(2, '0')
  return `YSX-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${id.value}`
})

async function generate() {
  if (busy.value) return
  busy.value = true
  report.value = ''
  reportId.value = ''
  pushed.value = false
  stepIndex.value = 0
  stepTimer = setInterval(() => { if (stepIndex.value < steps.length - 1) stepIndex.value++ }, 800)
  try {
    const res = await api.generateReport(id.value)
    await new Promise((r) => setTimeout(r, 1400))
    report.value = res?.report_content || ''
    reportId.value = res?.report_id || ''
    pushed.value = !!res?.pushed_to_app
    generatedAt.value = res?.generated_at || new Date().toISOString()
    await loadHistory()
    show('巡检报告已生成并保存入库')
  } catch (e) {
    report.value = ''
    show(e?.message || '报告生成失败，请确认后端已启动')
  } finally {
    clearInterval(stepTimer)
    busy.value = false
  }
}

async function loadHistory() {
  try {
    const res = await api.reports(id.value)
    history.value = res?.list || []
  } catch {
    history.value = []
  }
}

function viewHistory(rp) {
  report.value = rp.report_content || ''
  generatedAt.value = rp.generated_at || ''
  reportId.value = rp.report_id || ''
  pushed.value = !!rp.pushed_to_app
}

async function pushReport(rp) {
  try {
    const res = await api.pushReport(rp.report_id)
    if (res?.report) {
      history.value = history.value.map((x) => (x.report_id === rp.report_id ? res.report : x))
      if (reportId.value === rp.report_id) pushed.value = true
    }
    bus.emit('report:rectify', {
      homestay_id: id.value,
      homestay_name: current.value?.name,
      content: rp.report_content,
      at: Date.now()
    })
    show('巡检报告已下发至老板端 App')
  } catch (e) {
    show(e?.message || '下发失败，请确认后端已启动')
  }
}

function download() {
  const text = [`《豫宿巡·贷后风险巡检报告》`, `报告编号：${reportId.value || reportNo.value}`, `生成时间：${generatedAt.value}`, `巡检对象：${current.value?.name || ''}`, '', report.value].join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `豫宿巡巡检报告_${id.value}_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(a.href)
}

function sync() {
  const rp = history.value.find((x) => x.report_id === reportId.value)
  if (rp) return pushReport(rp)
  show('请先点击「生成 AI 巡检报告」再同步至老板端')
}

watch(id, () => {
  store.currentHomestayId = id.value
  report.value = ''
  reportId.value = ''
  pushed.value = false
  generatedAt.value = ''
  loadHistory()
})

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2800)
}
onBeforeUnmount(() => { clearInterval(stepTimer); clearTimeout(toastTimer) })
onMounted(() => {
  if (store.homestays.length && !store.homestays.find((h) => h.id === id.value)) id.value = store.homestays[0].id
  loadHistory()
})
</script>

<style scoped>
.rc { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; align-items: start; }

/* 左侧 */
.rc-side { padding: 15px 14px; border-radius: var(--r-md); position: sticky; top: 0; max-height: calc(100vh - 130px); display: flex; flex-direction: column; }
.rs-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 11px; }
.rs-head h4 { font-size: 14px; color: var(--text-1); }
.rs-list { display: flex; flex-direction: column; gap: 7px; overflow-y: auto; }
.rs-item {
  display: flex; align-items: center; gap: 10px; text-align: left; width: 100%;
  padding: 10px 11px; border-radius: 10px; border: 1px solid transparent;
  background: rgba(255, 255, 255, .02); transition: all .25s var(--ease-out);
}
.rs-item:hover { background: rgba(22, 93, 255, .1); }
.rs-item.active { background: linear-gradient(90deg, color-mix(in srgb, var(--risk) 20%, transparent), rgba(22, 93, 255, .06)); border-color: color-mix(in srgb, var(--risk) 42%, transparent); }
.rs-bar { width: 3px; align-self: stretch; border-radius: 3px; background: var(--risk); box-shadow: 0 0 10px var(--risk-glow); }
.rs-body { flex: 1; min-width: 0; }
.rs-name { font-size: 13px; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rs-meta { display: flex; gap: 10px; margin-top: 4px; font-size: 10.5px; color: var(--text-3); }
.rs-item .level-tag { height: 19px; font-size: 10.5px; padding: 0 7px; }

/* 右侧 */
.rc-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.rc-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 18px; border-radius: var(--r-md); flex-wrap: wrap; }
.rt-left { display: flex; align-items: center; gap: 12px; }
.rt-left b { font-size: 16px; color: #fff; }
.rt-right { display: flex; align-items: center; gap: 14px; }
.rt-hint { display: inline-flex; align-items: center; gap: 7px; font-size: 11.5px; color: var(--text-3); }
.rt-hint i { width: 6px; height: 6px; border-radius: 50%; background: var(--risk-green); box-shadow: 0 0 8px var(--risk-green-glow); animation: soft-pulse 1.5s infinite; }

/* 空态 */
.rc-empty { padding: 34px; border-radius: var(--r-md); }
.re-vis { display: flex; align-items: center; gap: 30px; flex-wrap: wrap; }
.re-brain { width: 220px; height: 220px; flex: 0 0 220px; }
.re-copy { flex: 1; min-width: 260px; }
.re-copy h3 { font-size: 22px; color: #fff; letter-spacing: .06em; }
.re-copy p { margin-top: 12px; font-size: 13.5px; color: var(--text-2); line-height: 1.9; }
.re-copy p b { color: #cfe0ff; }
.re-steps { margin: 16px 0 22px; display: flex; flex-direction: column; gap: 9px; }
.re-steps li { position: relative; padding-left: 18px; font-size: 12.5px; color: var(--text-3); line-height: 1.7; }
.re-steps li::before { content: ""; position: absolute; left: 0; top: 7px; width: 6px; height: 6px; border-radius: 2px; background: var(--brand-gold); }

/* 生成中 */
.rc-thinking { padding: 40px; border-radius: var(--r-md); text-align: center; }
.th-brain { width: 260px; height: 260px; margin: 0 auto; }
.rc-thinking h3 { font-family: var(--font-serif); font-size: 21px; color: #fff; letter-spacing: .1em; margin-top: 6px; }
.th-sub { font-size: 13px; color: var(--text-3); margin-top: 8px; }
.steps { margin: 22px auto 0; width: fit-content; text-align: left; display: flex; flex-direction: column; gap: 10px; }
.steps li { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-3); transition: color .3s; }
.steps li .sp { width: 8px; height: 8px; border-radius: 50%; background: rgba(120, 150, 195, .3); transition: all .3s; }
.steps li.on { color: #cfe0ff; }
.steps li.on .sp { background: var(--brand-blue); box-shadow: 0 0 12px var(--accent-glow); animation: soft-pulse 1.2s infinite; }

/* 报告纸 */
.rc-paper-wrap { display: flex; flex-direction: column; gap: 14px; }
.report-paper {
  position: relative; padding: 40px 52px 34px; border-radius: 6px; overflow: hidden;
  background: linear-gradient(180deg, #fbfcfe, #f3f6fa);
  box-shadow: 0 30px 70px -40px rgba(0, 0, 0, .95);
  color: #1c2434; border-top: 3px solid #165dff;
}
.paper-grid { position: absolute; inset: 0; pointer-events: none; opacity: .5; background-image: radial-gradient(rgba(22, 93, 255, .07) 1px, transparent 1px); background-size: 22px 22px; }
.stamp { position: absolute; right: 36px; top: 38%; opacity: .8; transform: rotate(-14deg); pointer-events: none; }
.stamp-arc { font-size: 10.5px; fill: #c8102e; letter-spacing: 2.2px; font-family: var(--font-sans); }
.stamp-txt { font-size: 15px; fill: #c8102e; letter-spacing: 4px; font-family: var(--font-serif); font-weight: 700; }

.rp-org { font-size: 12px; color: #5a6b86; letter-spacing: .18em; position: relative; z-index: 2; }
.rp-title { margin-top: 10px; font-size: 30px; color: #0e1f3d; letter-spacing: .12em; position: relative; z-index: 2; }
.rp-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-top: 16px; font-size: 12.5px; color: #5a6b86; position: relative; z-index: 2; }
.rp-meta em { font-style: normal; color: #1c2434; font-weight: 600; }
.rp-rule { height: 2px; margin: 20px 0 6px; background: linear-gradient(90deg, #165dff, #ffb800 60%, transparent); position: relative; z-index: 2; }
.rp-body { position: relative; z-index: 2; }
:deep(.md-h) { font-family: var(--font-serif); color: #0e1f3d; letter-spacing: .06em; margin: 20px 0 8px; font-size: 16.5px; padding-left: 11px; border-left: 3px solid #165dff; }
:deep(h2.md-h) { font-size: 19px; }
:deep(.md-p) { font-size: 13.5px; line-height: 2; color: #2c3648; margin: 6px 0; }
:deep(.md-ul li), :deep(.md-ol li) { font-size: 13.5px; line-height: 1.95; color: #2c3648; padding-left: 18px; position: relative; }
:deep(.md-ul) { margin: 6px 0; }
:deep(.md-ul li)::before { content: ""; position: absolute; left: 4px; top: 10px; width: 5px; height: 5px; border-radius: 50%; background: #165dff; }
:deep(.md-ol) { margin: 6px 0; counter-reset: ol; }
:deep(.md-ol li) { counter-increment: ol; }
:deep(.md-ol li)::before { content: counter(ol); position: absolute; left: 0; top: 4px; font-size: 11px; font-family: var(--font-num); color: #fff; background: #165dff; width: 15px; height: 15px; border-radius: 50%; display: grid; place-items: center; }
:deep(.md-quote) { margin: 8px 0; padding: 9px 14px; background: rgba(22, 93, 255, .06); border-left: 3px solid #165dff; font-size: 13px; color: #3b465c; border-radius: 0 6px 6px 0; }
:deep(.md-p strong), :deep(.md-ul li strong), :deep(.md-ol li strong) { color: #b4232a; font-weight: 700; }

.rp-foot { position: relative; z-index: 2; margin-top: 28px; padding-top: 16px; border-top: 1px dashed rgba(28, 36, 52, .18); }
.rp-note { font-size: 11.5px; color: #7a879c; line-height: 1.85; }
.rp-sign { display: flex; gap: 40px; margin-top: 16px; font-size: 12.5px; color: #4a5568; }
.sign-line { display: inline-block; width: 110px; border-bottom: 1px solid rgba(28, 36, 52, .35); }

.rc-actions { display: flex; gap: 12px; justify-content: flex-end; flex-wrap: wrap; }

/* 已保存报告 */
.rc-history { padding: 15px 18px; border-radius: var(--r-md); }
.rh-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 11px; }
.rh-head h4 { font-size: 14px; color: var(--text-1); }
.rh-list { display: flex; flex-direction: column; gap: 8px; max-height: 260px; overflow-y: auto; }
.rh-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 10px;
  background: rgba(255, 255, 255, .025); border: 1px solid var(--line); transition: all .22s;
}
.rh-item:hover { background: rgba(22, 93, 255, .08); border-color: var(--line-strong); }
.rh-item.current { border-color: rgba(22, 93, 255, .5); background: rgba(22, 93, 255, .1); }
.rh-item .level-tag { height: 20px; font-size: 11px; }
.rh-body { flex: 1; min-width: 0; }
.rh-top { display: flex; align-items: center; gap: 9px; }
.rh-top b { font-size: 12.5px; color: var(--text-1); }
.rh-badge { font-size: 10px; padding: 1px 7px; border-radius: 4px; }
.rh-badge.llm { color: #9dc0ff; background: rgba(22, 93, 255, .14); }
.rh-badge.off { color: var(--text-3); background: rgba(255, 255, 255, .06); }
.rh-pushed { font-size: 10px; color: #9ff0b4; background: rgba(0, 180, 42, .14); padding: 1px 7px; border-radius: 4px; }
.rh-sub { font-size: 11px; color: var(--text-3); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rh-ops { display: flex; gap: 7px; flex: 0 0 auto; }
.op { font-size: 11.5px; padding: 4px 12px; border-radius: 7px; color: var(--text-2); border: 1px solid var(--line); transition: all .2s; }
.op:hover:not(:disabled) { color: #fff; background: rgba(22, 93, 255, .16); border-color: var(--line-strong); }
.op.gold { color: #ffd08a; border-color: rgba(255, 184, 0, .34); }
.op.gold:hover:not(:disabled) { background: rgba(255, 184, 0, .16); color: #ffe0a3; }
.op:disabled { opacity: .5; cursor: default; }

.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 11px; font-size: 13.5px; z-index: 99;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong); color: var(--text-1); box-shadow: var(--shadow-lift);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

@media (max-width: 1160px) {
  .rc { grid-template-columns: 1fr; }
  .rc-side { position: static; max-height: none; }
  .rs-list { max-height: 260px; }
}
@media (max-width: 700px) {
  .report-paper { padding: 26px 20px; }
  .rp-meta { grid-template-columns: 1fr; }
  .stamp { display: none; }
}
</style>
