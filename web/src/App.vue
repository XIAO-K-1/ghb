<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
/* 页面切换过渡 */
.page-enter-active,
.page-leave-active { transition: opacity 0.32s var(--ease-out), transform 0.32s var(--ease-out); }
.page-enter-from { opacity: 0; transform: translateY(10px); }
.page-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
