<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from './api'
import Sidebar from './components/Sidebar.vue'
import Topbar from './components/Topbar.vue'
import ChatThread from './components/ChatThread.vue'
import Composer from './components/Composer.vue'
import Inspector from './components/Inspector.vue'
import UploadModal from './components/UploadModal.vue'
import DatasetPreview from './components/DatasetPreview.vue'

const EXAMPLES = [
  '各区域的销售额对比',
  '双11当天各小时销售额趋势',
  '销售额最高的5个品类',
  '各渠道的退款率排名'
]

const health = ref(null)
const datasets = ref([])
const activeDataset = ref(null)
const messages = ref([])
const loading = ref(false)
const activeResponse = ref(null)
const inspectorOpen = ref(false)
const uploadOpen = ref(false)
const previewOpen = ref(false)
const toast = ref('')
let toastTimer = null

const modelLabel = computed(() => {
  if (!health.value) return '连接中…'
  return health.value.mock_mode ? '演示模式' : (health.value.model || '大模型')
})

function showToast(message) {
  toast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2800)
}

async function refreshDatasets() {
  datasets.value = await api.listDatasets()
}

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch (exc) {
    showToast('后端未连接：' + (exc.message || '请启动 FastAPI'))
  }
  try {
    await refreshDatasets()
  } catch (exc) {
    /* 后端未启动时静默 */
  }
})

async function selectDataset(row) {
  try {
    const full = await api.getDataset(row.id)
    activeDataset.value = full
    messages.value = []
    activeResponse.value = null
    inspectorOpen.value = false
  } catch (exc) {
    showToast('读取数据集失败：' + exc.message)
  }
}

function newChat() {
  messages.value = []
  activeResponse.value = null
}

async function loadDemo() {
  if (loading.value) return
  try {
    const dataset = await api.loadDemo()
    await refreshDatasets()
    await selectDataset(dataset)
    showToast('已载入示例数据：双11大促销售数据')
  } catch (exc) {
    showToast('载入示例失败：' + exc.message)
  }
}

async function onUploaded(dataset) {
  uploadOpen.value = false
  await refreshDatasets()
  await selectDataset(dataset)
  showToast(`上传成功：${dataset.name}（${Number(dataset.rows).toLocaleString()} 行）`)
}

function historyPayload() {
  return messages.value
    .filter((m) => m.role === 'assistant' && m.response?.result)
    .slice(-3)
    .map((m) => ({
      question: m.question,
      sql: m.response.sql || null,
      columns: m.response.result?.columns || [],
      summary: m.response.insight?.headline || null
    }))
}

async function sendQuestion(rawQuestion) {
  const question = String(rawQuestion || '').trim()
  if (!question || loading.value) return

  if (!activeDataset.value) {
    await loadDemo()
    if (!activeDataset.value) {
      showToast('请先上传数据或载入示例数据')
      return
    }
  }

  const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  messages.value.push({ id: `u-${Date.now()}`, role: 'user', text: question, time })
  messages.value.push({
    id: `a-${Date.now()}`,
    role: 'assistant',
    question,
    loading: true,
    response: null,
    error: null
  })
  // 注意：必须取数组里的响应式代理，直接改原始对象不会触发视图更新与自动滚动
  const assistant = messages.value[messages.value.length - 1]
  loading.value = true

  try {
    const response = await api.chat({
      dataset_id: activeDataset.value.id,
      question,
      history: historyPayload()
    })
    assistant.loading = false
    assistant.response = response
    if (response.ok) {
      activeResponse.value = response
    } else {
      assistant.error = response.error || '分析失败'
    }
    if (response.error && response.ok) showToast(response.error)
  } catch (exc) {
    assistant.loading = false
    assistant.error = exc.message || '请求失败'
    showToast('分析失败：' + (exc.message || '请检查后端服务'))
  } finally {
    loading.value = false
  }
}

async function onExample(question) {
  if (!activeDataset.value) {
    await loadDemo()
    if (!activeDataset.value) return
  }
  sendQuestion(question)
}
</script>

<template>
  <div class="app" :class="{ 'inspector-open': inspectorOpen }">
    <Sidebar
      :datasets="datasets"
      :active-id="activeDataset?.id || ''"
      :health="health"
      @new-chat="newChat"
      @select="selectDataset"
      @upload="uploadOpen = true"
    />

    <main class="main">
      <Topbar
        :dataset="activeDataset"
        :health="health"
        :inspector-open="inspectorOpen"
        @toggle-inspector="inspectorOpen = !inspectorOpen"
        @preview="previewOpen = true"
      />

      <ChatThread
        :messages="messages"
        :dataset="activeDataset"
        :health="health"
        :loading="loading"
        :examples="EXAMPLES"
        @send="sendQuestion"
        @example="onExample"
        @upload="uploadOpen = true"
        @demo="loadDemo"
        @preview="previewOpen = true"
        @open-inspector="inspectorOpen = true"
      />

      <Composer
        :disabled="loading || !health"
        :loading="loading"
        :dataset="activeDataset"
        :model="modelLabel"
        @send="sendQuestion"
      />
    </main>

    <Inspector
      v-if="inspectorOpen"
      :response="activeResponse"
      :dataset="activeDataset"
      @close="inspectorOpen = false"
      @preview="previewOpen = true"
    />

    <UploadModal
      v-if="uploadOpen"
      @close="uploadOpen = false"
      @uploaded="onUploaded"
      @demo="loadDemo(); uploadOpen = false"
    />

    <DatasetPreview
      v-if="previewOpen && activeDataset"
      :dataset="activeDataset"
      @close="previewOpen = false"
    />

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>
