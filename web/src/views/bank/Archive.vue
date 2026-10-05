<template>
  <div class="archive">
    <!-- ========== 民宿切换 ========== -->
    <section class="picker glass">
      <div class="pk-left">
        <span class="mono-label">巡检对象</span>
        <div class="pk-select">
          <button class="pk-current" @click="open = !open">
            <span class="dot" :class="'risk-' + (hs?.risk_level || 'green')" />
            <b>{{ hs?.name || '加载中…' }}</b>
            <span class="pk-city">{{ hs?.city }}</span>
            <svg viewBox="0 0 24 24" width="14" height="14" :style="{ transform: open ? 'rotate(180deg)' : '' }"><path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <transition name="pop">
            <div v-if="open" class="pk-menu no-scrollbar">
              <button v-for="h in store.homestays" :key="h.id" class="pk-item" :class="{ active: h.id === id }" @click="select(h.id)">
                <span class="dot" :class="'risk-' + h.risk_level" />
                <span class="pki-name">{{ h.name }}</span>
                <span class="pki-city">{{ h.city }}</span>
              </button>
            </div>
          </transition>
        </div>
      </div>
      <div class="pk-right">
        <div class="pk-meta">
          <span>{{ hs?.address || '—' }}</span>
          <span>业主：{{ hs?.owner?.name || '—' }} · {{ hs?.owner?.phone || '' }}</span>
        </div>
        <div class="pk-tags">
          <span v-for="t in hs?.cultural_tags || []" :key="t" class="chip">{{ t }}</span>
        </div>
      </div>
    </section>

    <!-- ========== 核心指标 ========== -->
    <section class="core stagger">
      <div class="core-card glass risk-red">
        <label>合同金额</label>
        <div class="cc-v"><span class="num num-lg">{{ money(hs?.loan_amount) }}</span></div>
        <span class="cc-sub">授信上限 {{ money(hs?.credit_limit) }}</span>
      </div>
      <div class="core-card glass risk-amber">
        <label>已用额度</label>
        <div class="cc-v"><span class="num num-lg">{{ money(hs?.loan_used) }}</span></div>
        <div class="cc-progress"><i :style="{ width: percent(hs?.used_ratio ?? (hs?.loan_used / hs?.loan_amount), 0) }" /></div>
      </div>
      <div class="core-card glass risk-blue">
        <label>贷后余额（未偿本金）</label>
        <div class="cc-v"><span class="num num-lg">{{ money(hs?.loan_balance) }}</span></div>
        <span class="cc-sub">可用于风控敞口测算</span>
      </div>
      <div class="core-card glass risk-green">
        <label>下期应还 / 还款日</label>
        <div class="cc-v"><span class="num num-lg">{{ money(hs?.monthly_repayment, '元') }}</span></div>
        <span class="cc-sub">{{ hs?.repayment_day || '—' }}</span>
      </div>
    </section>

    <!-- ========== 趋势图 ========== -->
    <section class="charts">
      <div class="chart-card glass span2">
        <div class="c-head">
          <h4>近 30 天经营趋势</h4>
          <div class="segmented">
            <button v-for="m in modes" :key="m.key" :class="{ 'is-active': mode === m.key }" @click="mode = m.key">{{ m.label }}</button>
          </div>
        </div>
        <EChart :option="trendOption" height="300px" />
      </div>

      <div class="chart-card glass">
        <div class="c-head"><h4>近 7 日入住率</h4><span class="mono-label">阈值 30%</span></div>
        <EChart :option="occOption" height="212px" />
        <p class="c-note" :class="occRisk">
          {{ occRisk === 'risk-red' ? '⚠️ 连续 7 天低于 30%，已触发 R002 黄色预警' : '✅ 入住率未触发连续低于阈值规则' }}
        </p>
      </div>

      <div class="chart-card glass">
        <div class="c-head"><h4>OTA 评分走势</h4><span class="mono-label">阈值 4.0</span></div>
        <EChart :option="otaOption" height="212px" />
        <p class="c-note" :class="otaRisk">
          {{ otaRisk === 'risk-red' ? '🔴 评分已跌破 4.0，触发 R001 红色预警' : '✅ 评分处于安全区间' }}
        </p>
      </div>
    </section>

    <!-- ========== 舆情 + 评价 ========== -->
    <section class="sentiment">
      <div class="chart-card glass">
        <div class="c-head"><h4>舆情热词云</h4><span class="mono-label">近 7 日评价关键词</span></div>
        <div class="wordcloud">
          <span v-for="w in words" :key="w.k" class="wc-item" :class="w.tone"
            :style="{ fontSize: w.size + 'px', opacity: w.opacity }">{{ w.k }}
            <em class="num">{{ w.v }}</em>
          </span>
          <p v-if="!words.length" class="c-empty">暂无关键词数据</p>
        </div>
      </div>

      <div class="chart-card glass">
        <div class="c-head"><h4>近期真实评价</h4><span class="mono-label">合规爬取 · 公开页面</span></div>
        <div class="reviews no-scrollbar">
          <div v-for="(rv, i) in reviews" :key="i" class="review" :class="rv.score < 3 ? 'is-bad' : 'is-good'">
            <div class="rv-head">
              <span class="rv-platform">{{ rv.platform }}</span>
              <span class="rv-score num">{{ Number(rv.score).toFixed(1) }}</span>
              <span class="rv-date">{{ rv.date }}</span>
            </div>
            <p class="rv-content">{{ rv.content }}</p>
            <div class="rv-tags">
              <span v-for="k in rv.keywords || []" :key="k" class="rv-tag" :class="negWords.includes(k) ? 'neg' : 'pos'">{{ k }}</span>
            </div>
          </div>
          <p v-if="!reviews.length" class="c-empty">暂无评价样本</p>
        </div>
      </div>
    </section>

    <!-- ========== AI 预警 · 下发老板端 ========== -->
    <section class="chart-card glass warn-panel">
      <div class="c-head">
        <h4>AI 风险预警 · 下发老板端</h4>
        <span class="mono-label">AI 依据评分 / 评论 / 对话记录自动生成</span>
      </div>

      <div class="wp-actions">
        <button class="btn btn-primary" :disabled="genBusy" @click="genWarning">
          {{ genBusy ? 'AI 分析中…' : '⚡ AI 生成预警' }}
        </button>
        <button class="btn btn-gold" :disabled="!aiWarning || aiWarning.pushed_to_app" @click="pushWarning">
          {{ aiWarning?.pushed_to_app ? '✅ 已下发老板端' : '📲 下发至老板端' }}
        </button>
        <span v-if="aiWarning" class="wp-mode">
          {{ aiWarning.mode === 'llm' ? '大模型生成' : '离线模板生成' }}
        </span>
      </div>

      <div v-if="aiWarning" class="wp-card" :class="'risk-' + aiWarning.level">
        <div class="wp-top">
          <span class="level-tag" :class="'risk-' + aiWarning.level">{{ riskText[aiWarning.level] }}</span>
          <b>{{ aiWarning.rule_name }}</b>
          <span class="wp-time num">{{ shortTime(aiWarning.created_at) }}</span>
        </div>
        <p class="wp-reason">{{ aiWarning.reason }}</p>
        <div class="wp-sug">
          <span class="sug-label">AI 整改建议</span>
          <p>{{ aiWarning.suggestion }}</p>
        </div>
        <div v-if="aiWarning.sources?.length" class="wp-src">
          <span class="mono-label">参考知识</span>
          <span v-for="s in aiWarning.sources" :key="s.source" class="src-chip">{{ s.source }}</span>
        </div>
      </div>
      <div v-else class="wp-empty">
        点击「AI 生成预警」，系统将综合该店评分、近期评论与 AI 对话记录生成预警文案，可一键下发至老板端 App。
      </div>
    </section>

    <!-- ========== 巡检历史 ========== -->
    <section class="chart-card glass">
      <div class="c-head">
        <h4>AI 巡检报告历史</h4>
        <button class="btn btn-primary" @click="openReport(id)">生成新报告</button>
      </div>
      <div class="history">
        <div v-if="!reports.length" class="c-empty">该民宿暂无历史巡检报告，点击右上角生成</div>
        <div v-for="rp in reports" :key="rp.id || rp.generated_at" class="hs-item">
          <span class="hs-dot" />
          <div class="hs-body">
            <div class="hs-top">
              <b>{{ rp.title || '贷后风险巡检报告' }}</b>
              <span class="hs-time num">{{ shortTime(rp.generated_at) }}</span>
            </div>
            <p class="hs-preview">{{ (rp.report_content || '').replace(/[#*\n]/g, ' ').slice(0, 120) }}…</p>
          </div>
          <span v-if="rp.risk_level" class="level-tag" :class="'risk-' + rp.risk_level">{{ riskText[rp.risk_level] }}</span>
        </div>
      </div>
    </section>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EChart from '@/components/EChart.vue'
import { store, openReport, refreshWarnings } from '@/store'
import api from '@/api'
import { bus } from '@/utils/bus'
import { money, percent, shortTime, RISK_TEXT } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const riskText = RISK_TEXT

const id = ref(route.query.id || store.currentHomestayId || 'LY001')
const open = ref(false)
const mode = ref('all')
const data = ref(null)
const toast = ref('')
const genBusy = ref(false)
const aiWarning = ref(null)
let toastTimer = null

const modes = [
  { key: 'all', label: '综合' },
  { key: 'occupancy', label: '入住率' },
  { key: 'revenue', label: '营收' }
]

const negWords = ['卫生差', '隔音差', '设施差', '服务差', '位置偏', '价格高', '房间小', '有异味', '噪音大']

const hs = computed(() => {
  const fromList = store.homestays.find((h) => h.id === id.value)
  return data.value?.homestay || fromList || null
})
const trends = computed(() => data.value?.trends || {})
const reviews = computed(() => data.value?.review_samples || [])
const keywordCounts = computed(() => data.value?.keyword_counts || {})
const reports = computed(() => data.value?.reports || [])

const occRisk = computed(() => {
  const arr = hs.value?.occupancy_7d || []
  return arr.length && arr.every((v) => v < 0.3) ? 'risk-red' : 'risk-green'
})
const otaRisk = computed(() => (hs.value?.ota_score < 4.0 ? 'risk-red' : 'risk-green'))

const words = computed(() => {
  const entries = Object.entries(keywordCounts.value)
  if (!entries.length) return []
  const max = Math.max(...entries.map(([, v]) => v))
  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({
      k,
      v,
      size: 13 + (v / max) * 17,
      opacity: 0.55 + (v / max) * 0.45,
      tone: negWords.includes(k) ? 'neg' : 'pos'
    }))
})

/** 综合趋势：入住率 + 平均房价 + 营收 */
const trendOption = computed(() => {
  const t = trends.value
  const dates = (t.dates || []).map((d) => String(d).slice(5))
  const occupancy = (t.occupancy || []).map((v) => +(v * 100).toFixed(1))
  const price = t.avg_price || []
  const revenue = t.revenue || []

  const showOcc = mode.value === 'all' || mode.value === 'occupancy'
  const showRev = mode.value === 'all' || mode.value === 'revenue'

  return {
    legend: { top: 0, right: 0, textStyle: { color: '#A9BCD9', fontSize: 11 }, icon: 'roundRect', itemWidth: 10, itemHeight: 10 },
    tooltip: { trigger: 'axis', confine: true },
    grid: { left: 6, right: 8, top: 48, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false, data: dates,
      axisLabel: { hideOverlap: true, interval: 'auto' }
    },
    yAxis: [
      { type: 'value', name: '入住率%', nameGap: 16, nameTextStyle: { color: '#6D82A6', fontSize: 10 }, axisLabel: { formatter: '{value}%' } },
      { type: 'value', name: '营收(元)', nameGap: 16, nameTextStyle: { color: '#6D82A6', fontSize: 10 }, splitLine: { show: false } }
    ],
    series: [
      ...(showRev ? [{
        name: '日营收',
        type: 'bar',
        yAxisIndex: 1,
        data: revenue,
        barWidth: '46%',
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(22,93,255,.85)' }, { offset: 1, color: 'rgba(22,93,255,.12)' }]
          }
        }
      }] : []),
      ...(showOcc ? [{
        name: '入住率',
        type: 'line',
        smooth: true,
        data: occupancy,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2.6, color: '#FFB800', shadowColor: 'rgba(255,184,0,.55)', shadowBlur: 12 },
        itemStyle: { color: '#FFB800' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(255,184,0,.26)' }, { offset: 1, color: 'rgba(255,184,0,0)' }]
          }
        },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ yAxis: 30, name: '预警线' }],
          lineStyle: { color: '#F53F3F', type: 'dashed', width: 1.4 },
          label: { formatter: '预警线 30%', color: '#F53F3F', fontSize: 10, position: 'insideEndTop' }
        }
      }] : []),
      ...(mode.value === 'all' ? [{
        name: '平均房价',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: (price || []).map((v) => v * 30),
        symbol: 'none',
        lineStyle: { width: 1.6, color: 'rgba(0,180,42,.75)', type: 'dotted' }
      }] : [])
    ]
  }
})

const occOption = computed(() => {
  const arr = hs.value?.occupancy_7d || []
  const labels = arr.map((_, i) => `D-${arr.length - i}`)
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>入住率 ${(p[0].value).toFixed(1)}%` },
    grid: { left: 4, right: 8, top: 22, bottom: 4, containLabel: true },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', max: 60, axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: arr.map((v) => +(v * 100).toFixed(1)),
      barWidth: '48%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: (p) => (p.value < 30 ? '#F53F3F' : '#00B42A')
      },
      markLine: {
        silent: true, symbol: 'none',
        data: [{ yAxis: 30 }],
        lineStyle: { color: 'rgba(245,63,63,.8)', type: 'dashed', width: 1.3 },
        label: { formatter: '30%', color: '#F53F3F', fontSize: 10 }
      }
    }]
  }
})

const otaOption = computed(() => {
  const t = trends.value.ota || []
  const dates = (trends.value.dates || []).map((d) => String(d).slice(5))
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 4, right: 8, top: 22, bottom: 4, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: dates.filter((_, i) => i % 3 === 0) },
    yAxis: { type: 'value', min: 3, max: 5, axisLabel: { formatter: '{value}' } },
    series: [{
      type: 'line',
      smooth: true,
      data: t.filter((_, i) => i % 3 === 0),
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.6, color: '#165DFF', shadowColor: 'rgba(22,93,255,.6)', shadowBlur: 12 },
      itemStyle: { color: (p) => (p.value < 4 ? '#F53F3F' : '#4B83FF') },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(22,93,255,.3)' }, { offset: 1, color: 'rgba(22,93,255,0)' }]
        }
      },
      markLine: {
        silent: true, symbol: 'none',
        data: [{ yAxis: 4 }],
        lineStyle: { color: 'rgba(245,63,63,.8)', type: 'dashed', width: 1.3 },
        label: { formatter: '预警线 4.0', color: '#F53F3F', fontSize: 10, position: 'insideEndTop' }
      }
    }]
  }
})

async function load() {
  data.value = null
  try {
    data.value = await api.archive(id.value)
  } catch {
    data.value = null
  }
}

async function loadAiWarning() {
  aiWarning.value = null
  try {
    const res = await api.warnings()
    const list = (res?.list || []).filter((w) => w.homestay_id === id.value && w.rule_id === 'AI')
    list.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    aiWarning.value = list[0] || null
  } catch {
    aiWarning.value = null
  }
}

async function genWarning() {
  if (genBusy.value) return
  genBusy.value = true
  try {
    const res = await api.aiGenerateWarning(id.value)
    aiWarning.value = res?.warning || null
    show('AI 预警已生成，可下发至老板端')
    await refreshWarnings().catch(() => {})
  } catch (e) {
    show(e?.message || 'AI 预警生成失败')
  } finally {
    genBusy.value = false
  }
}

async function pushWarning() {
  if (!aiWarning.value?.id) return
  try {
    const res = await api.pushWarning(aiWarning.value.id)
    if (res?.warning) aiWarning.value = res.warning
    bus.emit('warning:new', { created: [aiWarning.value], at: Date.now() })
    show('预警已下发至老板端 App')
  } catch (e) {
    show(e?.message || '下发失败，请确认后端已启动')
  }
}

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 3000)
}

function select(newId) {
  open.value = false
  id.value = newId
  store.currentHomestayId = newId
  router.replace({ name: 'bank-archive', query: { id: newId } })
}

watch(id, () => { load(); loadAiWarning() })
onMounted(() => {
  if (store.homestays.length && !store.homestays.find((h) => h.id === id.value)) {
    id.value = store.homestays[0].id
  }
  load()
  loadAiWarning()
})
</script>

<style scoped>
.archive { display: flex; flex-direction: column; gap: 16px; }

/* 选择器 */
.picker { position: relative; z-index: 30; display: flex; align-items: center; gap: 26px; padding: 15px 18px; border-radius: var(--r-md); flex-wrap: wrap; }
.pk-left { display: flex; flex-direction: column; gap: 6px; }
.pk-select { position: relative; }
.pk-current {
  display: flex; align-items: center; gap: 10px; height: 42px; padding: 0 15px;
  border-radius: 10px; background: rgba(22, 93, 255, .1); border: 1px solid rgba(22, 93, 255, .3);
  color: #fff; font-size: 15px; transition: background .25s;
}
.pk-current:hover { background: rgba(22, 93, 255, .2); }
.pk-current b { font-weight: 600; }
.pk-city { font-size: 11.5px; color: var(--text-3); padding: 1px 7px; background: rgba(255, 255, 255, .06); border-radius: 5px; }
.pk-menu {
  position: absolute; z-index: 20; top: calc(100% + 6px); left: 0; width: 360px; max-height: 330px; overflow-y: auto;
  padding: 6px; border-radius: 12px; background: rgba(9, 22, 42, .97);
  border: 1px solid var(--line-strong); box-shadow: var(--shadow-lift); backdrop-filter: blur(14px);
}
.pk-item { display: flex; align-items: center; gap: 9px; width: 100%; text-align: left; padding: 9px 11px; border-radius: 8px; color: var(--text-2); font-size: 13px; transition: background .2s; }
.pk-item:hover { background: rgba(22, 93, 255, .16); color: #fff; }
.pk-item.active { background: rgba(22, 93, 255, .26); color: #fff; }
.pki-name { flex: 1; }
.pki-city { font-size: 11px; color: var(--text-3); }
.pk-right { display: flex; flex-direction: column; gap: 7px; flex: 1; min-width: 220px; }
.pk-meta { display: flex; gap: 18px; font-size: 12px; color: var(--text-3); flex-wrap: wrap; }
.pk-tags { display: flex; gap: 7px; flex-wrap: wrap; }

/* 核心指标 */
.core { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.core-card { padding: 15px 17px; border-radius: var(--r-md); }
.core-card label { font-size: 12.5px; color: var(--text-2); }
.cc-v { margin: 7px 0 5px; }
.cc-v .num { color: #fff; }
.cc-sub { font-size: 11.5px; color: var(--text-3); }
.cc-progress { height: 5px; margin-top: 8px; border-radius: 3px; background: rgba(255, 255, 255, .08); overflow: hidden; }
.cc-progress i { display: block; height: 100%; border-radius: 3px; background: linear-gradient(90deg, #ffcd4d, #ffb800); box-shadow: 0 0 12px rgba(255, 184, 0, .6); transition: width .8s var(--ease-out); }

/* 图表卡 */
.charts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.chart-card { padding: 16px 18px 17px; border-radius: var(--r-md); }
.span2 { grid-column: 1 / -1; }
.c-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 10px; flex-wrap: wrap; }
.c-head h4 { font-size: 14.5px; color: var(--text-1); font-weight: 700; letter-spacing: .04em; }
.c-note { margin-top: 8px; font-size: 12px; }
.c-note.risk-red { color: #ffb4b4; }
.c-note.risk-green { color: #9ff0b4; }
.c-empty { padding: 22px 4px; font-size: 12.5px; color: var(--text-3); text-align: center; }

/* 热词云 */
.sentiment { display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 16px; }
.wordcloud { display: flex; align-items: center; justify-content: center; align-content: center; flex-wrap: wrap; gap: 10px 16px; min-height: 214px; padding: 10px; }
.wc-item { display: inline-flex; align-items: baseline; gap: 4px; font-weight: 700; font-family: var(--font-serif); transition: transform .25s var(--ease-out); cursor: default; }
.wc-item:hover { transform: scale(1.12); }
.wc-item em { font-style: normal; font-size: 11px; font-family: var(--font-num); opacity: .7; }
.wc-item.neg { color: #ff7a7a; text-shadow: 0 0 18px rgba(245, 63, 63, .4); }
.wc-item.pos { color: #6fd98a; text-shadow: 0 0 18px rgba(0, 180, 42, .35); }

/* 评价 */
.reviews { display: flex; flex-direction: column; gap: 10px; max-height: 300px; overflow-y: auto; padding-right: 4px; }
.review { padding: 11px 13px; border-radius: 10px; background: rgba(255, 255, 255, .025); border-left: 3px solid var(--risk-green); }
.review.is-bad { border-left-color: var(--risk-red); background: rgba(245, 63, 63, .05); }
.rv-head { display: flex; align-items: center; gap: 10px; }
.rv-platform { font-size: 11px; color: var(--text-3); padding: 1px 7px; border-radius: 4px; background: rgba(255, 255, 255, .06); }
.rv-score { font-size: 14px; color: var(--risk-green); }
.review.is-bad .rv-score { color: var(--risk-red); }
.rv-date { margin-left: auto; font-size: 11px; color: var(--text-3); font-family: var(--font-num); }
.rv-content { font-size: 12.5px; color: var(--text-2); line-height: 1.7; margin-top: 7px; }
.rv-tags { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.rv-tag { font-size: 10.5px; padding: 1px 8px; border-radius: 4px; }
.rv-tag.neg { color: #ff9c9c; background: rgba(245, 63, 63, .14); }
.rv-tag.pos { color: #86e0a0; background: rgba(0, 180, 42, .14); }

/* 历史 */
.history { display: flex; flex-direction: column; gap: 4px; }
.hs-item { display: flex; align-items: center; gap: 12px; padding: 11px 4px; border-bottom: 1px solid var(--line); }
.hs-item:last-child { border-bottom: 0; }
.hs-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand-blue); box-shadow: 0 0 10px var(--accent-glow); flex: 0 0 8px; }
.hs-body { flex: 1; min-width: 0; }
.hs-top { display: flex; align-items: baseline; gap: 12px; }
.hs-top b { font-size: 13.5px; color: var(--text-1); }
.hs-time { font-size: 11px; color: var(--text-3); }
.hs-preview { font-size: 12px; color: var(--text-3); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* AI 预警下发 */
.warn-panel { position: relative; z-index: 1; }
.wp-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.wp-mode { font-size: 11.5px; color: var(--text-3); padding: 3px 10px; border-radius: 999px; background: rgba(255, 255, 255, .05); border: 1px solid var(--line); }
.wp-card {
  padding: 15px 17px; border-radius: 12px; border-left: 3px solid var(--risk, var(--brand-blue));
  background: linear-gradient(135deg, color-mix(in srgb, var(--risk) 8%, transparent), rgba(255, 255, 255, .02));
  border-top: 1px solid var(--line); border-right: 1px solid var(--line); border-bottom: 1px solid var(--line);
}
.wp-top { display: flex; align-items: center; gap: 11px; }
.wp-top b { flex: 1; font-size: 14px; color: var(--text-1); }
.wp-time { font-size: 11px; color: var(--text-3); }
.wp-reason { margin-top: 11px; font-size: 13px; color: var(--text-2); line-height: 1.85; }
.wp-sug { margin-top: 13px; padding: 12px 14px; border-radius: 10px; background: rgba(22, 93, 255, .07); border: 1px solid rgba(22, 93, 255, .18); }
.sug-label { display: inline-block; font-size: 11px; color: #9dc0ff; letter-spacing: .08em; }
.wp-sug p { margin-top: 6px; font-size: 12.5px; color: var(--text-2); line-height: 1.85; }
.wp-src { display: flex; align-items: center; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.src-chip { font-size: 11px; color: #cfe0ff; padding: 2px 9px; border-radius: 6px; background: rgba(22, 93, 255, .12); border: 1px solid rgba(22, 93, 255, .24); }
.wp-empty { padding: 22px; text-align: center; font-size: 12.5px; color: var(--text-3); border: 1px dashed var(--line); border-radius: 12px; line-height: 1.9; }

.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 11px; font-size: 13.5px; z-index: 99;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong); color: var(--text-1); box-shadow: var(--shadow-lift);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

.pop-enter-active { transition: all .22s var(--ease-out); }
.pop-leave-active { transition: all .16s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-8px); }

@media (max-width: 1240px) {
  .core { grid-template-columns: repeat(2, 1fr); }
  .sentiment { grid-template-columns: 1fr; }
}
@media (max-width: 900px) { .charts { grid-template-columns: 1fr; } }
</style>
