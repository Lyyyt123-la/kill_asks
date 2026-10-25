<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  dataset: { type: Object, default: null },
  document: { type: Object, default: null },
  model: { type: String, default: '演示模式' },
  prefill: { type: Object, default: null }
})
const emit = defineEmits(['send'])

const text = ref('')
const textarea = ref(null)
const canSend = computed(() => text.value.trim().length > 0 && !props.disabled && !props.loading)
const placeholder = computed(() => {
  if (props.document) return '针对这份文档提问，比如：核心结论是什么？'
  if (props.dataset) return '继续追问，比如：把结果按区域拆分看看…'
  return '请先上传数据 / 文档，或载入示例数据，然后输入你的问题…'
})
const contextLabel = computed(() => {
  if (props.document) return props.document.name
  if (props.dataset) return props.dataset.source_file
  return '未选择数据'
})
const contextIcon = computed(() => {
  if (props.document) return 'file-text'
  if (props.dataset) return 'database'
  return 'paperclip'
})

function autoGrow() {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function send() {
  if (!canSend.value) return
  const value = text.value.trim()
  text.value = ''
  emit('send', value)
  nextTick(autoGrow)
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

watch(text, () => nextTick(autoGrow))

watch(
  () => props.prefill,
  (value) => {
    if (!value || !value.text) return
    text.value = value.text
    nextTick(() => {
      autoGrow()
      const el = textarea.value
      if (el) {
        el.focus()
        el.setSelectionRange(el.value.length, el.value.length)
      }
    })
  }
)
</script>

<template>
  <div class="composer-wrap">
    <div class="composer">
      <textarea
        ref="textarea"
        v-model="text"
        rows="2"
        :placeholder="placeholder"
        :disabled="disabled"
        @keydown="onKeydown"
      />
      <div class="composer-bar">
        <span class="comp-chip"><Icon :name="contextIcon" :size="12" />{{ contextLabel }}</span>
        <span v-if="!document" class="comp-chip"><Icon name="line-chart" :size="12" />自动图表</span>
        <span v-if="document" class="comp-chip"><Icon name="file-text" :size="12" />文档 RAG</span>
        <span class="comp-chip"><Icon name="cpu" :size="12" />{{ model }}</span>
        <button class="send-btn" :disabled="!canSend" title="发送" @click="send">
          <Icon name="arrow-up" :size="15" />
        </button>
      </div>
    </div>
    <div class="composer-hint">
      问数可能会出错，关键结论请二次核对 · <b>Enter</b> 发送，<b>Shift + Enter</b> 换行
    </div>
  </div>
</template>
