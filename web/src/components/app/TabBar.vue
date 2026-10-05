<template>
  <nav class="tabbar">
    <button v-for="t in leftTabs" :key="t.key" class="tab" :class="{ active: modelValue === t.key }" @click="$emit('update:modelValue', t.key)">
      <span class="ti">
        <span class="ti-ico ti-off" v-html="t.icon" />
        <span class="ti-ico ti-on" v-html="t.iconActive" />
      </span>
      <span class="tl">{{ t.label }}</span>
      <span v-if="t.key === 'rectify' && badge" class="tab-badge num">{{ badge > 9 ? '9+' : badge }}</span>
    </button>

    <button class="tab center" :class="{ active: modelValue === 'assistant' }" @click="$emit('update:modelValue', 'assistant')">
      <span class="center-btn">
        <span class="cb-ring" />
        <span class="ti">
          <span class="ti-ico ti-off" v-html="ASSISTANT_ICON" />
          <span class="ti-ico ti-on" v-html="ASSISTANT_ICON_ACTIVE" />
        </span>
        <i v-if="badge" class="center-dot" />
      </span>
      <span class="tl center-label">AI助手</span>
    </button>

    <button v-for="t in rightTabs" :key="t.key" class="tab" :class="{ active: modelValue === t.key }" @click="$emit('update:modelValue', t.key)">
      <span class="ti">
        <span class="ti-ico ti-off" v-html="t.icon" />
        <span class="ti-ico ti-on" v-html="t.iconActive" />
      </span>
      <span class="tl">{{ t.label }}</span>
    </button>
  </nav>
</template>

<script setup>
/**
 * 底部导航栏。
 * 选中态提示：① 图标由「线性」切换为「实心」；② 图标与文字变品牌蓝；
 *           ③ 胶囊高亮底色 + 顶部指示条；④ 图标轻微上浮放大。
 * 注意：必须使用 modelValue 属性，才能与父组件 v-model 正确对接。
 */
defineProps({ modelValue: { type: String, default: '' }, badge: { type: Number, default: 0 } })
defineEmits(['update:modelValue'])

const leftTabs = [
  {
    key: 'home', label: '首页',
    icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 4l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z"/></svg>',
    iconActive: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none"><path d="M11.33 3.31a1 1 0 0 1 1.34 0l8 6.94c.21.18.33.45.33.73V20a2 2 0 0 1-2 2h-3.5v-5.1a1.2 1.2 0 0 0-1.2-1.2h-2.6a1.2 1.2 0 0 0-1.2 1.2V22H5a2 2 0 0 1-2-2v-9.02c0-.28.12-.55.33-.73l8-6.94Z" fill="currentColor"/></svg>'
  },
  {
    key: 'rectify', label: '预警',
    icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
    iconActive: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none"><path d="M12 2.2a6.6 6.6 0 0 0-6.6 6.6c0 3-.64 5.12-1.28 6.54-.32.71-.57 1.23-.73 1.53l-.15.28a1 1 0 0 0 .88 1.46h15.76a1 1 0 0 0 .88-1.46l-.15-.28c-.16-.3-.41-.82-.73-1.53-.64-1.42-1.28-3.54-1.28-6.54A6.6 6.6 0 0 0 12 2.2Z" fill="currentColor"/><path d="M9.6 20.3a2.6 2.6 0 0 0 4.8 0H9.6Z" fill="currentColor"/></svg>'
  }
]
const rightTabs = [
  {
    key: 'creative', label: 'AI文创',
    icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.6" cy="8.6" r="1.7"/><path d="m4 17 5-5 4 4 3-3 4 4"/></svg>',
    iconActive: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none"><defs><clipPath id="ysxTabCv"><rect x="3" y="3" width="18" height="18" rx="4.4"/></clipPath></defs><rect x="3" y="3" width="18" height="18" rx="4.4" fill="currentColor"/><g clip-path="url(#ysxTabCv)" fill="#fff"><circle cx="8.7" cy="8.7" r="1.9"/><path d="M2.4 21.4l6.6-6.6a1.7 1.7 0 0 1 2.4 0l2.2 2.2 3.3-3.3a1.7 1.7 0 0 1 2.4 0l4.3 4.3v3.4H2.4z"/></g></svg>'
  },
  {
    key: 'mine', label: '我的',
    icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></svg>',
    iconActive: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none"><circle cx="12" cy="8" r="4.2" fill="currentColor"/><path d="M12 13.6c-4.4 0-8 2.5-8 5.7 0 .9.7 1.7 1.6 1.7h12.8c.9 0 1.6-.8 1.6-1.7 0-3.2-3.6-5.7-8-5.7Z" fill="currentColor"/></svg>'
  }
]

/** 中央 AI 助手按钮：线性 → 实心（白色填充 + 蓝色笔画，保持蓝色圆底上的可读性） */
const ASSISTANT_ICON =
  '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 0 6v2a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-2a3 3 0 0 1 0-6V7a4 4 0 0 1 4-4z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M12 8.6v6.8M9.4 11h5.2M9.4 14.4h5.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
const ASSISTANT_ICON_ACTIVE =
  '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 3a4 4 0 0 1 4 4v1a3 3 0 0 1 0 6v2a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3v-2a3 3 0 0 1 0-6V7a4 4 0 0 1 4-4z" fill="currentColor"/><path d="M12 8.6v6.8M9.4 11h5.2M9.4 14.4h5.2" stroke="#165dff" stroke-width="1.5" stroke-linecap="round"/></svg>'
</script>

<style scoped>
.tabbar {
  position: relative; flex: 0 0 auto;
  display: grid; grid-template-columns: 1fr 1fr 1.18fr 1fr 1fr;
  align-items: end;
  height: 66px; padding: 6px 6px 8px;
  background: rgba(255, 255, 255, .96);
  border-top: 1px solid rgba(29, 33, 41, .07);
  backdrop-filter: blur(18px);
  box-shadow: 0 -8px 26px -18px rgba(0, 0, 0, .28);
}
.tab {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 5px 0; color: #86909c; transition: color .22s var(--ease-out);
}
/* 选中态：胶囊高亮底色 + 主色文字，明确提示当前所在栏目 */
.tab::before {
  content: ""; position: absolute; top: 1px; left: 50%; transform: translateX(-50%) scale(.72);
  width: 52px; height: 40px; border-radius: 13px;
  background: linear-gradient(160deg, rgba(22, 93, 255, .14), rgba(22, 93, 255, .07));
  opacity: 0; transition: opacity .24s var(--ease-out), transform .3s var(--ease-spring);
}
.tab.active::before { opacity: 1; transform: translateX(-50%) scale(1); }
.tab.active { color: #165dff; }
.tab:not(.center).active .tl { color: #165dff; }
/* 图标：默认线性，选中切换为实心（叠放交叉淡入淡出） */
.ti {
  position: relative; display: block; width: 21px; height: 21px; line-height: 0;
  transition: transform .28s var(--ease-spring);
}
.ti-ico {
  position: absolute; inset: 0; display: grid; place-items: center;
  transition: opacity .2s var(--ease-out), transform .3s var(--ease-spring);
}
.ti-off { opacity: 1; transform: scale(1); }
.ti-on { opacity: 0; transform: scale(.68); }
.tab.active .ti-off { opacity: 0; transform: scale(.68); }
.tab.active .ti-on { opacity: 1; transform: scale(1); }
.tab.active .ti { transform: translateY(-1px) scale(1.06); }
.tl { position: relative; font-size: 10.5px; letter-spacing: .02em; transition: color .22s var(--ease-out); }
.tab.active .tl { font-weight: 700; }
/* 选中态顶部指示条 */
.tab:not(.center)::after {
  content: ""; position: absolute; top: -6px; left: 50%; transform: translateX(-50%) scaleX(0);
  width: 22px; height: 3px; border-radius: 0 0 3px 3px;
  background: linear-gradient(90deg, #4b83ff, #165dff);
  transition: transform .3s var(--ease-spring);
}
.tab:not(.center).active::after { transform: translateX(-50%) scaleX(1); }

.tab-badge {
  position: absolute; top: 0; right: 50%; margin-right: -22px;
  min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px;
  background: #f53f3f; color: #fff; font-size: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: 0 0 0 2px #fff;
}

/* 中央凸起按钮 */
.tab.center { color: #86909c; }
.center-btn {
  position: relative; width: 54px; height: 54px; margin-top: -26px; border-radius: 50%;
  display: grid; place-items: center; color: #fff;
  background: linear-gradient(140deg, #4b83ff, #165dff 55%, #0b3fa8);
  box-shadow: 0 14px 28px -12px rgba(22, 93, 255, .75), 0 0 0 5px #f7f8fa;
  transition: transform .3s var(--ease-spring);
}
.tab.center.active .center-btn { transform: translateY(-3px) scale(1.05); }
.cb-ring {
  position: absolute; inset: -6px; border-radius: 50%;
  border: 1.5px dashed rgba(22, 93, 255, .4);
  animation: spin-slow 14s linear infinite;
}
.tab.center.active .cb-ring { border-color: rgba(255, 184, 0, .65); }
.center-dot {
  position: absolute; top: 3px; right: 3px; width: 10px; height: 10px; border-radius: 50%;
  background: #ffb800; box-shadow: 0 0 0 2px #fff;
}
.center-label { margin-top: 1px; color: #4e5969; font-weight: 600; }
.tab.center.active .center-label { color: #165dff; }
</style>
