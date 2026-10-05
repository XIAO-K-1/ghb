<template>
  <div class="models">
    <!-- ========== 顶部：说明 + 环境兜底状态 + 保存 ========== -->
    <section class="head glass">
      <div class="h-left">
        <h3 class="title-serif">AI 模型配置中心</h3>
        <p>按业务场景分别指定大模型提供方、模型名称与 API Key，保存后即时生效（无需重启服务）。保存后请点击「测试连接」确认真实可调用。</p>
      </div>
      <div class="h-right">
        <span class="env-chip" :class="{ on: env.dashscope }">
          <i class="dot" :class="env.dashscope ? 'ok' : 'off'" />DASHSCOPE_API_KEY
        </span>
        <span class="env-chip" :class="{ on: env.deepseek }">
          <i class="dot" :class="env.deepseek ? 'ok' : 'off'" />DEEPSEEK_API_KEY
        </span>
        <button class="btn btn-primary" :disabled="saving || loading" @click="save">
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
      </div>
    </section>

    <!-- ========== 场景总览 ========== -->
    <section class="overview stagger">
      <div v-for="s in scenes" :key="s.key" class="ov-card glass" :class="s.configured ? 'ok' : 'off'">
        <div class="ov-co">
          <span class="ov-name">{{ s.name }}</span>
          <span class="ov-state">{{ s.configured ? '已启用' : '离线兜底' }}</span>
        </div>
        <b class="ov-model">{{ s.configured ? (s.model || s.active_provider) : '未配置大模型' }}</b>
        <span class="ov-prov">{{ providerLabel(s.active_provider) }}</span>
      </div>
    </section>

    <!-- ========== 各场景配置 ========== -->
    <section class="grid" v-if="!loading">
      <article v-for="s in scenes" :key="s.key" class="scene glass" :class="{ bad: s.last_error }">
        <header class="sc-head">
          <span class="sc-ico" v-html="s.type === 'image' ? icoImage : icoSpark" />
          <div class="sc-title">
            <h4>{{ s.name }}</h4>
            <p>{{ s.desc }}</p>
          </div>
          <span class="sc-badge" :class="badgeOf(s)">{{ badgeText(s) }}</span>
        </header>

        <div class="sc-body">
          <label class="field">
            <span>模型提供方</span>
            <select v-model="form[s.key].provider" @change="onProvider(s.key)">
              <option value="auto">自动（跟随环境变量兜底）</option>
              <option v-for="p in s.providers || []" :key="p.key" :value="p.key">{{ p.label }}</option>
            </select>
          </label>

          <div class="field-row">
            <label class="field">
              <span class="fld-top">
                <i>模型名称</i>
                <button
                  v-if="canList(s)" class="lnk" :disabled="listing === s.key" @click="fetchModels(s.key)"
                >{{ listing === s.key ? '获取中…' : '获取可用模型' }}</button>
              </span>
              <input v-model="form[s.key].model" type="text" :placeholder="modelHint(s)" />
            </label>
            <label class="field">
              <span>API Key</span>
              <input
                v-model="form[s.key].api_key" type="password" autocomplete="new-password"
                :placeholder="s.api_key_masked ? `已配置 ${s.api_key_masked}（留空沿用）` : '粘贴 API Key'"
              />
            </label>
          </div>

          <!-- 从官方「模型列表」接口拉回的真实可选模型，点选即填入，避免手写模型名过期 -->
          <div v-if="modelOptions[s.key]" class="md-box">
            <template v-if="modelOptions[s.key].list.length">
              <span class="md-label">官方可用模型（点选填入）：</span>
              <div class="md-chips">
                <button
                  v-for="m in modelOptions[s.key].list" :key="m" class="md-chip"
                  :class="{ on: form[s.key].model === m }" @click="form[s.key].model = m"
                >{{ m }}</button>
              </div>
            </template>
            <span v-else class="md-msg">{{ modelOptions[s.key].message }}</span>
          </div>

          <label class="field">
            <span>接口地址 Base URL</span>
            <input v-model="form[s.key].base_url" type="text" :placeholder="urlHint(s)" />
          </label>
        </div>

        <!-- 上次调用失败的真实原因（避免「看着已生效、实际静默降级」） -->
        <div v-if="s.last_error" class="sc-err">
          <b>上次调用失败 · {{ s.last_error.at }}</b>
          <span>{{ s.last_error.message }}</span>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResult[s.key]" class="sc-test" :class="testResult[s.key].ok ? 'ok' : 'bad'">
          <b>{{ testResult[s.key].ok ? '✅ 连接成功' : '❌ 连接失败' }}</b>
          <span>{{ testResult[s.key].message }}</span>
        </div>

        <footer class="sc-foot">
          <span class="sc-tip">{{ tipText(s.key) }}</span>
          <button class="btn-mini" :disabled="testing === s.key" @click="test(s.key)">
            {{ testing === s.key ? '测试中…' : '测试连接' }}
          </button>
        </footer>
      </article>
    </section>

    <div v-else class="loading glass"><div class="spin" />正在读取模型配置…</div>

    <p class="note">
      配置优先级：<b>场景运行期配置</b> ＞ 环境变量 <b>DASHSCOPE_API_KEY</b> ＞ <b>DEEPSEEK_API_KEY</b> ＞ 离线兜底。
      未配置 Key 或调用失败时系统自动降级为知识库 / 模板答复，演示不中断；失败原因会显示在对应场景卡片上，便于定位。
      API Key 仅保存在本机运行时配置中，页面只展示脱敏结果。
    </p>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/api'

const loading = ref(true)
const saving = ref(false)
const testing = ref('')
const listing = ref('')
const toast = ref('')
let toastTimer = null

const scenes = ref([])
const providers = ref([])
const env = reactive({ dashscope: false, deepseek: false })
const form = reactive({})
const testResult = reactive({})
const modelOptions = reactive({})

const icoSpark = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.8 2.8M14.9 14.9l2.8 2.8M17.7 6.3l-2.8 2.8M9.1 14.9l-2.8 2.8"/><circle cx="12" cy="12" r="2.6"/></svg>'
const icoImage = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.6" cy="8.6" r="1.7"/><path d="m4 17 5-5 4 4 3-3 4 4"/></svg>'

const TIPS = {
  chat: '老板端 RAG 问答与经营建议使用该模型；未配置时改用本地知识库检索答复。',
  report: '生成贷后巡检报告正文，影响报告的措辞与专业度。',
  warning: '依据评分、评论、AI 对话记录自动生成预警文案。',
  copywriting: '为民宿生成小红书 / 抖音风格宣传文案。',
  image: '老板端「AI 文创」生图使用该模型。通义万相填 DashScope 生图地址；其他平台填 OpenAI 兼容的 /images/generations 地址。'
}
const tipText = (k) => TIPS[k] || ''

const MODEL_HINTS = {
  chat: '如 qwen3.8-max / deepseek-flash',
  image: '如 wanx2.1-t2i-turbo / qwen-image-max'
}
const URL_HINTS = {
  image: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'
}

/** 模型名占位提示：优先用所选提供方的官方命名示例 */
function modelHint(s) {
  const p = (s.providers || []).find((x) => x.key === form[s.key]?.provider)
  return p?.models_hint || MODEL_HINTS[s.key] || '请填写官方文档中的真实模型名'
}
const urlHint = (s) => URL_HINTS[s.key] || '选择提供方后自动填入官方地址，可手动覆盖'

/** 当前提供方是否支持从官方接口拉取模型列表 */
function canList(s) {
  const p = (s.providers || []).find((x) => x.key === form[s.key]?.provider)
  return !!p?.can_list_models
}

/**
 * 拉取官方「模型列表」。
 * 模型名会随官方版本迭代变化（DeepSeek 现为 deepseek-flash / deepseek-v4-pro，
 * 千问侧有 qwen-max-latest / qwen3-max 等），因此这里实时查询，避免手写过期导致 404。
 */
async function fetchModels(key) {
  if (listing.value) return
  listing.value = key
  try {
    const data = await api.availableModels(key, '')
    modelOptions[key] = { list: data?.models || [], message: data?.message || '未获取到模型' }
    if (!data?.ok) show(data?.message || '获取模型列表失败')
  } catch (e) {
    modelOptions[key] = { list: [], message: e?.message || '获取模型列表失败' }
    show(e?.message || '获取模型列表失败')
  } finally {
    listing.value = ''
  }
}

/** 状态徽标：调用失败 > 已生效 > 未配置 */
function badgeText(s) {
  if (s.last_error) return '配置异常'
  return s.configured ? '生效中' : '未配置'
}
function badgeOf(s) {
  if (s.last_error) return 'bad'
  return s.configured ? 'ok' : 'off'
}

function providerLabel(key) {
  const all = [...providers.value, ...scenes.value.flatMap((s) => s.providers || [])]
  const p = all.find((x) => x.key === key)
  if (p) return p.label
  if (key === 'auto') return '自动（环境变量兜底）'
  return '离线兜底'
}

function applyPreset(key) {
  const f = form[key]
  const s = scenes.value.find((x) => x.key === key)
  const preset = (s?.providers || providers.value).find((p) => p.key === f.provider)
  if (preset) {
    f.model = preset.model || f.model
    f.base_url = preset.base_url || f.base_url
  }
  if (f.provider === 'offline') {
    f.model = ''
    f.base_url = ''
    f.api_key = ''
  }
  // 切换提供方后，上一家拉取的模型列表不再适用
  delete modelOptions[key]
}

function onProvider(key) {
  applyPreset(key)
}

async function load() {
  loading.value = true
  try {
    const data = await api.models()
    providers.value = data?.providers || []
    applyScenes(data)
  } catch (e) {
    show(e?.message || '模型配置读取失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = {}
    Object.keys(form).forEach((k) => {
      payload[k] = {
        provider: form[k].provider,
        model: form[k].model,
        base_url: form[k].base_url,
        api_key: form[k].api_key
      }
    })
    const data = await api.saveModels(payload)
    applyScenes(data)
    // 保存后清空旧的测试结论，提示重新验证
    Object.keys(form).forEach((k) => delete testResult[k])
    show('模型配置已保存并即时生效，建议点击「测试连接」验证')
  } catch (e) {
    show(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

/** 用后端返回的最新场景数据同步列表与表单 */
function applyScenes(data) {
  if (data?.scenes) scenes.value = data.scenes
  if (data) {
    env.dashscope = !!data.env?.dashscope
    env.deepseek = !!data.env?.deepseek
  }
  scenes.value.forEach((s) => {
    if (!form[s.key]) form[s.key] = {}
    form[s.key].provider = s.provider || 'auto'
    form[s.key].model = s.model || ''
    form[s.key].base_url = s.base_url || ''
    form[s.key].api_key = ''
  })
}

/** 测试某场景是否真的能调通（不修改配置，直接用已保存的配置发起真实请求） */
async function test(key) {
  if (testing.value) return
  testing.value = key
  try {
    const data = await api.testModel(key)
    testResult[key] = data
    if (!data?.ok) show(data?.message || '连接失败')
  } catch (e) {
    testResult[key] = { ok: false, message: e?.message || '测试请求失败' }
    show(e?.message || '测试请求失败')
  } finally {
    testing.value = ''
  }
}

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  // 报错文案较长，给足阅读时间
  toastTimer = setTimeout(() => (toast.value = ''), msg && msg.length > 40 ? 7000 : 3200)
}

onMounted(load)
</script>

<style scoped>
.models { display: flex; flex-direction: column; gap: 16px; }

/* 顶部 */
.head { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 18px 20px; border-radius: var(--r-md); flex-wrap: wrap; }
.h-left h3 { font-size: 17px; color: #fff; letter-spacing: .05em; }
.h-left p { margin-top: 5px; font-size: 12.5px; color: var(--text-3); }
.h-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.env-chip {
  display: inline-flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px;
  border-radius: 9px; font-size: 11.5px; font-family: var(--font-num); letter-spacing: .02em;
  color: var(--text-3); background: rgba(255, 255, 255, .04); border: 1px solid var(--line);
}
.env-chip.on { color: #9ff0b4; background: rgba(0, 180, 42, .12); border-color: rgba(0, 180, 42, .32); }
.env-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
.env-chip .dot.ok { background: #00b42a; box-shadow: 0 0 8px rgba(0, 180, 42, .8); }
.env-chip .dot.off { background: #6b7a90; }

/* 总览 */
.overview { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.ov-card { padding: 14px 16px; border-radius: var(--r-md); display: flex; flex-direction: column; gap: 4px; border-left: 3px solid transparent; }
.ov-card.ok { border-left-color: var(--brand-green); }
.ov-card.off { border-left-color: var(--text-3); }
.ov-co { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ov-name { font-size: 12.5px; color: var(--text-2); }
.ov-state { font-size: 10.5px; padding: 1px 8px; border-radius: 999px; }
.ov-card.ok .ov-state { color: #9ff0b4; background: rgba(0, 180, 42, .14); border: 1px solid rgba(0, 180, 42, .3); }
.ov-card.off .ov-state { color: var(--text-3); background: rgba(255, 255, 255, .05); border: 1px solid var(--line); }
.ov-model { font-family: var(--font-num); font-size: 18px; color: #fff; margin-top: 3px; }
.ov-prov { font-size: 11px; color: var(--text-3); }

/* 配置网格 */
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.scene { display: flex; flex-direction: column; border-radius: var(--r-md); overflow: hidden; }
.sc-head { display: flex; align-items: flex-start; gap: 12px; padding: 16px 18px 13px; border-bottom: 1px solid var(--line); }
.sc-ico { width: 34px; height: 34px; flex: 0 0 34px; border-radius: 10px; display: grid; place-items: center; color: #8fb6ff; background: rgba(22, 93, 255, .14); border: 1px solid rgba(22, 93, 255, .22); }
.sc-title { flex: 1; min-width: 0; }
.sc-title h4 { font-size: 14.5px; color: var(--text-1); font-weight: 700; }
.sc-title p { margin-top: 3px; font-size: 11.5px; color: var(--text-3); }
.sc-badge { font-size: 10.5px; padding: 2px 9px; border-radius: 999px; flex: 0 0 auto; margin-top: 2px; }
.sc-badge.ok { color: #9ff0b4; background: rgba(0, 180, 42, .14); border: 1px solid rgba(0, 180, 42, .32); }
.sc-badge.off { color: #ffd08a; background: rgba(255, 125, 0, .12); border: 1px solid rgba(255, 125, 0, .3); }
.sc-badge.bad { color: #ffb3b3; background: rgba(245, 63, 63, .16); border: 1px solid rgba(245, 63, 63, .42); }

/* 配置异常：卡片描边转红，一眼可辨 */
.scene.bad { border-color: rgba(245, 63, 63, .38); }
.scene.bad .sc-head { border-bottom-color: rgba(245, 63, 63, .22); }

.sc-body { padding: 16px 18px; display: flex; flex-direction: column; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 7px; }
.field > span { font-size: 12px; color: var(--text-2); }
.field input, .field select {
  width: 100%; height: 40px; border-radius: 10px; background: rgba(255, 255, 255, .04);
  border: 1px solid var(--line); color: var(--text-1); font-size: 13px; padding: 0 12px;
  outline: none; font-family: inherit; transition: all .22s;
}
.field input::placeholder { color: var(--text-3); }
.field input:focus, .field select:focus { border-color: var(--brand-blue); box-shadow: 0 0 0 4px var(--accent-soft); background: rgba(22, 93, 255, .06); }
.field select option { background: #0d2140; color: #eaf2ff; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* 模型名称标题行：左侧标签 + 右侧「获取可用模型」链接按钮 */
.fld-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.fld-top i { font-style: normal; }
.lnk {
  background: none; border: none; padding: 0; cursor: pointer; font-family: inherit;
  font-size: 11.5px; color: #7aa5ff; text-decoration: underline; text-underline-offset: 3px;
}
.lnk:hover:not(:disabled) { color: #a9c4ff; }
.lnk:disabled { opacity: .55; cursor: default; }
.field > span.fld-top { font-size: 12px; color: var(--text-2); }

/* 官方模型列表（点选填入） */
.md-box { display: flex; flex-direction: column; gap: 7px; }
.md-label { font-size: 11px; color: var(--text-3); }
.md-chips { display: flex; flex-wrap: wrap; gap: 6px; max-height: 108px; overflow-y: auto; padding-right: 2px; }
.md-chip {
  font-family: inherit; font-size: 11.5px; padding: 4px 10px; border-radius: 999px; cursor: pointer;
  color: #bcd0f5; background: rgba(22, 93, 255, .1); border: 1px solid rgba(22, 93, 255, .26);
  transition: all .18s; white-space: nowrap;
}
.md-chip:hover { background: rgba(22, 93, 255, .22); border-color: rgba(22, 93, 255, .5); }
.md-chip.on { color: #fff; background: var(--brand-blue); border-color: var(--brand-blue); }
.md-msg { font-size: 11.5px; color: #ffd08a; line-height: 1.65; }

/* 上次调用失败原因 / 连接测试结果 */
.sc-err, .sc-test {
  margin: 0 18px 12px; padding: 10px 13px; border-radius: 10px;
  display: flex; flex-direction: column; gap: 4px; font-size: 11.5px; line-height: 1.65;
}
.sc-err { background: rgba(245, 63, 63, .1); border: 1px solid rgba(245, 63, 63, .3); }
.sc-err b { color: #ffb3b3; font-size: 11px; }
.sc-err span { color: #ffd9d9; }
.sc-test.ok { background: rgba(0, 180, 42, .1); border: 1px solid rgba(0, 180, 42, .32); }
.sc-test.ok b { color: #9ff0b4; }
.sc-test.ok span { color: #c8f2d4; }
.sc-test.bad { background: rgba(245, 63, 63, .1); border: 1px solid rgba(245, 63, 63, .3); }
.sc-test.bad b { color: #ffb3b3; }
.sc-test.bad span { color: #ffd9d9; }

.sc-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 18px; border-top: 1px solid var(--line); background: rgba(8, 20, 36, .45); }
.sc-tip { font-size: 11px; color: var(--text-3); line-height: 1.6; flex: 1; min-width: 0; }
.btn-mini {
  flex: 0 0 auto; height: 30px; padding: 0 14px; border-radius: 9px; font-size: 12px;
  color: #cfe0ff; background: rgba(22, 93, 255, .16); border: 1px solid rgba(22, 93, 255, .38);
  cursor: pointer; transition: all .2s; font-family: inherit;
}
.btn-mini:hover:not(:disabled) { background: rgba(22, 93, 255, .28); border-color: var(--brand-blue); }
.btn-mini:disabled { opacity: .55; cursor: default; }

.loading { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 46px; border-radius: var(--r-md); color: var(--text-3); font-size: 13px; }
.spin { width: 22px; height: 22px; border-radius: 50%; border: 2px solid rgba(22, 93, 255, .2); border-top-color: var(--brand-blue); animation: spin-slow .9s linear infinite; }

.note { font-size: 11.5px; color: var(--text-3); line-height: 1.85; text-align: center; }
.note b { color: #cfe0ff; font-family: var(--font-num); }

.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  max-width: min(720px, 86vw); padding: 12px 22px; border-radius: 11px; font-size: 13px; z-index: 99;
  line-height: 1.7; text-align: left; word-break: break-word;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong); color: var(--text-1); box-shadow: var(--shadow-lift);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

@media (max-width: 1500px) { .overview { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 1280px) { .overview { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1080px) { .grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .overview { grid-template-columns: 1fr; } .field-row { grid-template-columns: 1fr; } .sc-foot { flex-direction: column; align-items: stretch; } }
</style>
