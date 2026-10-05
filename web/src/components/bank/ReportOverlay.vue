<template>
  <transition name="ov">
    <div v-if="r.visible" class="ov theme-bank">
      <div class="ov-bg" />

      <!-- ========== 思考中：AI 粒子大脑 ========== -->
      <div v-if="r.phase === 'thinking'" class="think">
        <div class="brain-wrap">
          <AiBrain :size="280" />
          <div class="brain-ring" />
        </div>
        <h3 class="think-title">大模型正在分析经营数据…</h3>
        <p class="think-sub">{{ r.homestay?.name || '目标民宿' }} · RAG 私有知识库检索中</p>
        <ul class="steps">
          <li v-for="(s, i) in steps" :key="i" :class="{ on: i <= stepIndex }">
            <span class="sp" />{{ s }}
          </li>
        </ul>
      </div>

      <!-- ========== 完成：数字化 PDF 报告 ========== -->
      <div v-else-if="r.phase === 'done'" class="report-wrap">
        <div class="report-paper rise-in">
          <!-- 纸质纹路 & 公章 -->
          <div class="paper-grid" />
          <div class="stamp">
            <svg viewBox="0 0 140 140" width="118" height="118">
              <defs>
                <path id="stamp-arc" d="M70,70 m-52,0 a52,52 0 1,1 104,0 a52,52 0 1,1 -104,0" />
              </defs>
              <circle cx="70" cy="70" r="62" fill="none" stroke="#C8102E" stroke-width="2.6" />
              <circle cx="70" cy="70" r="52" fill="none" stroke="#C8102E" stroke-width="1" />
              <text class="stamp-arc">
                <textPath href="#stamp-arc" startOffset="0%">中国工商银行 · 贷后风控中心 · 豫宿巡</textPath>
              </text>
              <path d="M70 46l5.6 11.4 12.6 1.8-9.1 8.9 2.1 12.5L70 74.7 58.8 80.6l2.1-12.5-9.1-8.9 12.6-1.8z" fill="#C8102E" />
              <text x="70" y="102" text-anchor="middle" class="stamp-txt">贷后风控</text>
            </svg>
          </div>

          <!-- 抬头 -->
          <header class="rp-head">
            <div class="rp-org">中国工商银行 · 豫宿巡贷后风控中心</div>
            <h1 class="rp-title title-serif">贷后风险巡检报告</h1>
            <div class="rp-meta">
              <span>报告编号：<em class="num">{{ reportNo }}</em></span>
              <span>生成时间：<em class="num">{{ shortTime(r.generatedAt) }}</em></span>
              <span>巡检对象：<em>{{ r.homestay?.name || '—' }}</em></span>
              <span>报告类型：<em>AI 自动生成 · 辅助决策</em></span>
            </div>
          </header>

          <div class="rp-rule" />

          <!-- 正文 -->
          <article class="rp-body" v-html="html" />

          <!-- 页脚 -->
          <footer class="rp-foot">
            <div class="rp-note">
              本报告由「豫宿巡」AI 引擎基于 RAG 私有知识库与合规沙盒经营数据自动生成，仅作贷后管理辅助参考，不构成授信决策依据。
            </div>
            <div class="rp-sign">
              <div>客户经理：<span class="sign-line" /></div>
              <div>复核人：<span class="sign-line" /></div>
            </div>
          </footer>
        </div>

        <!-- 操作条 -->
        <div class="ov-actions">
          <span class="oa-mode">
            <i /> 生成模式：{{ r.content?.includes('离线') ? '离线模板' : '大模型 + RAG' }}
          </span>
          <button class="btn btn-ghost" @click="download">下载报告</button>
          <button class="btn btn-gold" @click="syncToApp">📲 同步整改建议至老板端</button>
          <button class="btn btn-primary" @click="close">完成</button>
        </div>
      </div>

      <!-- ========== 失败 ========== -->
      <div v-else class="err">
        <div class="err-ico">!</div>
        <h3>报告生成失败</h3>
        <p>{{ r.error }}</p>
        <button class="btn btn-primary" @click="close">关闭</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, watch, ref, onBeforeUnmount } from 'vue'
import AiBrain from './AiBrain.vue'
import { store, closeReport } from '@/store'
import { renderMarkdown, shortTime } from '@/utils/format'
import { bus } from '@/utils/bus'

const r = computed(() => store.report)
const html = computed(() => renderMarkdown(r.value.content))

const steps = [
  '抽取该民宿经营与贷款数据',
  'RAG 检索私有知识库（本店 SOP / 贷后管理办法）',
  '大模型生成风险分析与建议措施',
  '排版输出结构化巡检报告'
]
const stepIndex = ref(0)
let stepTimer = null

watch(() => r.value.phase, (p) => {
  clearInterval(stepTimer)
  if (p === 'thinking') {
    stepIndex.value = 0
    stepTimer = setInterval(() => {
      if (stepIndex.value < steps.length - 1) stepIndex.value++
    }, 900)
  }
})
onBeforeUnmount(() => clearInterval(stepTimer))

const reportNo = computed(() => {
  const hs = r.value.homestay
  const d = new Date(r.value.generatedAt || Date.now())
  const p = (n) => String(n).padStart(2, '0')
  return `YSX-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${hs?.id || 'H000'}`
})

function download() {
  const hs = r.value.homestay
  const text = [
    '《豫宿巡·贷后风险巡检报告》',
    `报告编号：${reportNo.value}`,
    `生成时间：${r.value.generatedAt}`,
    `巡检对象：${hs?.name || ''}（${hs?.city || ''}）`,
    '',
    r.value.content
  ].join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `豫宿巡巡检报告_${hs?.id || 'report'}_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(a.href)
}

function syncToApp() {
  bus.emit('report:rectify', {
    homestay_id: r.value.homestay?.id,
    homestay_name: r.value.homestay?.name,
    content: r.value.content,
    at: Date.now()
  })
}

const close = () => closeReport()
</script>

<style scoped>
.ov { position: fixed; inset: 0; z-index: 200; display: flex; align-items: center; justify-content: center; padding: 26px; }
.ov-bg { position: absolute; inset: 0; background: rgba(3, 8, 16, .88); backdrop-filter: blur(10px); }
.ov-enter-active, .ov-leave-active { transition: opacity .35s var(--ease-out); }
.ov-enter-from, .ov-leave-to { opacity: 0; }

/* ---------- 思考中 ---------- */
.think { position: relative; z-index: 2; text-align: center; }
.brain-wrap { position: relative; width: 300px; height: 300px; margin: 0 auto; }
.brain-ring {
  position: absolute; inset: 6px; border-radius: 50%;
  border: 1px dashed rgba(22, 93, 255, .35);
  animation: spin-slow 22s linear infinite;
}
.think-title { margin-top: 10px; font-family: var(--font-serif); font-size: 22px; color: #fff; letter-spacing: .1em; }
.think-sub { margin-top: 8px; font-size: 13px; color: var(--text-3); }
.steps { margin: 26px auto 0; display: flex; flex-direction: column; gap: 10px; width: fit-content; text-align: left; }
.steps li { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-3); transition: color .3s; }
.steps li .sp {
  width: 8px; height: 8px; border-radius: 50%; background: rgba(120, 150, 195, .3);
  transition: background .3s, box-shadow .3s;
}
.steps li.on { color: #cfe0ff; }
.steps li.on .sp { background: var(--brand-blue); box-shadow: 0 0 12px var(--accent-glow); animation: soft-pulse 1.2s infinite; }

/* ---------- 报告 ---------- */
.report-wrap { position: relative; z-index: 2; width: min(920px, 100%); max-height: 100%; display: flex; flex-direction: column; }
.report-paper {
  position: relative;
  background: linear-gradient(180deg, #fbfcfe, #f4f6fa);
  border-radius: 6px;
  padding: 40px 52px 34px;
  overflow-y: auto;
  box-shadow: 0 40px 90px -30px rgba(0, 0, 0, .95);
  color: #1c2434;
  border-top: 3px solid #165dff;
}
.paper-grid {
  position: absolute; inset: 0; pointer-events: none; opacity: .5;
  background-image: radial-gradient(rgba(22, 93, 255, .07) 1px, transparent 1px);
  background-size: 22px 22px;
}
.stamp { position: absolute; right: 34px; top: 40%; opacity: .82; transform: rotate(-14deg); pointer-events: none; }
.stamp-arc { font-size: 10.5px; fill: #c8102e; letter-spacing: 2.2px; font-family: var(--font-sans); }
.stamp-txt { font-size: 15px; fill: #c8102e; letter-spacing: 4px; font-family: var(--font-serif); font-weight: 700; }

.rp-head { position: relative; z-index: 2; }
.rp-org { font-size: 12px; color: #5a6b86; letter-spacing: .18em; }
.rp-title { margin-top: 10px; font-size: 30px; color: #0e1f3d; letter-spacing: .12em; }
.rp-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-top: 16px; font-size: 12.5px; color: #5a6b86; }
.rp-meta em { font-style: normal; color: #1c2434; font-weight: 600; }
.rp-rule { height: 2px; margin: 20px 0 6px; background: linear-gradient(90deg, #165dff, #ffb800 60%, transparent); position: relative; z-index: 2; }

.rp-body { position: relative; z-index: 2; }
:deep(.md-h) { font-family: var(--font-serif); color: #0e1f3d; letter-spacing: .06em; margin: 20px 0 8px; font-size: 16.5px; padding-left: 11px; border-left: 3px solid #165dff; }
:deep(.md-h:first-child) { margin-top: 4px; }
:deep(h2.md-h) { font-size: 19px; }
:deep(.md-p) { font-size: 13.5px; line-height: 2; color: #2c3648; margin: 6px 0; }
:deep(.md-ul), :deep(.md-ol) { margin: 6px 0 6px 4px; }
:deep(.md-ul li), :deep(.md-ol li) { font-size: 13.5px; line-height: 1.95; color: #2c3648; padding-left: 18px; position: relative; }
:deep(.md-ul li)::before { content: ""; position: absolute; left: 4px; top: 10px; width: 5px; height: 5px; border-radius: 50%; background: #165dff; }
:deep(.md-ol) { counter-reset: ol; }
:deep(.md-ol li) { counter-increment: ol; }
:deep(.md-ol li)::before { content: counter(ol); position: absolute; left: 0; top: 4px; font-size: 11px; font-family: var(--font-num); color: #fff; background: #165dff; width: 15px; height: 15px; border-radius: 50%; display: grid; place-items: center; }
:deep(.md-quote) { margin: 8px 0; padding: 9px 14px; background: rgba(22, 93, 255, .06); border-left: 3px solid #165dff; font-size: 13px; color: #3b465c; border-radius: 0 6px 6px 0; }
:deep(.md-hr) { border: 0; height: 1px; background: rgba(28, 36, 52, .12); margin: 16px 0; }
:deep(.md-p strong), :deep(.md-ul li strong), :deep(.md-ol li strong) { color: #b4232a; font-weight: 700; }
:deep(code) { font-family: var(--font-num); background: rgba(22, 93, 255, .08); padding: 1px 5px; border-radius: 4px; font-size: 12.5px; }

.rp-foot { position: relative; z-index: 2; margin-top: 28px; padding-top: 16px; border-top: 1px dashed rgba(28, 36, 52, .18); }
.rp-note { font-size: 11.5px; color: #7a879c; line-height: 1.85; }
.rp-sign { display: flex; gap: 40px; margin-top: 16px; font-size: 12.5px; color: #4a5568; }
.sign-line { display: inline-block; width: 110px; border-bottom: 1px solid rgba(28, 36, 52, .35); }

/* ---------- 操作条 ---------- */
.ov-actions { display: flex; align-items: center; gap: 12px; margin-top: 16px; flex: 0 0 auto; }
.oa-mode { flex: 1; display: inline-flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--text-3); }
.oa-mode i { width: 7px; height: 7px; border-radius: 50%; background: var(--risk-green); box-shadow: 0 0 10px var(--risk-green-glow); }

/* ---------- 失败 ---------- */
.err { position: relative; z-index: 2; text-align: center; }
.err-ico {
  width: 56px; height: 56px; margin: 0 auto 16px; border-radius: 50%;
  display: grid; place-items: center; font-size: 26px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #f53f3f, #a51c1c);
}
.err h3 { color: #fff; font-size: 19px; }
.err p { color: var(--text-3); margin: 10px 0 22px; font-size: 13.5px; max-width: 460px; }

@media (max-width: 760px) {
  .report-paper { padding: 26px 22px; }
  .rp-meta { grid-template-columns: 1fr; }
  .stamp { display: none; }
  .ov-actions { flex-wrap: wrap; }
}
</style>
