<template>
  <div class="dash">
    <!-- ========== KPI 指标卡 ========== -->
    <section class="kpis stagger">
      <StatCard label="在管民宿" :value="kpi.total_homestays ?? 0" unit="户"
        :hint="`覆盖 洛阳 / 开封 / 安阳`" accent="blue"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M3 10l9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10z'/><path d='M9 21v-6h6v6'/></svg>" />
      <StatCard label="高风险预警" :value="kpi.red ?? 0" unit="户"
        :hint="`需 3 个工作日内上门核查`" accent="red"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M12 3 2 20h20L12 3z'/><path d='M12 9v5M12 17.5v.4'/></svg>" />
      <StatCard label="中风险关注" :value="kpi.amber ?? 0" unit="户"
        :hint="`持续跟踪经营指标`" accent="amber"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><circle cx='12' cy='12' r='9'/><path d='M12 8v4l3 2'/></svg>" />
      <StatCard label="贷后余额" :value="loanWan" unit="万元"
        :hint="`合同总额 ${money(kpi.total_loan_amount)}`" accent="gold"
        :spark="citySpark"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><rect x='3' y='5' width='18' height='14' rx='2'/><path d='M3 10h18'/></svg>" />
      <StatCard label="平均入住率" :value="percent(kpi.avg_occupancy, 1)" unit=""
        hint="行业均值约 36%" accent="green"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M3 13h4l2 7 4-16 2 9h6'/></svg>" />
      <StatCard label="平均 OTA 评分" :value="(kpi.avg_ota ?? 0).toFixed(2)" unit="分"
        hint="低于 4.0 触发红色预警" accent="blue"
        icon="<svg viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='1.8'><path d='m12 4 2.5 5.2 5.5.8-4 3.9.9 5.5L12 16.8 7.1 19.4l.9-5.5-4-3.9 5.5-.8L12 4z'/></svg>" />
    </section>

    <!-- ========== 沙盘 + 右侧面板 ========== -->
    <section class="mid">
      <div class="mid-left">
        <RiskMap class="map" :points="mapPoints" :by-city="byCity" @open="openArchive" />

        <!-- 全辖经营趋势（填补沙盘下方留白） -->
        <div class="panel glass trend-panel">
          <div class="p-head">
            <h4>全辖 30 天经营趋势</h4>
            <span class="mono-label">各店均值 · OCCUPANCY / REVENUE</span>
          </div>
          <EChart :option="trendOption" height="210px" />
        </div>
      </div>

      <div class="side-col">
        <!-- 风险分布 -->
        <div class="panel glass">
          <div class="p-head">
            <h4>风险等级分布</h4>
            <span class="mono-label">RISK LEVEL</span>
          </div>
          <EChart :option="donutOption" height="180px" />
          <div class="risk-legend">
            <div v-for="r in riskRows" :key="r.key">
              <span class="dot" :class="'risk-' + r.key" />
              <span class="rl-name">{{ r.name }}</span>
              <span class="rl-val num">{{ r.value }}</span>
              <span class="rl-pct">{{ r.pct }}</span>
            </div>
          </div>
        </div>

        <!-- 实时预警流 -->
        <div class="panel glass feed-panel">
          <div class="p-head">
            <h4>实时预警动态</h4>
            <span class="live"><i /> LIVE</span>
          </div>
          <div class="feed no-scrollbar">
            <div v-if="!feed.length" class="feed-empty">暂无预警，点击左侧「一键触发风险扫描」</div>
            <button v-for="(w, i) in feed" :key="w.id || i" class="feed-item" :class="'risk-' + w.level" @click="openArchive(w.homestay_id)">
              <span class="fi-bar" />
              <div class="fi-body">
                <div class="fi-top">
                  <b>{{ w.homestay_name || w.homestay_id }}</b>
                  <span class="fi-time">{{ shortTime(w.created_at) }}</span>
                </div>
                <p class="fi-reason">{{ w.reason }}</p>
                <div class="fi-tags">
                  <span class="level-tag" :class="'risk-' + w.level">{{ riskText[w.level] }}</span>
                  <span class="fi-rule">{{ w.rule_id }} · {{ w.rule_name }}</span>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ========== 组合健康 · 城市矩阵 · 高风险敞口 ========== -->
    <section class="insight">
      <div class="panel glass health-panel">
        <div class="p-head">
          <h4>组合健康度</h4>
          <span class="mono-label">PORTFOLIO HEALTH</span>
        </div>
        <EChart :option="gaugeOption" height="172px" />
        <div class="health-stats">
          <div><label>额度使用率</label><b class="num">{{ percent(en.loan_utilization, 1) }}</b></div>
          <div><label>应收回款</label><b class="num">{{ money(en.monthly_repayment_total) }}</b></div>
          <div><label>OTA 评分</label><b class="num">{{ (en.avg_ota ?? kpi.avg_ota ?? 0).toFixed(2) }}</b></div>
        </div>
      </div>

      <div class="panel glass city-panel">
        <div class="p-head">
          <h4>城市风险矩阵</h4>
          <span class="mono-label">CITY RISK MATRIX</span>
        </div>
        <EChart :option="cityOption" height="248px" />
      </div>

      <div class="panel glass top-panel">
        <div class="p-head">
          <h4>高风险敞口 TOP</h4>
          <span class="mono-label">按剩余本金</span>
        </div>
        <div class="toprisk no-scrollbar">
          <button v-for="(t, i) in en.top_risk || []" :key="t.id" class="tr-item" @click="openArchive(t.id)">
            <span class="tr-rank num">{{ String(i + 1).padStart(2, '0') }}</span>
            <div class="tr-body">
              <div class="tr-top">
                <b>{{ t.name }}</b>
                <span class="tr-city">{{ t.city }}</span>
              </div>
              <div class="tr-metrics">
                <span>OTA <em class="num">{{ (t.ota_score ?? 0).toFixed(1) }}</em></span>
                <span>入住 <em class="num">{{ percent(t.occupancy, 0) }}</em></span>
              </div>
            </div>
            <span class="tr-bal num">{{ money(t.loan_balance) }}</span>
          </button>
          <p v-if="!(en.top_risk || []).length" class="todo-empty">当前无高风险敞口</p>
        </div>
      </div>
    </section>

    <!-- ========== 今日待办 ========== -->
    <section class="panel glass todo-panel">
      <div class="p-head">
        <h4>今日建议上门核查清单</h4>
        <span class="mono-label">按风险等级排序 · {{ todos.length }} 户</span>
      </div>
      <div class="todo-grid">
        <button v-for="(t, i) in todos" :key="t.id" class="todo-card" :class="'risk-' + t.risk_level" @click="openArchive(t.id)">
          <div class="td-left">
            <span class="td-rank num">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="td-line" />
          </div>
          <div class="td-body">
            <div class="td-top">
              <b>{{ t.name }}</b>
              <span class="level-tag" :class="'risk-' + t.risk_level">{{ riskText[t.risk_level] }}</span>
            </div>
            <p class="td-reason">{{ t.risk_reason || '综合指标异常' }}</p>
            <div class="td-metrics">
              <span>入住率 <em class="num">{{ percent(t.current_occupancy ?? t.occupancy) }}</em></span>
              <span>OTA <em class="num">{{ (t.ota_score ?? 0).toFixed(1) }}</em></span>
              <span>贷后余额 <em class="num">{{ money(t.loan_balance) }}</em></span>
            </div>
          </div>
          <svg class="td-arrow" viewBox="0 0 24 24" width="16" height="16"><path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <div v-if="!todos.length" class="todo-empty">策略良好，今日无需强制上门核查</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import StatCard from '@/components/bank/StatCard.vue'
import RiskMap from '@/components/bank/RiskMap.vue'
import EChart from '@/components/EChart.vue'
import { store, homestayById } from '@/store'
import { money, percent, shortTime, RISK_TEXT } from '@/utils/format'

const router = useRouter()
const riskText = RISK_TEXT

const dash = computed(() => store.dashboard || {})
const kpi = computed(() => dash.value.kpi || {})
const en = computed(() => dash.value.enhanced || {})
const byCity = computed(() => dash.value.by_city || [])
const mapPoints = computed(() => dash.value.map_points || [])
const todos = computed(() => (dash.value.todos || []).slice(0, 6))

const loanWan = computed(() => {
  const v = kpi.value.total_loan_balance
  return v ? (v / 10000).toFixed(0) : '0'
})
const citySpark = computed(() => byCity.value.map((c) => c.loan_balance || 0))

const feed = computed(() =>
  [...store.warnings]
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    .slice(0, 3)
)

const riskRows = computed(() => {
  const dist = dash.value.risk_distribution || []
  const total = dist.reduce((s, d) => s + (d.value || 0), 0) || 1
  const map = { 高风险: 'red', 中风险: 'amber', 低风险: 'green' }
  return dist.map((d) => ({
    key: map[d.name] || 'green',
    name: d.name,
    value: d.value,
    pct: `${((d.value / total) * 100).toFixed(0)}%`
  }))
})

const donutOption = computed(() => {
  const rows = riskRows.value
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 户 ({d}%)' },
    series: [
      {
        type: 'pie',
        radius: ['62%', '86%'],
        center: ['50%', '52%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: 'rgba(6,16,32,0)', borderWidth: 3, borderRadius: 4 },
        label: {
          show: true,
          position: 'center',
          formatter: () => `{a|${rows.reduce((s, r) => s + r.value, 0)}}\n{b|在管民宿}`,
          rich: {
            a: { fontFamily: 'Bahnschrift, monospace', fontSize: 30, color: '#EAF2FF', fontWeight: 700, lineHeight: 34 },
            b: { fontSize: 11, color: '#6D82A6', letterSpacing: 2 }
          }
        },
        emphasis: { scale: true, scaleSize: 6 },
        data: rows.map((r) => ({
          name: r.name,
          value: r.value,
          itemStyle: { color: { red: '#F53F3F', amber: '#FF7D00', green: '#00B42A' }[r.key] }
        }))
      }
    ]
  }
})

/** 全辖 30 天经营趋势（入住率线 + 日均营收柱） */
const trendOption = computed(() => {
  const t = en.value.trend || {}
  const dates = (t.dates || []).map((d) => String(d).slice(5))
  const occ = (t.occupancy || []).map((v) => +(v * 100).toFixed(1))
  const rev = t.revenue || []
  return {
    legend: { top: 0, left: 'center', right: 0, textStyle: { color: '#A9BCD9', fontSize: 10 }, icon: 'roundRect', itemWidth: 9, itemHeight: 9 },
    tooltip: { trigger: 'axis', confine: true },
    grid: { left: 4, right: 6, top: 36, bottom: 2, containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false, data: dates,
      axisLabel: { hideOverlap: true, interval: 'auto', fontSize: 10 }
    },
    yAxis: [
      {
        type: 'value', name: '入住%', nameTextStyle: { color: '#6D82A6', fontSize: 10 },
        axisLabel: { formatter: '{value}%', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(96,150,255,.08)' } }
      },
      {
        type: 'value', name: '营收', nameTextStyle: { color: '#6D82A6', fontSize: 10 },
        axisLabel: { fontSize: 10 }, splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '日均营收', type: 'bar', yAxisIndex: 1, data: rev, barWidth: '42%',
        itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(22,93,255,.8)' }, { offset: 1, color: 'rgba(22,93,255,.1)' }]
          }
        }
      },
      {
        name: '平均入住率', type: 'line', smooth: true, data: occ, symbol: 'none',
        lineStyle: { width: 2.4, color: '#FFB800', shadowColor: 'rgba(255,184,0,.5)', shadowBlur: 10 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(255,184,0,.22)' }, { offset: 1, color: 'rgba(255,184,0,0)' }]
          }
        }
      }
    ]
  }
})

/** 组合健康度仪表盘 */
const gaugeOption = computed(() => {
  const v = en.value.portfolio_health ?? 0
  const color = v >= 75 ? '#00B42A' : v >= 50 ? '#FF7D00' : '#F53F3F'
  return {
    series: [{
      type: 'gauge',
      startAngle: 210, endAngle: -30, min: 0, max: 100,
      radius: '68%', center: ['50%', '56%'],
      progress: { show: true, width: 12, roundCap: true, itemStyle: { color } },
      axisLine: { lineStyle: { width: 12, color: [[1, 'rgba(255,255,255,.08)']] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false }, anchor: { show: false },
      detail: {
        valueAnimation: true, offsetCenter: [0, '-6%'], formatter: '{value}',
        color: '#EAF2FF', fontSize: 30, fontFamily: 'Bahnschrift, monospace', fontWeight: 700
      },
      title: { offsetCenter: [0, '80%'], color: '#6D82A6', fontSize: 10.5 },
      data: [{ value: v, name: '组合健康度' }]
    }]
  }
})

/** 城市风险矩阵（风险指数） */
const cityOption = computed(() => {
  const rows = en.value.city_metrics || []
  return {
    tooltip: {
      trigger: 'axis', confine: true, axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const c = rows[p[0].dataIndex] || {}
        return `${c.city}<br/>风险指数 <b>${c.risk_index}</b><br/>在管 ${c.count} 户<br/>平均 OTA ${c.avg_ota}<br/>平均入住率 ${((c.avg_occupancy || 0) * 100).toFixed(0)}%<br/>贷后余额 ${money(c.loan_balance)}`
      }
    },
    grid: { left: 4, right: 12, top: 22, bottom: 2, containLabel: true },
    xAxis: { type: 'category', data: rows.map((c) => c.city), axisLabel: { color: '#A9BCD9', fontSize: 11 } },
    yAxis: {
      type: 'value', name: '风险指数', nameTextStyle: { color: '#6D82A6', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(96,150,255,.08)' } }, axisLabel: { fontSize: 10 }
    },
    series: [{
      type: 'bar', barWidth: '44%',
      data: rows.map((c) => ({
        value: c.risk_index,
        itemStyle: {
          borderRadius: [5, 5, 0, 0],
          color: c.risk_index >= 60 ? '#F53F3F' : c.risk_index >= 35 ? '#FF7D00' : '#00B42A'
        }
      })),
      label: {
        show: true, position: 'top', color: '#EAF2FF', fontSize: 11,
        fontFamily: 'Bahnschrift, monospace'
      }
    }]
  }
})

function openArchive(id) {
  if (!id) return
  store.currentHomestayId = id
  router.push({ name: 'bank-archive', query: { id } })
}
</script>

<style scoped>
.dash { display: flex; flex-direction: column; gap: 14px; }

/* KPI */
.kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; }

/* 中部：左右等高，消除沙盘与右栏下方留白 */
.mid { display: grid; grid-template-columns: minmax(0, 1.62fr) minmax(320px, 1fr); gap: 14px; align-items: stretch; }
.mid-left { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.side-col { display: flex; flex-direction: column; gap: 14px; }
.side-col .feed-panel { flex: 1; min-height: 0; display: flex; flex-direction: column; }

/* 组合健康 · 城市矩阵 · 高风险敞口 */
.insight { display: grid; grid-template-columns: 1fr 1.1fr 1fr; gap: 14px; align-items: stretch; }
.insight .panel { display: flex; flex-direction: column; min-height: 0; }
.insight .panel :deep(.echart) { flex: 1; min-height: 0; }
/* 组合健康度表盘：允许伸展但设最小高度，防止矮容器压缩表盘导致数值与标签重叠 */
.insight .health-panel :deep(.echart) { flex: 1 1 auto; min-height: 156px; }
/* 组合健康度底部指标条：三列等分，贴底放置避免面板内留白 */
.health-stats {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
  margin-top: 8px; padding-top: 11px; border-top: 1px solid var(--line);
}
.health-stats > div { display: flex; flex-direction: column; align-items: center; gap: 3px; min-width: 0; }
.health-stats label { font-size: 10.5px; color: var(--text-3); white-space: nowrap; }
.health-stats b { font-size: 17px; color: #fff; font-weight: 700; }
.toprisk { display: flex; flex-direction: column; gap: 8px; max-height: 268px; overflow-y: auto; padding-right: 3px; }
.tr-item {
  display: flex; align-items: center; gap: 11px; text-align: left; width: 100%;
  padding: 10px 12px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(245, 63, 63, .07), rgba(255, 255, 255, .02));
  border: 1px solid rgba(245, 63, 63, .2);
  transition: transform .25s var(--ease-out), border-color .25s, background .25s;
}
.tr-item:hover { transform: translateX(3px); border-color: rgba(245, 63, 63, .42); background: rgba(245, 63, 63, .12); }
.tr-rank { font-size: 13px; color: var(--risk-red); flex: 0 0 auto; }
.tr-body { flex: 1; min-width: 0; }
.tr-top { display: flex; align-items: baseline; gap: 8px; }
.tr-top b { font-size: 13px; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tr-city { font-size: 10.5px; color: var(--text-3); }
.tr-metrics { display: flex; gap: 12px; margin-top: 4px; font-size: 11px; color: var(--text-3); }
.tr-metrics em { font-style: normal; color: var(--text-2); font-size: 12px; margin-left: 2px; }
.tr-bal { font-size: 13px; color: var(--brand-gold); flex: 0 0 auto; }

.panel { padding: 16px 18px 18px; border-radius: var(--r-md); }
.p-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.p-head h4 { font-size: 14.5px; color: var(--text-1); font-weight: 700; letter-spacing: .04em; }
.live { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-num); font-size: 10.5px; letter-spacing: .18em; color: var(--risk-green); }
.live i { width: 6px; height: 6px; border-radius: 50%; background: var(--risk-green); animation: soft-pulse 1.4s infinite; }

/* 风险图例 */
.risk-legend { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
.risk-legend > div { display: flex; align-items: center; gap: 9px; font-size: 12.5px; }
.rl-name { color: var(--text-2); flex: 1; }
.rl-val { color: var(--text-1); font-size: 15px; }
.rl-pct { color: var(--text-3); font-size: 11.5px; width: 38px; text-align: right; }

/* 预警流 */
.feed-panel { display: flex; flex-direction: column; }
.feed { display: flex; flex-direction: column; gap: 9px; flex: 1; min-height: 0; overflow-y: auto; padding-right: 3px; }
.feed-empty { padding: 26px 8px; text-align: center; color: var(--text-3); font-size: 12.5px; }
.feed-item {
  display: flex; gap: 10px; text-align: left; width: 100%;
  padding: 11px 12px; border-radius: 10px;
  background: rgba(255, 255, 255, .025); border: 1px solid var(--line);
  transition: background .25s, border-color .25s, transform .25s;
}
.feed-item:hover { background: rgba(22, 93, 255, .1); border-color: var(--line-strong); transform: translateX(3px); }
.fi-bar { width: 3px; border-radius: 3px; flex: 0 0 3px; background: var(--risk, var(--text-3)); box-shadow: 0 0 10px var(--risk-glow); }
.fi-body { flex: 1; min-width: 0; }
.fi-top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.fi-top b { font-size: 13px; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-time { font-family: var(--font-num); font-size: 10.5px; color: var(--text-3); flex: 0 0 auto; }
.fi-reason { font-size: 12px; color: var(--text-2); margin-top: 4px; line-height: 1.55; }
.fi-tags { display: flex; align-items: center; gap: 8px; margin-top: 7px; }
.fi-tags .level-tag { height: 20px; font-size: 11px; }
.fi-rule { font-size: 10.5px; color: var(--text-3); font-family: var(--font-num); letter-spacing: .06em; }

/* 今日待办 */
.todo-panel { padding-bottom: 18px; }
.todo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 13px; }
.todo-card {
  display: flex; align-items: center; gap: 12px; text-align: left;
  padding: 13px 14px; border-radius: 12px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--risk) 9%, transparent), rgba(255, 255, 255, .02));
  border: 1px solid color-mix(in srgb, var(--risk) 26%, transparent);
  transition: transform .28s var(--ease-out), box-shadow .28s, border-color .28s;
}
.todo-card:hover { transform: translateY(-3px); box-shadow: 0 18px 36px -20px var(--risk-glow); }
.td-left { display: flex; flex-direction: column; align-items: center; gap: 4px; align-self: stretch; }
.td-rank { font-size: 15px; color: var(--risk); }
.td-line { flex: 1; width: 2px; border-radius: 2px; background: color-mix(in srgb, var(--risk) 40%, transparent); }
.td-body { flex: 1; min-width: 0; }
.td-top { display: flex; align-items: center; gap: 8px; }
.td-top b { flex: 1; font-size: 13.5px; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-top .level-tag { height: 20px; font-size: 11px; }
.td-reason { font-size: 12px; color: var(--text-2); margin-top: 5px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.td-metrics { display: flex; gap: 14px; margin-top: 8px; font-size: 11.5px; color: var(--text-3); flex-wrap: wrap; }
.td-metrics em { font-style: normal; color: var(--text-1); font-size: 13px; margin-left: 3px; }
.td-arrow { color: var(--text-3); flex: 0 0 auto; transition: transform .25s, color .25s; }
.todo-card:hover .td-arrow { transform: translateX(3px); color: var(--risk); }
.todo-empty { grid-column: 1 / -1; padding: 24px; text-align: center; color: var(--text-3); font-size: 13px; }

@media (max-width: 1440px) { .kpis { grid-template-columns: repeat(3, 1fr); } .insight { grid-template-columns: 1fr 1fr; } }
@media (max-width: 1240px) {
  .mid { grid-template-columns: 1fr; }
  .insight { grid-template-columns: 1fr; }
  .todo-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 760px) {
  .kpis { grid-template-columns: repeat(2, 1fr); }
  .todo-grid { grid-template-columns: 1fr; }
}
</style>
