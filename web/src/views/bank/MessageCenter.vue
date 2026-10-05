<template>
  <div class="mc">
    <!-- 左：会话列表 -->
    <aside class="mc-list panel glass">
      <div class="mc-head">
        <h4>会话列表</h4>
        <span class="mono-label">{{ convs.length }} 家民宿</span>
      </div>
      <div class="conv no-scrollbar">
        <button v-for="c in convs" :key="c.id" class="conv-item"
          :class="{ active: c.id === current, 'is-red': c.risk_level === 'red', 'is-amber': c.risk_level === 'amber' }"
          @click="openConv(c)">
          <span class="cv-ava num">{{ c.name[0] }}</span>
          <div class="cv-body">
            <div class="cv-top">
              <b>{{ c.name }}</b>
              <span class="cv-city">{{ c.city }}</span>
            </div>
            <p class="cv-sub">{{ c.sub || '暂无消息，可在右侧发起触点' }}</p>
          </div>
          <span v-if="c.unread" class="cv-dot num">{{ c.unread }}</span>
          <span v-else class="cv-time num">{{ fmtShort(c.at) }}</span>
        </button>
        <div v-if="!convs.length" class="mc-empty">暂无会话。老板在 App「我的贷款 → 联系客户经理」留言后会出现在这里</div>
      </div>
    </aside>

    <!-- 右：聊天详情 -->
    <section class="mc-detail panel glass">
      <template v-if="currentHs">
        <div class="mc-dhead">
          <div class="mc-owner">
            <span class="od-ava num">{{ currentHs.name[0] }}</span>
            <div>
              <b>{{ currentHs.name }}</b>
              <p>{{ currentHs.city }} · {{ ownerName }} {{ ownerPhone }}</p>
            </div>
          </div>
          <span class="level-tag" :class="'risk-' + currentHs.risk_level">{{ riskText[currentHs.risk_level] }}</span>
        </div>

        <div ref="bodyEl" class="mc-body no-scrollbar">
          <div v-for="m in msgs" :key="m.id" class="mb" :class="m.sender === 'bank' ? 'bank' : 'owner'">
            <div class="mb-meat">
              <p>{{ m.text }}</p>
              <span class="mb-time num">{{ fmtHm(m.at) }}</span>
            </div>
          </div>
          <div v-if="!msgs.length" class="mc-empty">还没有留言。老板在 App 中发送消息后会实时同步到本会话。</div>
        </div>

        <div class="mc-input">
          <input v-model="draft" maxlength="500" placeholder="输入回复内容，老板端 App 每 5 秒同步一次…" @keyup.enter="send" />
          <button class="mc-send" :disabled="!draft.trim()" @click="send">回复</button>
        </div>
      </template>
      <div v-else class="mc-placeholder">
        <svg viewBox="0 0 24 24" width="46" height="46"><path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 10.5h6M9 13.5h4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        <p>从左侧选择一个民宿会话，开始与老板沟通</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '@/api'
import { store, homestayById } from '@/store'
import { RISK_TEXT } from '@/utils/format'

const riskText = RISK_TEXT

const current = ref('')
const draft = ref('')
const bodyEl = ref(null)
const all = ref([]) // 全部消息（含 homestay_id）
let timer = null

const convs = computed(() =>
  store.homestays.map((h) => {
    const ms = all.value.filter((m) => m.homestay_id === h.id)
    const last = ms[ms.length - 1]
    return {
      id: h.id,
      name: h.name,
      city: h.city,
      risk_level: h.risk_level,
      owner_name: (h.owner || {}).name,
      owner_phone: (h.owner || {}).phone,
      at: last ? last.at : '',
      sub: last ? `${last.sender === 'owner' ? '老板' : '经理'}：${last.text}` : '',
      unread: ms.filter((m) => m.sender === 'owner' && !m.read).length
    }
  }).sort((a, b) => String(b.at).localeCompare(String(a.at)))
)

const currentHs = computed(() => (current.value ? homestayById(current.value) : null))
const ownerName = computed(() => currentHs.value?.owner?.name || '')
const ownerPhone = computed(() => currentHs.value?.owner?.phone || '')
const msgs = computed(() => all.value.filter((m) => m.homestay_id === current.value))

const nums = (n) => String(n).padStart(2, '0')
function fmtHm(s) {
  if (!s) return ''
  const d = new Date(String(s).replace(' ', 'T'))
  return `${nums(d.getHours())}:${nums(d.getMinutes())}`
}
function fmtShort(s) {
  if (!s) return ''
  const d = new Date(String(s).replace(' ', 'T'))
  return `${d.getMonth() + 1}/${d.getDate()} ${fmtHm(s)}`
}

async function refresh() {
  try {
    const raws = await api.messages()
    if (Array.isArray(raws)) all.value = raws
  } catch { /* 后端未启动时忽略 */ }
}

async function openConv(c) {
  current.value = c.id
  draft.value = ''
  scrollBottom()
  if (c.unread) {
    try { await api.markMessagesRead(c.id) } catch { /* ignore */ }
    await refresh()
  }
}

async function send() {
  const t = draft.value.trim()
  if (!t || !current.value) return
  draft.value = ''
  try {
    await api.sendMessage(current.value, 'bank', t)
  } catch (e) {
    draft.value = t
    alert(e?.message || '发送失败，请确认后端已启动')
    return
  }
  await refresh()
  scrollBottom()
}

function scrollBottom() {
  nextTick(() => {
    if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
  })
}

onMounted(async () => {
  await refresh()
  // 默认选中最近有动态（或最早有未读）的会话
  const sorted = [...convs.value].sort((a, b) => (b.unread || 0) - (a.unread || 0) || String(b.at).localeCompare(String(a.at)))
  const first = sorted[0]
  if (first && (first.at || first.unread)) current.value = first.id
  scrollBottom()
  timer = setInterval(async () => {
    await refresh()
    if (current.value) scrollBottom()
  }, 5000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.mc { display: grid; grid-template-columns: 330px minmax(0, 1fr); gap: 16px; height: calc(100vh - 128px); }

/* 会话列表 */
.mc-list { display: flex; flex-direction: column; padding: 16px 14px; overflow: hidden; }
.mc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding: 0 2px; }
.mc-head h4 { font-size: 14.5px; color: var(--text-1); font-weight: 700; letter-spacing: .04em; }
.conv { flex: 1; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; padding-right: 2px; }
.conv-item {
  display: flex; align-items: center; gap: 11px; width: 100%; text-align: left;
  padding: 11px 12px; border-radius: 12px;
  background: rgba(255, 255, 255, .025); border: 1px solid var(--line);
  transition: background .25s, border-color .25s, transform .25s;
}
.conv-item:hover { background: rgba(22, 93, 255, .1); border-color: var(--line-strong); transform: translateX(3px); }
.conv-item.active { background: linear-gradient(90deg, rgba(22, 93, 255, .24), rgba(22, 93, 255, .05)); border-color: rgba(22, 93, 255, .4); }
.conv-item.is-red.active { border-color: rgba(245, 63, 63, .45); }
.cv-ava {
  flex: 0 0 40px; width: 40px; height: 40px; border-radius: 12px;
  display: grid; place-items: center; font-size: 16px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #165dff, #0b3fa8);
  border: 1px solid rgba(120, 175, 255, .35);
}
.is-red .cv-ava { background: linear-gradient(135deg, #f53f3f, #a8071a); border-color: rgba(255, 120, 120, .4); }
.is-amber .cv-ava { background: linear-gradient(135deg, #ff7d00, #b25b00); border-color: rgba(255, 190, 90, .4); }
.cv-body { flex: 1; min-width: 0; }
.cv-top { display: flex; align-items: baseline; gap: 7px; }
.cv-top b { font-size: 13px; color: var(--text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cv-city { font-size: 10.5px; color: var(--text-3); flex: 0 0 auto; }
.cv-sub { font-size: 11.5px; color: var(--text-3); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cv-dot {
  flex: 0 0 auto; min-width: 19px; height: 19px; padding: 0 5px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; color: #fff; background: var(--risk-red); box-shadow: 0 0 10px var(--risk-red-glow);
}
.cv-time { flex: 0 0 auto; font-size: 10.5px; color: var(--text-3); font-family: var(--font-num); }

/* 聊天详情 */
.mc-detail { display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.mc-dhead {
  display: flex; align-items: center; justify-content: space-between;
  padding: 15px 20px; border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(22, 93, 255, .1), transparent);
}
.mc-owner { display: flex; align-items: center; gap: 12px; }
.od-ava {
  width: 42px; height: 42px; border-radius: 13px;
  display: grid; place-items: center; font-size: 17px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #165dff, #0b3fa8);
  border: 1px solid rgba(120, 175, 255, .4);
}
.mc-owner b { font-size: 14.5px; color: var(--text-1); }
.mc-owner p { font-size: 11px; color: var(--text-3); margin-top: 3px; }
.mc-dhead .level-tag { height: 22px; font-size: 11px; }

.mc-body { flex: 1; padding: 18px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.mb { display: flex; max-width: 68%; }
.mb.owner { align-self: flex-start; }
.mb.bank { align-self: flex-end; }
.mb-meat { padding: 10px 14px; border-radius: 14px; position: relative; }
.mb-meat p { font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.mb-time { display: block; font-size: 9.5px; margin-top: 5px; font-family: var(--font-num); }
.mb.owner .mb-meat { background: #f2f4f8; color: #1d2129; border-top-left-radius: 4px; }
.mb.owner .mb-time { color: #a9b0bd; }
.mb.bank .mb-meat { background: linear-gradient(135deg, #2f6dff, #165dff); color: #fff; border-top-right-radius: 4px; box-shadow: 0 10px 24px -14px var(--accent-glow); }
.mb.bank .mb-time { color: rgba(255, 255, 255, .75); text-align: right; }

.mc-input { display: flex; gap: 10px; padding: 14px 16px; border-top: 1px solid var(--line); }
.mc-input input {
  flex: 1; height: 42px; padding: 0 14px; border-radius: 11px; font-size: 13px;
  color: var(--text-1); background: rgba(255, 255, 255, .05);
  border: 1.5px solid var(--line); outline: none; font-family: inherit;
  transition: border-color .22s, background .22s;
}
.mc-input input::placeholder { color: var(--text-3); }
.mc-input input:focus { border-color: var(--brand-blue); background: rgba(255, 255, 255, .08); }
.mc-send {
  flex: 0 0 auto; height: 42px; padding: 0 22px; border-radius: 11px;
  font-size: 13px; font-weight: 700; color: #fff;
  background: linear-gradient(135deg, #2f6dff, #165dff);
  box-shadow: 0 10px 22px -12px var(--accent-glow);
  transition: opacity .2s, transform .2s;
}
.mc-send:disabled { opacity: .5; }
.mc-send:not(:disabled):active { transform: scale(.97); }

.mc-empty { padding: 26px 10px; text-align: center; color: var(--text-3); font-size: 12.5px; line-height: 1.7; }
.mc-placeholder {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px;
  color: var(--text-3); font-size: 13px;
}
.mc-placeholder svg { opacity: .5; }

@media (max-width: 1080px) { .mc { grid-template-columns: 260px minmax(0, 1fr); } }
@media (max-width: 860px) { .mc { grid-template-columns: 1fr; height: auto; } .mc-list { max-height: 280px; } }
</style>