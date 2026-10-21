<script setup>
import Icon from './Icon.vue'

defineProps({
  datasets: { type: Array, default: () => [] },
  activeId: { type: String, default: '' },
  health: { type: Object, default: null }
})
const emit = defineEmits(['new-chat', 'select', 'upload'])

function onClickDataset(ds) {
  emit('select', ds)
}
</script>

<template>
  <aside class="side">
    <div class="brand">
      <span class="logo"><Icon name="sparkles" :size="15" /></span>
      <span class="brand-name">问数<span class="brand-en">AskData</span></span>
    </div>

    <button class="btn-new" @click="emit('new-chat')">
      <Icon name="plus" :size="15" />新建对话
    </button>

    <nav class="nav">
      <a class="nav-item active"><Icon name="message-square" :size="15" />对话</a>
      <a class="nav-item" @click="emit('upload')">
        <Icon name="database" :size="15" />数据集
        <span v-if="datasets.length" class="badge">{{ datasets.length }}</span>
      </a>
      <a class="nav-item disabled"><Icon name="layout-grid" :size="15" />看板<span class="soon">soon</span></a>
      <a class="nav-item disabled"><Icon name="clock" :size="15" />历史记录<span class="soon">soon</span></a>
    </nav>

    <div class="side-sec">
      <div class="side-hd">数据源
        <button class="hd-add" title="上传数据" @click="emit('upload')"><Icon name="plus" :size="13" /></button>
      </div>
      <ul class="ds-list">
        <li
          v-for="ds in datasets"
          :key="ds.id"
          class="ds-item"
          :class="{ active: ds.id === activeId }"
          @click="onClickDataset(ds)"
        >
          <Icon :name="String(ds.source_file || '').toLowerCase().endsWith('.csv') ? 'file-text' : 'database'" :size="14" />
          <div class="ds-meta">
            <b>{{ ds.name }}</b>
            <span>{{ Number(ds.rows || 0).toLocaleString() }} 行 · {{ ds.cols }} 列</span>
          </div>
          <span class="dot ok" />
        </li>
        <li v-if="!datasets.length" class="ds-empty">还没有数据集，上传 CSV/Excel 或载入示例数据。</li>
      </ul>
    </div>

    <div class="side-sec">
      <div class="side-hd">提问灵感</div>
      <div class="tip-card">
        <Icon name="lightbulb" :size="14" />
        <p>各区域销售额对比<br />双11当天各小时趋势<br />销售额最高的 5 个品类<br />各渠道退款率排名</p>
      </div>
    </div>

    <div class="side-spacer" />

    <div class="side-foot">
      <span class="avatar">数</span>
      <div>
        <b>问数 AskData</b>
        <span>{{ health?.mock_mode ? '演示模式 · 无需 API Key' : '已接入 ' + (health?.model || '大模型') }}</span>
      </div>
    </div>
  </aside>
</template>
