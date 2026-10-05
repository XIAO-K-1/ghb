<template>
  <div class="mine">
    <!-- 个人头部 -->
    <header class="mn-head">
      <div class="mh-deco" />
      <div class="mh-profile">
        <div class="mp-avatar">{{ user?.name?.[0] || '老' }}</div>
        <div class="mp-info">
          <h2>{{ user?.name || '民宿经营者' }}</h2>
          <p>{{ homestay?.name || '未绑定民宿' }}</p>
          <span class="mp-phone num">{{ maskPhone(user?.phone) }}</span>
        </div>
      </div>
      <div class="mh-stats">
        <div class="ms-item"><b class="num">{{ money(hs.credit_limit) }}</b><span>授信额度</span></div>
        <div class="ms-item"><b class="num">{{ money(hs.available_credit) }}</b><span>可用额度</span></div>
        <div class="ms-item"><b class="num">{{ percent(hs.used_ratio, 0) }}</b><span>额度使用率</span></div>
      </div>
    </header>

    <!-- 豫游民宿贷 -->
    <section class="loan-card" role="button" tabindex="0" @click="$emit('go', 'loan')">
      <div class="lc-head">
        <span class="lc-badge">豫游民宿贷</span>
        <span class="lc-status">{{ RISK_TEXT[hs.risk_level] || '低风险' }}</span>
      </div>

      <div class="lc-main">
        <span class="lc-label">剩余未偿还本金</span>
        <div class="lc-value">
          <span class="num num-xl">{{ (hs.loan_balance || 0).toLocaleString('zh-CN') }}</span>
          <span class="lc-unit">元</span>
        </div>
      </div>

      <div class="lc-bar">
        <i :style="{ width: usedPct + '%' }" />
        <span class="lc-bar-label num">{{ usedPct }}%</span>
      </div>
      <div class="lc-meta">
        <span>已用 <b class="num">{{ money(hs.loan_used) }}</b></span>
        <span>总额度 <b class="num">{{ money(hs.credit_limit) }}</b></span>
      </div>

      <div class="lc-grid">
        <div class="lc-item"><span>下期还款日</span><b class="num">{{ hs.next_repayment_date || '—' }}</b></div>
        <div class="lc-item"><span>月还款额</span><b class="num">{{ thousands(hs.monthly_repayment) }} 元</b></div>
        <div class="lc-item"><span>还款日约定</span><b>{{ hs.repayment_day || '—' }}</b></div>
        <div class="lc-item"><span>执行利率</span><b class="num">3.45%</b></div>
      </div>

      <div class="lc-more">
        <span>查看贷款详情 · 还款计划 · 联系客户经理</span>
        <span class="lc-arrow">›</span>
      </div>
    </section>

    <!-- 还款压力智能预警 -->
    <section class="card">
      <div class="cc-head">
        <h4>还款压力智能预警</h4>
        <span class="ai-tag">AI 评估</span>
      </div>
      <div class="pressure" :class="pressure.tone">
        <div class="pr-ring" :style="{ '--p': pressure.score, '--c': pressure.color }">
          <span class="num">{{ pressure.score }}</span>
        </div>
        <div class="pr-body">
          <b>{{ pressure.label }}</b>
          <p>{{ pressure.desc }}</p>
        </div>
      </div>
      <ul class="pr-signs">
        <li v-for="s in pressure.signs" :key="s.k">
          <span class="ps-k">{{ s.k }}</span>
          <span class="ps-v num" :class="s.ok ? 'ok' : 'warn'">{{ s.v }}</span>
        </li>
      </ul>
    </section>

    <!-- 贷后经营改善记录 -->
    <section class="card">
      <div class="cc-head">
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

    <!-- 导向栏 -->
    <section class="menu">
      <button v-for="m in menus" :key="m.key" class="menu-item" @click="onMenu(m)">
        <span class="mi-ico" :class="'mi-' + m.tone" v-html="m.icon" />
        <span class="mi-main">
          <span class="mi-label">{{ m.label }}</span>
          <span v-if="m.desc" class="mi-desc">{{ m.desc }}</span>
        </span>
        <span v-if="m.badge" class="mi-badge num">{{ m.badge }}</span>
        <span class="mi-arrow">›</span>
      </button>
    </section>

    <button class="logout" @click="logout">退出登录</button>

    <p class="mn-note">豫宿巡 · 老板端 v1.0 · 经营数据经授权后由工行脱敏接口提供</p>

    <transition name="toast">
      <div v-if="tip" class="tip">{{ tip }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { store, persistUser, clearInbox } from '@/store'
import { money, thousands, percent, RISK_TEXT } from '@/utils/format'

const props = defineProps({ homestay: Object, user: Object })
const emit = defineEmits(['go'])

const hs = computed(() => props.homestay || {})

const usedPct = computed(() => Math.round((hs.value.used_ratio ?? 0) * 100))

const cover = computed(() => {
  const rev = hs.value.monthly_revenue || 0
  const pay = hs.value.monthly_repayment || 0
  return pay > 0 ? rev / pay : 0
})

const pressure = computed(() => {
  const used = hs.value.used_ratio ?? 0
  const c = cover.value
  const signs = [
    { k: '额度使用率', v: percent(used, 0), ok: used < 0.9 },
    { k: '营收 / 月还款', v: `${c.toFixed(1)} 倍`, ok: c >= 2.5 },
    { k: 'OTA 评分', v: (hs.value.ota_score ?? 0).toFixed(1), ok: (hs.value.ota_score ?? 0) >= 4.0 },
    { k: '近期流水', v: `-${Math.round((hs.value.flow_drop_30d ?? 0) * 100)}%`, ok: (hs.value.flow_drop_30d ?? 0) < 0.2 }
  ]

  if (used >= 0.9 || c < 1.5) {
    return {
      tone: 'high', score: 84, color: '#f53f3f',
      label: '还款压力偏高',
      desc: `额度使用率 ${percent(used, 0)}，月营收仅覆盖月还款 ${c.toFixed(1)} 倍，建议暂缓新增支用并优先安排回款。`,
      signs
    }
  }
  if (used >= 0.7 || c < 2.5) {
    return {
      tone: 'mid', score: 56, color: '#ff7d00',
      label: '还款压力中等',
      desc: `经营基本稳健，额度使用率 ${percent(used, 0)}，建议保持 2 倍以上营收覆盖以留足安全垫。`,
      signs
    }
  }
  return {
    tone: 'low', score: 22, color: '#00b42a',
    label: '还款压力较低',
    desc: `额度充裕、现金流健康，月营收可覆盖月还款 ${c.toFixed(1)} 倍，可结合旺季适度扩产。`,
    signs
  }
})

const improves = [
  { title: '差评回复率提升', value: '+35%', desc: 'AI 生成差评回复模板，近 7 日差评实现当日回复' },
  { title: 'OTA 页面优化', value: '评分 +0.2', desc: '依据 OTA 运营指南优化房源标题与首图顺序' },
  { title: '文创引流获客', value: '加微 60+', desc: 'AI 生成古都主题文创图赠客，带动社交平台自然曝光' }
]

const warnCount = computed(() =>
  store.warnings.filter((w) => w.homestay_id === hs.value.id && w.status !== 'closed').length
)

const menus = computed(() => [
  {
    key: 'rag', label: 'RAG 系统', desc: '查看与管理 AI 检索文档库', tone: 'blue',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="6" rx="7.5" ry="3"/><path d="M4.5 6v12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6"/><path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/></svg>'
  },
  {
    key: 'history', label: '历史报告', desc: 'AI 贷后巡检报告存档', tone: 'gold',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></svg>'
  },
  {
    key: 'bankWarning', label: '银行预警记录', desc: '银行端下发的贷后预警', tone: 'red',
    badge: warnCount.value,
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>'
  },
  {
    key: 'loan', label: '我的贷款', desc: '额度、还款计划与经理沟通', tone: 'green',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="6" width="18" height="13" rx="2.6"/><path d="M3 10h18M7 15h4"/></svg>'
  },
  {
    key: 'creativeWorks', label: 'AI 文创产物', desc: '本店生成的作品存档，仅自己可见', tone: 'purple',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4l1.6 3.4L19 9l-3.4 1.6L14 14l-1.6-3.4L9 9l3.4-1.6z"/><path d="M6 18l-2.5 2.5M9.5 15.5l-1.8 1.8"/></svg>'
  },
  {
    key: 'pwd', label: '修改登录密码', tone: 'gray',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="10" rx="2.4"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>'
  },
  {
    key: 'about', label: '关于豫宿巡', tone: 'gray',
    icon: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.6h.01"/></svg>'
  }
])

const tip = ref('')
let tipTimer = null
function showTip(msg) {
  tip.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { tip.value = '' }, 1900)
}

function onMenu(m) {
  if (m.key === 'rag' || m.key === 'history' || m.key === 'bankWarning' || m.key === 'loan' || m.key === 'creativeWorks') {
    emit('go', m.key)
    return
  }
  if (m.key === 'pwd') {
    showTip('演示环境：修改密码功能请联系客户经理')
    return
  }
  showTip('豫宿巡 v1.0 · 贷后风控与经营赋能，不做预订 / 支付 / 客服')
}

function logout() {
  persistUser(null)
  clearInbox()
}

function maskPhone(p) {
  if (!p) return '—'
  const s = String(p)
  return s.length >= 11 ? `${s.slice(0, 3)}****${s.slice(-4)}` : s
}
</script>

<style scoped>
.mine { padding-bottom: 24px; }

/* Header */
.mn-head {
  position: relative; padding: 40px 20px 26px; overflow: hidden;
  background: linear-gradient(150deg, #0e42c9 0%, #165dff 46%, #ffb800 155%);
  border-radius: 0 0 26px 26px; color: #fff;
}
.mh-deco {
  position: absolute; inset: 0; opacity: .22;
  background-image: radial-gradient(rgba(255, 255, 255, .6) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(ellipse 70% 70% at 88% 4%, #000, transparent 74%);
}
.mh-profile { position: relative; display: flex; align-items: center; gap: 14px; }
.mp-avatar {
  width: 56px; height: 56px; border-radius: 18px; display: grid; place-items: center;
  font-size: 22px; font-weight: 700; background: rgba(255, 255, 255, .22);
  border: 1px solid rgba(255, 255, 255, .38); backdrop-filter: blur(6px);
}
.mp-info h2 { font-size: 19px; font-weight: 700; letter-spacing: .03em; }
.mp-info p { font-size: 12px; opacity: .92; margin-top: 3px; }
.mp-phone {
  display: inline-block; margin-top: 7px; font-size: 11px; padding: 1px 9px; border-radius: 999px;
  background: rgba(255, 255, 255, .18); border: 1px solid rgba(255, 255, 255, .3);
}
.mh-stats { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 18px; }
.ms-item {
  padding: 9px 6px; border-radius: 13px; text-align: center;
  background: rgba(255, 255, 255, .15); border: 1px solid rgba(255, 255, 255, .25);
  backdrop-filter: blur(8px);
}
.ms-item b { display: block; font-size: 17px; line-height: 1.2; }
.ms-item span { font-size: 10.5px; opacity: .9; }

/* 贷款卡 */
.loan-card {
  position: relative; margin: -14px 14px 0; padding: 18px 17px 16px; border-radius: 20px; overflow: hidden;
  background: linear-gradient(150deg, #10233f 0%, #0a192f 58%, #14315c 100%);
  color: #eaf2ff; box-shadow: 0 26px 50px -30px rgba(10, 25, 47, .95);
  border: 1px solid rgba(255, 184, 0, .22);
}
.loan-card::after {
  content: ""; position: absolute; right: -40px; top: -40px; width: 150px; height: 150px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 184, 0, .3), transparent 68%);
}
.lc-head { position: relative; display: flex; align-items: center; justify-content: space-between; }
.lc-badge {
  font-size: 11.5px; font-weight: 700; letter-spacing: .1em; color: #2a1c00;
  padding: 3px 11px; border-radius: 999px;
  background: linear-gradient(135deg, #ffcd4d, #ffb800);
}
.lc-status { font-size: 11.5px; color: #ffd666; }
.lc-main { position: relative; margin-top: 16px; }
.lc-label { font-size: 11.5px; color: #a9bcd9; }
.lc-value { display: flex; align-items: baseline; gap: 6px; margin-top: 5px; }
.lc-value .num { color: #fff; letter-spacing: .01em; }
.lc-unit { font-size: 12px; color: #a9bcd9; }

.lc-bar { position: relative; height: 8px; margin-top: 16px; border-radius: 5px; background: rgba(255, 255, 255, .12); }
.lc-bar i {
  display: block; height: 100%; border-radius: 5px;
  background: linear-gradient(90deg, #ffcd4d, #ffb800);
  box-shadow: 0 0 14px rgba(255, 184, 0, .6);
  transition: width .9s var(--ease-out);
}
.lc-bar-label { position: absolute; right: 0; top: -20px; font-size: 11px; color: #ffd666; }
.lc-meta { display: flex; justify-content: space-between; margin-top: 9px; font-size: 11px; color: #a9bcd9; }
.lc-meta b { color: #fff; }

.lc-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; padding-top: 14px;
  border-top: 1px solid rgba(96, 150, 255, .18);
}
.lc-item { display: flex; flex-direction: column; gap: 3px; }
.lc-item span { font-size: 10.5px; color: #6d82a6; }
.lc-item b { font-size: 13px; color: #eaf2ff; }

.loan-card { cursor: pointer; transition: transform .25s var(--ease-out), box-shadow .25s; }
.loan-card:active { transform: scale(.99); }
.lc-more {
  position: relative; display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-top: 14px; padding-top: 12px;
  border-top: 1px dashed rgba(96, 150, 255, .22);
  font-size: 11px; color: #9fb6da;
}
.lc-arrow { font-size: 17px; color: #ffd666; line-height: 1; }

/* 卡片 */
.card {
  margin: 14px 14px 0; padding: 15px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.cc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.cc-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.ai-tag { font-size: 10.5px; font-weight: 700; color: #165dff; padding: 2px 9px; border-radius: 999px; background: rgba(22, 93, 255, .09); }

/* 压力评估 */
.pressure {
  display: flex; align-items: center; gap: 14px; padding: 13px 14px; border-radius: 14px;
  background: color-mix(in srgb, var(--pc) 8%, #fff);
  border: 1px solid color-mix(in srgb, var(--pc) 24%, transparent);
}
.pressure.high { --pc: #f53f3f; }
.pressure.mid { --pc: #ff7d00; }
.pressure.low { --pc: #00b42a; }
.pr-ring {
  width: 62px; height: 62px; flex: 0 0 62px; border-radius: 50%; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), #eef1f6 0);
  position: relative;
}
.pr-ring::before { content: ""; position: absolute; inset: 7px; border-radius: 50%; background: #fff; }
.pr-ring span { position: relative; font-size: 19px; color: var(--c); }
.pr-body b { font-size: 14px; color: #1d2129; }
.pr-body p { font-size: 11.5px; color: #4e5969; line-height: 1.65; margin-top: 5px; }

.pr-signs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.pr-signs li {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 8px 11px; border-radius: 11px; background: #f7f8fa;
}
.ps-k { font-size: 11px; color: #86909c; }
.ps-v { font-size: 12px; }
.ps-v.ok { color: #00b42a; }
.ps-v.warn { color: #f53f3f; }

/* 改善记录 */
.imp-list { display: flex; flex-direction: column; }
.imp-item { display: flex; gap: 11px; padding: 11px 0; border-bottom: 1px solid rgba(29, 33, 41, .06); }
.imp-item:last-child { border-bottom: 0; padding-bottom: 2px; }
.imp-dot { width: 7px; height: 7px; margin-top: 6px; border-radius: 50%; flex: 0 0 7px; background: linear-gradient(135deg, #165dff, #ffb800); }
.imp-body { flex: 1; }
.imp-top { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.imp-top b { font-size: 13px; color: #1d2129; }
.imp-val { font-size: 13.5px; color: #165dff; }
.imp-body p { font-size: 11.5px; color: #86909c; line-height: 1.7; margin-top: 4px; }

/* 菜单 */
.menu {
  margin: 14px 14px 0; border-radius: 16px; background: #fff; overflow: hidden;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.menu-item {
  display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px 15px; text-align: left;
  border-bottom: 1px solid rgba(29, 33, 41, .06); transition: background .2s;
}
.menu-item:last-child { border-bottom: 0; }
.menu-item:hover { background: #f7f8fa; }
.mi-ico { width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; flex: 0 0 30px; }
.mi-blue { color: #165dff; background: rgba(22, 93, 255, .1); }
.mi-gold { color: #c98a00; background: rgba(255, 184, 0, .16); }
.mi-red { color: #f53f3f; background: rgba(245, 63, 63, .1); }
.mi-green { color: #00a844; background: rgba(0, 180, 42, .1); }
.mi-purple { color: #722ed1; background: rgba(114, 46, 209, .1); }
.mi-gray { color: #4e5969; background: #f2f3f5; }
.mi-main { flex: 1; display: flex; flex-direction: column; gap: 3px; text-align: left; }
.mi-label { font-size: 13.5px; color: #1d2129; }
.mi-desc { font-size: 10.5px; color: #a9b0bd; }
.mi-badge {
  min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; margin-right: 2px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10.5px; color: #fff; background: #f53f3f;
}
.mi-arrow { font-size: 18px; color: #c9ced6; line-height: 1; }

.logout {
  display: block; width: calc(100% - 28px); margin: 18px 14px 0; height: 46px; border-radius: 14px;
  font-size: 14px; font-weight: 600; color: #f53f3f; background: #fff;
  border: 1px solid rgba(245, 63, 63, .22); transition: background .2s, transform .2s;
}
.logout:hover { background: rgba(245, 63, 63, .06); }
.logout:active { transform: scale(.99); }

.mn-note { margin: 16px 16px 0; font-size: 10.5px; color: #a9b0bd; line-height: 1.75; text-align: center; }

/* toast */
.tip {
  position: sticky; bottom: 12px; margin: 14px 20px 0; padding: 10px 14px; border-radius: 12px;
  font-size: 12px; color: #fff; background: rgba(29, 33, 41, .9); text-align: center;
  box-shadow: 0 14px 30px -18px rgba(0, 0, 0, .6);
}
.toast-enter-active, .toast-leave-active { transition: all .28s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
