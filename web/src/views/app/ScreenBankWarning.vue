<template>
  <div class="bankwarn">
    <!-- 概览 -->
    <section class="bw-stats">
      <div class="bs-item red"><b class="num">{{ pending.length }}</b><span>待处理</span></div>
      <div class="bs-item green"><b class="num">{{ closed.length }}</b><span>已处理</span></div>
      <div class="bs-item amber"><b class="num">{{ highRisk.length }}</b><span>高风险</span></div>
    </section>

    <!-- 筛选 -->
    <div class="seg">
      <button v-for="f in filters" :key="f.key" class="seg-btn" :class="{ on: tab === f.key }" @click="tab = f.key">
        {{ f.label }}
      </button>
      <button class="bw-refresh" :disabled="loading" @click="reload">{{ loading ? '…' : '刷新' }}</button>
    </div>

    <!-- 列表 -->
    <template v-if="shown.length">
      <article v-for="w in shown" :key="w.id" class="warn" :class="'risk-' + w.level">
        <div class="warn-top">
          <span class="warn-rule num">{{ w.rule_id }}</span>
          <span class="warn-name">{{ w.rule_name }}</span>
          <span v-if="w.ai_generated" class="ai-chip">AI</span>
          <span class="warn-level">{{ RISK_TEXT[w.level] }}</span>
        </div>

        <p class="warn-reason">{{ w.reason }}</p>

        <div v-if="w.suggestion" class="warn-sug">
          <span class="sug-label">整改建议</span>
          <p>{{ w.suggestion }}</p>
        </div>

        <div class="warn-foot">
          <span class="wf-time">{{ fromNow(w.created_at) }}</span>
          <span class="wf-tags">
            <span v-if="w.pushed_to_app" class="tag pushed">已下发老板端</span>
            <span class="tag" :class="w.status === 'closed' ? 'done' : (w.status === 'processing' ? 'doing' : 'wait')">
              {{ STATUS_TEXT[w.status] || '待处理' }}
            </span>
          </span>
        </div>
      </article>
    </template>

    <div v-else class="empty">
      <div class="em-ico" v-html="ICON_BELL" />
      <b>{{ tab === 'all' ? '暂无银行预警记录' : '该分类下暂无预警' }}</b>
      <p>银行端完成风险扫描或 AI 自动生成预警后，将在此留档</p>
    </div>

    <transition name="toast">
      <div v-if="tip" class="tip">{{ tip }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { store, refreshWarnings } from '@/store'
import { RISK_TEXT, fromNow } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })

const ICON_BELL = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>'

const STATUS_TEXT = { pending: '待处理', processing: '处理中', closed: '已处理' }
const filters = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待处理' },
  { key: 'closed', label: '已处理' }
]

const tab = ref('all')
const loading = ref(false)
const tip = ref('')
let tipTimer = null

function show(msg) {
  tip.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { tip.value = '' }, 1900)
}

const mine = computed(() => store.warnings.filter((w) => w.homestay_id === props.homestay?.id))
const pending = computed(() => mine.value.filter((w) => w.status !== 'closed'))
const closed = computed(() => mine.value.filter((w) => w.status === 'closed'))
const highRisk = computed(() => mine.value.filter((w) => w.level === 'red'))

const shown = computed(() => {
  if (tab.value === 'pending') return pending.value
  if (tab.value === 'closed') return closed.value
  return mine.value
})

async function reload() {
  loading.value = true
  try {
    await refreshWarnings()
    show('预警记录已刷新')
  } catch (e) {
    show(e?.message || '刷新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { refreshWarnings().catch(() => {}) })
</script>

<style scoped>
.bankwarn { padding: 14px 14px 22px; }

/* 概览 */
.bw-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
.bs-item {
  padding: 14px 8px; border-radius: 15px; text-align: center; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.bs-item b { display: block; font-size: 22px; line-height: 1.1; }
.bs-item span { font-size: 10.5px; color: #86909c; }
.bs-item.red b { color: #f53f3f; }
.bs-item.green b { color: #00b42a; }
.bs-item.amber b { color: #ff7d00; }

/* 筛选 */
.seg { display: flex; align-items: center; gap: 7px; margin: 14px 0 12px; }
.seg-btn {
  font-size: 11.5px; padding: 6px 14px; border-radius: 999px; color: #4e5969;
  background: #fff; border: 1px solid rgba(29, 33, 41, .08); transition: all .22s var(--ease-out);
}
.seg-btn.on { color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff); border-color: transparent; font-weight: 600; }
.bw-refresh { margin-left: auto; font-size: 11.5px; color: #165dff; padding: 6px 14px; border-radius: 999px; background: rgba(22, 93, 255, .09); }
.bw-refresh:disabled { opacity: .6; }

/* 预警卡 */
.warn {
  position: relative; padding: 13px 13px 12px 15px; border-radius: 14px; overflow: hidden; margin-bottom: 11px;
  background: color-mix(in srgb, var(--risk) 6%, #fff);
  border: 1px solid color-mix(in srgb, var(--risk) 22%, transparent);
}
.warn::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3.5px; background: var(--risk); }
.warn.risk-red { --risk: #f53f3f; }
.warn.risk-amber { --risk: #ff7d00; }
.warn.risk-green { --risk: #00b42a; }
.warn-top { display: flex; align-items: center; gap: 7px; }
.warn-rule { font-size: 11px; font-weight: 700; color: #fff; padding: 1px 7px; border-radius: 6px; background: var(--risk); }
.warn-name { font-size: 12.5px; font-weight: 700; color: #1d2129; flex: 1; }
.ai-chip { font-size: 9.5px; font-weight: 700; color: #165dff; background: rgba(22, 93, 255, .12); padding: 1px 6px; border-radius: 5px; }
.warn-level { font-size: 11px; font-weight: 700; color: var(--risk); }
.warn-reason { font-size: 12px; color: #4e5969; line-height: 1.62; margin-top: 7px; }
.warn-sug { margin-top: 8px; padding: 9px 11px; border-radius: 11px; background: rgba(255, 255, 255, .78); border: 1px dashed color-mix(in srgb, var(--risk) 32%, transparent); }
.sug-label { font-size: 10.5px; font-weight: 700; color: #b06a00; letter-spacing: .06em; }
.warn-sug p { font-size: 11.5px; color: #4e5969; line-height: 1.65; margin-top: 3px; }
.warn-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; }
.wf-time { font-size: 10.5px; color: #a9b0bd; }
.wf-tags { display: flex; gap: 6px; }
.tag { font-size: 10px; padding: 1px 9px; border-radius: 999px; }
.tag.pushed { color: #00a844; background: rgba(0, 180, 42, .1); }
.tag.wait { color: #f53f3f; background: rgba(245, 63, 63, .1); }
.tag.doing { color: #d96a00; background: rgba(255, 125, 0, .12); }
.tag.done { color: #86909c; background: #f2f3f5; }

/* 空态 */
.empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 46px 20px;
  text-align: center; border-radius: 16px; background: #fff; border: 1px dashed rgba(29, 33, 41, .12);
}
.em-ico { width: 58px; height: 58px; border-radius: 18px; display: grid; place-items: center; color: #f53f3f; background: rgba(245, 63, 63, .08); margin-bottom: 6px; }
.empty b { font-size: 13.5px; color: #1d2129; }
.empty p { font-size: 11.5px; color: #86909c; line-height: 1.7; }

.tip {
  position: fixed; left: 50%; bottom: 96px; transform: translateX(-50%); z-index: 80;
  max-width: 80%; padding: 10px 18px; border-radius: 11px; font-size: 12px;
  background: rgba(29, 33, 41, .93); color: #fff; text-align: center;
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
