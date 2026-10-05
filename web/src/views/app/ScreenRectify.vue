<template>
  <div class="rectify">
    <!-- 头部 -->
    <header class="rc-head">
      <div class="rh-deco" />
      <div class="rh-top">
        <div>
          <h2 class="title-serif">预警与整改</h2>
          <p>银行端预警 · AI 自动拆解为可执行任务</p>
        </div>
        <span class="rh-badge" :class="{ hot: activeWarnings.length > 0 }">
          {{ activeWarnings.length ? activeWarnings.length + ' 项待处理' : '经营健康' }}
        </span>
      </div>
      <div class="rh-stats">
        <div class="rs-item"><b class="num">{{ activeWarnings.length }}</b><span>待处理预警</span></div>
        <div class="rs-item"><b class="num">{{ tasks.length }}</b><span>整改任务</span></div>
        <div class="rs-item"><b class="num">{{ doneCount }}</b><span>已完成</span></div>
      </div>
    </header>

    <!-- 银行端消息 -->
    <section v-if="inbox.length" class="card msg-card">
      <div class="cc-head">
        <h4>银行端消息</h4>
        <button v-if="unreadCount" class="link-btn" @click="readAll">全部已读</button>
      </div>
      <ul class="msg-list">
        <li v-for="m in inbox" :key="m.at" class="msg" :class="{ unread: !m.read }">
          <span class="msg-dot" />
          <div class="msg-body">
            <div class="msg-top">
              <b>{{ m.title }}</b>
              <span class="msg-time">{{ fromNow(m.at) }}</span>
            </div>
            <p class="msg-content">{{ m.content }}</p>
            <div v-if="m.suggestion" class="msg-sug">
              <span class="sug-label">AI 整改建议</span>
              <p>{{ m.suggestion }}</p>
            </div>
            <div class="msg-foot">
              <span class="msg-src">{{ m.source }}</span>
              <button v-if="!m.read" class="mini-btn" @click="markInboxRead(m.at)">标记已读</button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- 当前贷后预警 -->
    <section class="card">
      <div class="cc-head"><h4>当前贷后预警</h4></div>

      <div v-if="activeWarnings.length" class="warn-list">
        <article v-for="w in activeWarnings" :key="w.id" class="warn" :class="'risk-' + w.level">
          <div class="warn-top">
            <span class="warn-rule num">{{ w.rule_id }}</span>
            <span class="warn-name">{{ w.rule_name }}</span>
            <span class="warn-level">{{ RISK_TEXT[w.level] }}</span>
          </div>
          <p class="warn-reason">{{ w.reason }}</p>
          <div v-if="w.suggestion" class="warn-sug">
            <span class="sug-label">建议</span>
            <p>{{ w.suggestion }}</p>
          </div>
          <div v-if="metricsOf(w).length" class="warn-metrics">
            <span v-for="m in metricsOf(w)" :key="m.label">
              {{ m.label }} <b class="num">{{ m.value }}</b>
            </span>
          </div>
        </article>
      </div>

      <div v-else class="ok-state">
        <div class="ok-ico">
          <svg viewBox="0 0 24 24" width="26" height="26"><path d="M20 6 9 17l-5-5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <b>暂无贷后风险预警</b>
        <p>综合经营指标处于健康区间，继续保持</p>
      </div>
    </section>

    <!-- AI 整改任务清单 -->
    <section v-if="tasks.length" class="card">
      <div class="cc-head">
        <h4>AI 整改任务清单</h4>
        <span class="prog-text num">{{ doneCount }}/{{ tasks.length }}</span>
      </div>
      <div class="prog-bar"><i :style="{ width: progress + '%' }" /></div>
      <ul class="task-list">
        <li v-for="t in tasks" :key="t.key" class="task" :class="{ done: !!checked[t.key] }" @click="toggle(t.key)">
          <span class="tk-check">
            <svg viewBox="0 0 24 24" width="12" height="12"><path d="M20 6 9 17l-5-5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
          <div class="tk-body">
            <b>{{ t.title }}</b>
            <p>{{ t.desc }}</p>
            <span class="tk-src">{{ t.rule_id }} · {{ t.rule_name }}</span>
          </div>
        </li>
      </ul>
    </section>

    <button class="ask-bar" @click="$emit('go', 'assistant')">
      <span>不懂怎么改？让 AI 经营助手帮你拆解</span>
      <span class="ab-go">去提问 →</span>
    </button>

    <p class="rc-note">
      整改任务由 AI 依据风控规则与本店私有知识库自动拆解，仅供参考；具体经营决策请结合实际。
    </p>
  </div>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { store, markInboxRead, markAllInboxRead } from '@/store'
import { RISK_TEXT, fromNow } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })
defineEmits(['go'])

/** 规则 → 整改任务模板（AI 拆解逻辑的可解释映射） */
const TASK_MAP = {
  R001: [
    { t: '差评溯源归因', d: '导出近 14 日全部差评，按「卫生 / 隔音 / 设施」分类归因' },
    { t: '布草管理整改', d: '建立布草「一客一换一登记」台账，污渍布草单独封存报废' },
    { t: '深度保洁排班', d: '保洁由每日 1 次调整为退房即时保洁 + 每日巡回复查' },
    { t: '差评回复话术', d: '启用 AI 生成的三套回复模板，24 小时内 100% 回复差评' }
  ],
  R002: [
    { t: 'OTA 曝光优化', d: '重写房源标题并更换首图，突出「古城步行可达」核心卖点' },
    { t: '淡季引流活动', d: '上线「连住 2 晚享 9 折」，联动本地文旅渠道投放' },
    { t: '动态价格调整', d: '参考同商圈竞品，工作日单价下调约 8% 提升入住率' }
  ],
  R003: [
    { t: '舆情关键词治理', d: '针对「卫生差 / 位置偏」类差评制定专项话术与补偿标准' },
    { t: '服务触点升级', d: '增加接驳车与免费行李寄存，弱化位置短板' }
  ],
  R004: [
    { t: '额度使用规划', d: '额度使用率偏高，建议暂缓新增支用，优先安排回款' },
    { t: '现金流监测', d: '连续 30 天流水下滑，启动月度现金流复盘并预留还款资金' }
  ]
}

/** 无预警时的经营提升建议（绿色民宿也能有内容） */
const FALLBACK_TASKS = [
  { key: 'fb-0', title: '口碑资产沉淀', desc: '引导满意客人在离店时留下图文好评，沉淀 OTA 评分优势', rule_id: 'BASE', rule_name: '经营提升建议' },
  { key: 'fb-1', title: '文创引流获客', desc: '使用 AI 文创生成古都主题图片赠予客人，带动社交平台自然曝光', rule_id: 'BASE', rule_name: '经营提升建议' },
  { key: 'fb-2', title: '旺季备货与人力', desc: '结合历史入住曲线提前储备布草与兼职人力，避免旺季服务掉档', rule_id: 'BASE', rule_name: '经营提升建议' }
]

const activeWarnings = computed(() =>
  store.warnings.filter((w) => w.homestay_id === props.homestay?.id && w.status !== 'closed')
)

const inbox = computed(() => store.inbox)
const unreadCount = computed(() => store.inbox.filter((i) => !i.read).length)

const tasks = computed(() => {
  const out = []
  activeWarnings.value.forEach((w) => {
    const list = TASK_MAP[w.rule_id] || []
    list.forEach((t, i) => out.push({ key: `${w.id}-${i}`, title: t.t, desc: t.d, rule_id: w.rule_id, rule_name: w.rule_name }))
  })
  return out.length ? out : FALLBACK_TASKS
})

const checked = reactive({})
const doneCount = computed(() => tasks.value.filter((t) => checked[t.key]).length)
const progress = computed(() => (tasks.value.length ? Math.round((doneCount.value / tasks.value.length) * 100) : 0))

function toggle(key) {
  checked[key] = !checked[key]
}

function readAll() {
  markAllInboxRead()
}

/** 仅展示已定义口径的指标，隐藏 keyword_count 等原始字段，避免暴露内部字段名 */
const METRIC_LABELS = {
  ota_score: 'OTA 评分',
  bad_7d: '近7日差评',
  occupancy_7d: '近7日入住率',
  used_ratio: '额度使用率',
  flow_drop: '30天流水降幅',
  negative_hits: '负面关键词'
}
const PCT_KEYS = ['occupancy_7d', 'used_ratio', 'flow_drop']

function metricsOf(w) {
  const m = w?.metrics || {}
  return Object.entries(m)
    .filter(([k]) => METRIC_LABELS[k])
    .map(([k, v]) => ({
      label: METRIC_LABELS[k],
      value: PCT_KEYS.includes(k) && typeof v === 'number' ? `${(v * 100).toFixed(0)}%` : v
    }))
}
</script>

<style scoped>
.rectify { padding-bottom: 18px; }

/* Header */
.rc-head {
  position: relative; padding: 40px 20px 30px; overflow: hidden;
  background: linear-gradient(135deg, #f53f3f 0%, #ff7d3a 52%, #ffb800 130%);
  border-radius: 0 0 26px 26px; color: #fff;
}
.rh-deco {
  position: absolute; inset: 0; opacity: .22;
  background-image: radial-gradient(rgba(255, 255, 255, .6) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(ellipse 70% 75% at 85% 0%, #000, transparent 74%);
}
.rh-top { position: relative; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.rh-top h2 { font-size: 21px; letter-spacing: .04em; }
.rh-top p { font-size: 12px; opacity: .9; margin-top: 5px; }
.rh-badge {
  font-size: 11px; padding: 4px 11px; border-radius: 999px; white-space: nowrap;
  background: rgba(255, 255, 255, .2); border: 1px solid rgba(255, 255, 255, .32);
}
.rh-badge.hot { background: #fff; color: #e5342f; font-weight: 700; border-color: transparent; animation: soft-pulse 1.8s infinite; }

.rh-stats { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 20px; }
.rs-item {
  padding: 10px 8px; border-radius: 13px; text-align: center;
  background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .26);
  backdrop-filter: blur(8px);
}
.rs-item b { display: block; font-size: 22px; line-height: 1.1; }
.rs-item span { font-size: 10.5px; opacity: .9; }

/* 卡片 */
.card {
  margin: 14px 14px 0; padding: 15px 15px 12px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.cc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.cc-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.link-btn { font-size: 11.5px; color: #165dff; }
.prog-text { font-size: 13px; color: #165dff; }

/* 消息 */
.msg-list { display: flex; flex-direction: column; }
.msg { display: flex; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(29, 33, 41, .06); }
.msg:last-child { border-bottom: 0; padding-bottom: 2px; }
.msg-dot { width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; flex: 0 0 8px; background: #c9ced6; }
.msg.unread .msg-dot { background: #f53f3f; box-shadow: 0 0 0 4px rgba(245, 63, 63, .14); }
.msg-body { flex: 1; min-width: 0; }
.msg-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.msg-top b { font-size: 13px; color: #1d2129; }
.msg-time { font-size: 10.5px; color: #a9b0bd; white-space: nowrap; }
.msg-content { font-size: 11.5px; color: #4e5969; line-height: 1.65; margin-top: 4px; white-space: pre-line; }
.msg-sug {
  margin-top: 8px; padding: 9px 11px; border-radius: 11px;
  background: linear-gradient(135deg, rgba(255, 184, 0, .12), rgba(255, 125, 0, .07));
  border: 1px solid rgba(255, 184, 0, .3);
}
.msg-sug p { font-size: 11.5px; color: #7a5b00; line-height: 1.65; margin-top: 2px; }
.msg-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 7px; }
.msg-src { font-size: 10.5px; color: #a9b0bd; }
.mini-btn { font-size: 11px; color: #165dff; padding: 2px 9px; border-radius: 999px; background: rgba(22, 93, 255, .08); }

/* 预警 */
.warn-list { display: flex; flex-direction: column; gap: 10px; }
.warn {
  position: relative; padding: 12px 13px 12px 15px; border-radius: 13px; overflow: hidden;
  background: color-mix(in srgb, var(--risk) 6%, #fff);
  border: 1px solid color-mix(in srgb, var(--risk) 22%, transparent);
}
.warn::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--risk); }
.warn-top { display: flex; align-items: center; gap: 7px; }
.warn-rule {
  font-size: 11px; font-weight: 700; color: #fff; padding: 1px 7px; border-radius: 6px;
  background: var(--risk);
}
.warn-name { font-size: 12.5px; font-weight: 700; color: #1d2129; flex: 1; }
.warn-level { font-size: 11px; font-weight: 700; color: var(--risk); }
.warn-reason { font-size: 12px; color: #4e5969; line-height: 1.6; margin-top: 6px; }
.warn-sug {
  margin-top: 8px; padding: 9px 11px; border-radius: 11px; background: rgba(255, 255, 255, .75);
  border: 1px dashed color-mix(in srgb, var(--risk) 34%, transparent);
}
.warn-sug p { font-size: 11.5px; color: #4e5969; line-height: 1.65; margin-top: 2px; }
.sug-label { font-size: 10.5px; font-weight: 700; color: #b06a00; letter-spacing: .06em; }
.warn-metrics { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.warn-metrics span {
  font-size: 10.5px; color: #86909c; padding: 2px 8px; border-radius: 999px; background: #f5f6f8;
}
.warn-metrics b { color: #1d2129; font-weight: 700; margin-left: 2px; }

.ok-state { display: flex; flex-direction: column; align-items: center; gap: 5px; padding: 22px 0 16px; }
.ok-ico { width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center; color: #00b42a; background: rgba(0, 180, 42, .1); margin-bottom: 4px; }
.ok-state b { font-size: 14px; color: #1d2129; }
.ok-state p { font-size: 11.5px; color: #86909c; }

/* 任务清单 */
.prog-bar { height: 6px; border-radius: 4px; background: #f2f3f5; overflow: hidden; margin-bottom: 12px; }
.prog-bar i { display: block; height: 100%; border-radius: 4px; background: linear-gradient(90deg, #ffcd4d, #ffb800); transition: width .5s var(--ease-out); }
.task-list { display: flex; flex-direction: column; }
.task { display: flex; gap: 11px; padding: 11px 0; border-bottom: 1px solid rgba(29, 33, 41, .06); cursor: pointer; }
.task:last-child { border-bottom: 0; padding-bottom: 2px; }
.tk-check {
  width: 20px; height: 20px; flex: 0 0 20px; margin-top: 1px; border-radius: 7px; display: grid; place-items: center;
  color: transparent; background: #fff; border: 1.6px solid #d5dae2;
  transition: all .25s var(--ease-spring);
}
.task.done .tk-check { color: #fff; background: linear-gradient(135deg, #5fd47a, #00b42a); border-color: transparent; transform: scale(1.06); }
.tk-body { flex: 1; }
.tk-body b { font-size: 13px; color: #1d2129; transition: color .25s; }
.task.done .tk-body b { color: #a9b0bd; text-decoration: line-through; }
.tk-body p { font-size: 11.5px; color: #86909c; line-height: 1.62; margin-top: 3px; }
.task.done .tk-body p { color: #b8bdc7; }
.tk-src { display: inline-block; font-size: 10.5px; color: #165dff; background: rgba(22, 93, 255, .07); padding: 1px 8px; border-radius: 999px; margin-top: 7px; }

/* 追问条 */
.ask-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 10px; width: calc(100% - 28px);
  margin: 16px 14px 0; padding: 14px 16px; border-radius: 15px; text-align: left;
  background: linear-gradient(135deg, #165dff, #3a72ff); color: #fff;
  box-shadow: 0 16px 32px -20px rgba(22, 93, 255, .85);
  transition: transform .25s var(--ease-out), box-shadow .25s;
}
.ask-bar:hover { transform: translateY(-2px); box-shadow: 0 20px 40px -20px rgba(22, 93, 255, .9); }
.ask-bar span:first-child { font-size: 12.5px; font-weight: 600; }
.ab-go { font-size: 11.5px; font-weight: 700; white-space: nowrap; opacity: .95; }

.rc-note { margin: 14px 16px 0; font-size: 10.5px; color: #a9b0bd; line-height: 1.75; text-align: center; }
</style>
