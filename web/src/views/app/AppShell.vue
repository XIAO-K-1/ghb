<template>
  <div class="stage theme-app">
    <div class="stage-bg" />
    <div class="stage-glow g1" />
    <div class="stage-glow g2" />

    <!-- 左侧说明面板（桌面端） -->
    <aside class="stage-aside">
      <button class="back" @click="$router.push('/')">
        <svg viewBox="0 0 24 24" width="15" height="15"><path d="M15 6l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回演示入口
      </button>

      <div class="sa-brand">
        <svg viewBox="0 0 48 48" width="36" height="36"><path d="M24 3 43 13v22L24 45 5 35V13z" fill="none" stroke="#165DFF" stroke-width="2"/><path d="M15 30c0-6 4-10 9-10s9 4 9 10" fill="none" stroke="#FFB800" stroke-width="2.2" stroke-linecap="round"/><circle cx="24" cy="16" r="3.2" fill="#FFB800"/><path d="M17 34h14" stroke="#4B83FF" stroke-width="2.2" stroke-linecap="round"/></svg>
        <div>
          <h2 class="title-serif">豫宿巡 · 老板端</h2>
          <p>AI 经营助手 · 民宿经营者版</p>
        </div>
      </div>

      <ul class="sa-points">
        <li><b>经营概览</b>入住率 / 营收 / OTA 评分 / 差评一屏掌握</li>
        <li><b>AI 经营助手</b>RAG 私有知识库，回答附带来源标注</li>
        <li><b>AI 文创生成</b>一句话生成 Q 版新中式文创图，自动加「AI生成」标识</li>
        <li><b>预警与整改</b>接收银行端预警，AI 自动拆解为整改任务</li>
        <li><b>我的贷款</b>额度、下期还款、还款压力智能预警</li>
      </ul>

      <div class="sa-demo">
        <div class="sd-title">演示账号</div>
        <div class="sd-row"><span>账号</span><em class="num">ly001</em></div>
        <div class="sd-row"><span>密码</span><em class="num">123456</em></div>
        <p class="sd-tip">登录后建议在另一个窗口打开「银行端」，点击侧栏「一键触发风险扫描」，即可演示 <b>大屏报警 → 手机收到整改建议</b> 的双屏联动。</p>
      </div>

      <div class="sa-status">
        <span class="dot" :class="apiState.online ? 'risk-green' : 'risk-red'" />
        {{ apiState.online ? '后端服务已连接' : '后端离线（展示缓存数据）' }}
      </div>
    </aside>

    <!-- 手机外壳 -->
    <div class="phone-wrap">
      <div class="phone">
        <div class="phone-bar">
          <span class="pb-time num">{{ clock }}</span>
          <span class="pb-island" />
          <span class="pb-icons">
            <i class="sig" /><i class="wifi" /><i class="bat" />
          </span>
        </div>

        <div class="phone-screen" :class="'screen-' + screenKey">
          <!-- 未登录 -->
          <ScreenLogin v-if="!store.user" :api-state="apiState" @authed="onAuthed" />

          <!-- 已登录 -->
          <template v-else>
            <!-- 子页面返回栏（RAG系统 / 历史报告 / 银行预警记录 / 我的贷款） -->
            <transition name="subslide">
              <div v-if="isSub" class="sub-bar">
                <button class="sb-back" @click="tab = 'mine'">
                  <svg viewBox="0 0 24 24" width="16" height="16"><path d="M15 6l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="sb-title">{{ subTitle }}</span>
                <span class="sb-tag">我的 · {{ subTitle }}</span>
              </div>
            </transition>
            <div :class="tab === 'assistant' ? 'app-fill' : 'app-scroll no-scrollbar'">
              <KeepAlive>
                <component :is="currentScreen" :key="tab" :homestay="homestay" :user="store.user" @go="goTab" />
              </KeepAlive>
            </div>
            <TabBar v-model="tabbarModel" :badge="badgeCount" />
          </template>
        </div>

        <div class="phone-home" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import ScreenLogin from './ScreenLogin.vue'
import ScreenHome from './ScreenHome.vue'
import ScreenAssistant from './ScreenAssistant.vue'
import ScreenCreative from './ScreenCreative.vue'
import ScreenRectify from './ScreenRectify.vue'
import ScreenMine from './ScreenMine.vue'
import ScreenRag from './ScreenRag.vue'
import ScreenHistory from './ScreenHistory.vue'
import ScreenBankWarning from './ScreenBankWarning.vue'
import ScreenLoan from './ScreenLoan.vue'
import ScreenCreativeWorks from './ScreenCreativeWorks.vue'
import TabBar from '@/components/app/TabBar.vue'
import { store, bootstrap, pushInbox } from '@/store'
import { apiState } from '@/api'
import { bus } from '@/utils/bus'

const tab = ref('home')
const SUB_TITLES = { rag: 'RAG 系统', history: '历史报告', bankWarning: '银行预警记录', loan: '我的贷款', creativeWorks: 'AI 文创产物' }
const screens = {
  home: ScreenHome, assistant: ScreenAssistant, creative: ScreenCreative,
  rectify: ScreenRectify, mine: ScreenMine,
  rag: ScreenRag, history: ScreenHistory, bankWarning: ScreenBankWarning, loan: ScreenLoan,
  creativeWorks: ScreenCreativeWorks
}
const currentScreen = computed(() => screens[tab.value] || ScreenHome)
const screenKey = computed(() => (store.user ? tab.value : 'login'))
const isSub = computed(() => !!SUB_TITLES[tab.value])
const subTitle = computed(() => SUB_TITLES[tab.value] || '')
/** 子页面时底部导航仍高亮「我的」，符合“从我的进入”的层级认知 */
const tabbarModel = computed({ get: () => (isSub.value ? 'mine' : tab.value), set: (v) => { tab.value = v } })

const homestay = computed(() => {
  const id = store.user?.homestay_id
  return store.homestays.find((h) => h.id === id) || store.homestays[0] || null
})

const badgeCount = computed(() => store.inbox.filter((i) => !i.read).length)

const clock = ref('')
let timer = null
function tick() {
  const d = new Date()
  clock.value = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function goTab(t) { tab.value = t }

function onAuthed() {
  tab.value = 'home'
  // 登录后自动为老板推送一次「本店预警」，保证演示效果
  const mine = store.warnings.filter((w) => w.homestay_id === homestay.value?.id)
  if (mine.length && !store.inbox.length) {
    pushInbox({ type: 'warning', title: '贷后风险预警', content: mine[0].reason, at: Date.now(), source: '银行端' })
  }
}

/** 双屏联动：监听银行端推送 */
let offs = []
onMounted(async () => {
  tick(); timer = setInterval(tick, 20000)
  await bootstrap()

  offs.push(bus.on('warning:new', (payload) => {
    const mine = (payload?.created || []).filter((w) => w.homestay_id === homestay.value?.id)
    if (mine.length) {
      pushInbox({
        type: 'warning',
        title: '银行端触发贷后预警',
        content: mine.map((m) => `${m.rule_id} ${m.reason}`).join('\n'),
        suggestion: mine[0].suggestion,
        at: Date.now(),
        source: '客户经理'
      })
      tab.value = 'rectify'
    }
  }))

  offs.push(bus.on('report:rectify', (payload) => {
    if (payload?.homestay_id === homestay.value?.id) {
      pushInbox({
        type: 'report',
        title: '收到 AI 巡检整改建议',
        content: payload.homestay_name,
        suggestion: summarize(payload.content),
        at: Date.now(),
        source: '贷后风控中心'
      })
      tab.value = 'rectify'
    }
  }))
})

function summarize(md) {
  if (!md) return ''
  const m = String(md).match(/建议措施[\s\S]{0,320}/)
  return (m ? m[0] : String(md)).replace(/[#*]/g, '').slice(0, 260)
}

watch(() => store.inbox.length, () => { /* 触发响应式刷新 */ })

onBeforeUnmount(() => {
  clearInterval(timer)
  offs.forEach((off) => off && off())
})
</script>

<style scoped>
.stage {
  position: relative; min-height: 100vh; display: flex; align-items: center; justify-content: center;
  gap: 46px; padding: 40px 34px; overflow: hidden;
  background: linear-gradient(155deg, #eef2f9 0%, #e7ecf6 42%, #f4f0e8 100%);
}
.stage-bg {
  position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(22, 93, 255, .05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(22, 93, 255, .05) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 45%, #000 30%, transparent 100%);
}
.stage-glow { position: absolute; border-radius: 50%; filter: blur(100px); opacity: .5; }
.g1 { width: 460px; height: 460px; left: 4%; top: 6%; background: rgba(22, 93, 255, .35); }
.g2 { width: 400px; height: 400px; right: 6%; bottom: 4%; background: rgba(255, 184, 0, .35); }

/* 左说明 */
.stage-aside { position: relative; z-index: 2; width: 372px; flex: 0 0 372px; }
.back {
  display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 14px;
  border-radius: 9px; font-size: 12.5px; color: #4e5969;
  background: rgba(255, 255, 255, .7); border: 1px solid rgba(29, 33, 41, .08);
  box-shadow: 0 6px 18px -10px rgba(0, 0, 0, .25); transition: all .25s var(--ease-out);
}
.back:hover { color: #165dff; border-color: rgba(22, 93, 255, .3); transform: translateX(-2px); }

.sa-brand { display: flex; align-items: center; gap: 13px; margin-top: 26px; }
.sa-brand h2 { font-size: 23px; color: #1d2129; letter-spacing: .08em; }
.sa-brand p { font-size: 12.5px; color: #86909c; margin-top: 3px; }

.sa-points { margin-top: 24px; display: flex; flex-direction: column; gap: 12px; }
.sa-points li {
  position: relative; padding-left: 20px; font-size: 13px; color: #4e5969; line-height: 1.7;
}
.sa-points li::before {
  content: ""; position: absolute; left: 0; top: 8px; width: 7px; height: 7px; border-radius: 2px;
  background: linear-gradient(135deg, #165dff, #ffb800);
}
.sa-points b { color: #1d2129; font-weight: 700; margin-right: 6px; }

.sa-demo {
  margin-top: 26px; padding: 16px 18px; border-radius: 14px;
  background: rgba(255, 255, 255, .8); border: 1px solid rgba(22, 93, 255, .16);
  box-shadow: 0 16px 40px -26px rgba(22, 93, 255, .5);
}
.sd-title { font-size: 12px; font-weight: 700; color: #165dff; letter-spacing: .1em; }
.sd-row { display: flex; justify-content: space-between; font-size: 13px; color: #4e5969; margin-top: 9px; }
.sd-row em { font-style: normal; color: #1d2129; background: rgba(22, 93, 255, .08); padding: 0 9px; border-radius: 6px; }
.sd-tip { margin-top: 12px; font-size: 11.5px; color: #86909c; line-height: 1.75; }
.sd-tip b { color: #b06a00; }

.sa-status { display: inline-flex; align-items: center; gap: 8px; margin-top: 22px; font-size: 12px; color: #4e5969; }

/* 手机壳 */
.phone-wrap { position: relative; z-index: 2; }
.phone {
  position: relative; width: 392px; height: 812px;
  border-radius: 46px; padding: 12px;
  background: linear-gradient(160deg, #2a3142, #10141d 45%, #232a38);
  box-shadow: 0 50px 90px -40px rgba(10, 20, 40, .75), 0 0 0 1px rgba(255, 255, 255, .06) inset,
    0 2px 4px rgba(255, 255, 255, .18) inset;
}
.phone-bar {
  position: absolute; top: 22px; left: 0; right: 0; z-index: 20;
  display: flex; align-items: center; justify-content: space-between; padding: 0 26px;
  font-size: 12px; color: #1d2129; pointer-events: none;
}
.pb-island {
  position: absolute; left: 50%; top: -6px; transform: translateX(-50%);
  width: 104px; height: 26px; border-radius: 14px; background: #0b0e14;
}
.pb-icons { display: inline-flex; gap: 4px; align-items: center; }
.pb-icons i { display: block; background: #1d2129; border-radius: 1px; }
.sig { width: 11px; height: 8px; clip-path: polygon(0 100%, 25% 100%, 25% 60%, 0 60%, 0 100%, 33% 100%, 33% 40%, 58% 40%, 58% 100%, 66% 100%, 66% 20%, 91% 20%, 91% 100%, 100% 100%, 100% 0, 58% 0); }
.wifi { width: 11px; height: 8px; clip-path: polygon(50% 100%, 0 40%, 20% 22%, 50% 45%, 80% 22%, 100% 40%); }
.bat { width: 16px; height: 8px; border-radius: 2px; background: #1d2129; }

.phone-screen {
  position: relative; width: 100%; height: 100%; border-radius: 36px; overflow: hidden;
  background: #f7f8fa; display: flex; flex-direction: column;
}
.app-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; }
.app-fill { flex: 1; min-height: 0; display: flex; flex-direction: column; }

/* 子页面返回栏 */
.sub-bar {
  flex: 0 0 auto; display: flex; align-items: center; gap: 10px;
  padding: 46px 14px 10px;
  background: linear-gradient(160deg, #0e42c9, #165dff);
  color: #fff;
}
.sb-back {
  width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center;
  color: #fff; background: rgba(255, 255, 255, .18); border: 1px solid rgba(255, 255, 255, .28);
  transition: transform .2s var(--ease-out), background .2s;
}
.sb-back:hover { background: rgba(255, 255, 255, .3); transform: translateX(-2px); }
.sb-title { flex: 1; font-size: 15px; font-weight: 700; letter-spacing: .04em; }
.sb-tag { font-size: 10.5px; opacity: .85; padding: 2px 9px; border-radius: 999px; background: rgba(255, 255, 255, .16); }

.subslide-enter-active, .subslide-leave-active { transition: all .25s var(--ease-out); }
.subslide-enter-from, .subslide-leave-to { opacity: 0; transform: translateY(-8px); }

.phone-home { position: absolute; left: 50%; bottom: 20px; transform: translateX(-50%); width: 128px; height: 5px; border-radius: 3px; background: rgba(255, 255, 255, .55); }

@media (max-width: 1080px) {
  .stage { padding: 20px 12px; gap: 0; }
  .stage-aside { display: none; }
}
@media (max-width: 440px) {
  .phone { width: 100vw; height: 100vh; border-radius: 0; padding: 0; box-shadow: none; }
  .phone-screen { border-radius: 0; }
  .phone-home, .pb-island { display: none; }
  .phone-bar { padding: 0 16px; }
}
</style>
