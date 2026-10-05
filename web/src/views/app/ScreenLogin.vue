<template>
  <div class="login">
    <!-- 顶部渐变区 -->
    <div class="lg-hero">
      <div class="hero-deco" />
      <div class="hero-seal seal">豫宿巡</div>
      <h1 class="title-serif">让民宿赚得安心</h1>
      <p>AI 经营助手 · 工行「豫游民宿贷」贷后赋能</p>
      <div class="hero-tags">
        <span>洛阳</span><span>开封</span><span>安阳</span>
      </div>
    </div>

    <!-- 表单卡 -->
    <div class="lg-card">
      <div class="lg-tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        <span class="lg-ind" :style="{ transform: `translateX(${mode === 'login' ? 0 : '100'}%)` }" />
      </div>

      <div class="lg-fields">
        <label class="field">
          <span class="f-ico"><svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></span>
          <input v-model.trim="form.username" placeholder="请输入账号" autocomplete="username" />
        </label>

        <label class="field">
          <span class="f-ico"><svg viewBox="0 0 24 24" width="16" height="16"><rect x="4" y="10" width="16" height="10" rx="2.2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="1.8"/></svg></span>
          <input v-model.trim="form.password" :type="showPwd ? 'text' : 'password'" placeholder="请输入密码" autocomplete="current-password" />
          <button class="f-eye" @click="showPwd = !showPwd" type="button">
            <svg viewBox="0 0 24 24" width="16" height="16"><path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" stroke-width="1.7"/><path v-if="!showPwd" d="M4 20 20 4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
          </button>
        </label>

        <template v-if="mode === 'register'">
          <label class="field">
            <span class="f-ico"><svg viewBox="0 0 24 24" width="16" height="16"><path d="M4 5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5z" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M14 3v5h5" fill="none" stroke="currentColor" stroke-width="1.7"/></svg></span>
            <input v-model.trim="form.name" placeholder="业主姓名" />
          </label>
          <label class="field">
            <span class="f-ico"><svg viewBox="0 0 24 24" width="16" height="16"><rect x="6" y="2" width="12" height="20" rx="2.6" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M11 18.4h2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></span>
            <input v-model.trim="form.phone" placeholder="手机号" maxlength="11" />
          </label>
          <label class="field">
            <span class="f-ico"><svg viewBox="0 0 24 24" width="16" height="16"><path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9.5z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg></span>
            <select v-model="form.homestay_id" class="f-select">
              <option v-for="h in store.homestays" :key="h.id" :value="h.id">{{ h.name }}</option>
            </select>
          </label>
        </template>
      </div>

      <p v-if="error" class="lg-error">{{ error }}</p>

      <button class="lg-submit" :disabled="loading" @click="submit">
        <span v-if="loading" class="spin" />
        {{ loading ? '验证中…' : mode === 'login' ? '登 录' : '注册并登录' }}
      </button>

      <div v-if="mode === 'login'" class="lg-demo">
        <span class="ld-label">演示账号一键填充</span>
        <div class="ld-chips">
          <button v-for="d in demos" :key="d.u" class="ld-chip" @click="fill(d)">
            <b>{{ d.name }}</b>{{ d.u }}
          </button>
        </div>
      </div>

      <p class="lg-foot">
        <svg viewBox="0 0 24 24" width="12" height="12"><path d="M12 3 3 7v6c0 5 3.8 8.4 9 9 5.2-.6 9-4 9-9V7l-9-4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>
        登录信息仅用于演示，密码为明文存储的沙盒数据
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { store, bootstrap, persistUser } from '@/store'
import api from '@/api'

const emit = defineEmits(['authed'])
const props = defineProps({ apiState: Object })

const mode = ref('login')
const showPwd = ref(false)
const loading = ref(false)
const error = ref('')

const form = reactive({ username: 'ly001', password: '123456', name: '', phone: '', homestay_id: '' })

const demos = [
  { u: 'ly001', name: '张建国', p: '123456', tip: '洛阳·高风险' },
  { u: 'kf001', name: '王秀兰', p: '123456', tip: '开封·高风险' },
  { u: 'ly002', name: '李慧敏', p: '123456', tip: '洛阳·经营良好' }
]

function fill(d) {
  form.username = d.u
  form.password = d.p
  error.value = ''
}

async function submit() {
  error.value = ''
  if (!form.username || !form.password) { error.value = '请输入账号和密码'; return }
  if (mode.value === 'register' && (!form.name || !form.phone)) { error.value = '请填写姓名与手机号'; return }
  loading.value = true
  try {
    await bootstrap()
    let res
    if (mode.value === 'login') {
      res = await api.login(form.username, form.password)
    } else {
      res = await api.register({
        username: form.username,
        password: form.password,
        name: form.name,
        phone: form.phone,
        homestay_id: form.homestay_id || store.homestays[0]?.id || 'LY001'
      })
    }
    persistUser(res.user, res.token)
    emit('authed', res.user)
  } catch (e) {
    error.value = e?.message || '登录失败，请检查后端服务是否已启动'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await bootstrap()
  if (!form.homestay_id && store.homestays.length) form.homestay_id = store.homestays[0].id
})
</script>

<style scoped>
.login { display: flex; flex-direction: column; height: 100%; background: #f7f8fa; overflow-y: auto; }

/* 顶部 */
.lg-hero {
  position: relative; flex: 0 0 auto;
  padding: 54px 26px 34px;
  background: linear-gradient(140deg, #165dff 0%, #2f6dff 45%, #ffb800 145%);
  color: #fff; overflow: hidden;
  border-radius: 0 0 26px 26px;
}
.hero-deco {
  position: absolute; inset: 0; opacity: .28;
  background-image: radial-gradient(rgba(255, 255, 255, .5) 1px, transparent 1px);
  background-size: 20px 20px;
  mask-image: radial-gradient(ellipse 70% 80% at 80% 10%, #000, transparent 70%);
}
.hero-seal { position: absolute; right: 22px; top: 48px; border-color: rgba(255, 255, 255, .55); color: #fff; transform: rotate(-4deg); }
.lg-hero h1 { position: relative; font-size: 26px; letter-spacing: .1em; margin-top: 4px; }
.lg-hero p { position: relative; font-size: 12.5px; opacity: .9; margin-top: 8px; }
.hero-tags { position: relative; display: flex; gap: 8px; margin-top: 16px; }
.hero-tags span {
  font-size: 11px; padding: 3px 11px; border-radius: 999px;
  background: rgba(255, 255, 255, .18); border: 1px solid rgba(255, 255, 255, .28);
}

/* 表单卡 */
.lg-card {
  position: relative; flex: 1; margin: -18px 18px 18px; padding: 22px 20px 20px;
  background: #fff; border-radius: 20px;
  box-shadow: 0 20px 50px -28px rgba(10, 25, 47, .45);
}
.lg-tabs { position: relative; display: grid; grid-template-columns: 1fr 1fr; border-bottom: 1px solid rgba(29, 33, 41, .07); }
.lg-tabs button { height: 42px; font-size: 15px; color: #86909c; font-weight: 600; transition: color .25s; }
.lg-tabs button.active { color: #165dff; }
.lg-ind {
  position: absolute; bottom: -1px; left: 0; width: 50%; height: 2.5px; border-radius: 2px;
  background: linear-gradient(90deg, #165dff, #ffb800);
  transition: transform .34s var(--ease-spring);
}

.lg-fields { display: flex; flex-direction: column; gap: 13px; margin-top: 22px; }
.field {
  display: flex; align-items: center; gap: 10px; height: 48px; padding: 0 14px;
  border-radius: 12px; background: #f5f7fb; border: 1.5px solid transparent;
  transition: border-color .25s, background .25s;
}
.field:focus-within { border-color: #165dff; background: #fff; box-shadow: 0 0 0 4px rgba(22, 93, 255, .1); }
.f-ico { color: #86909c; line-height: 0; }
.field:focus-within .f-ico { color: #165dff; }
.field input, .f-select {
  flex: 1; min-width: 0; height: 100%; border: 0; outline: none; background: none;
  font-size: 14.5px; color: #1d2129; font-family: inherit;
}
.field input::placeholder { color: #a9b0bd; }
.f-select { appearance: none; cursor: pointer; }
.f-eye { color: #86909c; line-height: 0; padding: 4px; }

.lg-error {
  margin-top: 14px; font-size: 12.5px; color: #f53f3f;
  background: rgba(245, 63, 63, .08); border-radius: 9px; padding: 9px 12px;
}

.lg-submit {
  position: relative; width: 100%; height: 50px; margin-top: 20px; border-radius: 14px;
  font-size: 16px; font-weight: 700; letter-spacing: .18em; color: #fff;
  background: linear-gradient(135deg, #3d78ff, #165dff 60%, #0b3fa8);
  box-shadow: 0 16px 30px -14px rgba(22, 93, 255, .8);
  display: flex; align-items: center; justify-content: center; gap: 9px;
  transition: transform .2s var(--ease-out), box-shadow .3s;
}
.lg-submit:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 20px 36px -14px rgba(22, 93, 255, .9); }
.lg-submit:disabled { opacity: .75; }
.spin { width: 15px; height: 15px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, .35); border-top-color: #fff; animation: spin-slow .8s linear infinite; }

.lg-demo { margin-top: 22px; padding-top: 18px; border-top: 1px dashed rgba(29, 33, 41, .12); }
.ld-label { font-size: 11.5px; color: #86909c; letter-spacing: .06em; }
.ld-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.ld-chip {
  display: inline-flex; align-items: center; gap: 7px; height: 32px; padding: 0 12px;
  border-radius: 999px; font-size: 11.5px; color: #4e5969;
  background: #f5f7fb; border: 1px solid rgba(29, 33, 41, .06);
  font-family: var(--font-num); transition: all .25s var(--ease-out);
}
.ld-chip b { font-family: var(--font-sans); color: #1d2129; font-weight: 700; }
.ld-chip:hover { border-color: rgba(22, 93, 255, .4); color: #165dff; background: rgba(22, 93, 255, .06); transform: translateY(-2px); }

.lg-foot {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  margin-top: 18px; font-size: 10.5px; color: #a9b0bd;
}
</style>
