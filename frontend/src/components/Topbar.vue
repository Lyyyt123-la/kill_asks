<script setup>
import Icon from './Icon.vue'

defineProps({
  dataset: { type: Object, default: null },
  document: { type: Object, default: null },
  health: { type: Object, default: null },
  inspectorOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-inspector', 'preview', 'exit-doc'])
</script>

<template>
  <header class="topbar">
    <div class="crumbs">
      <span>对话</span>
      <Icon name="chevron-right" :size="13" />
      <b>{{ document ? document.name : dataset ? dataset.name : '新的分析' }}</b>
      <span v-if="document" class="mode-pill"><Icon name="file-text" :size="10" />文档问答</span>
    </div>
    <div class="top-actions">
      <button v-if="document" class="chip click" @click="emit('exit-doc')">
        <Icon name="x" :size="12" />退出文档模式
      </button>
      <button v-else-if="dataset" class="chip click" @click="emit('preview')">
        <span class="dot ok" />{{ dataset.source_file }}
      </button>
      <span class="chip">
        <Icon name="cpu" :size="13" />{{ health?.mock_mode ? '演示模式' : (health?.model || '大模型') }}
      </span>
      <button
        v-if="!document"
        class="icon-btn"
        :class="{ on: inspectorOpen }"
        title="检查器：查看 SQL / 结果 / 字段"
        @click="emit('toggle-inspector')"
      >
        <Icon name="panel-left" :size="16" />
      </button>
      <button class="icon-btn" title="分享（开发中）"><Icon name="share-2" :size="16" /></button>
      <button class="icon-btn" title="更多"><Icon name="more-horizontal" :size="16" /></button>
    </div>
  </header>
</template>
