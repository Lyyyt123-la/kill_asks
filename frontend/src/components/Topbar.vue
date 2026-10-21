<script setup>
import Icon from './Icon.vue'

defineProps({
  dataset: { type: Object, default: null },
  health: { type: Object, default: null },
  inspectorOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-inspector', 'preview'])
</script>

<template>
  <header class="topbar">
    <div class="crumbs">
      <span>对话</span>
      <Icon name="chevron-right" :size="13" />
      <b>{{ dataset ? dataset.name : '新的分析' }}</b>
    </div>
    <div class="top-actions">
      <button v-if="dataset" class="chip click" @click="emit('preview')">
        <span class="dot ok" />{{ dataset.source_file }}
      </button>
      <span class="chip">
        <Icon name="cpu" :size="13" />{{ health?.mock_mode ? '演示模式' : (health?.model || '大模型') }}
      </span>
      <button
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
