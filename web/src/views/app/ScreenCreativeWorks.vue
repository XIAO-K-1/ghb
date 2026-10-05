<template>
  <div class="cw">
    <!-- 顶部说明 -->
    <section class="cw-top">
      <div class="cw-brand">
        <div class="cw-ico" v-html="ICON_WAND" />
        <div>
          <h3>本店 AI 文创产物</h3>
          <p>仅展示您本人（本店账号）生成的作品，其他店铺不可见</p>
        </div>
      </div>
      <button class="cw-refresh" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </section>

    <!-- 筛选 -->
    <div class="cw-tabs">
      <button v-for="t in tabs" :key="t.k" class="ct" :class="{ on: tab === t.k }" @click="tab = t.k">
        {{ t.label }}<span v-if="t.count">{{ t.count }}</span>
      </button>
    </div>

    <!-- 加载/空态 -->
    <div v-if="loading && !works.length" class="cw-empty">正在加载历史作品…</div>
    <div v-else-if="!works.length" class="cw-empty">
      <div class="empty-ico" v-html="ICON_WAND" />
      <h4>还没有生成过{{ tab === 'all' ? '' : tab === 'image' ? '图片' : '文案' }}作品</h4>
      <p>到「AI 文创生成」试试吧，生成后会保存在这里</p>
      <button class="cw-go" @click="$emit('go', 'creative')">去 AI 文创生成 ›</button>
    </div>

    <template v-else>
      <!-- 图片产物 -->
      <section v-if="tab !== 'copy'" class="cw-grid">
        <figure v-for="(w, i) in shownImages" :key="w.id" class="cw-cell rise-in" :style="{ animationDelay: i * 0.05 + 's' }" @click="preview = w">
          <img :src="w.image_urls[0]" :alt="w.title" loading="lazy" />
          <span class="cw-wm">AI生成</span>
          <figcaption>
            <b>{{ w.title }}</b>
            <span class="num">{{ shortTime(w.at) }}</span>
          </figcaption>
        </figure>
      </section>

      <!-- 文案产物 -->
      <section v-if="tab !== 'image'" class="cw-copies">
        <div v-for="w in shownCopies" :key="w.id" class="cw-copy">
          <div class="cc-head">
            <b>{{ w.title }}</b>
            <span class="mode-tag" :class="w.mode === 'llm' ? 'ai' : 'off'">{{ w.mode === 'llm' ? 'AI 创作' : '模板生成' }}</span>
          </div>
          <p class="cc-text">{{ w.content }}</p>
          <div class="cc-foot">
            <span class="num">{{ w.at }}</span>
            <div class="cc-acts">
              <button class="cc-btn ghost" @click="copyText(w)">复制文案</button>
              <button class="cc-btn" @click="$emit('go', 'creative')">去生成</button>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- 大图预览 -->
    <transition name="ov">
      <div v-if="preview" class="lightbox" @click="preview = null">
        <div class="lb-inner" @click.stop>
          <div class="lb-head">
            <b>{{ preview.title }}</b>
            <span class="num">{{ preview.at }}</span>
          </div>
          <div class="lb-imgs">
            <img v-for="url in preview.image_urls" :key="url" :src="url" :alt="preview.title" loading="lazy" />
          </div>
          <span class="wm wm-lg">AI生成</span>
          <div class="lb-actions">
            <button class="lb-btn" @click="download(preview)">下载图片</button>
            <button class="lb-btn primary" @click="preview = null">关闭</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="toast">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onActivated } from 'vue'
import api from '@/api'

const props = defineProps({ homestay: Object, user: Object })
const emit = defineEmits(['go'])

const ICON_WAND = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4l1.6 3.4L19 9l-3.4 1.6L14 14l-1.6-3.4L9 9l3.4-1.6z"/><path d="M6 18l-2.5 2.5M9.5 15.5l-1.8 1.8"/></svg>'

const tab = ref('all')
const works = ref([])
const loading = ref(false)
const error = ref('')
const preview = ref(null)
const toast = ref('')
let toastTimer = null

const shownImages = computed(() => works.value.filter((w) => w.type === 'image'))
const shownCopies = computed(() => works.value.filter((w) => w.type === 'copy'))

/* tabs 计数 */
const tabs = computed(() => [
  { k: 'all', label: '全部', count: works.value.length },
  { k: 'image', label: '图片', count: shownImages.value.length },
  { k: 'copy', label: '文案', count: shownCopies.value.length }
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.creativeWorks(props.homestay?.id || '')
    works.value = res?.works || []
  } catch (e) {
    error.value = e?.message || '加载失败，请确认后端服务已启动'
  } finally {
    loading.value = false
  }
}

function copyText(w) {
  navigator.clipboard.writeText(w.content || '').then(
    () => show('文案已复制到剪贴板'),
    () => show('复制失败，请手动复制')
  )
}

async function download(w) {
  const url = w.image_urls?.[0]
  if (!url) return
  try {
    const res = await fetch(url)
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `豫宿巡文创_${w.title}_${Date.now()}.png`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    window.open(url, '_blank')
  }
}

function shortTime(t) {
  if (!t) return ''
  return String(t).slice(5, 16)
}

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2200)
}

/* 子页被 KeepAlive 缓存：每次激活重新拉取，保证新生成的作品及时出现 */
onActivated(load)
</script>

<style scoped>
.cw { padding-bottom: 24px; }

/* 顶部 */
.cw-top {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  margin: 12px 14px 0; padding: 14px 15px; border-radius: 16px;
  background: linear-gradient(140deg, #fff, #f4f8ff);
  border: 1px solid rgba(22, 93, 255, .1); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.cw-brand { display: flex; gap: 11px; align-items: center; min-width: 0; }
.cw-ico {
  width: 38px; height: 38px; border-radius: 12px; flex: 0 0 38px; display: grid; place-items: center;
  color: #c98a00; background: rgba(255, 184, 0, .16);
}
.cw-brand h3 { font-size: 14px; color: #1d2129; }
.cw-brand p { font-size: 10.5px; color: #86909c; line-height: 1.6; margin-top: 3px; }
.cw-refresh {
  flex: 0 0 auto; height: 30px; padding: 0 12px; border-radius: 10px; font-size: 11.5px;
  color: #165dff; background: rgba(22, 93, 255, .09); border: 1px solid rgba(22, 93, 255, .22);
  transition: transform .2s;
}
.cw-refresh:disabled { opacity: .55; }
.cw-refresh:active { transform: scale(.97); }

/* tabs */
.cw-tabs { display: flex; gap: 8px; margin: 12px 14px 0; }
.ct {
  height: 30px; padding: 0 12px; border-radius: 999px; font-size: 11.5px; color: #4e5969;
  background: #fff; border: 1px solid rgba(29, 33, 41, .08);
  display: inline-flex; align-items: center; gap: 5px; transition: all .22s var(--ease-out);
}
.ct span { font-size: 10px; font-family: var(--font-num); color: #86909c; background: #f2f3f5; border-radius: 999px; padding: 0 6px; }
.ct.on { color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff); border-color: transparent; }
.ct.on span { color: #165dff; background: rgba(255, 255, 255, .92); }

/* 图片墙 */
.cw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; margin: 13px 14px 0; }
.cw-cell {
  position: relative; aspect-ratio: 1 / 1; border-radius: 14px; overflow: hidden; cursor: pointer;
  background: #fff; border: 1px solid rgba(29, 33, 41, .06);
  box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
  transition: transform .28s var(--ease-out), box-shadow .28s;
}
.cw-cell:hover { transform: translateY(-3px); box-shadow: 0 20px 34px -22px rgba(10, 25, 47, .6); }
.cw-cell img { width: 100%; height: 100%; object-fit: cover; }
.cw-wm {
  position: absolute; right: 6px; top: 6px; font-size: 8.5px; letter-spacing: .06em;
  color: rgba(255, 255, 255, .92); background: rgba(0, 0, 0, .3); padding: 1px 6px; border-radius: 4px;
  backdrop-filter: blur(3px);
}
.cw-cell figcaption {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 16px 9px 6px;
  display: flex; flex-direction: column; gap: 2px;
  background: linear-gradient(180deg, transparent, rgba(255, 255, 255, .97) 55%);
}
.cw-cell figcaption b { font-size: 11px; font-weight: 600; color: #1d2129; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cw-cell figcaption span { font-size: 9.5px; color: #86909c; }

/* 文案 */
.cw-copies { display: flex; flex-direction: column; gap: 11px; margin: 13px 14px 0; }
.cw-copy {
  padding: 13px 14px; border-radius: 15px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.cc-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.cc-head b { font-size: 13px; color: #1d2129; }
.mode-tag { font-size: 10px; padding: 1px 9px; border-radius: 999px; flex: 0 0 auto; }
.mode-tag.ai { color: #165dff; background: rgba(22, 93, 255, .1); }
.mode-tag.off { color: #86909c; background: #f2f3f5; }
.cc-text {
  margin-top: 9px; font-size: 12px; color: #4e5969; line-height: 1.85;
  white-space: pre-wrap; word-break: break-word; max-height: 168px; overflow: hidden;
  position: relative;
}
.cc-text::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 34px;
  background: linear-gradient(180deg, transparent, #fff);
}
.cc-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; }
.cc-foot > span { font-size: 10.5px; color: #a9b0bd; }
.cc-acts { display: flex; gap: 8px; }
.cc-btn {
  height: 30px; padding: 0 13px; border-radius: 10px; font-size: 11.5px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff); transition: transform .2s;
}
.cc-btn.ghost { color: #165dff; background: rgba(22, 93, 255, .09); border: 1px solid rgba(22, 93, 255, .2); }
.cc-btn:active { transform: scale(.97); }

/* 空态 */
.cw-empty { margin: 40px 14px 0; padding: 30px 16px; text-align: center; background: #fff; border-radius: 16px; border: 1px dashed rgba(29, 33, 41, .12); }
.cw-empty .empty-ico { width: 58px; height: 58px; margin: 0 auto 12px; border-radius: 18px; display: grid; place-items: center; color: #ffb800; background: rgba(255, 184, 0, .12); }
.cw-empty h4 { font-size: 13.5px; color: #1d2129; }
.cw-empty p { font-size: 11.5px; color: #86909c; margin-top: 6px; }
.cw-go {
  height: 34px; margin-top: 14px; padding: 0 16px; border-radius: 11px; font-size: 12px; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #ffc93c, #ff9d00 55%, #e07b00);
  box-shadow: 0 10px 22px -12px rgba(255, 157, 0, .8); transition: transform .2s;
}
.cw-go:active { transform: scale(.97); }

/* 大图 */
.lightbox { position: absolute; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; padding: 18px; background: rgba(8, 14, 24, .88); backdrop-filter: blur(8px); }
.lb-inner { position: relative; width: 100%; }
.lb-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; color: #fff; margin-bottom: 10px; }
.lb-head b { font-size: 14px; }
.lb-head span { font-size: 11px; opacity: .8; }
.lb-imgs { display: flex; flex-direction: column; gap: 10px; max-height: 58vh; overflow-y: auto; }
.lb-imgs img { width: 100%; border-radius: 16px; box-shadow: 0 30px 60px -20px rgba(0, 0, 0, .8); }
.wm-lg { right: 10px; bottom: 12px; font-size: 11px; position: absolute; }
.wm {
  font-size: 9px; letter-spacing: .06em; color: rgba(255, 255, 255, .92);
  background: rgba(0, 0, 0, .32); padding: 1px 6px; border-radius: 4px; backdrop-filter: blur(3px);
}
.lb-actions { display: flex; gap: 8px; margin-top: 14px; }
.lb-btn { flex: 1; height: 40px; border-radius: 11px; font-size: 12.5px; font-weight: 600; color: #1d2129; background: #fff; transition: transform .2s; }
.lb-btn:hover { transform: translateY(-2px); }
.lb-btn.primary { background: linear-gradient(135deg, #4b83ff, #165dff); color: #fff; }
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