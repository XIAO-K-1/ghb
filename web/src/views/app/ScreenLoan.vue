<template>
  <div class="loan">
    <!-- 贷款总览 -->
    <section class="hero">
      <div class="hero-deco" />
      <div class="hero-top">
        <span class="hero-badge">豫游民宿贷</span>
        <span class="hero-status">{{ RISK_TEXT[hs.risk_level] || '低风险' }}</span>
      </div>
      <div class="hero-main">
        <span class="hm-label">剩余未偿还本金</span>
        <div class="hm-value">
          <span class="num num-xl">{{ (hs.loan_balance || 0).toLocaleString('zh-CN') }}</span>
          <span class="hm-unit">元</span>
        </div>
      </div>
      <div class="hero-ring">
        <div class="hr-circle" :style="{ '--p': usedPct, '--c': ringColor }">
          <span class="num">{{ usedPct }}%</span>
        </div>
        <span class="hr-cap">额度使用率</span>
      </div>
      <div class="hero-grid">
        <div class="hg-item"><span>授信额度</span><b class="num">{{ money(hs.credit_limit) }}</b></div>
        <div class="hg-item"><span>已用额度</span><b class="num">{{ money(hs.loan_used) }}</b></div>
        <div class="hg-item"><span>可用额度</span><b class="num">{{ money(hs.available_credit) }}</b></div>
        <div class="hg-item"><span>执行利率</span><b class="num">3.45%</b></div>
      </div>
    </section>

    <!-- 额度构成 -->
    <section class="card">
      <div class="cc-head">
        <h4>额度使用构成</h4>
        <span class="mono-label">实时</span>
      </div>
      <EChart :option="quotaOption" height="176px" theme="light" />
    </section>

    <!-- 余额递减趋势 -->
    <section class="card">
      <div class="cc-head">
        <h4>剩余本金递减趋势</h4>
        <span class="hc-tag safe">预计 {{ schedule.length }} 期结清</span>
      </div>
      <EChart :option="balanceOption" height="168px" theme="light" />
    </section>

    <!-- 现金流覆盖 -->
    <section class="card">
      <div class="cc-head">
        <h4>现金流覆盖能力</h4>
        <span class="hc-tag" :class="coverOk ? 'safe' : 'danger'">{{ coverOk ? '覆盖充足' : '覆盖偏紧' }}</span>
      </div>
      <EChart :option="cashOption" height="164px" theme="light" />
      <p class="cf-note">月营收可覆盖月还款 <b class="num">{{ cover.toFixed(1) }}</b> 倍，银行安全线为 1.5 倍</p>
    </section>

    <!-- 还款计划 -->
    <section class="card">
      <div class="cc-head">
        <h4>未来还款计划</h4>
        <span class="mono-label">等额本息估算</span>
      </div>
      <div class="sched">
        <div class="sc-head">
          <span>期数</span><span>还款日</span><span>应还本息</span><span>剩余本金</span>
        </div>
        <div v-for="s in schedule" :key="s.idx" class="sc-row">
          <span class="sc-idx num">{{ s.idx }}</span>
          <span class="num">{{ s.date }}</span>
          <span class="num">{{ thousands(s.pay) }}</span>
          <span class="num">{{ thousands(s.left) }}</span>
        </div>
      </div>
    </section>

    <!-- 联系客户经理 -->
    <section class="card">
      <div class="cc-head">
        <h4>联系客户经理</h4>
        <span class="ai-tag">在线</span>
      </div>
      <div class="mgr">
        <div class="mgr-avatar">{{ manager.name[0] }}</div>
        <div class="mgr-info">
          <b>{{ manager.name }}</b>
          <p>{{ manager.bank }} · {{ manager.title }}</p>
        </div>
        <a class="mgr-call" :href="'tel:' + manager.phone">拨打电话</a>
      </div>

      <div class="chat">
        <div v-for="(m, i) in messages" :key="i" class="bubble" :class="m.me ? 'me' : 'them'">
          <p>{{ m.text }}</p>
          <span class="bt">{{ fmtTime(m.at) }}</span>
        </div>
        <div v-if="!messages.length" class="chat-empty">有任何贷款问题，可在此给客户经理留言</div>
      </div>

      <div class="chat-input">
        <input v-model="draft" placeholder="输入留言，如：下期能否调整还款日？" @keyup.enter="send" />
        <button class="send-btn" :disabled="!draft.trim()" @click="send">发送</button>
      </div>
    </section>

    <p class="ln-note">贷款数据经客户授权后由工行脱敏接口提供 · 本页为合规沙盒演示数据，不作实际还款依据</p>

    <transition name="toast">
      <div v-if="tip" class="tip">{{ tip }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import EChart from '@/components/EChart.vue'
import api from '@/api'
import { money, thousands, RISK_TEXT } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })

const hs = computed(() => props.homestay || {})
const usedPct = computed(() => Math.round((hs.value.used_ratio ?? 0) * 100))
const ringColor = computed(() => (usedPct.value >= 90 ? '#f53f3f' : usedPct.value >= 70 ? '#ff7d00' : '#ffb800'))

const cover = computed(() => {
  const rev = hs.value.monthly_revenue || 0
  const pay = hs.value.monthly_repayment || 0
  return pay > 0 ? rev / pay : 0
})
const coverOk = computed(() => cover.value >= 1.5)

/** 未来还款计划（按剩余本金 / 月还款额等额本息估算） */
const schedule = computed(() => {
  const pay = hs.value.monthly_repayment || 0
  let left = hs.value.loan_balance || 0
  const out = []
  const now = new Date()
  for (let i = 1; i <= 8 && left > 0; i++) {
    const interest = Math.round(left * 0.0345 / 12)
    const principal = Math.max(0, Math.min(pay - interest, left))
    left = Math.max(0, left - principal)
    const d = new Date(now.getFullYear(), now.getMonth() + i, 15)
    out.push({
      idx: i,
      date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-15`,
      pay, left
    })
  }
  return out
})

const quotaOption = computed(() => ({
  tooltip: { trigger: 'item', confine: true, formatter: '{b}<br/>{c} 元（{d}%）' },
  legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 10.5, color: '#4e5969' } },
  series: [{
    type: 'pie', radius: ['52%', '74%'], center: ['50%', '44%'], avoidLabelOverlap: true,
    itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 6 },
    label: { show: false }, labelLine: { show: false },
    data: [
      { value: hs.value.loan_used || 0, name: '已用额度', itemStyle: { color: '#165DFF' } },
      { value: hs.value.available_credit || 0, name: '可用额度', itemStyle: { color: '#FFB800' } }
    ]
  }]
}))

const balanceOption = computed(() => {
  const pts = [hs.value.loan_balance || 0, ...schedule.value.map((s) => s.left)]
  const xs = ['当前', ...schedule.value.map((s) => `第${s.idx}期`)]
  return {
    grid: { top: 18, left: 8, right: 14, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', confine: true, valueFormatter: (v) => `${Number(v).toLocaleString('zh-CN')} 元` },
    xAxis: { type: 'category', data: xs, axisLine: { lineStyle: { color: '#e5e8ef' } }, axisTick: { show: false }, axisLabel: { fontSize: 9.5, color: '#86909c', interval: 0 } },
    yAxis: {
      type: 'value', splitLine: { lineStyle: { color: '#f0f2f6' } },
      axisLabel: { fontSize: 9.5, color: '#86909c', formatter: (v) => (v >= 10000 ? `${(v / 10000).toFixed(0)}万` : v) }
    },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: pts,
      lineStyle: { width: 2.6, color: '#165DFF' },
      itemStyle: { color: '#165DFF', borderColor: '#fff', borderWidth: 1.5 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(22,93,255,.28)' }, { offset: 1, color: 'rgba(22,93,255,.02)' }]
        }
      }
    }]
  }
})

const cashOption = computed(() => {
  const rev = hs.value.monthly_revenue || 0
  const pay = hs.value.monthly_repayment || 0
  const safe = Math.round(pay * 1.5)
  return {
    grid: { top: 20, left: 8, right: 14, bottom: 6, containLabel: true },
    tooltip: { trigger: 'axis', confine: true, valueFormatter: (v) => `${Number(v).toLocaleString('zh-CN')} 元` },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f2f6' } }, axisLabel: { fontSize: 9.5, color: '#86909c', formatter: (v) => (v >= 10000 ? `${(v / 10000).toFixed(0)}万` : v) } },
    yAxis: { type: 'category', data: ['月还款额', '安全线(1.5倍)', '月经营营收'], axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 10.5, color: '#4e5969' } },
    series: [{
      type: 'bar', barWidth: 14, data: [
        { value: pay, itemStyle: { color: '#FF7D00', borderRadius: [0, 6, 6, 0] } },
        { value: safe, itemStyle: { color: '#86909c', borderRadius: [0, 6, 6, 0] } },
        { value: rev, itemStyle: { color: '#00B42A', borderRadius: [0, 6, 6, 0] } }
      ],
      label: { show: true, position: 'right', fontSize: 9.5, color: '#4e5969', formatter: (p) => `${Number(p.value).toLocaleString('zh-CN')}` }
    }]
  }
})

/* ---------------- 客户经理沟通（后端持久化 + 轮询接收经理回复） ---------------- */
const manager = { name: '王经理', bank: '工商银行洛阳分行', title: '普惠金融客户经理', phone: '0379-6588-1234' }
const messages = ref([])
const draft = ref('')
const tip = ref('')
let tipTimer = null
let pollTimer = null

function show(msg) {
  tip.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { tip.value = '' }, 1900)
}
function fmtTime(ts) {
  const d = new Date(ts)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadMsgs() {
  const id = hs.value.id
  if (!id) { messages.value = []; return }
  let raws = []
  try { raws = await api.messages(id) } catch { return }
  messages.value = raws.map((m) => ({
    id: m.id,
    me: m.sender === 'owner',
    text: m.text,
    at: new Date(String(m.at).replace(' ', 'T')).getTime() || Date.now()
  }))
}

async function send() {
  const t = draft.value.trim()
  if (!t || !hs.value.id) return
  draft.value = ''
  try {
    const m = await api.sendMessage(hs.value.id, 'owner', t)
    messages.value.push({ id: m.id, me: true, text: m.text, at: Date.now() })
    nextTick(() => show('留言已发送至客户经理'))
  } catch (e) {
    show(e?.message || '发送失败，请稍后再试')
  }
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(loadMsgs, 5000)
}
function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => { loadMsgs(); startPoll() })
watch(() => hs.value.id, () => { loadMsgs(); startPoll() })
onBeforeUnmount(stopPoll)
</script>

<style scoped>
.loan { padding-bottom: 22px; }

/* 贷款总览 */
.hero {
  position: relative; margin: 14px 14px 0; padding: 18px 17px 16px; border-radius: 20px; overflow: hidden;
  background: linear-gradient(150deg, #10233f 0%, #0a192f 58%, #14315c 100%);
  color: #eaf2ff; box-shadow: 0 26px 50px -30px rgba(10, 25, 47, .95);
  border: 1px solid rgba(255, 184, 0, .22);
}
.hero-deco {
  position: absolute; inset: 0; opacity: .16;
  background-image: radial-gradient(rgba(255, 255, 255, .7) 1px, transparent 1px);
  background-size: 17px 17px;
  mask-image: radial-gradient(ellipse 70% 80% at 92% 0%, #000, transparent 72%);
}
.hero-top { position: relative; display: flex; align-items: center; justify-content: space-between; }
.hero-badge {
  font-size: 11.5px; font-weight: 700; letter-spacing: .1em; color: #2a1c00;
  padding: 3px 11px; border-radius: 999px;
  background: linear-gradient(135deg, #ffcd4d, #ffb800);
}
.hero-status { font-size: 11.5px; color: #ffd666; }
.hero-main { position: relative; margin-top: 16px; }
.hm-label { font-size: 11.5px; color: #a9bcd9; }
.hm-value { display: flex; align-items: baseline; gap: 6px; margin-top: 5px; }
.hm-value .num { color: #fff; }
.hm-unit { font-size: 12px; color: #a9bcd9; }

.hero-ring { position: absolute; right: 16px; top: 62px; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.hr-circle {
  width: 74px; height: 74px; border-radius: 50%; display: grid; place-items: center; position: relative;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255, 255, 255, .12) 0);
}
.hr-circle::before { content: ""; position: absolute; inset: 8px; border-radius: 50%; background: #0c1b30; }
.hr-circle span { position: relative; font-size: 17px; color: #fff; }
.hr-cap { font-size: 10px; color: #a9bcd9; }

.hero-grid {
  position: relative; display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-top: 18px; padding-top: 14px;
  border-top: 1px solid rgba(96, 150, 255, .18);
}
.hg-item { display: flex; flex-direction: column; gap: 3px; }
.hg-item span { font-size: 10.5px; color: #6d82a6; }
.hg-item b { font-size: 13px; color: #eaf2ff; }

/* 卡片 */
.card {
  margin: 14px 14px 0; padding: 15px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.cc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.cc-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.hc-tag { font-size: 10.5px; padding: 2px 9px; border-radius: 999px; }
.hc-tag.safe { color: #00a844; background: rgba(0, 180, 42, .1); }
.hc-tag.danger { color: #f53f3f; background: rgba(245, 63, 63, .1); }
.ai-tag { font-size: 10.5px; font-weight: 700; color: #165dff; padding: 2px 9px; border-radius: 999px; background: rgba(22, 93, 255, .09); }
.cf-note { margin-top: 8px; font-size: 11px; color: #86909c; text-align: center; }
.cf-note b { color: #165dff; }

/* 还款计划 */
.sched { border-radius: 12px; overflow: hidden; border: 1px solid rgba(29, 33, 41, .07); }
.sc-head, .sc-row { display: grid; grid-template-columns: 44px 1fr 1fr 1.15fr; align-items: center; padding: 9px 10px; font-size: 11.5px; }
.sc-head { background: #f7f8fa; color: #86909c; font-size: 10.5px; }
.sc-row { color: #1d2129; border-top: 1px solid rgba(29, 33, 41, .05); }
.sc-row:nth-child(odd) { background: #fcfdff; }
.sc-idx { color: #165dff; font-weight: 700; }

/* 客户经理 */
.mgr { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border-radius: 13px; background: #f7f9fc; }
.mgr-avatar {
  width: 40px; height: 40px; border-radius: 13px; display: grid; place-items: center;
  font-size: 16px; font-weight: 700; color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff);
}
.mgr-info { flex: 1; }
.mgr-info b { font-size: 13.5px; color: #1d2129; }
.mgr-info p { font-size: 11px; color: #86909c; margin-top: 2px; }
.mgr-call {
  font-size: 11.5px; font-weight: 600; color: #165dff; padding: 6px 12px; border-radius: 999px;
  background: rgba(22, 93, 255, .1);
}

.chat { display: flex; flex-direction: column; gap: 9px; margin-top: 12px; max-height: 240px; overflow-y: auto; }
.chat-empty { text-align: center; font-size: 11.5px; color: #a9b0bd; padding: 16px 0; }
.bubble { max-width: 78%; padding: 9px 12px; border-radius: 13px; position: relative; }
.bubble p { font-size: 12.5px; line-height: 1.6; }
.bubble .bt { display: block; font-size: 9.5px; color: #a9b0bd; margin-top: 4px; }
.bubble.them { align-self: flex-start; background: #f2f4f8; color: #1d2129; border-top-left-radius: 4px; }
.bubble.me { align-self: flex-end; background: linear-gradient(135deg, #4b83ff, #165dff); color: #fff; border-top-right-radius: 4px; }
.bubble.me .bt { color: rgba(255, 255, 255, .75); text-align: right; }

.chat-input { display: flex; gap: 8px; margin-top: 12px; }
.chat-input input {
  flex: 1; height: 40px; padding: 0 13px; border-radius: 11px; font-size: 12.5px; color: #1d2129;
  background: #f7f8fa; border: 1.5px solid rgba(29, 33, 41, .08); outline: none; font-family: inherit;
  transition: all .22s;
}
.chat-input input:focus { border-color: #165dff; background: #fff; box-shadow: 0 0 0 4px rgba(22, 93, 255, .09); }
.send-btn {
  flex: 0 0 auto; padding: 0 18px; height: 40px; border-radius: 11px; font-size: 12.5px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff);
  transition: opacity .2s, transform .2s;
}
.send-btn:disabled { opacity: .5; }
.send-btn:not(:disabled):active { transform: scale(.97); }

.ln-note { margin: 16px 16px 0; font-size: 10.5px; color: #a9b0bd; line-height: 1.75; text-align: center; }

.tip {
  position: sticky; bottom: 12px; margin: 14px 20px 0; padding: 10px 14px; border-radius: 12px;
  font-size: 12px; color: #fff; background: rgba(29, 33, 41, .9); text-align: center;
  box-shadow: 0 14px 30px -18px rgba(0, 0, 0, .6);
}
.toast-enter-active, .toast-leave-active { transition: all .28s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
