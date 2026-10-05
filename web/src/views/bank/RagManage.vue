<template>
  <div class="rag">
    <!-- ========== 顶部：对象切换 + 操作 ========== -->
    <section class="bar glass">
      <div class="bar-left">
        <span class="mono-label">知识库对象</span>
        <div class="pk-select">
          <button class="pk-current" @click="open = !open">
            <span class="dot" :class="'risk-' + (hs?.risk_level || 'green')" />
            <b>{{ hs?.name || '加载中…' }}</b>
            <span class="pk-city">{{ hs?.city }}</span>
            <svg viewBox="0 0 24 24" width="14" height="14" :style="{ transform: open ? 'rotate(180deg)' : '' }"><path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <transition name="pop">
            <div v-if="open" class="pk-menu no-scrollbar">
              <button v-for="h in store.homestays" :key="h.id" class="pk-item" :class="{ active: h.id === id }" @click="select(h.id)">
                <span class="dot" :class="'risk-' + h.risk_level" />
                <span class="pki-name">{{ h.name }}</span>
                <span class="pki-city">{{ h.city }}</span>
              </button>
            </div>
          </transition>
        </div>
      </div>

      <div class="bar-mid">
        <span class="mono-label">向量集合</span>
        <code class="coll">{{ lib?.collection || '—' }}</code>
        <span class="backend" :class="lib?.backend === 'chromadb' ? 'ok' : 'warn'">
          {{ lib?.backend === 'chromadb' ? 'ChromaDB' : '内置检索（降级）' }}
        </span>
      </div>

      <div class="bar-right">
        <button class="btn btn-ghost" :disabled="crawling" @click="crawl">
          {{ crawling ? '采集中…' : '🛰 采集平台评论' }}
        </button>
        <button class="btn btn-primary" @click="openCreate">＋ 新增文档</button>
      </div>
    </section>

    <!-- ========== 统计条 ========== -->
    <section class="stats stagger">
      <div class="stat glass"><span class="s-label">公用文档</span><b class="num">{{ lib?.public_count ?? 0 }}</b><span class="s-sub">全部民宿共享</span></div>
      <div class="stat glass"><span class="s-label">本店专属</span><b class="num">{{ lib?.private_count ?? 0 }}</b><span class="s-sub">含档案 / 合同 / 对话</span></div>
      <div class="stat glass"><span class="s-label">文档总数</span><b class="num">{{ lib?.total_docs ?? 0 }}</b><span class="s-sub">检索文档库</span></div>
      <div class="stat glass"><span class="s-label">知识切片</span><b class="num">{{ lib?.total_chunks ?? 0 }}</b><span class="s-sub">分块后可检索单元</span></div>
      <div class="stat glass"><span class="s-label">最近采集</span><b class="num time">{{ shortTime(crawlState.last_run) }}</b><span class="s-sub">累计 {{ crawlState.count || 0 }} 次</span></div>
    </section>

    <!-- ========== 文档库 ========== -->
    <section class="lib" v-if="!loading">
      <div class="lib-col">
        <div class="col-head">
          <h4>公用文档库</h4>
          <span class="mono-label">PUBLIC · {{ publicDocs.length }}</span>
        </div>
        <div class="doc-list">
          <article v-for="d in publicDocs" :key="d.id" class="doc glass">
            <div class="doc-head">
              <span class="doc-ico pub" v-html="icoDoc" />
              <div class="doc-title">
                <b>{{ d.title }}</b>
                <div class="doc-meta">
                  <span class="type-badge">{{ typeText(d.doc_type) }}</span>
                  <span>{{ d.chars }} 字 · {{ d.chunks }} 切片</span>
                  <span>{{ d.updated_at }}</span>
                </div>
              </div>
            </div>
            <p class="doc-preview" :class="{ expanded: expanded[d.id] }">{{ d.content }}</p>
            <button class="doc-toggle" @click="expanded[d.id] = !expanded[d.id]">{{ expanded[d.id] ? '收起' : '展开全文' }}</button>
          </article>
          <p v-if="!publicDocs.length" class="empty">暂无公用文档</p>
        </div>
      </div>

      <div class="lib-col">
        <div class="col-head">
          <h4>本店专属文档库</h4>
          <span class="mono-label">PRIVATE · {{ privateDocs.length }}</span>
        </div>
        <div class="doc-list">
          <article v-for="d in privateDocs" :key="d.id" class="doc glass">
            <div class="doc-head">
              <span class="doc-ico priv" v-html="icoDoc" />
              <div class="doc-title">
                <b>{{ d.title }}</b>
                <div class="doc-meta">
                  <span class="type-badge">{{ typeText(d.doc_type) }}</span>
                  <span>{{ d.chars }} 字 · {{ d.chunks }} 切片</span>
                  <span>{{ d.source }}</span>
                </div>
              </div>
              <div v-if="d.editable" class="doc-ops">
                <button class="op" title="编辑" @click="openEdit(d)">编辑</button>
                <button class="op danger" title="删除" @click="remove(d)">删除</button>
              </div>
            </div>
            <p class="doc-preview" :class="{ expanded: expanded[d.id] }">{{ d.content }}</p>
            <button class="doc-toggle" @click="expanded[d.id] = !expanded[d.id]">{{ expanded[d.id] ? '收起' : '展开全文' }}</button>
          </article>
          <p v-if="!privateDocs.length" class="empty">暂无本店专属文档，可点击右上角「采集平台评论」或「新增文档」</p>
        </div>
      </div>
    </section>

    <div v-else class="loading glass"><div class="spin" />正在读取 RAG 文档库…</div>

    <p class="note">
      RAG 多租户隔离：每家民宿使用独立向量集合 <b>homestay_&lt;ID&gt;</b>，检索时只命中本店知识库与公用文档，绝不跨店串数据。
      每日定时自动采集各平台评论沉淀为本店专属文档（演示环境为合规模拟采集）。
    </p>

    <!-- ========== 新增 / 编辑 弹窗 ========== -->
    <transition name="ov">
      <div v-if="modal.show" class="overlay" @click.self="closeModal">
        <div class="modal glass">
          <div class="m-head">
            <h3>{{ modal.editId ? '编辑 RAG 文档' : '新增 RAG 文档' }}</h3>
            <button class="m-close" @click="closeModal">✕</button>
          </div>

          <div class="m-body">
            <label class="field">
              <span>文档标题</span>
              <input v-model="modal.title" type="text" placeholder="例如：本店卫生整改 SOP" />
            </label>

            <div class="field-row">
              <label class="field">
                <span>作用范围</span>
                <select v-model="modal.scope" :disabled="!!modal.editId">
                  <option value="private">本店专属（仅该民宿可见）</option>
                  <option value="public">公用文档（所有民宿可见）</option>
                </select>
              </label>
              <label class="field">
                <span>文档类型</span>
                <select v-model="modal.doc_type">
                  <option value="custom">自定义文档</option>
                  <option value="sop">经营 SOP</option>
                  <option value="ota">OTA 运营</option>
                  <option value="finance">财务 / 贷后</option>
                  <option value="policy">政策制度</option>
                  <option value="review_crawl">平台评论采集</option>
                </select>
              </label>
            </div>

            <label class="field">
              <span>文档正文</span>
              <textarea v-model="modal.content" rows="9" placeholder="粘贴知识文档正文，保存后自动分块并写入向量库，供 AI 检索使用…" />
            </label>
          </div>

          <div class="m-foot">
            <span class="m-hint">{{ scopeHint }}</span>
            <div class="m-actions">
              <button class="btn btn-ghost" @click="closeModal">取消</button>
              <button class="btn btn-primary" :disabled="saving || !modal.title.trim() || !modal.content.trim()" @click="save">
                {{ saving ? '保存中…' : (modal.editId ? '保存修改' : '写入文档库') }}
              </button>
            </div>
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { store } from '@/store'
import api from '@/api'
import { shortTime } from '@/utils/format'

const id = ref(store.currentHomestayId || 'LY001')
const open = ref(false)
const loading = ref(true)
const crawling = ref(false)
const lib = ref(null)
const expanded = reactive({})
const toast = ref('')
let toastTimer = null

const icoDoc = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></svg>'

const TYPE_TEXT = {
  sop: '经营SOP', ota: 'OTA运营', finance: '财务贷后', competitor: '竞品数据',
  local: '本地文旅', homestay_profile: '经营档案', loan_contract: '贷款合同',
  chat_history: 'AI对话记录', custom: '自定义', review_crawl: '评论采集', policy: '政策制度'
}
const typeText = (t) => TYPE_TEXT[t] || t

const modal = reactive({ show: false, editId: '', title: '', content: '', scope: 'private', doc_type: 'custom' })
const saving = ref(false)

const hs = computed(() => store.homestays.find((h) => h.id === id.value) || null)
const docs = computed(() => lib.value?.documents || [])
const publicDocs = computed(() => docs.value.filter((d) => d.scope === 'public'))
const privateDocs = computed(() => docs.value.filter((d) => d.scope === 'private'))
const crawlState = computed(() => store.dashboard?.crawl || {})
const scopeHint = computed(() =>
  modal.scope === 'public'
    ? '公用文档写入后，所有民宿的 AI 助手均可检索到该内容。'
    : '本店专属文档仅写入该民宿的向量集合，其他民宿无法检索。'
)

async function load() {
  loading.value = true
  try {
    lib.value = await api.ragDocuments(id.value)
  } catch (e) {
    lib.value = null
    show(e?.message || '文档库读取失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

function select(newId) {
  open.value = false
  id.value = newId
  store.currentHomestayId = newId
}

async function crawl() {
  if (crawling.value) return
  crawling.value = true
  try {
    const res = await api.ragCrawl(id.value)
    lib.value = res?.library || lib.value
    store.dashboard = await api.dashboard().catch(() => store.dashboard)
    show(`已采集平台评论并写入本店专属文档库（${res?.doc?.title || ''}）`)
  } catch (e) {
    show(e?.message || '采集失败，请确认后端已启动')
  } finally {
    crawling.value = false
  }
}

function openCreate() {
  Object.assign(modal, { show: true, editId: '', title: '', content: '', scope: 'private', doc_type: 'custom' })
}

function openEdit(d) {
  Object.assign(modal, {
    show: true, editId: d.id, title: d.title, content: d.content,
    scope: d.scope, doc_type: d.doc_type
  })
}

function closeModal() {
  modal.show = false
}

async function save() {
  if (saving.value) return
  saving.value = true
  try {
    if (modal.editId) {
      const res = await api.ragUpdateDocument(modal.editId, {
        title: modal.title, content: modal.content, doc_type: modal.doc_type
      })
      if (res?.library) lib.value = res.library
      show('文档已更新，向量库已重建')
    } else {
      const res = await api.ragAddDocument({
        homestay_id: id.value, title: modal.title, content: modal.content,
        doc_type: modal.doc_type, scope: modal.scope, tags: []
      })
      if (res?.library) lib.value = res.library
      else await load()
      show(modal.scope === 'public' ? '公用文档已写入，全部民宿可检索' : '本店专属文档已写入知识库')
    }
    closeModal()
  } catch (e) {
    show(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(d) {
  try {
    const res = await api.ragDeleteDocument(d.id)
    if (res?.library) lib.value = res.library
    else await load()
    show(`已删除文档：${d.title}`)
  } catch (e) {
    show(e?.message || '删除失败')
  }
}

function show(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 3200)
}

watch(id, load)
onMounted(() => {
  if (store.homestays.length && !store.homestays.find((h) => h.id === id.value)) id.value = store.homestays[0].id
  load()
})
</script>

<style scoped>
.rag { display: flex; flex-direction: column; gap: 16px; }

/* 顶部操作条 */
.bar { position: relative; z-index: 30; display: flex; align-items: center; gap: 26px; padding: 15px 18px; border-radius: var(--r-md); flex-wrap: wrap; }
.bar-left { display: flex; flex-direction: column; gap: 6px; }
.bar-mid { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 220px; }
.coll { font-family: var(--font-num); font-size: 12.5px; color: #cfe0ff; background: rgba(22, 93, 255, .12); padding: 4px 10px; border-radius: 7px; border: 1px solid rgba(22, 93, 255, .25); }
.backend { font-size: 11.5px; padding: 3px 10px; border-radius: 999px; }
.backend.ok { color: #9ff0b4; background: rgba(0, 180, 42, .14); border: 1px solid rgba(0, 180, 42, .34); }
.backend.warn { color: #ffd08a; background: rgba(255, 125, 0, .14); border: 1px solid rgba(255, 125, 0, .34); }
.bar-right { display: flex; align-items: center; gap: 10px; }

/* 选择器（复用 Archive 风格） */
.pk-select { position: relative; }
.pk-current {
  display: flex; align-items: center; gap: 10px; height: 42px; padding: 0 15px;
  border-radius: 10px; background: rgba(22, 93, 255, .1); border: 1px solid rgba(22, 93, 255, .3);
  color: #fff; font-size: 15px; transition: background .25s;
}
.pk-current:hover { background: rgba(22, 93, 255, .2); }
.pk-current b { font-weight: 600; }
.pk-city { font-size: 11.5px; color: var(--text-3); padding: 1px 7px; background: rgba(255, 255, 255, .06); border-radius: 5px; }
.pk-menu {
  position: absolute; z-index: 40; top: calc(100% + 6px); left: 0; width: 360px; max-height: 330px; overflow-y: auto;
  padding: 6px; border-radius: 12px; background: rgba(9, 22, 42, .97);
  border: 1px solid var(--line-strong); box-shadow: var(--shadow-lift); backdrop-filter: blur(14px);
}
.pk-item { display: flex; align-items: center; gap: 9px; width: 100%; text-align: left; padding: 9px 11px; border-radius: 8px; color: var(--text-2); font-size: 13px; transition: background .2s; }
.pk-item:hover { background: rgba(22, 93, 255, .16); color: #fff; }
.pk-item.active { background: rgba(22, 93, 255, .26); color: #fff; }
.pki-name { flex: 1; }
.pki-city { font-size: 11px; color: var(--text-3); }

/* 统计 */
.stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.stat { padding: 14px 16px; border-radius: var(--r-md); display: flex; flex-direction: column; gap: 3px; }
.s-label { font-size: 12px; color: var(--text-3); }
.stat b { font-size: 27px; color: #fff; line-height: 1.1; }
.stat b.time { font-size: 18px; }
.s-sub { font-size: 11px; color: var(--text-3); }

/* 文档库 */
.lib { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
.lib-col { display: flex; flex-direction: column; gap: 10px; }
.col-head { display: flex; align-items: baseline; justify-content: space-between; padding: 0 2px; }
.col-head h4 { font-size: 14.5px; color: var(--text-1); font-weight: 700; letter-spacing: .04em; }
.doc-list { display: flex; flex-direction: column; gap: 10px; }
.doc { padding: 13px 15px; border-radius: var(--r-md); }
.doc-head { display: flex; align-items: flex-start; gap: 11px; }
.doc-ico { width: 30px; height: 30px; flex: 0 0 30px; border-radius: 9px; display: grid; place-items: center; margin-top: 1px; }
.doc-ico.pub { color: #7fb0ff; background: rgba(22, 93, 255, .14); }
.doc-ico.priv { color: #ffcd4d; background: rgba(255, 184, 0, .16); }
.doc-title { flex: 1; min-width: 0; }
.doc-title b { font-size: 13.5px; color: var(--text-1); }
.doc-meta { display: flex; align-items: center; gap: 10px; margin-top: 5px; font-size: 11px; color: var(--text-3); flex-wrap: wrap; }
.type-badge { font-size: 10.5px; color: #cfe0ff; background: rgba(22, 93, 255, .14); border: 1px solid rgba(22, 93, 255, .24); padding: 1px 8px; border-radius: 999px; }
.doc-ops { display: flex; gap: 6px; flex: 0 0 auto; }
.op { font-size: 11.5px; padding: 3px 11px; border-radius: 7px; color: var(--text-2); border: 1px solid var(--line); transition: all .2s; }
.op:hover { color: #fff; border-color: var(--line-strong); background: rgba(22, 93, 255, .14); }
.op.danger:hover { color: #ffb4b4; border-color: rgba(245, 63, 63, .45); background: rgba(245, 63, 63, .12); }
.doc-preview {
  margin-top: 10px; font-size: 12px; color: var(--text-2); line-height: 1.75; white-space: pre-wrap;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.doc-preview.expanded { -webkit-line-clamp: unset; max-height: 340px; overflow-y: auto; }
.doc-toggle { margin-top: 7px; font-size: 11.5px; color: var(--brand-blue-400); }
.doc-toggle:hover { text-decoration: underline; }
.empty { padding: 22px; text-align: center; font-size: 12.5px; color: var(--text-3); border: 1px dashed var(--line); border-radius: var(--r-md); }

.loading { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 46px; border-radius: var(--r-md); color: var(--text-3); font-size: 13px; }
.spin { width: 22px; height: 22px; border-radius: 50%; border: 2px solid rgba(22, 93, 255, .2); border-top-color: var(--brand-blue); animation: spin-slow .9s linear infinite; }

.note { font-size: 11.5px; color: var(--text-3); line-height: 1.8; text-align: center; }
.note b { color: #cfe0ff; font-family: var(--font-num); }

/* 弹窗 */
.overlay { position: fixed; inset: 0; z-index: 80; display: flex; align-items: center; justify-content: center; padding: 26px; background: rgba(4, 10, 20, .72); backdrop-filter: blur(8px); }
.modal { width: min(720px, 100%); max-height: 88vh; display: flex; flex-direction: column; border-radius: var(--r-lg); overflow: hidden; }
.m-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--line); }
.m-head h3 { font-size: 16.5px; color: #fff; font-family: var(--font-serif); letter-spacing: .06em; }
.m-close { font-size: 15px; color: var(--text-3); width: 30px; height: 30px; border-radius: 8px; }
.m-close:hover { color: #fff; background: rgba(255, 255, 255, .08); }
.m-body { padding: 20px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
.field { display: flex; flex-direction: column; gap: 7px; }
.field > span { font-size: 12.5px; color: var(--text-2); }
.field input, .field select, .field textarea {
  width: 100%; border-radius: 10px; background: rgba(255, 255, 255, .04);
  border: 1px solid var(--line); color: var(--text-1); font-size: 13.5px;
  padding: 10px 12px; outline: none; font-family: inherit; transition: all .22s;
}
.field textarea { resize: vertical; line-height: 1.7; }
.field input::placeholder, .field textarea::placeholder { color: var(--text-3); }
.field input:focus, .field select:focus, .field textarea:focus { border-color: var(--brand-blue); box-shadow: 0 0 0 4px var(--accent-soft); background: rgba(22, 93, 255, .06); }
.field select option { background: #0d2140; color: #eaf2ff; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.m-foot { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 15px 22px; border-top: 1px solid var(--line); background: rgba(8, 20, 36, .5); }
.m-hint { font-size: 11.5px; color: var(--text-3); line-height: 1.6; }
.m-actions { display: flex; gap: 10px; }

/* 弹层动画 */
.ov-enter-active, .ov-leave-active { transition: opacity .26s var(--ease-out); }
.ov-enter-from, .ov-leave-to { opacity: 0; }
.pop-enter-active { transition: all .22s var(--ease-out); }
.pop-leave-active { transition: all .16s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-8px); }

.toast {
  position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%);
  padding: 12px 22px; border-radius: 11px; font-size: 13.5px; z-index: 99;
  background: rgba(10, 25, 47, .96); border: 1px solid var(--line-strong); color: var(--text-1); box-shadow: var(--shadow-lift);
}
.toast-enter-active, .toast-leave-active { transition: all .3s var(--ease-out); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translate(-50%, 14px); }

@media (max-width: 1280px) { .stats { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 1080px) { .lib { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .stats { grid-template-columns: repeat(2, 1fr); } .field-row { grid-template-columns: 1fr; } }
</style>
