<template>
  <div class="rag">
    <!-- 概览 -->
    <section class="summary">
      <div class="sm-card">
        <b class="num">{{ lib.public_count || 0 }}</b>
        <span>公用文档</span>
      </div>
      <div class="sm-card">
        <b class="num">{{ lib.private_count || 0 }}</b>
        <span>本店专属</span>
      </div>
      <div class="sm-card">
        <b class="num">{{ lib.total_chunks || 0 }}</b>
        <span>知识块</span>
      </div>
      <div class="sm-card">
        <b class="backend">{{ lib.backend === 'chromadb' ? '向量库' : '内置' }}</b>
        <span>检索后端</span>
      </div>
    </section>

    <p class="scope-note">
      本店知识库 <b class="num">{{ lib.collection || '—' }}</b> 独立隔离：仅检索「公用知识 + 本店专属文档」，不会读取其他民宿数据。
    </p>

    <!-- 操作 -->
    <div class="actions">
      <button class="act primary" :disabled="crawling" @click="crawl">
        <svg viewBox="0 0 24 24" width="15" height="15"><path d="M12 3v12m0 0-4.5-4.5M12 15l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>
        {{ crawling ? '采集中…' : '采集平台评论' }}
      </button>
      <button class="act ghost" @click="openAdd">
        <svg viewBox="0 0 24 24" width="15" height="15"><path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        新增文档
      </button>
    </div>

    <p class="crawl-state">
      系统每日 <b class="num">{{ schedule }}</b> 自动采集各平台评价并入库
      <span v-if="crawlAt"> · 最近一次：<b class="num">{{ crawlAt }}</b></span>
    </p>

    <!-- 公用文档库 -->
    <section class="lib-card">
      <div class="lc-head">
        <h4>公用文档库</h4>
        <span class="lc-count num">{{ pubDocs.length }}</span>
      </div>
      <div class="doc-list">
        <div v-for="d in pubDocs" :key="d.id" class="doc">
          <span class="doc-ico pub" v-html="ICON_DOC" />
          <div class="doc-body">
            <div class="doc-top">
              <b>{{ d.title }}</b>
              <span class="doc-tag">{{ typeLabel(d.doc_type) }}</span>
            </div>
            <p class="doc-meta">{{ d.source }} · {{ d.chars }} 字 · {{ d.chunks }} 块</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 本店专属文档库 -->
    <section class="lib-card">
      <div class="lc-head">
        <h4>本店专属文档库</h4>
        <span class="lc-count num">{{ privDocs.length }}</span>
      </div>
      <div class="doc-list">
        <div v-for="d in privDocs" :key="d.id" class="doc">
          <span class="doc-ico priv" v-html="ICON_DOC" />
          <div class="doc-body">
            <div class="doc-top">
              <b>{{ d.title }}</b>
              <span class="doc-tag">{{ typeLabel(d.doc_type) }}</span>
            </div>
            <p class="doc-meta">{{ d.source }} · {{ d.chars }} 字 · {{ d.chunks }} 块</p>
            <div v-if="d.editable || d.removable" class="doc-ops">
              <button v-if="d.editable" class="op" @click="openEdit(d)">编辑</button>
              <button v-if="d.removable" class="op danger" @click="askDelete(d)">删除</button>
            </div>
          </div>
        </div>
      </div>
      <p class="lib-tip">「民宿名称/地址/评分、AI 对话记录、平台采集评论」等本店信息会自动沉淀为专属文档，仅供本店 AI 检索使用。</p>
    </section>

    <!-- 新增 / 编辑弹窗 -->
    <transition name="ov">
      <div v-if="editing" class="overlay" @click.self="editing = null">
        <div class="sheet">
          <div class="sh-head">
            <h4>{{ editing.id ? '编辑文档' : '新增文档' }}</h4>
            <button class="sh-x" @click="editing = null">✕</button>
          </div>
          <label class="fld">
            <span>文档标题</span>
            <input v-model="form.title" placeholder="如：本店周边交通与景点攻略" />
          </label>
          <label class="fld">
            <span>文档内容</span>
            <textarea v-model="form.content" rows="6" placeholder="粘贴或输入要录入知识库的文本内容…" />
          </label>
          <div class="sheet-acts">
            <button class="act ghost" @click="editing = null">取消</button>
            <button class="act primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存入库' }}</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 删除确认 -->
    <transition name="ov">
      <div v-if="pendingDelete" class="overlay" @click.self="pendingDelete = null">
        <div class="confirm">
          <b>确认删除该文档？</b>
          <p>{{ pendingDelete.title }}</p>
          <div class="sheet-acts">
            <button class="act ghost" @click="pendingDelete = null">取消</button>
            <button class="act danger" @click="doDelete">确认删除</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="toast">
      <div v-if="tip" class="tip">{{ tip }}</div>
    </transition>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import api from '@/api'

const props = defineProps({ homestay: Object, user: Object })

const ICON_DOC = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></svg>'

const DOC_TYPE = {
  sop: '经营SOP', ota: 'OTA运营', finance: '财务贷后', competitor: '竞品数据',
  local: '本地文旅', homestay_profile: '经营档案', loan_contract: '贷款合同',
  chat_history: 'AI咨询记录', review_crawl: '平台评论', custom: '自定义'
}
const typeLabel = (t) => DOC_TYPE[t] || t || '文档'

const lib = ref({ documents: [] })
const crawling = ref(false)
const crawlAt = ref('')
const schedule = ref('03:00')
const editing = ref(null)
const pendingDelete = ref(null)
const saving = ref(false)
const tip = ref('')
let tipTimer = null

const pubDocs = computed(() => (lib.value.documents || []).filter((d) => d.scope === 'public'))
const privDocs = computed(() => (lib.value.documents || []).filter((d) => d.scope !== 'public'))
const form = ref({ title: '', content: '' })

function show(msg) {
  tip.value = msg
  clearTimeout(tipTimer)
  tipTimer = setTimeout(() => { tip.value = '' }, 1900)
}

async function load() {
  if (!props.homestay?.id) return
  try {
    lib.value = await api.ragDocuments(props.homestay.id)
  } catch (e) {
    show(e?.message || '文档库加载失败')
  }
  api.health()
    .then((h) => {
      schedule.value = h?.crawl?.schedule || schedule.value
      crawlAt.value = h?.crawl?.last_run || crawlAt.value
    })
    .catch(() => {})
}

async function crawl() {
  if (crawling.value) return
  crawling.value = true
  try {
    const res = await api.ragCrawl(props.homestay.id)
    lib.value = res?.library || lib.value
    const st = res?.state || {}
    crawlAt.value = st.last_run || ''
    show('已采集各平台评论并写入本店专属文档库')
  } catch (e) {
    show(e?.message || '采集失败，请确认后端服务已启动')
  } finally {
    crawling.value = false
  }
}

function openAdd() {
  editing.value = { id: '' }
  form.value = { title: '', content: '' }
}
function openEdit(d) {
  editing.value = d
  form.value = { title: d.title, content: d.content || '' }
}
function askDelete(d) {
  pendingDelete.value = d
}

async function save() {
  if (!form.value.title.trim()) return show('请填写文档标题')
  saving.value = true
  try {
    if (editing.value.id) {
      const res = await api.ragUpdateDocument(editing.value.id, {
        title: form.value.title.trim(), content: form.value.content
      })
      lib.value = res?.library || lib.value
      show('文档已更新')
    } else {
      const res = await api.ragAddDocument({
        homestay_id: props.homestay.id,
        title: form.value.title.trim(),
        content: form.value.content,
        scope: 'private',
        doc_type: 'custom'
      })
      lib.value = res?.library || lib.value
      show('文档已入库，AI 立即可检索')
    }
    editing.value = null
    await load()
  } catch (e) {
    show(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function doDelete() {
  const d = pendingDelete.value
  if (!d) return
  try {
    await api.ragDeleteDocument(d.id)
    pendingDelete.value = null
    show('文档已删除')
    await load()
  } catch (e) {
    show(e?.message || '删除失败')
  }
}

onMounted(load)
watch(() => props.homestay?.id, load)
</script>

<style scoped>
.rag { padding: 14px 14px 22px; }

/* 概览 */
.summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.sm-card {
  padding: 12px 6px; border-radius: 14px; text-align: center; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.sm-card b { display: block; font-size: 18px; line-height: 1.15; color: #165dff; }
.sm-card b.backend { font-size: 13px; color: #00a844; padding: 2px 0; }
.sm-card span { font-size: 10px; color: #86909c; }

.scope-note {
  margin-top: 12px; padding: 10px 12px; border-radius: 12px; font-size: 11px; color: #5a6473; line-height: 1.7;
  background: rgba(22, 93, 255, .05); border: 1px dashed rgba(22, 93, 255, .22);
}
.scope-note b { color: #165dff; }

/* 操作 */
.actions { display: grid; grid-template-columns: 1.2fr 1fr; gap: 9px; margin-top: 12px; }
.act {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 42px; border-radius: 12px; font-size: 12.5px; font-weight: 600;
  transition: transform .2s var(--ease-out), opacity .2s;
}
.act:not(:disabled):active { transform: scale(.98); }
.act.primary { color: #fff; background: linear-gradient(135deg, #4b83ff, #165dff); box-shadow: 0 14px 26px -16px rgba(22, 93, 255, .8); }
.act.ghost { color: #165dff; background: rgba(22, 93, 255, .09); border: 1px solid rgba(22, 93, 255, .2); }
.act.danger { color: #fff; background: linear-gradient(135deg, #ff7875, #f53f3f); }
.act:disabled { opacity: .55; }

.crawl-state { margin-top: 10px; font-size: 10.5px; color: #86909c; line-height: 1.7; }
.crawl-state b { color: #165dff; }

/* 文档库 */
.lib-card {
  margin-top: 14px; padding: 14px; border-radius: 16px; background: #fff;
  border: 1px solid rgba(29, 33, 41, .05); box-shadow: 0 12px 26px -22px rgba(10, 25, 47, .5);
}
.lc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.lc-head h4 { font-size: 14px; font-weight: 700; color: #1d2129; }
.lc-count { font-size: 12px; color: #165dff; background: rgba(22, 93, 255, .09); padding: 1px 9px; border-radius: 999px; }

.doc-list { display: flex; flex-direction: column; }
.doc { display: flex; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(29, 33, 41, .06); }
.doc:last-child { border-bottom: 0; }
.doc-ico { width: 30px; height: 30px; flex: 0 0 30px; border-radius: 10px; display: grid; place-items: center; }
.doc-ico.pub { color: #165dff; background: rgba(22, 93, 255, .1); }
.doc-ico.priv { color: #c98a00; background: rgba(255, 184, 0, .16); }
.doc-body { flex: 1; min-width: 0; }
.doc-top { display: flex; align-items: center; gap: 8px; }
.doc-top b { flex: 1; font-size: 13px; color: #1d2129; }
.doc-tag { flex: 0 0 auto; font-size: 10px; color: #165dff; background: rgba(22, 93, 255, .08); padding: 1px 7px; border-radius: 6px; }
.doc-meta { font-size: 10.5px; color: #a9b0bd; margin-top: 4px; }
.doc-ops { display: flex; gap: 8px; margin-top: 8px; }
.op { font-size: 11px; padding: 3px 12px; border-radius: 999px; color: #165dff; background: rgba(22, 93, 255, .08); }
.op.danger { color: #f53f3f; background: rgba(245, 63, 63, .08); }
.lib-tip { margin-top: 10px; font-size: 10.5px; color: #a9b0bd; line-height: 1.7; }

/* 弹窗 */
.overlay {
  position: absolute; inset: 0; z-index: 60; display: flex; align-items: flex-end; justify-content: center;
  padding: 16px; background: rgba(8, 14, 24, .55); backdrop-filter: blur(4px);
}
.sheet {
  width: 100%; background: #fff; border-radius: 18px; padding: 16px;
  box-shadow: 0 30px 60px -24px rgba(0, 0, 0, .6);
}
.sh-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sh-head h4 { font-size: 15px; color: #1d2129; }
.sh-x { font-size: 14px; color: #86909c; padding: 2px 6px; }
.fld { display: block; margin-bottom: 12px; }
.fld span { display: block; font-size: 11.5px; color: #4e5969; margin-bottom: 6px; }
.fld input, .fld textarea {
  width: 100%; padding: 10px 12px; border-radius: 11px; font-size: 12.5px; color: #1d2129; font-family: inherit;
  background: #f9fafc; border: 1.5px solid rgba(29, 33, 41, .08); outline: none; resize: none; line-height: 1.7;
  transition: all .22s;
}
.fld input:focus, .fld textarea:focus { border-color: #165dff; background: #fff; box-shadow: 0 0 0 4px rgba(22, 93, 255, .09); }
.sheet-acts { display: grid; grid-template-columns: 1fr 1.3fr; gap: 9px; margin-top: 4px; }
.confirm { width: 100%; background: #fff; border-radius: 18px; padding: 18px 16px; text-align: center; box-shadow: 0 30px 60px -24px rgba(0, 0, 0, .6); }
.confirm b { font-size: 14.5px; color: #1d2129; }
.confirm p { font-size: 12px; color: #86909c; margin: 8px 0 14px; word-break: break-all; }

.ov-enter-active, .ov-leave-active { transition: opacity .25s var(--ease-out); }
.ov-enter-from, .ov-leave-to { opacity: 0; }

.tip {
  position: fixed; left: 50%; bottom: 96px; transform: translateX(-50%); z-index: 80;
  max-width: 80%; padding: 10px 18px; border-radius: 11px; font-size: 12px;
  background: rgba(29, 33, 41, .93); color: #fff; text-align: center;
  box-shadow: 0 14px 30px -14px rgba(0, 0, 0, .7);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 10px); }
</style>
