<template>
  <div class="bank theme-bank">
    <!-- Globe Study 全屏背景（豫宿巡文字点阵地球） -->
    <GlobeCanvas class="globe-bg" :interactive="false" :density="110" :speed="70" :globe="{ radius: 100, drift: 210, letters: 100 }" />
    <div class="bg-grid" />
    <div class="bg-glow" />

    <!-- ============ 左侧导航 ============ -->
    <aside class="side">
      <div class="side-brand" @click="$router.push('/')">
        <svg viewBox="0 0 48 48" width="34" height="34" aria-hidden="true">
          <path d="M24 3 43 13v22L24 45 5 35V13z" fill="none" stroke="#165DFF" stroke-width="2" />
          <path d="M15 30c0-6 4-10 9-10s9 4 9 10" fill="none" stroke="#FFB800" stroke-width="2.2" stroke-linecap="round" />
          <circle cx="24" cy="16" r="3.2" fill="#FFB800" />
          <path d="M17 34h14" stroke="#4B83FF" stroke-width="2.2" stroke-linecap="round" />
        </svg>
        <div>
          <div class="sb-name title-serif">豫宿巡</div>
          <div class="sb-role">客户经理端 · 贷后风控</div>
        </div>
      </div>

      <nav class="side-nav">
        <router-link v-for="n in navs" :key="n.path" :to="n.path" class="nav-item"
          :class="{ active: $route.path.startsWith(n.path) }">
          <span class="nav-ico" v-html="n.icon" />
          <span class="nav-label">{{ n.label }}</span>
          <span v-if="n.key === 'warnings' && warningSummary.pending" class="badge-num">{{ warningSummary.pending }}</span>
          <span v-if="n.key === 'messages' && msgUnread" class="badge-num msg">{{ msgUnread }}</span>
        </router-link>
      </nav>

      <div class="side-foot">
        <div class="engine-card">
          <div class="ec-row">
            <span class="ec-k">风控规则引擎</span>
            <span class="ec-v ok">运行中</span>
          </div>
          <div class="ec-row">
            <span class="ec-k">大模型</span>
            <span class="ec-v">{{ llmLabel }}</span>
          </div>
          <div class="ec-row">
            <span class="ec-k">向量检索</span>
            <span class="ec-v">{{ vectorLabel }}</span>
          </div>
          <button class="ec-btn" :disabled="running" @click="handleTrigger">
            {{ running ? '规则引擎扫描中…' : '⚡ 一键触发风险扫描' }}
          </button>
        </div>
        <div class="side-user">
          <div class="su-avatar">李</div>
          <div>
            <div class="su-name">李明远</div>
            <div class="su-dept">工商银行 · 洛阳分行 信贷部</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ============ 主区域 ============ -->
    <main class="main">
      <header class="topbar">
        <div class="tb-left">
          <h2 class="tb-title title-serif">{{ $route.meta.title || '贷后驾驶舱' }}</h2>
          <span class="tb-sub">{{ $route.meta.sub || '' }}</span>
        </div>
        <div class="tb-right">
          <GlobeCanvas class="tb-globe" :width="84" :height="84" :density="150" :glyph-size="64" />
          <div class="tb-clock">
            <span class="num tb-time">{{ clock.time }}</span>
            <span class="tb-date">{{ clock.date }}</span>
          </div>
          <button class="tb-btn" @click="openTwin">
            <svg viewBox="0 0 24 24" width="15" height="15"><rect x="3" y="4" width="8" height="16" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="14" y="7" width="7" height="12" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
            双屏联动演示
          </button>
          <div v-if="!apiState.online" class="tb-offline">离线缓存模式</div>
        </div>
      </header>

      <div v-if="loading" class="boot">
        <div class="boot-spin" />
        <p>正在接入贷后风控数据总线…</p>
      </div>

      <div v-else class="content no-scrollbar">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 全局 AI 巡检报告遮罩 -->
    <ReportOverlay />

    <!-- 全局提示 -->
    <transition name="toast">
      <div v-if="toast.show" class="toast" :class="'toast-' + toast.type">{{ toast.msg }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { store, bootstrap, runRuleEngine, refreshWarnings } from '@/store'
import api, { apiState } from '@/api'
import { bus } from '@/utils/bus'
import ReportOverlay from '@/components/bank/ReportOverlay.vue'
import GlobeCanvas from '@/components/bank/GlobeCanvas.vue'

const navs = [
  { key: 'dashboard', path: '/bank/dashboard', label: '贷后驾驶舱', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13h4l2 7 4-16 2 9h6"/></svg>' },
  { key: 'warnings', path: '/bank/warnings', label: '预警中心', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20L12 3z"/><path d="M12 9v5M12 17.5v.4"/></svg>' },
  { key: 'archive', path: '/bank/archive', label: '民宿数字档案', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></svg>' },
  { key: 'report', path: '/bank/report', label: 'AI巡检报告', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 0 6v2a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-2a3 3 0 0 1 0-6V7a4 4 0 0 1 4-4z"/></svg>' },
  { key: 'rag', path: '/bank/rag', label: 'RAG 系统管理', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v15H6.5A2.5 2.5 0 0 0 4 20.5V5.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H19v3H6.5A2.5 2.5 0 0 1 4 20.5z"/><path d="M8 7.5h7M8 11h5"/></svg>' },
  { key: 'messages', path: '/bank/messages', label: '消息中心', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z"/><path d="M9 10.5h6M9 14h3"/></svg>' },
  { key: 'models', path: '/bank/models', label: '模型管理', icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><rect x="9" y="9" width="6" height="6" rx="1.5"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/></svg>' }
]

const loading = ref(true)
const running = ref(false)
const toast = reactive({ show: false, msg: '', type: 'info' })
let toastTimer = null

const warningSummary = computed(() => store.warningSummary)
const llmLabel = computed(() => ({ qwen: '通义千问', deepseek: 'DeepSeek', offline: '离线兜底' }[store.llmMode] || '检测中'))
const vectorLabel = computed(() => ({ chromadb: 'ChromaDB', builtin: '内置检索' }[store.vectorMode] || '检测中'))

/* 消息中心未读角标：轮询老板发来的未读条数 */
const msgUnread = ref(0)
let msgTimer = null
async function refreshMsgUnread() {
  try {
    const r = await api.bankUnread()
    msgUnread.value = r?.count || 0
  } catch { /* 后端未启动时忽略 */ }
}

const clock = reactive({ time: '', date: '' })
let clockTimer = null
function tickClock() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  clock.time = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
  const w = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  clock.date = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${w}`
}

function showToast(msg, type = 'info') {
  toast.msg = msg
  toast.type = type
  toast.show = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.show = false), 3200)
}

async function handleTrigger() {
  if (running.value) return
  running.value = true
  try {
    const res = await runRuleEngine()
    const created = res?.created?.length || 0
    showToast(created ? `规则引擎扫描完成，新增 ${created} 条风险预警` : '规则引擎扫描完成，暂无新增风险', 'success')
    if (created) {
      // 双屏联动：把新增预警推送给老板端 App
      bus.emit('warning:new', { created: res.created, at: Date.now() })
      await refreshWarnings()
    }
  } catch (e) {
    showToast(e?.message || '规则引擎调用失败，请确认后端已启动', 'error')
  } finally {
    running.value = false
  }
}

function openTwin() {
  window.open(`${location.origin}${location.pathname}#/app`, 'ysx-app', 'width=480,height=920,left=120,top=60')
  showToast('已打开老板端 App 窗口，可演示「大屏报警 → 手机收到整改建议」', 'info')
}

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 1000)
  refreshMsgUnread()
  msgTimer = setInterval(refreshMsgUnread, 8000)
  await bootstrap()
  loading.value = false
  if (!store.warnings.length) {
    try { await runRuleEngine() } catch { /* 后端未启动时忽略 */ }
  }
})
onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearInterval(msgTimer)
})
</script>

<style scoped>
.bank { position: relative; display: flex; height: 100vh; overflow: hidden; }
/* Globe Study 全屏背景：铺满屏幕、固定不动、不拦截点击，弱化透明度保证可读性 */
/* 注意：组件根元素 inline style 自带 position:relative，需 !important 强制脱离文档流，
   否则背景会成为 flex 布局子元素把左侧导航挤到右侧、主内容宽度压成 0 */
.globe-bg {
  position: fixed !important; inset: 0; z-index: 0;
  opacity: .5; pointer-events: none;
  -webkit-mask-image: radial-gradient(ellipse 82% 78% at 50% 46%, #000 52%, transparent 96%);
  mask-image: radial-gradient(ellipse 82% 78% at 50% 46%, #000 52%, transparent 96%);
}
.bg-grid {
  position: fixed; inset: 0; z-index: 1; pointer-events: none;
  background-image:
    linear-gradient(rgba(96, 150, 255, .04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(96, 150, 255, .04) 1px, transparent 1px);
  background-size: 60px 60px;
}
.bg-glow {
  position: fixed; width: 640px; height: 640px; border-radius: 50%;
  right: -220px; top: -260px; filter: blur(120px);
  background: rgba(22, 93, 255, .18); pointer-events: none;
}

/* ---------- 侧栏 ---------- */
.side {
  position: relative; z-index: 3;
  width: 236px; flex: 0 0 236px;
  display: flex; flex-direction: column;
  background: linear-gradient(180deg, #0b1a2e, #081424);
  border-right: 1px solid var(--line);
}
.side-brand {
  display: flex; align-items: center; gap: 11px;
  padding: 20px 18px 18px; cursor: pointer;
  border-bottom: 1px solid var(--line);
}
.sb-name { font-size: 19px; color: #fff; letter-spacing: .12em; }
.sb-role { font-size: 11px; color: var(--text-3); margin-top: 2px; }

.side-nav { padding: 14px 12px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; overflow-x: hidden; }
.side-nav::-webkit-scrollbar { width: 0; }
.nav-item {
  position: relative; display: flex; align-items: center; gap: 11px;
  height: 44px; padding: 0 13px; border-radius: 10px;
  color: var(--text-2); font-size: 13.5px;
  transition: background .25s, color .25s;
}
.nav-item::before {
  content: ""; position: absolute; left: -12px; top: 50%; transform: translateY(-50%);
  width: 3px; height: 0; border-radius: 0 3px 3px 0;
  background: var(--brand-blue); box-shadow: 0 0 14px var(--accent-glow);
  transition: height .3s var(--ease-out);
}
.nav-item:hover { background: rgba(22, 93, 255, .1); color: var(--text-1); }
.nav-item.active { background: linear-gradient(90deg, rgba(22, 93, 255, .26), rgba(22, 93, 255, .06)); color: #fff; font-weight: 600; }
.nav-item.active::before { height: 22px; }
.nav-ico { display: inline-flex; align-items: center; }
.nav-label { flex: 1; }

.side-foot { margin-top: auto; padding: 14px 12px 16px; }
.engine-card {
  padding: 13px; border-radius: 12px;
  background: rgba(22, 93, 255, .07); border: 1px solid var(--line);
}
.ec-row { display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; padding: 3px 0; }
.ec-k { color: var(--text-3); }
.ec-v { color: var(--text-2); font-weight: 600; }
.ec-v.ok { color: var(--risk-green); }
.ec-btn {
  width: 100%; margin-top: 10px; height: 34px; border-radius: 9px;
  font-size: 12px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #2f6dff, #165dff);
  box-shadow: 0 10px 22px -12px var(--accent-glow);
  transition: transform .2s, box-shadow .25s, opacity .2s;
}
.ec-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 28px -12px var(--accent-glow); }
.ec-btn:disabled { opacity: .6; cursor: wait; }

.side-user { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding: 0 4px; }
.su-avatar {
  width: 34px; height: 34px; border-radius: 10px; flex: 0 0 34px;
  display: grid; place-items: center; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #165dff, #0b3fa8);
  border: 1px solid rgba(120, 175, 255, .4);
}
.su-name { font-size: 13px; color: var(--text-1); font-weight: 600; }
.su-dept { font-size: 10.5px; color: var(--text-3); }

/* ---------- 主区 ---------- */
.main { position: relative; z-index: 2; flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 26px 16px; border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(8, 20, 36, .7), transparent);
  backdrop-filter: blur(8px);
}
.tb-left { display: flex; align-items: baseline; gap: 12px; }
.tb-title { font-size: 23px; color: #fff; letter-spacing: .06em; }
.tb-sub { font-family: var(--font-num); font-size: 10.5px; letter-spacing: .24em; color: var(--text-3); }
.tb-right { display: flex; align-items: center; gap: 14px; }
.tb-clock { text-align: right; line-height: 1.2; }
.tb-time { font-size: 17px; color: var(--text-1); letter-spacing: .06em; }
.tb-date { display: block; font-size: 10.5px; color: var(--text-3); }
.tb-btn {
  display: inline-flex; align-items: center; gap: 7px; height: 36px; padding: 0 15px;
  border-radius: 9px; font-size: 12.5px; font-weight: 600; color: #cfdfff;
  background: rgba(22, 93, 255, .14); border: 1px solid rgba(22, 93, 255, .34);
  transition: background .25s, transform .2s;
}
.tb-btn:hover { background: rgba(22, 93, 255, .3); transform: translateY(-1px); }
.tb-offline {
  font-size: 11.5px; color: var(--risk-amber); padding: 6px 11px; border-radius: 8px;
  background: rgba(255, 125, 0, .12); border: 1px solid rgba(255, 125, 0, .3);
}
/* Globe Study 小组件：顶栏右侧只保留地球本体，无背景框/边框 */
.tb-globe {
  flex: 0 0 84px; width: 84px; height: 84px;
  border-radius: 50%; overflow: hidden;
  transition: transform .3s var(--ease-out);
}
.tb-globe:hover { transform: translateY(-2px); }

.content { flex: 1; padding: 22px 26px 30px; overflow-y: auto; }

/* ---------- 启动态 ---------- */
.boot { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; }
.boot-spin {
  width: 46px; height: 46px; border-radius: 50%;
  border: 2px solid rgba(22, 93, 255, .2); border-top-color: var(--brand-blue);
  animation: spin-slow .9s linear infinite;
}
.boot p { color: var(--text-3); font-size: 13px; letter-spacing: .1em; }

/* ---------- 提示 ---------- */
.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 11px; font-size: 13.5px; z-index: 99;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong);
  color: var(--text-1); box-shadow: var(--shadow-lift); backdrop-filter: blur(12px);
}
.toast-success { border-color: rgba(0, 180, 42, .45); color: #9ff0b4; }
.toast-error { border-color: rgba(245, 63, 63, .45); color: #ffb4b4; }
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

@media (max-width: 1080px) {
  .side { width: 76px; flex: 0 0 76px; }
  .sb-name, .sb-role, .nav-label, .engine-card, .side-user div { display: none; }
  .side-brand { justify-content: center; padding: 18px 10px; }
  .nav-item { justify-content: center; padding: 0; }
  .side-user { justify-content: center; }
}
</style>
