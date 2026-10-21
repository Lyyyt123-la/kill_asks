<script setup>
import { ref } from 'vue'
import Icon from './Icon.vue'
import { api } from '../api'

const emit = defineEmits(['close', 'uploaded', 'demo'])
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')
const fileInput = ref(null)

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
  if (!(name.endsWith('.csv') || name.endsWith('.xlsx') || name.endsWith('.xlsm'))) {
    error.value = '仅支持 .csv / .xlsx / .xlsm 文件'
    return
  }
  if (file.size > 30 * 1024 * 1024) {
    error.value = '文件超过 30MB 限制，请先抽样。'
    return
  }
  uploading.value = true
  error.value = ''
  try {
    const dataset = await api.upload(file)
    emit('uploaded', dataset)
  } catch (exc) {
    error.value = exc.message || '上传失败，请检查文件格式'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-hd">
        <div>
          <b>接入数据</b>
          <span>上传 CSV / Excel，自动识别字段并建表</span>
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
            <span>支持 CSV / Excel（xlsx），最大 30MB，最多 50 万行</span>
          </template>
          <template v-else>
            <span class="dz-icon"><span class="spinner" style="width:18px;height:18px;border-width:2.5px" /></span>
            <b>正在解析并建表…</b>
            <span>大文件可能需要几秒钟</span>
          </template>
        </div>
        <input ref="fileInput" type="file" accept=".csv,.xlsx,.xlsm" style="display:none" @change="onFiles($event.target.files)" />

        <div v-if="error" class="upload-error">{{ error }}</div>

        <div class="upload-tips">
          · 首行为表头，支持中文列名与 UTF-8 / GBK 编码；<br />
          · Excel 默认读取第一个工作表；<br />
          · 上传后会自动识别时间、数值、布尔字段并生成数据概览。
        </div>
      </div>

      <div class="modal-ft">
        <button class="btn-secondary" @click="emit('demo')">
          <Icon name="sparkles" :size="13" />使用示例数据
        </button>
        <span class="spacer" />
        <button class="btn-primary" :disabled="uploading" @click="pick">
          <Icon name="upload" :size="13" />{{ uploading ? '上传中…' : '选择文件' }}
        </button>
      </div>
    </div>
  </div>
</template>
