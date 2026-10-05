<template>
  <div class="assistant">
    <!-- 头部 -->
    <header class="as-head">
      <div class="ah-left">
        <div class="ah-avatar">
          <svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 0 6v2a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-2a3 3 0 0 1 0-6V7a4 4 0 0 1 4-4z" fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <h3>AI 经营助手</h3>
          <p><span class="live-dot" /> {{ modeLabel }} · 基于您的私有知识库</p>
        </div>
      </div>
      <div class="ah-iso" title="多租户隔离：仅检索本店 collection">
        <svg viewBox="0 0 24 24" width="13" height="13"><path d="M12 3 3 7v6c0 5 3.8 8.4 9 9 5.2-.6 9-4 9-9V7l-9-4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="m9 12 2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        数据隔离
      </div>
    </header>

    <!-- 消息区 -->
    <div ref="listEl" class="as-list no-scrollbar">
      <div class="as-tip">
        <span>🔒 本对话仅检索「{{ homestay?.name || '本店' }}」的私有知识库，其他民宿数据不会被检索到</span>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div v-if="m.role === 'ai'" class="msg-avatar">AI</div>
        <div class="bubble-wrap">
          <div class="bubble" v-html="render(m.text)" />
          <div v-if="m.sources && m.sources.length" class="sources">
            <div v-for="(s, si) in m.sources" :key="si" class="src" @click="s.show = !s.show">
              <span class="src-tag">📚 来源：{{ s.source || s.doc_type }}</span>
              <transition name="pop">
                <p v-if="s.show" class="src-snippet">{{ s.snippet }}</p>
              </transition>
            </div>
          </div>
          <div v-if="m.role === 'ai' && m.mode" class="msg-mode">{{ m.mode }}</div>
        </div>
      </div>

      <div v-if="typing" class="msg ai">
        <div class="msg-avatar">AI</div>
        <div class="bubble typing"><i /><i /><i /></div>
      </div>
    </div>

    <!-- 快捷指令 -->
    <div class="as-quick no-scrollbar">
      <button v-for="q in quicks" :key="q" class="quick-pill" :disabled="typing" @click="send(q)">{{ q }}</button>
    </div>

    <!-- 输入栏 -->
    <div class="as-input">
      <input v-model="draft" placeholder="问问经营难题，例如「国庆该怎么定价？」"
        @keyup.enter="send()" :disabled="typing" />
      <button class="send-btn" :disabled="typing || !draft.trim()" @click="send()">
        <svg viewBox="0 0 24 24" width="17" height="17"><path d="M3.5 20.5 21 12 3.5 3.5l3 7L15 12l-8.5 1.5-3 7z" fill="currentColor"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { store } from '@/store'
import api from '@/api'

const props = defineProps({ homestay: Object, user: Object })

const draft = ref('')
const typing = ref(false)
const listEl = ref(null)

const messages = ref([
  {
    role: 'ai',
    text: `您好，${props.user?.name || '老板'}！我是您的 AI 经营助手 👋\n\n我已接入**本店私有的经营 SOP、OTA 运营指南、贷款合同与本地文旅知识**。您可以问我：\n• 国庆该怎么给房间定价？\n• 卫生差评怎么整改？\n• 下个月要还多少钱？\n\n回答下方会标注引用来源，方便您核对。`,
    sources: [],
    mode: ''
  }
])

const modeLabel = computed(() => ({ qwen: '通义千问', deepseek: 'DeepSeek', offline: '本地知识库模式' }[store.llmMode] || '智能问答'))

const quicks = ['国庆该怎么定价？', '卫生差评怎么整改？', '下个月要还多少钱？', '帮我写一条营销文案']

/** 轻量 Markdown：加粗 + 换行 */
function render(text) {
  if (!text) return ''
  const esc = String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>')
}

async function send(preset) {
  const q = (preset || draft.value).trim()
  if (!q || typing.value) return
  draft.value = ''
  messages.value.push({ role: 'user', text: q })
  typing.value = true
  await scrollToBottom()
  try {
    const res = await api.chat(props.homestay?.id || 'LY001', q)
    const sources = (res?.sources || [])
      .filter((s) => (s.score === undefined || s.score > 0))
      .slice(0, 3)
      .map((s) => ({ ...s, show: false }))
    messages.value.push({
      role: 'ai',
      text: res?.answer || '（未获得回答）',
      sources,
      mode: res?.mode === 'offline' ? '离线知识库抽取（未配置大模型 API Key）' : '大模型 + RAG 检索增强生成'
    })
  } catch (e) {
    messages.value.push({
      role: 'ai',
      text: `抱歉，暂时无法连接后端服务。\n\n**错误信息**：${e?.message || '未知错误'}\n\n请确认已启动 FastAPI 后端（默认 http://127.0.0.1:8000）。`,
      sources: [],
      mode: ''
    })
  } finally {
    typing.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

onMounted(scrollToBottom)
</script>

<style scoped>
.assistant { display: flex; flex-direction: column; height: 100%; background: #f7f8fa; }

/* 头部 */
.as-head {
  flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 40px 16px 13px;
  background: linear-gradient(135deg, #165dff, #3a72ff 60%, #6f8dff);
  color: #fff;
}
.ah-left { display: flex; align-items: center; gap: 10px; }
.ah-avatar {
  width: 36px; height: 36px; border-radius: 12px; display: grid; place-items: center;
  background: rgba(255, 255, 255, .2); border: 1px solid rgba(255, 255, 255, .32);
}
.ah-left h3 { font-size: 15.5px; font-weight: 700; }
.ah-left p { display: flex; align-items: center; gap: 5px; font-size: 10.5px; opacity: .9; margin-top: 2px; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: #7dffa8; box-shadow: 0 0 8px #7dffa8; animation: soft-pulse 1.4s infinite; }
.ah-iso {
  display: inline-flex; align-items: center; gap: 5px; font-size: 10.5px;
  padding: 5px 10px; border-radius: 999px;
  background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .28);
}

/* 消息 */
.as-list { flex: 1; min-height: 0; overflow-y: auto; padding: 14px 14px 6px; display: flex; flex-direction: column; gap: 13px; }
.as-tip {
  font-size: 10.5px; color: #86909c; text-align: center; line-height: 1.7;
  background: rgba(22, 93, 255, .06); border: 1px dashed rgba(22, 93, 255, .22);
  border-radius: 10px; padding: 8px 11px;
}
.msg { display: flex; gap: 8px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar {
  flex: 0 0 28px; width: 28px; height: 28px; border-radius: 9px; display: grid; place-items: center;
  font-size: 10.5px; font-weight: 700; color: #fff;
  background: linear-gradient(140deg, #4b83ff, #165dff);
  box-shadow: 0 6px 14px -8px rgba(22, 93, 255, .8);
}
.bubble-wrap { max-width: 78%; display: flex; flex-direction: column; }
.msg.user .bubble-wrap { align-items: flex-end; }
.bubble {
  padding: 11px 13px; border-radius: 14px; font-size: 13px; line-height: 1.75;
  word-break: break-word;
}
.msg.ai .bubble {
  background: #fff; color: #1d2129; border-top-left-radius: 4px;
  box-shadow: 0 10px 24px -20px rgba(10, 25, 47, .5); border: 1px solid rgba(29, 33, 41, .05);
}
.msg.user .bubble {
  background: linear-gradient(135deg, #3d78ff, #165dff); color: #fff; border-top-right-radius: 4px;
  box-shadow: 0 10px 22px -14px rgba(22, 93, 255, .8);
}
.bubble :deep(strong) { color: #165dff; }
.msg.user .bubble :deep(strong) { color: #fff; }

.typing { display: flex; gap: 4px; align-items: center; padding: 14px 15px; }
.typing i { width: 6px; height: 6px; border-radius: 50%; background: #b8c2d3; animation: typing-dot 1.1s infinite; }
.typing i:nth-child(2) { animation-delay: .16s; }
.typing i:nth-child(3) { animation-delay: .32s; }

/* 来源 */
.sources { display: flex; flex-direction: column; gap: 6px; margin-top: 7px; }
.src { cursor: pointer; }
.src-tag {
  display: inline-block; font-size: 10.5px; color: #7a5a00;
  background: rgba(255, 184, 0, .18); border: 1px solid rgba(255, 184, 0, .34);
  padding: 3px 9px; border-radius: 999px;
}
.src-snippet {
  margin-top: 5px; font-size: 11px; color: #5a6473; line-height: 1.7;
  background: rgba(29, 33, 41, .04); border-left: 2px solid #ffb800;
  border-radius: 0 8px 8px 0; padding: 7px 10px;
}
.msg-mode { margin-top: 5px; font-size: 10px; color: #a9b0bd; }

/* 快捷指令 */
.as-quick {
  flex: 0 0 auto; display: flex; gap: 8px; padding: 8px 14px 4px; overflow-x: auto;
}
.quick-pill {
  flex: 0 0 auto; height: 30px; padding: 0 13px; border-radius: 999px; font-size: 11.5px;
  color: #165dff; background: rgba(22, 93, 255, .08); border: 1px solid rgba(22, 93, 255, .2);
  white-space: nowrap; transition: all .22s var(--ease-out);
}
.quick-pill:hover:not(:disabled) { background: rgba(22, 93, 255, .16); transform: translateY(-1px); }
.quick-pill:disabled { opacity: .5; }

/* 输入 */
.as-input {
  flex: 0 0 auto; display: flex; align-items: center; gap: 9px;
  padding: 8px 14px 12px; background: #f7f8fa;
}
.as-input input {
  flex: 1; height: 42px; padding: 0 15px; border-radius: 999px;
  border: 1.5px solid rgba(29, 33, 41, .08); background: #fff;
  font-size: 13px; color: #1d2129; outline: none; font-family: inherit;
  transition: border-color .25s, box-shadow .25s;
}
.as-input input:focus { border-color: #165dff; box-shadow: 0 0 0 4px rgba(22, 93, 255, .1); }
.as-input input::placeholder { color: #a9b0bd; font-size: 12.5px; }
.send-btn {
  flex: 0 0 42px; width: 42px; height: 42px; border-radius: 50%; color: #fff;
  background: linear-gradient(135deg, #4b83ff, #165dff); display: grid; place-items: center;
  box-shadow: 0 10px 22px -12px rgba(22, 93, 255, .85);
  transition: transform .22s var(--ease-out), opacity .22s;
}
.send-btn:hover:not(:disabled) { transform: scale(1.06); }
.send-btn:disabled { opacity: .45; }

.pop-enter-active { transition: all .22s var(--ease-out); }
.pop-enter-from { opacity: 0; transform: translateY(-4px); }
</style>
