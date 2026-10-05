<template>
  <div class="history">
    <!-- 详情 -->
    <template v-if="detail">
      <div class="dt-bar">
        <button class="dt-back" @click="detail = null">‹ 返回列表</button>
        <span class="dt-id num">{{ detail.report_id }}</span>
      </div>

      <section class="dt-card">
        <div class="dt-head">
          <span class="risk-pill" :class="'r-' + detail.risk_level">{{ RISK_TEXT[detail.risk_level] || '低风险' }}</span>
          <span class="mode-pill" :class="detail.mode === 'llm' ? 'ai' : 'off'">{{ detail.mode === 'llm' ? 'AI 生成' : '模板生成' }}</span>
        </div>
        <h3 class="dt-title">《豫宿巡 · 贷后风险巡检报告》</h3>
        <p class="dt-sub">{{ detail.homestay_name }} · {{ detail.generated_at }}</p>

        <div v-if="detail.sources?.length" class="dt-src">
          <span class="src-label">RAG 引用来源</span>
          <div class="src-chips">
            <span v-for="(s, i) in detail.sources" :key="i">{{ s.source }}</span>
          </div>
        </div>

        <article class="md" v-html="renderMarkdown(detail.report_content)" />
      </section>
    </template>

    <!-- 列表 -->
    <template v-else>
      <section class="hd-top">
        <div class="hd-brand">
          <div class="hd-ico" v-html="ICON_REPORT" />
          <div>
            <h3>AI 巡检报告存档</h3>
            <p>银行端生成并下发的贷后风险巡检报告</p>
          </div>
        </div>
        <button class="hd-refresh" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
      </section>

      <div v-if="loading && !list.length" class="hd-empty">正在加载报告…</div>

      <template v-else-if="list.length">
        <button v-for="r in list" :key="r.report_id" class="rp-card" @click="openDetail(r)">
          <div class="rp-side" :class="'r-' + r.risk_level" />
          <div class="rp-body">
            <div class="rp-top">
              <b class="num">{{ r.report_id }}</b>
              <span v-if="r.pushed_to_app" class="rp-pushed">已下发</span>
            </div>
            <p class="rp-time">{{ r.generated_at }}</p>
            <p class="rp-preview">{{ plain(r.report_content).slice(0, 66) }}…</p>
            <div class="rp-foot">
              <span class="risk-pill sm" :class="'r-' + r.risk_level">{{ RISK_TEXT[r.risk_level] || '低风险' }}</span>
              <span class="rp-mode">{{ r.mode === 'llm' ? 'AI 生成' : '模板生成' }}</span>
            </div>
          </div>
          <span class="rp-arrow">›</span>
        </button>
      </template>

      <div v-else class="hd-empty">
        <div class="he-ico" v-html="ICON_REPORT" />
        <b>暂无巡检报告</b>
        <p>银行端完成 AI 巡检并下发后，报告将出现在这里</p>
      </div>
    </template>

    <transition name="toast">
      <div v-if="tip" class="tip">{{ tip }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '@/api'
import { RISK_TEXT, renderMarkdown } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })

const ICON_REPORT = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></svg>'

const list = ref([])
const loading = ref(false)
const detail = ref(null)
const tip = ref('')
let tipTimer = null

function show(msg) {
  tip.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { tip.value = '' }, 1900)
}

const plain = (md) => String(md || '').replace(/[#*>`_\-]/g, '').replace(/\s+/g, ' ').trim()

async function load() {
  if (!props.homestay?.id) return
  loading.value = true
  try {
    const res = await api.reports(props.homestay.id)
    list.value = res?.list || []
  } catch (e) {
    show(e?.message || '报告加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(r) {
  detail.value = r
}

onMounted(load)
watch(() => props.homestay?.id, () => { detail.value = null; load() })
</script>

<style scoped>
.history { padding: 14px 14px 22px; }

/* 顶部 */
.hd-top { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.hd-brand { flex: 1; display: flex; align-items: center; gap: 11px; }
.hd-ico {
  width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center;
  color: #165dff; background: rgba(22, 93, 255, .1);
}
.hd-brand h3 { font-size: 15.5px; color: #1d2129; font-weight: 700; }
.hd-brand p { font-size: 11px; color: #86909c; margin-top: 3px; }
.hd-refresh {
  font-size: 11.5px; color: #165dff; padding: 7px 14px; border-radius: 999px;
  background: rgba(22, 93, 255, .09); border: 1px solid rgba(22, 93, 255, .2);
}
.hd-refresh:disabled { opacity: .6; }

/* 列表卡片 */
.rp-card {
  position: relative; display: flex; align-items: stretch; gap: 0; width: 100%; text-align: left;
  margin-bottom: 11px; border-radius: 16px; overflow: hidden; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
  transition: transform .24s var(--ease-out), box-shadow .24s;
}
.rp-card:hover { transform: translateY(-2px); box-shadow: 0 18px 32px -22px rgba(10, 25, 47, .6); }
.rp-side { flex: 0 0 4px; }
.rp-side.r-red { background: #f53f3f; }
.rp-side.r-amber { background: #ff7d00; }
.rp-side.r-green { background: #00b42a; }
.rp-body { flex: 1; padding: 13px 12px; min-width: 0; }
.rp-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.rp-top b { font-size: 12.5px; color: #1d2129; }
.rp-pushed { font-size: 10px; color: #00a844; background: rgba(0, 180, 42, .1); padding: 1px 8px; border-radius: 999px; }
.rp-time { font-size: 10.5px; color: #a9b0bd; margin-top: 4px; }
.rp-preview { font-size: 11.5px; color: #5a6473; line-height: 1.6; margin-top: 6px; overflow: hidden; }
.rp-foot { display: flex; align-items: center; gap: 8px; margin-top: 9px; }
.rp-mode { font-size: 10px; color: #86909c; }
.rp-arrow { display: grid; place-items: center; padding-right: 10px; font-size: 18px; color: #c9ced6; }

.risk-pill { font-size: 10.5px; font-weight: 700; padding: 1px 9px; border-radius: 999px; }
.risk-pill.sm { font-size: 10px; }
.r-red { color: #f53f3f; background: rgba(245, 63, 63, .1); }
.r-amber { color: #d96a00; background: rgba(255, 125, 0, .12); }
.r-green { color: #00a844; background: rgba(0, 180, 42, .1); }
.rp-side.r-red, .rp-side.r-amber, .rp-side.r-green { color: transparent; }

/* 空态 */
.hd-empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 46px 20px;
  text-align: center; border-radius: 16px; background: #fff; border: 1px dashed rgba(29, 33, 41, .12);
  font-size: 12px; color: #86909c;
}
.he-ico { width: 58px; height: 58px; border-radius: 18px; display: grid; place-items: center; color: #165dff; background: rgba(22, 93, 255, .08); margin-bottom: 6px; }
.hd-empty b { font-size: 13.5px; color: #1d2129; }
.hd-empty p { font-size: 11.5px; }

/* 详情 */
.dt-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.dt-back { font-size: 12.5px; color: #165dff; padding: 6px 12px; border-radius: 999px; background: rgba(22, 93, 255, .09); }
.dt-id { font-size: 11px; color: #86909c; }
.dt-card {
  padding: 16px 15px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.dt-head { display: flex; align-items: center; gap: 8px; }
.mode-pill { font-size: 10px; padding: 1px 9px; border-radius: 999px; }
.mode-pill.ai { color: #165dff; background: rgba(22, 93, 255, .1); }
.mode-pill.off { color: #86909c; background: #f2f3f5; }
.dt-title { font-size: 15.5px; color: #1d2129; margin-top: 10px; letter-spacing: .02em; }
.dt-sub { font-size: 11px; color: #86909c; margin-top: 5px; }
.dt-src { margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: rgba(22, 93, 255, .05); border: 1px dashed rgba(22, 93, 255, .2); }
.src-label { font-size: 10.5px; font-weight: 700; color: #165dff; letter-spacing: .06em; }
.src-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
.src-chips span { font-size: 10.5px; color: #4e5969; background: #fff; padding: 2px 9px; border-radius: 999px; border: 1px solid rgba(22, 93, 255, .16); }

/* Markdown */
.md { margin-top: 14px; }
.md :deep(.md-h) { font-size: 13.5px; color: #165dff; font-weight: 700; margin: 14px 0 8px; padding-left: 9px; border-left: 3px solid #165dff; }
.md :deep(.md-p) { font-size: 12px; color: #4e5969; line-height: 1.85; margin: 6px 0; }
.md :deep(.md-ul), .md :deep(.md-ol) { margin: 6px 0 6px 4px; padding-left: 16px; }
.md :deep(.md-ul li), .md :deep(.md-ol li) { font-size: 12px; color: #4e5969; line-height: 1.8; margin: 3px 0; }
.md :deep(strong) { color: #1d2129; }
.md :deep(code) { font-family: var(--font-num); font-size: 11px; background: #f2f3f5; padding: 1px 5px; border-radius: 4px; }
.md :deep(.md-quote) { font-size: 12px; color: #5a6473; border-left: 3px solid #e5e8ef; padding-left: 10px; margin: 8px 0; }
.md :deep(.md-hr) { border: 0; border-top: 1px dashed rgba(29, 33, 41, .12); margin: 12px 0; }

.tip {
  position: fixed; left: 50%; bottom: 96px; transform: translateX(-50%); z-index: 80;
  max-width: 80%; padding: 10px 18px; border-radius: 11px; font-size: 12px;
  background: rgba(29, 33, 41, .93); color: #fff; text-align: center;
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
