<template>
  <div ref="el" class="echart" :style="{ height: height }" />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '260px' },
  theme: { type: String, default: 'dark' }
})

const el = ref(null)
let chart = null
let ro = null

function buildTheme() {
  return {
    color: ['#165DFF', '#FFB800', '#00B42A', '#F53F3F', '#7B61FF', '#00B8D9'],
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif' },
    grid: { left: 8, right: 12, top: 28, bottom: 6, containLabel: true },
    tooltip: props.theme === 'light'
      ? {
          trigger: 'axis',
          backgroundColor: 'rgba(255,255,255,.98)',
          borderColor: 'rgba(29,33,41,.08)',
          borderWidth: 1,
          textStyle: { color: '#1D2129', fontSize: 12 },
          extraCssText: 'box-shadow:0 12px 32px -12px rgba(0,0,0,.22);border-radius:10px;padding:8px 12px;'
        }
      : {
          trigger: 'axis',
          backgroundColor: 'rgba(10,25,47,.94)',
          borderColor: 'rgba(96,150,255,.35)',
          borderWidth: 1,
          textStyle: { color: '#EAF2FF', fontSize: 12 },
          extraCssText: 'box-shadow:0 12px 32px -12px rgba(0,0,0,.9);border-radius:10px;padding:8px 12px;'
        },
    categoryAxis: {
      axisLine: { lineStyle: { color: props.theme === 'light' ? 'rgba(29,33,41,.12)' : 'rgba(96,150,255,.22)' } },
      axisTick: { show: false },
      axisLabel: { color: props.theme === 'light' ? '#86909C' : '#6D82A6', fontSize: 11 },
      splitLine: { show: false }
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: props.theme === 'light' ? '#86909C' : '#6D82A6', fontSize: 11 },
      splitLine: { lineStyle: { color: props.theme === 'light' ? 'rgba(29,33,41,.06)' : 'rgba(96,150,255,.09)', type: 'dashed' } }
    }
  }
}

function render() {
  if (!el.value) return
  if (!chart) {
    echarts.registerTheme(`ysx-${props.theme}`, buildTheme())
    chart = echarts.init(el.value, `ysx-${props.theme}`, { renderer: 'canvas' })
  }
  chart.setOption(props.option, true)
}

onMounted(async () => {
  await nextTick()
  render()
  ro = new ResizeObserver(() => chart && chart.resize())
  ro.observe(el.value)
})

watch(() => props.option, () => render(), { deep: true })
onBeforeUnmount(() => {
  ro && ro.disconnect()
  chart && chart.dispose()
  chart = null
})
</script>

<style scoped>
.echart { width: 100%; }
</style>
