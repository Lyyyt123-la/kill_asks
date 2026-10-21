<script setup>
import { onMounted, ref } from 'vue'
import Icon from './Icon.vue'
import { api } from '../api'

const props = defineProps({
  dataset: { type: Object, required: true }
})
const emit = defineEmits(['close'])

const loading = ref(true)
const error = ref('')
const columns = ref([])
const rows = ref([])
const total = ref(0)

onMounted(async () => {
  try {
    const data = await api.preview(props.dataset.id, 100)
    columns.value = data.columns || []
    rows.value = data.rows || []
    total.value = data.total || 0
  } catch (exc) {
    error.value = exc.message || '加载预览失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal wide">
      <div class="modal-hd">
        <div>
          <b>数据预览 · {{ dataset.name }}</b>
          <span>{{ Number(dataset.rows || 0).toLocaleString() }} 行 · {{ dataset.cols }} 列 · {{ dataset.source_file }}</span>
        </div>
        <button class="modal-close" @click="emit('close')"><Icon name="x" :size="16" /></button>
      </div>

      <div class="modal-body">
        <div v-if="loading" class="preview-meta">
          <span class="spinner" />正在加载数据预览…
        </div>
        <div v-else-if="error" class="upload-error">{{ error }}</div>
        <template v-else>
          <div class="preview-meta">
            <span>显示前 <b>{{ rows.length }}</b> 行（共 {{ Number(total).toLocaleString() }} 行）</span>
            <span class="spacer" style="flex:1" />
          </div>
          <div class="preview-table-wrap">
            <table class="data-table">
              <thead><tr><th v-for="col in columns" :key="col">{{ col }}</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in rows" :key="index">
                  <td v-for="(value, i) in row" :key="i" :class="{ num: typeof value === 'number' }">
                    {{ typeof value === 'number' ? Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : (value ?? '-') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>

      <div class="modal-ft">
        <span class="muted" style="font-size:11px">数据预览只读 · 查询在 DuckDB 中执行，原始文件不对外暴露</span>
        <span class="spacer" style="flex:1" />
        <button class="btn-secondary" @click="emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>
