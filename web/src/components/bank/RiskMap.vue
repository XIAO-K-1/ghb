<template>
  <div class="risk-map corner-notch">
    <!-- 顶部标题栏 -->
    <div class="rm-head">
      <div class="rm-title">
        <span class="rm-dot" /> 风险态势沙盘 · 河南省 3D
        <em>HENAN 3D RISK MAP</em>
      </div>
      <div class="rm-legend">
        <span><i class="lg lg-red" /> 高风险</span>
        <span><i class="lg lg-amber" /> 中风险</span>
        <span><i class="lg lg-green" /> 低风险</span>
      </div>
    </div>

    <!-- 3D 地图主体（右键拖拽平移，此处屏蔽系统右键菜单） -->
    <div class="rm-body" @contextmenu.prevent>
      <div ref="el" class="rm-canvas" />
      <div v-if="loading" class="rm-loading"><i /> 正在加载河南省三维地形…</div>
      <div v-if="err" class="rm-loading err">{{ err }}</div>
      <div class="rm-readout">
        <span>GRID 34.6°N / 112.4°E</span>
        <span class="ok">● 实时同步</span>
      </div>
    </div>

    <!-- 城市统计条 -->
    <div class="rm-cities">
      <div v-for="c in cityStats" :key="c.city" class="city-bar">
        <div class="cb-top">
          <span class="cb-name">{{ c.city }}</span>
          <span class="cb-count num">{{ c.count }} 户</span>
        </div>
        <div class="cb-track">
          <i class="cb-red" :style="{ width: barW(c.red, c.count) }" />
          <i class="cb-amber" :style="{ width: barW(c.amber, c.count) }" />
          <i class="cb-green" :style="{ width: barW(c.green, c.count) }" />
        </div>
        <div class="cb-foot"><span class="num">{{ money(c.loan_balance) }}</span><span class="muted">贷后余额</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { money, RISK_TEXT } from '@/utils/format'

const props = defineProps({
  points: { type: Array, default: () => [] },
  byCity: { type: Array, default: () => [] }
})
const emit = defineEmits(['open'])

const riskText = RISK_TEXT
const el = ref(null)
const loading = ref(true)
const err = ref('')
let chart = null
let ro = null

/* 河南主要城市真实经纬度（用于 3D 地图标注，与 mock 数据一致） */
const CITY_COORDS = [
  { name: '洛阳', en: 'LUOYANG', lat: 34.6197, lng: 112.454 },
  { name: '开封', en: 'KAIFENG', lat: 34.797, lng: 114.3074 },
  { name: '安阳', en: 'ANYANG', lat: 36.0977, lng: 114.393 }
]
const EN_MAP = Object.fromEntries(CITY_COORDS.map((c) => [c.name, c.en]))

/* 风险 → 柱高 / 颜色 */
const HEIGHT = { red: 26, amber: 18, green: 10 }
const COLOR = { red: '#F53F3F', amber: '#FF7D00', green: '#00B42A' }

async function ensureGeo() {
  const res = await fetch('/geo/henan.json')
  if (!res.ok) throw new Error('河南地理数据加载失败')
  const geo = await res.json()
  echarts.registerMap('henan', geo)
  return geo
}

/* ==================== 风险光环（静态三层同心圆，高风险更大更亮） ====================
   为什么不做逐帧动画：脉冲需要用 chart.setOption 周期性重绘，
   而 echarts-gl 每次 setOption 都会重新执行 Geo3DView.render()，
   把 viewControl 的 alpha/beta/distance/center 复位 —— 表现为
   ① 旋转/缩放/平移一操作就被弹回；② hover 的区域高亮与地区名一闪就消失。
   因此这里改为「静态三层同心圆」：由内到外逐层放大、逐层变淡，
   配合 postEffect.bloom 呈现柔和光辉，视觉上等同扩散涟漪的定格，且零重绘开销。 */
const HALO = {
  red: { core: 4.2, mid: 9, outer: 15.5, op: 0.9 },   // 高风险：最大 / 最亮
  amber: { core: 3.4, mid: 7.2, outer: 12, op: 0.66 }, // 中风险
  green: { core: 2.8, mid: 5.6, outer: 9.2, op: 0.46 } // 低风险：最小 / 最暗
}
let haloPoints = { red: [], amber: [], green: [] }

/** 新增：把风险点按等级拆分为光环数据（原有 bar3D 数据映射逻辑保持不变） */
function buildHaloPoints(pts) {
  const bag = { red: [], amber: [], green: [] }
  pts.forEach((p, i) => {
    const lv = bag[p.risk_level] ? p.risk_level : 'green'
    bag[lv].push({ value: [p.lng, p.lat, 3.4, i], name: p.name })
  })
  return bag
}

/** 新增：某风险等级的三层光环系列（外/中/内，透明度递增） */
function haloSeries(lv, points) {
  const c = HALO[lv]
  const layer = (id, size, opacity) => ({
    id,
    name: '风险光环',
    type: 'scatter3D',
    coordinateSystem: 'geo3D',
    symbol: 'circle',
    symbolSize: size,
    itemStyle: { color: COLOR[lv], opacity },
    label: { show: false },
    silent: true,
    data: points
  })
  return [
    layer(`halo-${lv}-outer`, c.outer, c.op * 0.12),
    layer(`halo-${lv}-mid`, c.mid, c.op * 0.30),
    layer(`halo-${lv}-core`, c.core, c.op)
  ]
}

function buildOption() {
  const pts = props.points || []
  haloPoints = buildHaloPoints(pts)
  return {
    // ========== 1. 背景提亮（本次新增）：GL 层清屏底色（蓝天科技色，替代纯黑）
    // 注意：真正可见的背景由下方 geo3D.environment 的径向渐变天空盒提供，此项作为兜底清屏色
    backgroundColor: '#0B2550',
    // ========== 5. 交互细节（本次新增）：深色半透明弹窗，字体与全局大屏统一 ==========
    tooltip: {
      show: true,
      confine: true,
      backgroundColor: 'rgba(6,16,32,.86)',           // 新增：更深色半透明底，贴合暗色大屏
      borderColor: 'rgba(65,166,255,.36)',            // 新增：浅蓝细边，与地图边框色呼应
      borderWidth: 1,
      padding: [9, 12],                               // 新增：内边距，避免文字贴边
      textStyle: { color: '#A9BCD9', fontSize: 10 },  // 规范：文字色 #A9BCD9 / 字号 10px
      extraCssText: 'backdrop-filter:blur(6px);box-shadow:0 14px 36px -14px rgba(0,0,0,.95);border-radius:10px;',
      formatter: (p) => {
        if (!p || p.seriesName !== '风险点') return ''
        const d = pts[p.data && p.data.value ? p.data.value[3] : -1]
        if (!d) return ''
        const risk = riskText[d.risk_level] || ''
        const util = d.loan_balance && d.loan_amount ? (d.loan_balance / d.loan_amount * 100).toFixed(0) + '%' : '—'
        return `<b style="font-size:13px">${d.name}</b> <span style="color:${COLOR[d.risk_level] || '#00B42A'}">${risk}</span><br/>
          地市：${d.city || ''}<br/>
          贷后余额：${money(d.loan_balance)}<br/>
          当前入住率：${(d.occupancy ?? 0) * 100}％<br/>
          OTA 评分：${(d.ota_score ?? 0).toFixed(1)}<br/>
          额度使用率：${util}<br/>`
      }
    },
    // ========== 2. geo3D 底图：浮雕 + 光照 + 辉光 + 视角锁定（本次新增优化） ==========
    geo3D: {
      map: 'henan',                                   // 原有保留：地图注册名不变
      roam: true,                                     // 原有保留：拖拽旋转 / 滚轮缩放
      center: [113.4, 34.0, 0],                       // 原有保留
      boxHeight: 12,                                  // 新增：加厚底体，强化 3D 体积层次
      regionHeight: 3.2,                              // 新增：抬高行政区浮雕，强化立体凹凸感
      shading: 'lambert',                             // 原有保留
      // 修复：原 'transparent' 会被 echarts-gl 当作可解析颜色而生成「不透明黑」天空盒，导致背景死黑；
      // 改为径向渐变天空盒，呈现规范要求的 #0B2550 → #020617 深蓝层次，替代死黑底色。
      environment: new echarts.graphic.RadialGradient(0.5, 0.38, 0.9, [
        { offset: 0, color: '#0B2550' },
        { offset: 0.5, color: '#071A33' },
        { offset: 1, color: '#020617' }
      ]),
      viewControl: {
        // ===== 交互改造（本次新增）：左键拖拽旋转 / 右键拖拽平移 / 滚轮自由缩放 =====
        distance: 150,                                // 初始视角距离：保证河南全省完整居中
        alpha: 50,                                    // 初始俯仰角
        beta: 0,                                      // 初始水平角
        autoRotate: false,                            // 原有保留 + 规范：关闭自动旋转
        minAlpha: 1,                                  // 放开俯仰下限：可自由压平观察
        maxAlpha: 89,                                 // 放开俯仰上限：可自由俯视
        minBeta: -180,                                // 放开水平范围：可 360° 环绕
        maxBeta: 180,
        minDistance: 30,                              // 放开缩放：可大幅拉近看细节（原来最小 95，几乎不能放大）
        maxDistance: 600,                             // 放开缩放：可拉远纵览全省
        rotateSensitivity: 1,                          // 恢复默认旋转灵敏度，拖拽更跟手
        zoomSensitivity: 1,                            // 保持滚轮缩放灵敏度
        panSensitivity: 1,                             // 放开平移（原来为 0，导致完全无法移动）
        rotateMouseButton: 'left',                     // 左键拖拽 = 旋转
        panMouseButton: 'right',                       // 右键拖拽 = 平移，配合外层 @contextmenu.prevent
        animationDurationUpdate: 300                   // 视角过渡更短，操作更跟手
      },
      light: {
        main: { intensity: 1.8, shadow: true, shadowQuality: 'medium', alpha: 45, beta: 18 }, // 新增：主光增强 + 开启阴影
        ambient: { intensity: 0.62 }                  // 新增：环境光补光（若仍偏暗可上调至 0.75）
      },
      postEffect: {                                   // 新增：三维后处理，营造高级大屏辉光氛围
        enable: true,
        bloom: { enable: true, intensity: 0.12 },     // 辉光：调低强度，保留质感同时避免整体发虚
        FXAA: { enable: true },                       // 抗锯齿：弱化生硬边缘
        colorCorrection: { enable: true, exposure: 0.08, brightness: 0.06, contrast: 1.1, saturation: 1.18 } // 调色：整体提亮 + 增强层次
      },
      // 新增：关闭时域超采样（默认 'auto' 会随 postEffect 开启并逐帧累积），
      // 避免脉冲呼吸动画出现拖影/鬼影，同时降低持续重绘的 GPU 开销。
      temporalSuperSampling: { enable: false },
      itemStyle: {
        color: '#14457A',                             // 行政区底色：深蓝科技色
        opacity: 1,
        borderColor: 'rgba(107,196,255,.95)',          // 清晰度优化：边框提亮，省界/市界更锐利
        borderWidth: 1.6                              // 清晰度优化：由 0.8 加粗到 1.6，解决边界发虚发糊
      },
      emphasis: {
        itemStyle: { color: '#2277CC', opacity: 1 },  // hover 高亮：区块整体提亮发光
        label: {
          show: true,
          color: '#FFE08A',                           // 持续显示的地区名：亮金色
          fontSize: 13,
          fontWeight: 700,
          distance: 1
        }
      },
      label: { show: false },                         // 原有保留
      regions: [                                      // 原有保留结构：在管城市底色同步提亮
        { name: '洛阳市', itemStyle: { color: '#1B5C9C' } },
        { name: '开封市', itemStyle: { color: '#1B5C9C' } },
        { name: '安阳市', itemStyle: { color: '#1B5C9C' } },
        { name: '郑州市', itemStyle: { color: '#123F6E' } },
        { name: '南阳市', itemStyle: { color: '#123F6E' } }
      ]
    },
    // ========== 3./4. series 分层：风险光环（底层） → bar3D 风险柱 → 柱顶高光 → 城市标注 ==========
    series: [
      ...haloSeries('green', haloPoints.green),  // 低风险光环（底层，不遮挡柱子）
      ...haloSeries('amber', haloPoints.amber),  // 中风险光环
      ...haloSeries('red', haloPoints.red),      // 高风险光环（尺寸最大 / 最亮）
      {
        // 民宿风险柱（原有保留：数据映射逻辑完全不变，仅调整视觉参数）
        id: 'riskBar',
        name: '风险点',
        type: 'bar3D',
        coordinateSystem: 'geo3D',
        shading: 'lambert',
        barSize: 1.55,                            // 优化：统一柱体粗细，避免过粗遮挡文字
        bevelSize: 0.28,                          // 优化：加大倒角，柱体更具质感
        bevelSmoothness: 3,                       // 优化：倒角更圆润，弱化生硬棱边
        data: pts.map((p, i) => ({
          value: [p.lng, p.lat, HEIGHT[p.risk_level] || 10, i],
          name: p.name,
          itemStyle: { color: COLOR[p.risk_level] || '#00B42A' }   // 原有保留：风险等级配色逻辑不变
        })),
        emphasis: { itemStyle: { color: '#FFFFFF' } }
      },
      {
        // 新增：柱顶高光点（白色亮点，经 bloom 泛光≈柱顶自发光，按风险层级区分亮度）
        id: 'barGlow',
        name: '柱顶高光',
        type: 'scatter3D',
        coordinateSystem: 'geo3D',
        symbol: 'circle',
        symbolSize: 3,
        silent: true,
        data: pts.map((p) => ({
          value: [p.lng, p.lat, (HEIGHT[p.risk_level] || 10) + 1.4, 0],
          itemStyle: { color: '#FFFFFF', opacity: p.risk_level === 'red' ? 0.95 : p.risk_level === 'amber' ? 0.8 : 0.62 }
        }))
      },
      {
        // 城市标注（原有保留：洛阳 / 开封 / 安阳，位置精确到真实经纬度）
        name: '城市标注',
        type: 'scatter3D',
        coordinateSystem: 'geo3D',
        symbolSize: 3.2,
        data: CITY_COORDS.map((c) => ({ value: [c.lng, c.lat, 5], name: c.name })),
        itemStyle: { color: '#FFB800' },
        emphasis: { itemStyle: { color: '#FFCD4D' } },
        label: {
          show: true,
          position: 'top',
          distance: 10,
          formatter: (p) => `${p.name}\n${EN_MAP[p.name] || ''}`,
          color: 'rgba(159,208,255,.72)',          // 优化：降低标签透明度，避免遮挡地图主体
          fontSize: 11.5,
          fontFamily: 'var(--font-serif), serif',
          fontWeight: 700,
          lineHeight: 16,
          textShadowBlur: 6,
          textShadowColor: 'rgba(0,0,0,.8)'
        }
      }
    ]
  }
}

function render() {
  if (!el.value || !chart) return
  chart.setOption(buildOption(), true)
}

/* 说明：本组件不做逐帧动画。
   原因：脉冲需要用 chart.setOption 周期性重绘，而 echarts-gl 每次 setOption 都会
   重新执行 Geo3DView.render()，把 viewControl 的 alpha/beta/distance/center 复位 ——
   表现为 ① 旋转/缩放/平移一操作就被弹回；② hover 的区域高亮与地区名一闪就消失。
   因此改用静态三层同心圆光环（见上方 haloSeries），零重绘开销。 */

onMounted(async () => {
  await nextTick()
  loading.value = true
  err.value = ''
  try {
    await ensureGeo()
    chart = echarts.init(el.value, null, { renderer: 'canvas' })
    chart.on('click', (params) => {
      // 本次新增（占位注释）：后续可在此按 params.name 触发「区县级地图下钻」，当前仅保留原有进入档案逻辑
      if (params && params.seriesName === '风险点') {
        const idx = params.data && params.data.value ? params.data.value[3] : -1
        const d = (props.points || [])[idx]
        if (d) emit('open', d.id)
      }
    })
    render()
  } catch (e) {
    err.value = e?.message || '3D 地图加载失败'
  } finally {
    loading.value = false
  }
  ro = new ResizeObserver(() => chart && chart.resize())
  ro.observe(el.value)
})
onBeforeUnmount(() => {
  ro && ro.disconnect()
  chart && chart.dispose()
  chart = null
})

const cityStats = () => props.byCity
watch(() => props.points, render, { deep: true })
function barW(v, total) {
  if (!total) return '0%'
  return `${(v / total) * 100}%`
}
</script>

<style scoped>
.risk-map {
  position: relative;
  padding: 16px 18px 18px;
  border-radius: var(--r-md);
  background: linear-gradient(160deg, rgba(20, 41, 74, .72), rgba(7, 18, 34, .8));
  border: 1px solid var(--line);
  backdrop-filter: blur(14px);
  overflow: hidden;
}
.rm-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.rm-title { display: flex; align-items: center; gap: 9px; font-size: 15px; font-weight: 700; color: var(--text-1); letter-spacing: .04em; }
.rm-title em { font-family: var(--font-num); font-size: 10px; letter-spacing: .2em; color: var(--text-3); font-style: normal; }
.rm-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand-blue); box-shadow: 0 0 12px var(--accent-glow); animation: soft-pulse 1.6s infinite; }
.rm-legend { display: flex; gap: 16px; font-size: 12px; color: var(--text-2); }
.rm-legend span { display: inline-flex; align-items: center; gap: 6px; }
.lg { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.lg-red { background: var(--risk-red); box-shadow: 0 0 8px var(--risk-red-glow); }
.lg-amber { background: var(--risk-amber); box-shadow: 0 0 8px var(--risk-amber-glow); }
.lg-green { background: var(--risk-green); box-shadow: 0 0 8px var(--risk-green-glow); }

.rm-body { position: relative; width: 100%; height: 460px; border-radius: 12px; overflow: hidden; border: 1px solid rgba(96, 150, 255, .12); background: radial-gradient(120% 120% at 50% 0%, #0B1E39 0%, #061020 100%); }
.rm-canvas { width: 100%; height: 100%; }
.rm-loading {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  gap: 10px; color: var(--text-3); font-size: 13px; letter-spacing: .08em;
}
.rm-loading i {
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid rgba(22, 93, 255, .22); border-top-color: var(--brand-blue);
  animation: spin-slow .9s linear infinite;
}
.rm-loading.err { color: var(--risk-red); }

.rm-readout {
  position: absolute; left: 14px; bottom: 12px;
  display: flex; gap: 14px; font-family: var(--font-num); font-size: 10.5px;
  letter-spacing: .16em; color: var(--text-3); pointer-events: none;
}
.rm-readout .ok { color: var(--risk-green); }

.rm-cities { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 16px; }
.city-bar { padding: 11px 13px; border-radius: 11px; background: rgba(255, 255, 255, .025); border: 1px solid var(--line); }
.cb-top { display: flex; justify-content: space-between; align-items: baseline; }
.cb-name { font-size: 13px; color: var(--text-1); font-weight: 600; }
.cb-count { font-size: 12px; color: var(--text-3); }
.cb-track { display: flex; height: 6px; margin: 9px 0 8px; border-radius: 3px; overflow: hidden; background: rgba(255, 255, 255, .06); gap: 1px; }
.cb-track i { display: block; height: 100%; transition: width .6s var(--ease-out); }
.cb-red { background: var(--risk-red); }
.cb-amber { background: var(--risk-amber); }
.cb-green { background: var(--risk-green); }
.cb-foot { display: flex; justify-content: space-between; align-items: baseline; font-size: 11px; }
.cb-foot .num { color: var(--brand-gold); font-size: 13px; }

@media (max-width: 1200px) { .rm-cities { grid-template-columns: 1fr 1fr; } .rm-body { height: 400px; } }
@media (max-width: 760px) { .rm-cities { grid-template-columns: 1fr; } }
</style>