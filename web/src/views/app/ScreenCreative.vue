<template>
  <div class="creative">
    <!-- 头部 -->
    <header class="cr-head" :class="{ slim: view !== 'entry' }">
      <div class="ch-deco" />
      <button v-if="view !== 'entry'" class="ch-back" @click="back">
        <svg viewBox="0 0 24 24" width="15" height="15"><path d="M15 6l-6 6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回
      </button>
      <h2 class="title-serif">{{ headTitle }}</h2>
      <p>{{ headSub }}</p>
      <div v-if="view === 'entry'" class="ch-tags">
        <span>Q版新中式</span><span>徽章插画</span><span>贴纸风格</span><span>含 AI 标识</span>
      </div>
    </header>

    <!-- ============ 入口主页 ============ -->
    <template v-if="view === 'entry'">
      <section class="entries">
        <button class="entry" @click="openCustomImage">
          <span class="en-ico img" v-html="ICON_IMG" />
          <b>文创图片</b>
          <p>自己写提示词，上传照片生成</p>
        </button>
        <button class="entry" @click="openCopy">
          <span class="en-ico txt" v-html="ICON_TXT" />
          <b>文案生成</b>
          <p>根据民宿信息生成宣传文案</p>
        </button>
      </section>

      <section class="wall">
        <div class="wall-head">
          <h4>提示词生图样式</h4>
          <span class="mono-label">点选即用</span>
        </div>
        <p class="wall-tip">选择喜欢的样式，上传一张照片，即可生成同风格文创图（样式提示词由系统内置，无需填写）</p>
        <div class="wall-grid">
          <button v-for="s in styles" :key="s.key" class="style-card" @click="openStyle(s)">
            <img :src="s.cover" :alt="s.title" loading="lazy" />
            <span class="sc-wm">AI生成</span>
            <span class="sc-title">{{ s.title }}</span>
          </button>
          <div v-if="!styles.length" class="wall-empty">样式加载中…</div>
        </div>
      </section>
    </template>

    <!-- ============ 文创图片 ============ -->
    <template v-else-if="view === 'image'">
      <section class="panel">
        <div v-if="style" class="picked">
          <img :src="style.cover" :alt="style.title" />
          <div class="pk-body">
            <span class="pk-tag">已选样式</span>
            <b>{{ style.title }}</b>
            <p>提示词由系统内置，只需上传一张照片即可生成同风格图片</p>
          </div>
        </div>

        <div v-else class="field">
          <label>描述您想要的文创主题</label>
          <textarea v-model="theme" rows="3"
            placeholder="例如：国庆快到了，帮我做几张洛阳水席主题、能送给客人的冰箱贴图片" />
          <div class="chips no-scrollbar">
            <button v-for="t in presets" :key="t" class="chip" @click="theme = t">{{ t }}</button>
          </div>
        </div>

        <div class="field">
          <label>{{ style ? '① 上传一张照片' : '上传参考照片（可选）' }}</label>
          <div class="upload" :class="{ filled: !!uploadPreview }" @click="pick">
            <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
            <img v-if="uploadPreview" :src="uploadPreview" alt="已上传" />
            <div v-else class="up-hint">
              <span class="up-ico" v-html="ICON_UP" />
              <b>点击上传图片</b>
              <small>支持 JPG / PNG，建议方形清晰照片</small>
            </div>
          </div>
        </div>

        <button class="gen-btn" :disabled="loading || (!style && !theme.trim())" @click="generate">
          <span class="gb-spark" v-html="ICON_SPARK" />
          {{ loading ? '正在生成…' : (style ? '生成同风格文创图' : '生成文创图片') }}
        </button>
      </section>

      <section class="cr-result">
        <div class="cr-bar">
          <h4>生成结果</h4>
          <span class="cr-count">{{ images.length }} 张</span>
        </div>

        <div class="grid">
          <template v-if="loading">
            <div v-for="i in 2" :key="'sk' + i" class="cell skeleton-cell"><div class="sk-shine" /></div>
          </template>

          <figure v-for="(img, i) in images" :key="img.url + i" class="cell rise-in" :style="{ animationDelay: i * 0.08 + 's' }" @click="preview = img">
            <img :src="img.url" :alt="img.theme" loading="lazy" @load="img.loaded = true" @error="img.failed = true" />
            <div v-if="!img.loaded && !img.failed" class="cell-loading"><div class="sk-shine" /></div>
            <div v-if="img.failed" class="cell-failed">图片加载失败<br /><small>请检查网络</small></div>
            <span class="wm">AI生成</span>
            <figcaption>{{ img.theme }}</figcaption>
          </figure>

          <div v-if="!loading && !images.length" class="empty">
            <div class="empty-ico" v-html="ICON_IMG" />
            <h4>{{ style ? '上传照片后点击生成' : '还没有生成任何文创图' }}</h4>
            <p>{{ style ? '系统将按所选样式生成，可直接下载使用' : '输入主题或点选上方标签，一键生成文创图片' }}</p>
          </div>
        </div>
      </section>
    </template>

    <!-- ============ 文案生成 ============ -->
    <template v-else-if="view === 'copy'">
      <section class="panel">
        <div class="field">
          <label>选择文案风格</label>
          <div class="copy-styles">
            <button v-for="c in copyStyles" :key="c.key" class="cs" :class="{ on: copyStyle === c.key }" @click="copyStyle = c.key">
              <b>{{ c.name }}</b>
              <span>{{ c.desc }}</span>
            </button>
          </div>
        </div>

        <div class="field">
          <label>告诉 AI 你的要求</label>
          <textarea v-model="requirement" rows="4"
            placeholder="例如：突出古都夜游与亲子体验，语气温柔有画面感，控制在 250 字左右" />
        </div>

        <button class="gen-btn" :disabled="copyLoading" @click="genCopy">
          <span class="gb-spark" v-html="ICON_SPARK" />
          {{ copyLoading ? '正在创作…' : '生成宣传文案' }}
        </button>
      </section>

      <section v-if="copyText" class="panel copy-out">
        <div class="co-head">
          <h4>生成结果</h4>
          <span class="mode-tag" :class="copyMode === 'llm' ? 'ai' : 'off'">{{ copyMode === 'llm' ? 'AI 创作' : '模板生成' }}</span>
        </div>
        <pre class="co-text">{{ copyText }}</pre>
        <p v-if="copyDegrade" class="co-degrade">{{ copyDegrade }}</p>
        <div class="co-acts">
          <button class="co-btn ghost" @click="copyToClipboard">复制文案</button>
          <button class="co-btn" @click="genCopy">重新生成</button>
        </div>
      </section>

      <div v-else-if="!copyLoading" class="panel copy-empty">
        <div class="empty-ico" v-html="ICON_TXT" />
        <h4>还没有生成文案</h4>
        <p>选择风格、写下要求，AI 将结合本店信息生成宣传文案</p>
      </div>
    </template>

    <!-- 大图预览 -->
    <transition name="ov">
      <div v-if="preview" class="lightbox" @click="preview = null">
        <div class="lb-inner" @click.stop>
          <img :src="preview.url" :alt="preview.theme" />
          <span class="wm wm-lg">AI生成</span>
          <div class="lb-actions">
            <button class="lb-btn" @click="download(preview)">下载图片</button>
            <button class="lb-btn ghost" @click="vectorize(preview)">{{ vecLoading ? '转换中…' : '矢量化 SVG' }}</button>
            <button class="lb-btn primary" @click="preview = null">关闭</button>
          </div>
          <p v-if="vecNote" class="lb-note">{{ vecNote }}</p>
        </div>
      </div>
    </transition>

    <p class="cr-note">
      依据 2025 年 9 月 1 日施行的《人工智能生成合成内容标识办法》，所有 AI 生成图片均已添加「AI生成」显式标识。
    </p>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount, onActivated, watch } from 'vue'
import api from '@/api'

const props = defineProps({ homestay: Object, user: Object })

const ICON_IMG = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.6" cy="8.6" r="1.7"/><path d="m4 17 5-5 4 4 3-3 4 4"/></svg>'
const ICON_TXT = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 11h12M4 16h8"/></svg>'
const ICON_UP = '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V5m0 0-4 4m4-4 4 4"/><path d="M5 19h14"/></svg>'
const ICON_SPARK = '<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12 2.5 13.9 9l6.6 1.9-6.6 1.9L12 19.4 10.1 12.8 3.5 10.9 10.1 9 12 2.5z" fill="currentColor"/></svg>'

const view = ref('entry')       // entry / image / copy
const styles = ref([])
const copyStyles = ref([])

/**
 * 提示词生图样式（公共数据，谁都能看）。后端离线 / 请求失败时兜底展示内置样式，
 * 保证切换账号后样式墙始终可见。封面走与后端一致的文生图地址。
 */
const COVER_API = (prompt) => `https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${encodeURIComponent(prompt)}&image_size=square_hd`
const CHINESE_STYLE = '古都民宿'
const DEFAULT_STYLES = [
  { key: 'q_newchin', title: 'Q版新中式徽章', prompt: 'Q版新中式徽章插画，圆润胶囊状古建，扁平糖果色块，孔版印刷颗粒质感，纯白背景，徽章美学，主题：' + CHINESE_STYLE },
  { key: 'peony', title: '洛阳牡丹伴手礼', prompt: '洛阳牡丹主题伴手礼插画，盛放牡丹与古典窗棂，粉金配色，烫金质感，扁平矢量，纯色背景，主题：' + CHINESE_STYLE },
  { key: 'water_banquet', title: '洛阳水席美食贴纸', prompt: '洛阳水席美食贴纸插画，汤碗与二十四道菜小巧排布，暖橙色调，圆润描边，贴纸风格，主题：' + CHINESE_STYLE },
  { key: 'longmen', title: '龙门石窟佛龛剪影', prompt: '龙门石窟佛龛剪影插画，石窟造像与山峦线条，砂岩暖褐色系，现代扁平解构，留白构图，主题：' + CHINESE_STYLE },
  { key: 'opera', title: '豫剧脸谱潮流徽章', prompt: '豫剧脸谱潮流徽章插画，戏曲脸谱几何解构，红金蓝撞色，圆角单线轮廓，徽章美学，主题：' + CHINESE_STYLE },
  { key: 'guodu_night', title: '古都夜游灯会', prompt: '古都夜游灯会插画，古城楼与灯笼，靛蓝夜色配暖金光晕，扁平渐变，光斑点点，主题：' + CHINESE_STYLE }
]
const DEFAULT_COPY_STYLES = [
  { key: 'xiaohongshu', name: '小红书种草风', desc: '口语化、带话题标签、突出氛围感' },
  { key: 'ota', name: 'OTA详情页风', desc: '卖点清晰、适合携程/美团房源介绍' },
  { key: 'cultural', name: '古都文化风', desc: '典雅书面语、融入历史人文底蕴' },
  { key: 'promo', name: '节日促销风', desc: '强调优惠力度与行动号召' }
]
function fallbackStyles() {
  return DEFAULT_STYLES.map((s) => ({ key: s.key, title: s.title, cover: COVER_API(s.prompt) }))
}

/* 生图 */
const style = ref(null)         // 选中的样式（null=自定义提示词）
const theme = ref('')
const presets = ['洛阳水席主题冰箱贴', '龙门石窟Q版徽章', '开封菊花文化贴纸', '洛阳牡丹伴手礼图案', '国庆节主题文创']
const loading = ref(false)
const images = ref([])
const preview = ref(null)
const vecLoading = ref(false)
const vecNote = ref('')
const uploadPreview = ref('')
const fileInput = ref(null)

/* 文案 */
const copyStyle = ref('xiaohongshu')
const requirement = ref('')
const copyLoading = ref(false)
const copyText = ref('')
const copyMode = ref('offline')
const copyDegrade = ref('')

const toast = ref('')
let toastTimer = null

const headTitle = computed(() => {
  if (view.value === 'image') return style.value ? style.value.title : '文创图片生成'
  if (view.value === 'copy') return '民宿宣传文案'
  return 'AI 文创生成'
})
const headSub = computed(() => {
  if (view.value === 'image') return style.value ? '上传照片，一键生成同风格文创图' : '写一句提示词，生成专属文创图'
  if (view.value === 'copy') return '结合本店信息，生成可直接使用的宣传文案'
  return '一句话生成专属文创图，免费赠予客人引流获客'
})

async function loadStyles() {
  try {
    const res = await api.creativeStyles(props.homestay?.id || '')
    styles.value = res?.styles || fallbackStyles()
    copyStyles.value = res?.copy_styles || DEFAULT_COPY_STYLES
    if (!res?.styles) {
      // 后端返回空时兜底，保证样式墙不空白
      styles.value = fallbackStyles()
      copyStyles.value = DEFAULT_COPY_STYLES
    }
  } catch (e) {
    // 后端离线 / 网络异常：使用内置公共样式兜底，切换账号后样式墙依旧可见
    console.warn('[ScreenCreative] 样式加载失败，使用内置公共样式：', e?.message || e)
    styles.value = fallbackStyles()
    copyStyles.value = DEFAULT_COPY_STYLES
  }
}

function back() {
  view.value = 'entry'
  vecNote.value = ''
}

/**
 * 重置为本店入口主页。
 * ScreenCreative 被 AppShell 的 KeepAlive 缓存：换账号 / 切换 Tab 后组件实例复用，
 * 若还停留在「文创图片/文案生成」子页，入口的「提示词生图样式」墙就看不到了，
 * 因此在每次激活时回到入口，并换民宿时重载该店的样式。
 */
function resetToEntry() {
  view.value = 'entry'
  style.value = null
  theme.value = ''
  uploadPreview.value = ''
  images.value = []
  copyText.value = ''
  vecNote.value = ''
  loadStyles()
}
function openCustomImage() {
  style.value = null
  theme.value = ''
  uploadPreview.value = ''
  images.value = []
  view.value = 'image'
}
function openStyle(s) {
  style.value = s
  theme.value = ''
  uploadPreview.value = ''
  images.value = []
  view.value = 'image'
}
function openCopy() {
  view.value = 'copy'
}

function pick() {
  fileInput.value?.click()
}
function onFile(e) {
  const f = e.target.files?.[0]
  if (!f) return
  const reader = new FileReader()
  reader.onload = () => { uploadPreview.value = String(reader.result || '') }
  reader.readAsDataURL(f)
}

async function generate() {
  if (loading.value) return
  if (!style.value && !theme.value.trim()) return show('请先输入提示词')
  loading.value = true
  vecNote.value = ''
  try {
    const hid = props.homestay?.id || 'LY001'
    let res
    if (style.value) {
      res = await api.styleGenerate(hid, style.value.key, 2, uploadPreview.value ? 'uploaded' : '')
      images.value = (res?.image_urls || []).map((url, i) => ({ url, theme: res?.style_title || style.value.title, loaded: false, failed: false, id: i }))
    } else {
      const t = theme.value.trim()
      res = await api.generateCreative(hid, t, 2)
      images.value = (res?.image_urls || []).map((url, i) => ({ url, theme: t, loaded: false, failed: false, id: i }))
    }
    if (!images.value.length) show('未生成图片，请稍后重试')
    else if (res?.degrade_reason) show(res.degrade_reason)
    else show(`已生成 ${images.value.length} 张文创图，可点击下载`)
  } catch (e) {
    show(e?.message || '生成失败，请确认后端服务已启动')
  } finally {
    loading.value = false
  }
}

async function genCopy() {
  if (copyLoading.value) return
  copyLoading.value = true
  try {
    const res = await api.copywriting(props.homestay?.id || 'LY001', requirement.value.trim(), copyStyle.value)
    copyText.value = res?.content || ''
    copyMode.value = res?.mode || 'offline'
    copyDegrade.value = res?.degrade_reason || ''
    if (!copyText.value) show('未生成文案，请稍后重试')
  } catch (e) {
    show(e?.message || '文案生成失败')
  } finally {
    copyLoading.value = false
  }
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(copyText.value)
    show('文案已复制到剪贴板')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = copyText.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    show('文案已复制到剪贴板')
  }
}

async function download(img) {
  try {
    const res = await fetch(img.url)
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `豫宿巡文创_${img.theme}_${Date.now()}.png`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    window.open(img.url, '_blank')
  }
}

async function vectorize(img) {
  vecLoading.value = true
  vecNote.value = ''
  try {
    const res = await api.vectorize(img.url)
    vecNote.value = `矢量化方式：${res?.method || 'placeholder'}${res?.note ? ' · ' + res.note : ''}${res?.svg_url ? ' · 输出：' + res.svg_url : ''}`
    show('矢量化处理完成')
  } catch (e) {
    vecNote.value = e?.message || '矢量化失败'
    show(vecNote.value)
  } finally {
    vecLoading.value = false
  }
}

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  // 降级原因较长，给足阅读时间
  const ms = msg && msg.length > 40 ? 7000 : 3000
  nextTick(() => { toastTimer = setTimeout(() => (toast.value = ''), ms) })
}

onMounted(loadStyles)
onActivated(resetToEntry)
watch(() => props.homestay?.id, () => resetToEntry())
onBeforeUnmount(() => clearTimeout(toastTimer))
</script>

<style scoped>
.creative { min-height: 100%; padding-bottom: 16px; }

/* 头部 */
.cr-head {
  position: relative; padding: 42px 20px 22px; color: #fff; overflow: hidden;
  background: linear-gradient(140deg, #6b4a00 0%, #b58300 42%, #165dff 145%);
  border-radius: 0 0 24px 24px;
}
.cr-head.slim { padding-bottom: 18px; }
.ch-deco {
  position: absolute; inset: 0; opacity: .28;
  background-image: radial-gradient(rgba(255, 255, 255, .55) 1px, transparent 1px);
  background-size: 17px 17px;
  mask-image: radial-gradient(ellipse 70% 80% at 20% 0%, #000, transparent 70%);
}
.ch-back {
  position: relative; display: inline-flex; align-items: center; gap: 4px; margin-bottom: 10px;
  font-size: 12px; color: #fff; padding: 4px 12px 4px 8px; border-radius: 999px;
  background: rgba(255, 255, 255, .18); border: 1px solid rgba(255, 255, 255, .3);
}
.cr-head h2 { position: relative; font-size: 21px; letter-spacing: .08em; }
.cr-head p { position: relative; font-size: 12px; opacity: .92; margin-top: 7px; }
.ch-tags { position: relative; display: flex; gap: 7px; margin-top: 14px; flex-wrap: wrap; }
.ch-tags span { font-size: 10.5px; padding: 3px 10px; border-radius: 999px; background: rgba(255, 255, 255, .18); border: 1px solid rgba(255, 255, 255, .28); }

/* 双入口 */
.entries { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; margin: -14px 14px 0; position: relative; z-index: 3; }
.entry {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px; text-align: left;
  padding: 14px 13px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 16px 36px -26px rgba(10, 25, 47, .55);
  transition: transform .24s var(--ease-out), box-shadow .24s;
}
.entry:hover { transform: translateY(-2px); box-shadow: 0 20px 40px -26px rgba(10, 25, 47, .6); }
.en-ico { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; margin-bottom: 4px; }
.en-ico.img { color: #165dff; background: rgba(22, 93, 255, .1); }
.en-ico.txt { color: #c98a00; background: rgba(255, 184, 0, .18); }
.entry b { font-size: 14px; color: #1d2129; }
.entry p { font-size: 10.5px; color: #86909c; line-height: 1.5; }

/* 样式墙 */
.wall { margin: 16px 14px 0; }
.wall-head { display: flex; align-items: baseline; justify-content: space-between; }
.wall-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.wall-tip { font-size: 10.5px; color: #a9b0bd; line-height: 1.7; margin-top: 6px; }
.wall-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; margin-top: 11px; }
.style-card {
  position: relative; aspect-ratio: 1 / 1; border-radius: 14px; overflow: hidden; background: #fff;
  border: 1px solid rgba(29, 33, 41, .06); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
  transition: transform .28s var(--ease-out), box-shadow .28s;
}
.style-card:hover { transform: translateY(-3px); box-shadow: 0 20px 34px -22px rgba(10, 25, 47, .6); }
.style-card img { width: 100%; height: 100%; object-fit: cover; }
.sc-wm {
  position: absolute; right: 6px; top: 6px; font-size: 8.5px; letter-spacing: .06em;
  color: rgba(255, 255, 255, .92); background: rgba(0, 0, 0, .3); padding: 1px 6px; border-radius: 4px;
  backdrop-filter: blur(3px);
}
.sc-title {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 16px 9px 7px;
  font-size: 11px; font-weight: 600; color: #1d2129; text-align: left;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, .97) 55%);
}
.wall-empty { grid-column: 1 / -1; text-align: center; font-size: 11.5px; color: #a9b0bd; padding: 24px 0; }

/* 面板 */
.panel {
  margin: 14px 14px 0; padding: 15px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.field { margin-bottom: 14px; }
.field:last-of-type { margin-bottom: 0; }
.field label { display: block; font-size: 12px; font-weight: 600; color: #1d2129; margin-bottom: 8px; }
.field textarea {
  width: 100%; border: 1.5px solid rgba(29, 33, 41, .08); border-radius: 12px;
  padding: 11px 13px; font-size: 13px; color: #1d2129; outline: none; resize: none;
  font-family: inherit; line-height: 1.7; background: #f9fafc; transition: all .25s;
}
.field textarea:focus { border-color: #165dff; background: #fff; box-shadow: 0 0 0 4px rgba(22, 93, 255, .09); }
.field textarea::placeholder { color: #a9b0bd; }
.chips { display: flex; gap: 7px; margin-top: 10px; overflow-x: auto; padding-bottom: 2px; }
.chip {
  flex: 0 0 auto; height: 28px; padding: 0 12px; border-radius: 999px; font-size: 11px;
  color: #b06a00; background: rgba(255, 184, 0, .12); border: 1px solid rgba(255, 184, 0, .3);
  white-space: nowrap; transition: all .22s var(--ease-out);
}
.chip:hover { background: rgba(255, 184, 0, .22); transform: translateY(-1px); }

/* 文案风格 */
.copy-styles { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
.cs {
  display: flex; flex-direction: column; gap: 3px; text-align: left; padding: 11px 12px; border-radius: 13px;
  background: #f7f8fa; border: 1.5px solid transparent; transition: all .22s var(--ease-out);
}
.cs b { font-size: 12.5px; color: #1d2129; }
.cs span { font-size: 10px; color: #86909c; line-height: 1.5; }
.cs.on { background: rgba(22, 93, 255, .06); border-color: #165dff; }
.cs.on b { color: #165dff; }

/* 已选样式 */
.picked { display: flex; gap: 12px; padding: 11px; border-radius: 14px; background: #f7f9fc; margin-bottom: 14px; }
.picked img { width: 76px; height: 76px; border-radius: 12px; object-fit: cover; flex: 0 0 76px; }
.pk-body { flex: 1; min-width: 0; }
.pk-tag { display: inline-block; font-size: 9.5px; color: #165dff; background: rgba(22, 93, 255, .1); padding: 1px 7px; border-radius: 5px; }
.pk-body b { display: block; font-size: 13.5px; color: #1d2129; margin-top: 6px; }
.pk-body p { font-size: 10.5px; color: #86909c; line-height: 1.6; margin-top: 5px; }

/* 上传 */
.upload {
  position: relative; width: 100%; height: 150px; border-radius: 14px; overflow: hidden; cursor: pointer;
  border: 1.6px dashed rgba(22, 93, 255, .32); background: rgba(22, 93, 255, .04);
  display: grid; place-items: center; transition: all .24s var(--ease-out);
}
.upload:hover { border-color: #165dff; background: rgba(22, 93, 255, .07); }
.upload.filled { border-style: solid; border-color: rgba(29, 33, 41, .08); }
.upload img { width: 100%; height: 100%; object-fit: cover; }
.up-hint { display: flex; flex-direction: column; align-items: center; gap: 5px; color: #165dff; }
.up-ico { display: grid; place-items: center; }
.up-hint b { font-size: 12.5px; color: #1d2129; }
.up-hint small { font-size: 10.5px; color: #a9b0bd; }

/* 生成按钮 */
.gen-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; height: 46px; margin-top: 14px;
  border-radius: 13px; font-size: 14.5px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #ffc93c, #ff9d00 55%, #e07b00);
  box-shadow: 0 14px 28px -14px rgba(255, 157, 0, .85);
  transition: transform .22s var(--ease-out), opacity .22s;
}
.gen-btn:hover:not(:disabled) { transform: translateY(-2px); }
.gen-btn:disabled { opacity: .55; }
.gb-spark { line-height: 0; }

/* 结果 */
.cr-result { margin: 16px 14px 0; }
.cr-bar { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 11px; }
.cr-bar h4 { font-size: 14px; color: #1d2129; font-weight: 700; }
.cr-count { font-size: 11px; color: #86909c; font-family: var(--font-num); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; }
.cell {
  position: relative; aspect-ratio: 1 / 1; border-radius: 14px; overflow: hidden;
  background: #fff; border: 1px solid rgba(29, 33, 41, .06);
  box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5); cursor: pointer;
  transition: transform .28s var(--ease-out), box-shadow .28s;
}
.cell:hover { transform: translateY(-3px); box-shadow: 0 20px 34px -22px rgba(10, 25, 47, .6); }
.cell img { width: 100%; height: 100%; object-fit: cover; }
.cell-loading, .skeleton-cell { position: absolute; inset: 0; background: #eef1f6; overflow: hidden; }
.sk-shine {
  position: absolute; inset: 0;
  background: linear-gradient(100deg, transparent 25%, rgba(255, 255, 255, .85) 50%, transparent 75%);
  animation: shimmer 1.4s infinite linear; background-size: 220% 100%;
}
.cell-failed { position: absolute; inset: 0; display: grid; place-items: center; text-align: center; font-size: 11.5px; color: #86909c; background: #f4f6fa; line-height: 1.8; }
.wm {
  position: absolute; right: 6px; bottom: 22px; font-size: 8.5px; color: rgba(255, 255, 255, .92);
  letter-spacing: .06em; background: rgba(0, 0, 0, .32); padding: 1px 6px; border-radius: 4px;
  backdrop-filter: blur(3px); pointer-events: none;
}
.cell figcaption {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 6px 9px; font-size: 10.5px; color: #4e5969;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, .96) 40%);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.empty { grid-column: 1 / -1; text-align: center; padding: 30px 16px; background: #fff; border-radius: 16px; border: 1px dashed rgba(29, 33, 41, .12); }
.empty-ico { width: 58px; height: 58px; margin: 0 auto 12px; border-radius: 18px; display: grid; place-items: center; color: #ffb800; background: rgba(255, 184, 0, .12); }
.empty h4 { font-size: 13.5px; color: #1d2129; }
.empty p { font-size: 11.5px; color: #86909c; margin-top: 6px; line-height: 1.7; }

/* 文案输出 */
.copy-out .co-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.copy-out .co-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.mode-tag { font-size: 10px; padding: 1px 9px; border-radius: 999px; }
.mode-tag.ai { color: #165dff; background: rgba(22, 93, 255, .1); }
.mode-tag.off { color: #86909c; background: #f2f3f5; }
/* 大模型调用失败时的降级说明 */
.co-degrade {
  margin-top: 10px; padding: 10px 12px; border-radius: 11px; font-size: 11.5px; line-height: 1.7;
  color: #a8500a; background: #fff7e8; border: 1px solid #ffe0a8; word-break: break-word;
}
.co-text {
  font-family: inherit; font-size: 12.5px; color: #1d2129; line-height: 1.9; white-space: pre-wrap; word-break: break-word;
  padding: 13px; border-radius: 13px; background: #f7f9fc; border: 1px solid rgba(29, 33, 41, .06);
}
.co-acts { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-top: 12px; }
.co-btn { height: 42px; border-radius: 12px; font-size: 13px; font-weight: 600; color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff); transition: transform .2s; }
.co-btn.ghost { color: #165dff; background: rgba(22, 93, 255, .09); border: 1px solid rgba(22, 93, 255, .2); }
.co-btn:active { transform: scale(.98); }
.copy-empty { text-align: center; padding: 34px 16px; }

.cr-note { margin: 14px 16px 0; font-size: 10.5px; color: #a9b0bd; line-height: 1.75; text-align: center; }

/* 大图 */
.lightbox { position: absolute; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; padding: 18px; background: rgba(8, 14, 24, .88); backdrop-filter: blur(8px); }
.lb-inner { position: relative; width: 100%; }
.lb-inner img { width: 100%; border-radius: 16px; box-shadow: 0 30px 60px -20px rgba(0, 0, 0, .8); }
.wm-lg { right: 10px; bottom: 12px; font-size: 11px; }
.lb-actions { display: flex; gap: 8px; margin-top: 14px; }
.lb-btn { flex: 1; height: 40px; border-radius: 11px; font-size: 12.5px; font-weight: 600; color: #1d2129; background: #fff; transition: transform .2s; }
.lb-btn:hover { transform: translateY(-2px); }
.lb-btn.ghost { background: rgba(255, 255, 255, .16); color: #fff; border: 1px solid rgba(255, 255, 255, .3); }
.lb-btn.primary { background: linear-gradient(135deg, #4b83ff, #165dff); color: #fff; }
.lb-note { margin-top: 10px; font-size: 10.5px; color: #cfd8e6; line-height: 1.7; text-align: center; }
.ov-enter-active, .ov-leave-active { transition: opacity .28s var(--ease-out); }
.ov-enter-from, .ov-leave-to { opacity: 0; }

.toast {
  position: absolute; left: 50%; bottom: 86px; transform: translateX(-50%);
  max-width: 86%; padding: 10px 18px; border-radius: 11px; font-size: 12px; z-index: 60;
  background: rgba(29, 33, 41, .93); color: #fff; text-align: center;
  box-shadow: 0 14px 30px -14px rgba(0, 0, 0, .7);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
