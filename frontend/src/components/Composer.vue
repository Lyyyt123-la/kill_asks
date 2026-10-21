<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  dataset: { type: Object, default: null },
  model: { type: String, default: '演示模式' }
})
const emit = defineEmits(['send'])

const text = ref('')
const textarea = ref(null)
const canSend = computed(() => text.value.trim().length > 0 && !props.disabled && !props.loading)
const placeholder = computed(() =>
  props.dataset
    ? '继续追问，比如：把结果按区域拆分看看…'
    : '请先上传数据或载入示例数据，然后输入你的问题…'
)

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
        <span class="comp-chip"><Icon name="paperclip" :size="12" />{{ dataset ? dataset.source_file : '未选择数据' }}</span>
        <span class="comp-chip"><Icon name="line-chart" :size="12" />自动图表</span>
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
