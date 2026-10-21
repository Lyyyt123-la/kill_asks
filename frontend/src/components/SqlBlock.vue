<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  sql: { type: String, default: '' },
  result: { type: Object, default: null }
})

const open = ref(false)
const copied = ref(false)

const preview = computed(() => String(props.sql || '').replace(/\s+/g, ' ').slice(0, 96))

async function copySql() {
  try {
    await navigator.clipboard.writeText(props.sql || '')
    copied.value = true
    setTimeout(() => { copied.value = false }, 1600)
  } catch (e) {
    copied.value = false
  }
}
</script>

<template>
  <details class="sql-block" :open="open" @toggle="open = $event.target.open">
    <summary class="sql-summary">
      <span class="sql-tag">SQL</span>
      <span class="sql-preview">{{ preview }}</span>
      <span class="sql-run">
        <Icon name="check" :size="11" />已执行 · {{ result?.elapsed_ms ?? 0 }} ms
      </span>
      <span class="sql-toggle">{{ open ? '收起' : '查看' }}</span>
    </summary>
    <div class="sql-box">
      <button class="sql-copy" @click.prevent="copySql">
        <Icon name="copy" :size="11" />{{ copied ? '已复制' : '复制' }}
      </button>
      <pre>{{ sql }}</pre>
    </div>
  </details>
</template>
