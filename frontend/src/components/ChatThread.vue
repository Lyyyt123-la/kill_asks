<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'
import AnswerCard from './AnswerCard.vue'
import DocAnswer from './DocAnswer.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  dataset: { type: Object, default: null },
  document: { type: Object, default: null },
  health: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  examples: { type: Array, default: () => [] }
})
const emit = defineEmits(['send', 'upload', 'demo', 'preview', 'open-inspector', 'example', 'fill', 'analyze-dataset', 'exit-doc'])

const scrollEl = ref(null)
const DOC_EXAMPLES = [
  '这份文档的核心结论是什么？',
  '文档里有哪些关键数字？',
  '文档中的表格说明了什么？'
]

const docExamples = computed(() => (props.document ? DOC_EXAMPLES : props.examples))
const docIcon = computed(() => {
  const type = props.document?.file_type || ''
  if (['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(type)) return 'image'
  if (type === 'pdf') return 'file-pdf'
  return 'file-text'
})

function scrollToBottom() {
  const el = scrollEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

watch(
  () => props.messages,
  () => {
    nextTick(scrollToBottom)
    setTimeout(scrollToBottom, 300)
    setTimeout(scrollToBottom, 900)
  },
  { deep: true }
)
watch(() => [props.dataset, props.document], () => nextTick(scrollToBottom))
</script>

<template>
  <div ref="scrollEl" class="chat-scroll">
    <div class="thread" :class="{ 'welcome-mode': !dataset && !document }">
      <!-- 欢迎态 -->
      <div v-if="!dataset && !document" class="welcome">
        <div class="welcome-inner">
          <span class="eyebrow"><Icon name="sparkles" :size="12" />AI 数据分析助手</span>
          <h1 class="hero-title">把问题说出来，<br /><span>让数据回答。</span></h1>
          <p class="hero-sub">
            上传 CSV / Excel 直接分析；PDF / Word / 截图自动提取表格与正文。
            用一句自然语言完成查询、图表、洞察与文档问答，不需要写代码。
          </p>

          <div class="start-actions">
            <button class="start-card primary" @click="emit('upload')">
              <span class="ic-wrap"><Icon name="upload" :size="17" /></span>
              <b>上传数据 / 文档</b>
              <span>CSV / Excel / PDF / Word / 截图</span>
            </button>
            <button class="start-card" @click="emit('demo')">
              <span class="ic-wrap"><Icon name="sparkles" :size="17" /></span>
              <b>载入示例数据</b>
              <span>双11大促销售数据 · 36,000 行</span>
            </button>
          </div>

          <div class="example-chips">
            <button v-for="example in examples" :key="example" class="example-chip" @click="emit('example', example)">
              <Icon name="sparkles" :size="12" />{{ example }}
            </button>
          </div>

          <div class="feature-row">
            <span><Icon name="check-circle" :size="13" />自然语言转 SQL</span>
            <span><Icon name="line-chart" :size="13" />自动图表</span>
            <span><Icon name="lightbulb" :size="13" />智能洞察</span>
            <span><Icon name="file-text" :size="13" />PDF 表格提取</span>
            <span><Icon name="image" :size="13" />截图识别</span>
          </div>
        </div>
      </div>

      <!-- 文档问答模式 -->
      <template v-else-if="document">
        <div v-if="!messages.length" class="doc-ready">
          <div class="dr-hd">
            <span class="dr-icon"><Icon :name="docIcon" :size="17" /></span>
            <div>
              <b>{{ document.name }}</b>
              <span>
                {{ String(document.file_type || '').toUpperCase() }} · {{ document.chars }} 字 ·
                {{ document.chunks }} 个片段<template v-if="document.tables?.length"> · {{ document.tables.length }} 张表格</template>
              </span>
            </div>
            <button class="btn-ghost" @click="emit('exit-doc')">
              <Icon name="arrow-left" :size="12" />退出文档模式
            </button>
          </div>

          <div v-if="document.tables && document.tables.length" class="doc-tables">
            <div class="doc-tables-hd"><Icon name="table" :size="11" />已提取表格 · 可直接作为数据集分析</div>
            <div v-for="table in document.tables" :key="table.dataset_id" class="doc-table-row">
              <Icon name="table" :size="14" />
              <div>
                <b>{{ table.name }}</b>
                <span>{{ table.rows }} 行 · {{ table.cols }} 列</span>
              </div>
              <button class="btn-ghost" @click="emit('analyze-dataset', table.dataset_id)">
                <Icon name="line-chart" :size="12" />作为数据集分析
              </button>
            </div>
          </div>

          <div class="doc-preview">
            <div class="doc-preview-hd"><Icon name="file-text" :size="11" />文档内容预览</div>
            <pre>{{ document.text_preview || '（没有可预览的文字，可能只有表格/图片）' }}</pre>
          </div>

          <div class="dr-examples">
            <span>试着这样问</span>
            <button v-for="example in docExamples" :key="example" class="dr-example" @click="emit('example', example)">
              <Icon name="sparkles" :size="11" />{{ example }}
            </button>
          </div>
        </div>

        <template v-for="message in messages" :key="message.id">
          <div v-if="message.role === 'user'" class="msg-user">
            <div class="user-bubble">{{ message.text }}</div>
            <div class="user-meta"><Icon name="clock" :size="11" />{{ message.time }}</div>
          </div>
          <DocAnswer
            v-else
            :message="message"
            @fill="emit('fill', $event)"
          />
        </template>
      </template>

      <!-- 数据集分析模式 -->
      <template v-else>
        <div v-if="!messages.length" class="dataset-ready">
          <div class="dr-hd">
            <span class="dr-icon"><Icon name="database" :size="17" /></span>
            <div>
              <b>{{ dataset.name }}</b>
              <span>{{ Number(dataset.rows || 0).toLocaleString() }} 行 · {{ dataset.cols }} 列 · {{ dataset.source_file }}</span>
            </div>
            <button class="btn-ghost" @click="emit('preview')">
              <Icon name="eye" :size="12" />查看数据预览
            </button>
          </div>
          <div class="dr-cols">
            <span v-for="col in (dataset.columns || []).slice(0, 10)" :key="col.name" class="dr-col">
              {{ col.name }}<em>{{ col.dtype }}</em>
            </span>
          </div>
          <div class="dr-examples">
            <span>试着这样问</span>
            <button v-for="example in examples" :key="example" class="dr-example" @click="emit('example', example)">
              <Icon name="sparkles" :size="11" />{{ example }}
            </button>
          </div>
        </div>

        <div v-if="!messages.length" class="ready-hint">
          <div class="rh-item">
            <span class="rh-n">1</span>
            <b>数据已就绪</b>
            <p>自动识别字段类型、枚举值与空值情况</p>
          </div>
          <div class="rh-item">
            <span class="rh-n">2</span>
            <b>用一句话提问</b>
            <p>支持多轮追问、按维度下钻与追问澄清</p>
          </div>
          <div class="rh-item">
            <span class="rh-n">3</span>
            <b>拿到可追溯的答案</b>
            <p>结论 + 图表 + 洞察，全部可展开 SQL 核对</p>
          </div>
        </div>

        <template v-for="message in messages" :key="message.id">
          <div v-if="message.role === 'user'" class="msg-user">
            <div class="user-bubble">{{ message.text }}</div>
            <div class="user-meta"><Icon name="clock" :size="11" />{{ message.time }}</div>
          </div>
          <AnswerCard
            v-else
            :message="message"
            @send="emit('send', $event)"
            @fill="emit('fill', $event)"
            @open-inspector="emit('open-inspector')"
          />
        </template>
      </template>
    </div>
  </div>
</template>
