<template>
  <div class="entry theme-bank">
    <!-- 背景氛围层 -->
    <div class="bg-grid" />
    <div class="bg-glow g1" />
    <div class="bg-glow g2" />
    <div class="bg-scan" />

    <div class="entry-inner">
      <!-- 顶部品牌 -->
      <header class="brand rise-in">
        <div class="brand-mark">
          <svg viewBox="0 0 48 48" width="46" height="46" aria-hidden="true">
            <defs>
              <linearGradient id="g-brand" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#4B83FF" />
                <stop offset="100%" stop-color="#165DFF" />
              </linearGradient>
            </defs>
            <path d="M24 3 43 13v22L24 45 5 35V13z" fill="none" stroke="url(#g-brand)" stroke-width="2" />
            <path d="M15 30c0-6 4-10 9-10s9 4 9 10" fill="none" stroke="#FFB800" stroke-width="2.2" stroke-linecap="round" />
            <circle cx="24" cy="16" r="3.2" fill="#FFB800" />
            <path d="M17 34h14" stroke="#4B83FF" stroke-width="2.2" stroke-linecap="round" />
          </svg>
        </div>
        <div class="brand-text">
          <h1 class="title-serif">豫宿巡</h1>
          <p class="brand-en">YUSUXUN · POST-LOAN RISK CONTROL</p>
        </div>
        <div class="seal brand-seal">中原智巡</div>
      </header>

      <!-- 价值主张 -->
      <section class="hero">
        <p class="hero-kicker rise-in" style="animation-delay: .08s">
          <span class="dot" style="--risk: #00B42A" /> 基于 AI 大模型与 RAG 的古都民宿贷后赋能与风控系统
        </p>
        <h2 class="hero-title rise-in" style="animation-delay: .14s">
          银行贷了钱之后，<span class="hl">怎么办？</span>
        </h2>
        <p class="hero-sub rise-in" style="animation-delay: .2s">
          构建「一后台 · 一App · 一引擎」，打通
          <b>数据采集 → AI分析 → 贷后预警 → 经营赋能 → 风险改善</b> 的完整闭环
        </p>
        <div class="hero-slogan rise-in" style="animation-delay: .26s">
          <span class="slogan-a">让工行贷得放心</span>
          <span class="slogan-sep">·</span>
          <span class="slogan-b">让民宿赚得安心</span>
        </div>
      </section>

      <!-- 双端入口 -->
      <section class="entries">
        <button class="entry-card bank rise-in" style="animation-delay: .32s" @click="go('/bank')">
          <div class="ec-tag">
            <span class="dot" style="--risk: #F53F3F" /> WEB 后台
          </div>
          <h3 class="title-serif">贷后风控指挥舱</h3>
          <p class="ec-desc">面向工行客户经理 · 全局风险态势感知</p>
          <ul class="ec-list">
            <li>贷后驾驶舱 · 今日待办</li>
            <li>地图脉冲预警 · 风险分级</li>
            <li>AI 巡检报告 · 数字档案</li>
          </ul>
          <span class="ec-go">
            进入指挥舱
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </button>

        <button class="entry-card app rise-in" style="animation-delay: .4s" @click="go('/app')">
          <div class="ec-tag app-tag">
            <span class="dot" style="--risk: #165DFF" /> 移动 App
          </div>
          <h3 class="title-serif">AI 经营助手</h3>
          <p class="ec-desc">面向民宿老板 · 随身经营赋能</p>
          <ul class="ec-list app-list">
            <li>经营概览 · 风险提醒</li>
            <li>RAG 智能问答 · 来源可溯</li>
            <li>AI 文创生图 · 引流获客</li>
          </ul>
          <span class="ec-go app-go">
            进入 App
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </button>
      </section>

      <!-- 底部：数据来源与合规 -->
      <footer class="entry-foot rise-in" style="animation-delay: .48s">
        <div class="cities">
          <span v-for="c in cities" :key="c" class="city">{{ c }}</span>
        </div>
        <p class="compliance">
          本系统采用<b>合规沙盒数据</b>演示：经营数据经客户授权后通过 PMS 系统 API 或工行脱敏账户流水接口获取；
          舆情数据仅采集公开可访问页面，遵守 robots.txt，仅用于学术研究。AI 生成内容已按《人工智能生成合成内容标识办法》添加标识。
        </p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const go = (p) => router.push(p)
const cities = ['洛阳 · 老城', '洛阳 · 栾川', '开封 · 鼓楼', '安阳 · 林州']
</script>

<style scoped>
.entry {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: radial-gradient(1200px 700px at 12% -10%, #12305e 0%, transparent 55%),
    radial-gradient(900px 600px at 92% 8%, #1b2a4d 0%, transparent 52%),
    linear-gradient(180deg, #050b16, #071427 55%, #050b16);
}

/* ---------- 背景 ---------- */
.bg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(96, 150, 255, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(96, 150, 255, 0.055) 1px, transparent 1px);
  background-size: 54px 54px;
  mask-image: radial-gradient(ellipse 90% 70% at 50% 40%, #000 35%, transparent 100%);
}
.bg-glow { position: absolute; border-radius: 50%; filter: blur(90px); opacity: .5; }
.g1 { width: 420px; height: 420px; left: -90px; top: 8%; background: #165dff; animation: float-y 9s ease-in-out infinite; }
.g2 { width: 380px; height: 380px; right: -80px; bottom: 6%; background: #7a4a00; animation: float-y 11s ease-in-out infinite reverse; }
.bg-scan {
  position: absolute; left: 0; right: 0; height: 180px;
  background: linear-gradient(180deg, transparent, rgba(70, 140, 255, .07), transparent);
  animation: scan-line 12s linear infinite;
}

.entry-inner {
  position: relative;
  z-index: 2;
  max-width: 1180px;
  margin: 0 auto;
  padding: 46px 32px 40px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ---------- 品牌 ---------- */
.brand { display: flex; align-items: center; gap: 16px; }
.brand-mark { filter: drop-shadow(0 0 18px rgba(22, 93, 255, .55)); }
.brand-text { flex: 1; }
.brand-text h1 { font-size: 34px; line-height: 1.1; letter-spacing: .1em; color: #fff; }
.brand-en { font-family: var(--font-num); font-size: 11px; letter-spacing: .3em; color: var(--text-3); margin-top: 4px; }
.brand-seal { transform: rotate(-3deg); }

/* ---------- Hero ---------- */
.hero { margin-top: 52px; }
.hero-kicker {
  display: inline-flex; align-items: center; gap: 9px;
  font-size: 13px; color: var(--text-2);
  padding: 7px 16px; border-radius: 999px;
  border: 1px solid var(--line); background: rgba(22, 93, 255, .09);
}
.hero-title {
  margin-top: 22px;
  font-family: var(--font-serif);
  font-size: clamp(38px, 5.4vw, 68px);
  line-height: 1.14; font-weight: 900; letter-spacing: .02em;
  color: #fff;
}
.hero-title .hl {
  background: linear-gradient(100deg, #4b83ff, #ffb800);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { margin-top: 18px; max-width: 680px; font-size: 16px; color: var(--text-2); }
.hero-sub b { color: #cfe0ff; font-weight: 600; }
.hero-slogan { margin-top: 20px; display: flex; align-items: center; gap: 14px; font-family: var(--font-serif); font-size: 20px; }
.slogan-a { color: #9fc0ff; }
.slogan-b { color: var(--brand-gold); }
.slogan-sep { color: var(--text-3); }

/* ---------- 入口卡片 ---------- */
.entries { margin-top: 46px; display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
.entry-card {
  position: relative;
  text-align: left;
  padding: 26px 26px 22px;
  border-radius: var(--r-lg);
  border: 1px solid var(--line);
  background: linear-gradient(155deg, rgba(23, 45, 80, .8), rgba(8, 20, 38, .78));
  backdrop-filter: blur(12px);
  overflow: hidden;
  transition: transform .38s var(--ease-out), border-color .38s, box-shadow .38s;
}
.entry-card::before {
  content: ""; position: absolute; inset: 0;
  background: radial-gradient(420px 200px at 100% 0%, rgba(22, 93, 255, .22), transparent 70%);
  opacity: 0; transition: opacity .4s;
}
.entry-card.app::before { background: radial-gradient(420px 200px at 100% 0%, rgba(255, 184, 0, .2), transparent 70%); }
.entry-card:hover { transform: translateY(-6px); border-color: var(--line-strong); box-shadow: 0 30px 60px -30px rgba(0, 0, 0, .9); }
.entry-card:hover::before { opacity: 1; }
.entry-card.app { background: linear-gradient(155deg, rgba(46, 41, 30, .55), rgba(8, 20, 38, .78)); }

.ec-tag { display: inline-flex; align-items: center; gap: 8px; font-family: var(--font-num); font-size: 11px; letter-spacing: .22em; color: var(--text-3); }
.ec-tag .dot { animation: soft-pulse 1.8s ease-in-out infinite; }
.ec-tag.app-tag .dot { animation: pulse-ring 2.2s ease-out infinite; }
.entry-card h3 { margin-top: 14px; font-size: 26px; color: #fff; letter-spacing: .06em; }
.ec-desc { margin-top: 8px; color: var(--text-2); font-size: 14px; }
.ec-list { margin-top: 18px; display: flex; flex-direction: column; gap: 9px; }
.ec-list li { position: relative; padding-left: 18px; font-size: 13.5px; color: #bcd0ee; }
.ec-list li::before {
  content: ""; position: absolute; left: 0; top: 8px;
  width: 6px; height: 6px; border-radius: 2px; background: var(--brand-blue); box-shadow: 0 0 8px var(--accent-glow);
}
.app-list li::before { background: var(--brand-gold); box-shadow: 0 0 8px rgba(255, 184, 0, .6); }
.ec-go {
  margin-top: 22px; display: inline-flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: var(--brand-blue-400);
}
.app-go { color: var(--brand-gold); }
.entry-card:hover .ec-go svg { transform: translateX(4px); }
.ec-go svg { transition: transform .3s var(--ease-out); }

/* ---------- 底部 ---------- */
.entry-foot { margin-top: auto; padding-top: 40px; }
.cities { display: flex; gap: 10px; flex-wrap: wrap; }
.city {
  font-size: 12px; color: var(--text-2); padding: 5px 13px;
  border: 1px solid var(--line); border-radius: 999px;
  background: rgba(255, 255, 255, .02);
}
.compliance { margin-top: 16px; font-size: 12px; line-height: 1.9; color: var(--text-3); max-width: 900px; }
.compliance b { color: var(--text-2); }

@media (max-width: 880px) {
  .entries { grid-template-columns: 1fr; }
  .entry-inner { padding: 30px 20px; }
  .brand-text h1 { font-size: 26px; }
  .hero { margin-top: 34px; }
}
</style>
