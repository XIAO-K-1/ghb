<template>
  <div class="home">
    <!-- 渐变 Header -->
    <header class="hm-header">
      <div class="hh-deco" />
      <div class="hh-top">
        <div class="hh-place">
          <span class="hh-city">{{ homestay?.city || '洛阳' }}</span>
          <h2>{{ homestay?.name || '我的民宿' }}</h2>
        </div>
        <div class="hh-right">
          <div class="hh-weather">
            <span class="hw-temp num">{{ weather.temp }}°</span>
            <span class="hw-desc">{{ weather.desc }}</span>
          </div>
          <div class="hh-avatar">{{ user?.name?.[0] || '老' }}</div>
        </div>
      </div>

      <!-- 风险提示条 -->
      <transition name="pop">
        <button v-if="riskAlert" class="risk-bar" @click="$emit('go', 'rectify')">
          <span class="rb-ico">⚠️</span>
          <span class="rb-text">
            <b>贷后风险提示</b>
            {{ riskAlert.reason }}
          </span>
          <span class="rb-go">查看整改 →</span>
        </button>
      </transition>
      <div v-if="!riskAlert" class="risk-bar ok">
        <span class="rb-ico">✅</span>
        <span class="rb-text"><b>经营健康</b>当前未触发贷后风险规则，继续保持</span>
      </div>
    </header>

    <!-- 核心数据盘 -->
    <section class="hm-kpi">
      <div class="kpi-grid">
        <div v-for="k in kpis" :key="k.label" class="kpi-tile" :class="'t-' + k.tone">
          <div class="kt-head">
            <span class="kt-label">{{ k.label }}</span>
            <span class="kt-trend" :class="k.up ? 'up' : 'down'">
              {{ k.up ? '▲' : '▼' }} {{ k.delta }}
            </span>
          </div>
          <div class="kt-value">
            <span class="num num-lg">{{ k.value }}</span>
            <span class="kt-unit">{{ k.unit }}</span>
          </div>
          <span class="kt-bar"><i :style="{ width: k.fill }" /></span>
        </div>
      </div>
    </section>

    <!-- 近 14 日营收趋势 -->
    <section class="hm-card">
      <div class="hc-head">
        <h4>近 14 日营收趋势</h4>
        <span class="hc-tag safe">日均 {{ money(avgRevenue, '元') }}</span>
      </div>
      <EChart :option="revOption" height="152px" theme="light" />
    </section>

    <!-- 近7日入住率 -->
    <section class="hm-card">
      <div class="hc-head">
        <h4>近 7 日入住率</h4>
        <span class="hc-tag" :class="occLow ? 'danger' : 'safe'">{{ occLow ? '低于阈值' : '正常区间' }}</span>
      </div>
      <EChart :option="occOption" height="148px" theme="light" />
    </section>

    <!-- 评价关键词分布 -->
    <section class="hm-card">
      <div class="hc-head">
        <h4>评价关键词分布</h4>
        <span class="mono-label">近 7 日点评</span>
      </div>
      <EChart :option="kwOption" height="176px" theme="light" />
      <p class="kw-note"><i class="kw-dot neg" />差评关键词<i class="kw-dot pos" />好评关键词</p>
    </section>

    <!-- 经营改善记录 -->
    <section class="hm-card improve">
      <div class="hc-head">
        <h4>贷后经营改善记录</h4>
        <span class="mono-label">AI 赋能成效</span>
      </div>
      <div class="imp-list">
        <div v-for="(im, i) in improves" :key="i" class="imp-item">
          <span class="imp-dot" />
          <div class="imp-body">
            <div class="imp-top"><b>{{ im.title }}</b><span class="num imp-val">{{ im.value }}</span></div>
            <p>{{ im.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 合规说明 -->
    <p class="hm-note">
      经营数据经客户授权后通过 PMS 系统 API 或工行脱敏账户流水接口获取 · 本页为合规沙盒演示数据
    </p>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import EChart from '@/components/EChart.vue'
import { store } from '@/store'
import api from '@/api'
import { money, percent } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })
defineEmits(['go'])

const weather = { temp: 21, desc: '多云转晴' }

/** 该民宿的经营明细（趋势 / 关键词） */
const arch = ref(null)

async function loadArch() {
  if (!props.homestay?.id) return
  try {
    arch.value = await api.archive(props.homestay.id)
  } catch {
    arch.value = null
  }
}
watch(() => props.homestay?.id, loadArch)
onMounted(loadArch)

const riskAlert = computed(() => {
  const hs = props.homestay
  if (!hs) return null
  const w = store.warnings.find((x) => x.homestay_id === hs.id && x.status !== 'closed')
  if (w) return w
  if (hs.risk_level !== 'green') return { reason: hs.risk_reason || '综合经营指标出现波动' }
  return null
})

const occLow = computed(() => {
  const arr = props.homestay?.occupancy_7d || []
  return arr.length > 0 && arr.every((v) => v < 0.3)
})

const kpis = computed(() => {
  const h = props.homestay || {}
  const occ = h.current_occupancy ?? 0
  const bad = h.recent_reviews?.bad_7d ?? 0
  return [
    { label: '今日入住率', value: percent(occ, 0), unit: '', up: occ >= 0.4, delta: '4.2%', tone: occ < 0.3 ? 'danger' : 'blue', fill: `${Math.min(100, occ * 100)}%` },
    { label: '本月营收', value: money(h.monthly_revenue), unit: '', up: (h.monthly_revenue || 0) > 70000, delta: '8.6%', tone: 'gold', fill: '68%' },
    { label: 'OTA 评分', value: (h.ota_score ?? 0).toFixed(1), unit: '分', up: (h.ota_score ?? 0) >= 4.2, delta: (h.ota_score ?? 0) >= 4 ? '0.2' : '0.5', tone: (h.ota_score ?? 0) < 4 ? 'danger' : 'green', fill: `${((h.ota_score ?? 0) / 5) * 100}%` },
    { label: '未处理差评', value: bad, unit: '条', up: bad <= 2, delta: `${bad}`, tone: bad > 3 ? 'danger' : 'blue', fill: `${Math.min(100, bad * 16)}%` }
  ]
})

/** 近 14 日营收 */
const revSeries = computed(() => (arch.value?.trends?.revenue || []).slice(-14))
const avgRevenue = computed(() => {
  const arr = revSeries.value
  return arr.length ? Math.round(arr.reduce((s, v) => s + v, 0) / arr.length) : 0
})

const revOption = computed(() => {
  const dates = (arch.value?.trends?.dates || []).slice(-14).map((d) => String(d).slice(5))
  return {
    grid: { left: 2, right: 10, top: 20, bottom: 2, containLabel: true },
    tooltip: { trigger: 'axis', confine: true, formatter: (p) => `${p[0].name}<br/>营收 ${p[0].value} 元` },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 9, interval: 2 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 9, formatter: (v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : v) }, splitLine: { lineStyle: { color: 'rgba(29,33,41,.06)' } } },
    series: [{
      type: 'bar', data: revSeries.value, barWidth: '54%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: '#FFB800' }, { offset: 1, color: 'rgba(255,184,0,.28)' }]
        }
      },
      markLine: {
        silent: true, symbol: 'none',
        data: [{ type: 'average', name: '均值' }],
        lineStyle: { color: '#165DFF', type: 'dashed', width: 1.2 },
        label: { formatter: '均值', fontSize: 9, color: '#165DFF' }
      }
    }]
  }
})

const occOption = computed(() => {
  const fromTrend = (arch.value?.trends?.occupancy || []).slice(-7)
  const arr = fromTrend.length ? fromTrend : (props.homestay?.occupancy_7d || [0.4, 0.42, 0.38, 0.45, 0.41, 0.44, 0.43])
  const labels = arr.map((_, i) => `D-${arr.length - 1 - i}`)
  return {
    grid: { left: 2, right: 8, top: 18, bottom: 2, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: labels, axisLabel: { fontSize: 9 } },
    yAxis: { type: 'value', max: 60, axisLabel: { formatter: '{value}%', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(29,33,41,.06)' } } },
    series: [
      {
        type: 'line', smooth: true, symbol: 'circle', symbolSize: 6,
        data: arr.map((v) => +(v * 100).toFixed(1)),
        lineStyle: { width: 2.6, color: '#165DFF', shadowColor: 'rgba(22,93,255,.45)', shadowBlur: 10 },
        itemStyle: { color: (p) => (p.value < 30 ? '#F53F3F' : '#165DFF') },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(22,93,255,.28)' }, { offset: 1, color: 'rgba(22,93,255,0)' }]
          }
        },
        markLine: { silent: true, symbol: 'none', data: [{ yAxis: 30 }], lineStyle: { color: 'rgba(245,63,63,.75)', type: 'dashed', width: 1.2 } }
      }
    ]
  }
})

/** 评价关键词分布（差评红 / 好评绿） */
const NEG_WORDS = ['卫生差', '隔音差', '设施差', '服务差', '位置偏', '价格高', '房间小', '有异味', '噪音大']

const kwOption = computed(() => {
  const counts = arch.value?.keyword_counts || props.homestay?.keyword_counts || {}
  const entries = Object.entries(counts).sort((a, b) => a[1] - b[1]).slice(-6)
  return {
    grid: { left: 2, right: 30, top: 6, bottom: 2, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, formatter: '{b}：{c} 次' },
    xAxis: { type: 'value', axisLabel: { show: false }, splitLine: { show: false } },
    yAxis: {
      type: 'category', data: entries.map((e) => e[0]),
      axisLabel: { fontSize: 11, color: '#4e5969' }, axisTick: { show: false }, axisLine: { show: false }
    },
    series: [{
      type: 'bar', barWidth: '54%',
      data: entries.map(([k, v]) => ({
        value: v,
        itemStyle: {
          borderRadius: [0, 5, 5, 0],
          color: NEG_WORDS.includes(k) ? '#F53F3F' : '#00B42A'
        }
      })),
      label: { show: true, position: 'right', fontSize: 10, color: '#86909c', formatter: '{c} 次' },
      showBackground: true,
      backgroundStyle: { color: 'rgba(29,33,41,.04)', borderRadius: [0, 5, 5, 0] }
    }]
  }
})

const improves = [
  { title: '差评回复率提升', value: '+35%', desc: 'AI 生成 3 套差评回复模板，近 7 日差评 100% 当日回复' },
  { title: 'OTA 页面优化', value: '评分 +0.2', desc: '基于 RAG 检索的 OTA 运营指南优化房源标题与首图顺序' },
  { title: '文创引流获客', value: '加微 60+', desc: 'AI 生成洛阳水席主题文创图赠予客人，带动小红书自然曝光' }
]
</script>

<style scoped>
.home { padding-bottom: 18px; }

/* Header */
.hm-header {
  position: relative; padding: 40px 20px 54px;
  background: linear-gradient(135deg, #165dff 0%, #3a72ff 42%, #ffb800 145%);
  border-radius: 0 0 26px 26px; color: #fff; overflow: hidden;
}
.hh-deco {
  position: absolute; inset: 0; opacity: .25;
  background-image: radial-gradient(rgba(255, 255, 255, .55) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(ellipse 65% 70% at 85% 0%, #000, transparent 72%);
}
.hh-top { position: relative; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.hh-city { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: rgba(255, 255, 255, .2); border: 1px solid rgba(255, 255, 255, .28); }
.hh-place h2 { font-size: 19px; font-weight: 700; margin-top: 7px; letter-spacing: .03em; line-height: 1.35; }
.hh-right { display: flex; align-items: center; gap: 12px; }
.hh-weather { text-align: right; }
.hw-temp { display: block; font-size: 20px; }
.hw-desc { font-size: 10.5px; opacity: .88; }
.hh-avatar {
  width: 40px; height: 40px; border-radius: 13px; display: grid; place-items: center;
  font-size: 16px; font-weight: 700; background: rgba(255, 255, 255, .22);
  border: 1px solid rgba(255, 255, 255, .35); backdrop-filter: blur(6px);
}

.risk-bar {
  position: relative; display: flex; align-items: center; gap: 10px; width: 100%;
  margin-top: 18px; padding: 11px 13px; border-radius: 13px; text-align: left;
  background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .3);
  backdrop-filter: blur(10px); color: #fff; transition: transform .25s var(--ease-out), background .25s;
}
.risk-bar:not(.ok):hover { transform: translateY(-2px); background: rgba(255, 255, 255, .24); }
.risk-bar.ok { background: rgba(255, 255, 255, .12); }
.rb-ico { font-size: 15px; }
.rb-text { flex: 1; font-size: 11.5px; line-height: 1.55; opacity: .95; }
.rb-text b { display: block; font-size: 12.5px; margin-bottom: 1px; }
.rb-go { font-size: 11px; font-weight: 700; white-space: nowrap; opacity: .95; }

/* KPI */
.hm-kpi { margin: -38px 14px 0; position: relative; z-index: 3; }
.kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.kpi-tile {
  position: relative; padding: 13px 14px 12px; border-radius: 16px; background: #fff;
  box-shadow: 0 14px 30px -22px rgba(10, 25, 47, .5); border: 1px solid rgba(29, 33, 41, .05);
  overflow: hidden;
}
.kt-head { display: flex; align-items: center; justify-content: space-between; }
.kt-label { font-size: 11.5px; color: #86909c; }
.kt-trend { font-size: 10.5px; font-family: var(--font-num); }
.kt-trend.up { color: #00b42a; }
.kt-trend.down { color: #f53f3f; }
.kt-value { display: flex; align-items: baseline; gap: 5px; margin-top: 7px; }
.kt-value .num { font-size: 27px; color: #1d2129; }
.kt-unit { font-size: 11px; color: #86909c; }
.kt-bar { display: block; height: 4px; margin-top: 10px; border-radius: 3px; background: #f2f3f5; overflow: hidden; }
.kt-bar i { display: block; height: 100%; border-radius: 3px; transition: width .8s var(--ease-out); }
.t-blue .kt-bar i { background: linear-gradient(90deg, #6f9bff, #165dff); }
.t-gold .kt-bar i { background: linear-gradient(90deg, #ffcd4d, #ffb800); }
.t-green .kt-bar i { background: linear-gradient(90deg, #5fd47a, #00b42a); }
.t-danger .kt-bar i { background: linear-gradient(90deg, #ff8080, #f53f3f); }
.t-danger .kt-value .num { color: #f53f3f; }
.t-gold .kt-value .num { color: #c98a00; }

/* 快捷入口 */
.hm-quick { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 16px 14px 0; }
.quick {
  display: flex; flex-direction: column; gap: 3px; align-items: flex-start; text-align: left;
  padding: 13px 14px; border-radius: 15px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
  transition: transform .26s var(--ease-out), box-shadow .26s;
}
.quick:hover { transform: translateY(-3px); box-shadow: 0 18px 34px -22px rgba(10, 25, 47, .55); }
.q-ico { width: 34px; height: 34px; border-radius: 11px; display: grid; place-items: center; margin-bottom: 5px; }
.q-blue { color: #165dff; background: rgba(22, 93, 255, .1); }
.q-gold { color: #c98a00; background: rgba(255, 184, 0, .16); }
.q-red { color: #f53f3f; background: rgba(245, 63, 63, .1); }
.q-green { color: #00b42a; background: rgba(0, 180, 42, .1); }
.q-label { font-size: 13.5px; font-weight: 700; color: #1d2129; }
.q-desc { font-size: 11px; color: #86909c; }

/* 卡片 */
.hm-card {
  margin: 16px 14px 0; padding: 15px 15px 12px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.hc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.hc-head h4 { font-size: 14px; color: #1d2129; font-weight: 700; }
.hc-tag { font-size: 10.5px; padding: 2px 9px; border-radius: 999px; }
.hc-tag.safe { color: #00b42a; background: rgba(0, 180, 42, .1); }
.hc-tag.danger { color: #f53f3f; background: rgba(245, 63, 63, .1); }

.kw-note {
  display: flex; align-items: center; justify-content: flex-end; gap: 6px;
  margin-top: 8px; font-size: 10.5px; color: #86909c;
}
.kw-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
.kw-dot.neg { background: #f53f3f; }
.kw-dot.pos { background: #00b42a; margin-left: 8px; }

.improve { padding-bottom: 8px; }
.imp-list { display: flex; flex-direction: column; }
.imp-item { display: flex; gap: 11px; padding: 11px 0; border-bottom: 1px solid rgba(29, 33, 41, .06); }
.imp-item:last-child { border-bottom: 0; }
.imp-dot { width: 7px; height: 7px; margin-top: 6px; border-radius: 50%; flex: 0 0 7px; background: linear-gradient(135deg, #165dff, #ffb800); }
.imp-body { flex: 1; }
.imp-top { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.imp-top b { font-size: 13px; color: #1d2129; }
.imp-val { font-size: 13.5px; color: #165dff; }
.imp-body p { font-size: 11.5px; color: #86909c; line-height: 1.7; margin-top: 4px; }

.hm-note { margin: 16px 16px 0; font-size: 10.5px; color: #a9b0bd; line-height: 1.75; text-align: center; }

.pop-enter-active { transition: all .3s var(--ease-out); }
.pop-enter-from { opacity: 0; transform: translateY(-6px); }
</style>
