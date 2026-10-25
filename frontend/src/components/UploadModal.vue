<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'
import { api } from '../api'

const emit = defineEmits(['close', 'uploaded', 'document-uploaded', 'demo'])
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')
const statusText = ref('')
const fileInput = ref(null)

const DOC_EXTS = ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.webp']

function pick() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onFiles(fileList) {
  const file = fileList && fileList[0]
  if (!file) return
  upload(file)
}

function onDrop(event) {
  dragging.value = false
  onFiles(event.dataTransfer.files)
}

async function upload(file) {
  const name = String(file.name || '').toLowerCase()
  const supported = ['.csv', '.xlsx', '.xlsm', ...DOC_EXTS]
  if (!supported.some((ext) => name.endsWith(ext))) {
    error.value = '仅支持 CSV / Excel / PDF / Word / 图片（png、jpg）'
    return
  }
  if (file.size > 30 * 1024 * 1024) {
    error.value = '文件超过 30MB 限制，请先压缩或抽样。'
    return
  }
  uploading.value = true
  error.value = ''
  const isDocument = DOC_EXTS.some((ext) => name.endsWith(ext))
  statusText.value = isDocument ? '正在解析文档 / 识别表格，可能需要几秒…' : '正在解析并建表…'
  try {
    if (isDocument) {
      const doc = await api.uploadDocument(file)
      emit('document-uploaded', doc)
    } else {
      const dataset = await api.upload(file)
      emit('uploaded', dataset)
    }
  } catch (exc) {
    error.value = exc.message || '上传失败，请检查文件格式'
  } finally {
    uploading.value = false
    statusText.value = ''
  }
}

const accept = computed(() => '.csv,.xlsx,.xlsm,.pdf,.docx,.png,.jpg,.jpeg,.webp')
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-hd">
        <div>
          <b>接入数据 / 文档</b>
          <span>表格直接分析；PDF / Word 提取表格与正文；截图用视觉模型识别</span>
        </div>
        <button class="modal-close" @click="emit('close')"><Icon name="x" :size="16" /></button>
      </div>

      <div class="modal-body">
        <div
          class="dropzone"
          :class="{ drag: dragging }"
          @click="pick"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <template v-if="!uploading">
            <span class="dz-icon"><Icon name="upload" :size="20" /></span>
            <b>点击选择文件，或拖拽到这里</b>
            <span>CSV / Excel 直接分析 · PDF / Word 提取表格 · 图片走视觉识别</span>
          </template>
          <template v-else>
            <span class="dz-icon"><span class="spinner" style="width:18px;height:18px;border-width:2.5px" /></span>
            <b>{{ statusText }}</b>
            <span>大文件或图片识别可能需要几秒钟</span>
          </template>
        </div>
        <input ref="fileInput" type="file" :accept="accept" style="display:none" @change="onFiles($event.target.files)" />

        <div v-if="error" class="upload-error">{{ error }}</div>

        <div class="upload-tips">
          · <b>CSV / Excel</b>：自动识别字段并建表，直接进入分析；<br />
          · <b>PDF / Word</b>：提取表格变成可分析数据集，正文用于「文档问答」；<br />
          · <b>图片截图</b>：调用视觉大模型识别表格 → 转成数据集；<br />
          · 支持中文表头、UTF-8 / GBK 编码，单文件最大 30MB。
        </div>
      </div>

      <div class="modal-ft">
        <button class="btn-secondary" @click="emit('demo')">
          <Icon name="sparkles" :size="13" />使用示例数据
        </button>
        <span class="spacer" />
        <button class="btn-primary" :disabled="uploading" @click="pick">
          <Icon name="upload" :size="13" />{{ uploading ? '解析中…' : '选择文件' }}
        </button>
      </div>
    </div>
  </div>
</template>
