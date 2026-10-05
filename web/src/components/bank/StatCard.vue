<template>
  <div class="stat glass corner-notch" :class="'accent-' + accent">
    <div class="st-top">
      <span class="st-label">{{ label }}</span>
      <span class="st-ico" v-html="icon" />
    </div>
    <div class="st-value">
      <span class="num num-xl">{{ value }}</span>
      <span class="st-unit">{{ unit }}</span>
    </div>
    <div class="st-foot">
      <span v-if="hint" class="st-hint">{{ hint }}</span>
      <div v-if="spark && spark.length" class="st-spark">
        <i v-for="(v, i) in spark" :key="i" :style="{ height: barH(v) }" />
      </div>
    </div>
    <div class="st-glow" />
  </div>
</template>

<script setup>
const props = defineProps({
  label: String,
  value: [String, Number],
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  icon: { type: String, default: '' },
  accent: { type: String, default: 'blue' }, // blue | gold | red | amber | green
  spark: { type: Array, default: () => [] }
})

function barH(v) {
  const arr = props.spark
  const max = Math.max(...arr, 1)
  return `${Math.max(12, (v / max) * 100)}%`
}
</script>

<style scoped>
.stat {
  position: relative;
  padding: 16px 17px 14px;
  border-radius: var(--r-md);
  overflow: hidden;
  transition: transform .3s var(--ease-out), border-color .3s;
}
.stat:hover { transform: translateY(-3px); border-color: var(--line-strong); }
.st-top { display: flex; align-items: center; justify-content: space-between; }
.st-label { font-size: 12.5px; color: var(--text-2); letter-spacing: .04em; }
.st-ico { opacity: .75; }
.st-value { display: flex; align-items: baseline; gap: 6px; margin-top: 9px; }
.st-unit { font-size: 12.5px; color: var(--text-3); font-family: var(--font-num); }
.st-foot { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; margin-top: 9px; min-height: 22px; }
.st-hint { font-size: 11.5px; color: var(--text-3); }
.st-spark { display: flex; align-items: flex-end; gap: 2px; height: 22px; }
.st-spark i { width: 3px; border-radius: 1px; background: currentColor; opacity: .55; }

.accent-blue { color: var(--brand-blue-400); }
.accent-blue .st-value .num { color: #dbe8ff; }
.accent-gold { color: var(--brand-gold); }
.accent-gold .st-value .num { color: #ffe1a0; }
.accent-red { color: var(--risk-red); }
.accent-red .st-value .num { color: #ffc4c4; }
.accent-amber { color: var(--risk-amber); }
.accent-amber .st-value .num { color: #ffd9b0; }
.accent-green { color: var(--risk-green); }
.accent-green .st-value .num { color: #b6f0c4; }

.st-glow {
  position: absolute; right: -40px; bottom: -50px; width: 140px; height: 140px;
  border-radius: 50%; filter: blur(42px); opacity: .3; background: currentColor;
  pointer-events: none;
}
</style>
