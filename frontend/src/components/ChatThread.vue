<script setup>
import { nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'
import AnswerCard from './AnswerCard.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  dataset: { type: Object, default: null },
  health: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  examples: { type: Array, default: () => [] }
})
const emit = defineEmits(['send', 'upload', 'demo', 'preview', 'open-inspector', 'example', 'fill'])

const scrollEl = ref(null)

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
watch(() => props.dataset, () => nextTick(scrollToBottom))
</script>

<template>
  <div ref="scrollEl" class="chat-scroll">
    <div class="thread" :class="{ 'welcome-mode': !dataset }">
      <!-- 欢迎态 -->
      <div v-if="!dataset" class="welcome">
        <div class="welcome-inner">
          <span class="eyebrow"><Icon name="sparkles" :size="12" />AI 数据分析助手</span>
          <h1 class="hero-title">把问题说出来，<br /><span>让数据回答。</span></h1>
          <p class="hero-sub">
            上传 CSV / Excel，用一句自然语言完成查询、分析与可视化。
            自动生成 SQL、图表与业务洞察，不需要写代码。
          </p>

          <div class="start-actions">
            <button class="start-card primary" @click="emit('upload')">
              <span class="ic-wrap"><Icon name="upload" :size="17" /></span>
              <b>上传数据文件</b>
              <span>CSV / Excel，最大 30MB</span>
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
            <span><Icon name="code" :size="13" />SQL 可追溯</span>
            <span><Icon name="database" :size="13" />数据不出域</span>
          </div>
        </div>
      </div>

      <!-- 数据集就绪 -->
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

        <AnswerCard
          v-for="message in messages"
          :key="message.id"
          :message="message"
          @send="emit('send', $event)"
          @fill="emit('fill', $event)"
          @open-inspector="emit('open-inspector')"
        />
      </template>
    </div>
  </div>
</template>
