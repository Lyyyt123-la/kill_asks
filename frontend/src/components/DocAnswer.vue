<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  message: { type: Object, required: true }
})
const emit = defineEmits(['fill'])

const showCitations = ref(true)

const response = computed(() => props.message.docAnswer)
const elapsed = computed(() => {
  const ms = response.value?.elapsed_ms
  return ms ? `${(ms / 1000).toFixed(1)}s` : ''
})
const followups = ['把文档中的表格作为数据集分析', '这份文档的核心结论是什么？', '文档里有哪些关键数字？']
</script>

<template>
  <div class="ai-wrap">
    <div class="ai-head">
      <span class="ai-avatar">问</span>
      <div class="ai-meta">
        <b>问数 · 文档问答</b>
        <span v-if="message.loading"><span class="spinner" />正在检索文档并生成回答…</span>
        <span v-else>
          <Icon name="check-circle" :size="11" />
          已完成{{ elapsed ? ' · ' + elapsed : '' }} · {{ response?.model || '演示模式' }}
        </span>
      </div>
    </div>

    <div class="answer">
      <template v-if="message.loading">
        <div class="loading-steps">
          <span class="lstep done"><Icon name="check" :size="11" />解析文档</span>
          <span class="lstep on"><span class="spinner" />检索相关片段</span>
          <span class="lstep">生成回答</span>
        </div>
        <div class="card loading-box">
          <div class="skeleton w80" />
          <div class="skeleton w60" />
        </div>
      </template>

      <template v-else-if="!response">
        <div class="error-card">
          <div class="eh"><Icon name="alert-circle" :size="15" />文档问答失败</div>
          <p>{{ message.error || '请求出错，请稍后重试。' }}</p>
        </div>
      </template>

      <template v-else>
        <p class="doc-answer-text">{{ response.answer }}</p>

        <div v-if="response.citations && response.citations.length" class="doc-citations">
          <button class="citations-toggle" @click="showCitations = !showCitations">
            <Icon name="file-text" :size="12" />引用片段（{{ response.citations.length }}）{{ showCitations ? '收起' : '展开' }}
          </button>
          <div v-show="showCitations" class="citation-list">
            <div v-for="citation in response.citations" :key="citation.index" class="citation-item">
              <span class="cite-index">[{{ citation.index }}]</span>
              <span>{{ citation.text }}</span>
            </div>
          </div>
        </div>

        <div class="doc-answer-footer">
          <span>检索片段：{{ response.citations?.length || 0 }} 条</span>
          <span>模型：{{ response.model }}</span>
          <span v-if="response.mock" class="mock-badge"><Icon name="zap" :size="10" />演示模式</span>
        </div>

        <div class="followups">
          <button v-for="followup in followups" :key="followup" class="followup" @click="emit('fill', followup)">
            <Icon name="sparkles" :size="12" />{{ followup }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
