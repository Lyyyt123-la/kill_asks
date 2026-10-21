<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from './Icon.vue'
import ChartCard from './ChartCard.vue'
import SqlBlock from './SqlBlock.vue'

const props = defineProps({
  message: { type: Object, required: true }
})
const emit = defineEmits(['send', 'open-inspector'])

const LOADING_STEPS = ['理解问题', '生成 SQL', '执行查询', '生成图表', '撰写洞察']
const activeStep = ref(0)
let timer = null

onMounted(() => {
  if (props.message.loading) {
    timer = setInterval(() => {
      if (activeStep.value < LOADING_STEPS.length - 1) activeStep.value += 1
    }, 650)
  }
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})

const response = computed(() => props.message.response)
const isClarify = computed(() => response.value?.intent === 'clarify' || response.value?.intent === 'unsupported')
const hasResult = computed(() => response.value?.result && response.value.result.columns?.length)
const modelLabel = computed(() => response.value?.model || '演示模式')
const elapsed = computed(() => {
  const ms = response.value?.elapsed_ms
  return ms ? `${(ms / 1000).toFixed(1)}s` : ''
})
</script>

<template>
  <!-- 用户消息 -->
  <div v-if="message.role === 'user'" class="msg-user">
    <div class="user-bubble">{{ message.text }}</div>
    <div class="user-meta"><Icon name="clock" :size="11" />{{ message.time }}</div>
  </div>

  <!-- AI 回答 -->
  <div v-else class="ai-wrap">
    <div class="ai-head">
      <span class="ai-avatar">问</span>
      <div class="ai-meta">
        <b>问数</b>
        <span v-if="message.loading"><span class="spinner" />正在分析你的问题…</span>
        <span v-else>
          <Icon name="check-circle" :size="11" />
          已完成{{ elapsed ? ' · ' + elapsed : '' }} · {{ modelLabel }}
        </span>
      </div>
    </div>

    <div class="answer">
      <!-- 加载态 -->
      <template v-if="message.loading">
        <div class="loading-steps">
          <span
            v-for="(label, index) in LOADING_STEPS"
            :key="label"
            class="lstep"
            :class="{ done: index < activeStep, on: index === activeStep }"
          >
            <span v-if="index === activeStep" class="spinner" />
            <Icon v-else :name="index < activeStep ? 'check' : 'clock'" :size="11" />
            {{ label }}
          </span>
        </div>
        <div class="card loading-box">
          <div class="skeleton w60" />
          <div class="skeleton w80" />
          <div class="skeleton h80" />
        </div>
      </template>

      <!-- 请求失败 -->
      <template v-else-if="!response">
        <div class="error-card">
          <div class="eh"><Icon name="alert-circle" :size="15" />分析失败</div>
          <p>{{ message.error || '请求出错，请稍后重试。' }}</p>
        </div>
      </template>

      <!-- 澄清 / 不支持 -->
      <template v-else-if="isClarify">
        <div class="plan-steps">
          <span v-for="step in response.steps || []" :key="step.key" class="plan-step">
            <Icon name="check" :size="11" />{{ step.label }}
          </span>
        </div>
        <div class="clarify-card">
          <b>{{ response.intent === 'clarify' ? '需要再确认一下' : '这个问题暂时无法回答' }}</b>
          <p>{{ response.clarification?.question || response.plan || '换个问法试试看。' }}</p>
          <div v-if="response.clarification?.options?.length" class="clarify-options">
            <button
              v-for="option in response.clarification.options"
              :key="option"
              class="clarify-opt"
              @click="emit('send', option)"
            >
              {{ option }}
            </button>
          </div>
        </div>
      </template>

      <!-- 正常结果 -->
      <template v-else>
        <div class="plan-steps">
          <span v-for="step in response.steps || []" :key="step.key" class="plan-step">
            <Icon name="check" :size="11" />{{ step.label }}
            <span v-if="step.detail" class="tag">{{ step.detail }}</span>
          </span>
          <span v-if="response.mock" class="mock-badge"><Icon name="zap" :size="10" />演示模式</span>
        </div>

        <p v-if="response.insight?.headline" class="lead">{{ response.insight.headline }}</p>

        <div v-if="response.insight?.bullets?.length" class="insight-block">
          <div class="insight-hd"><Icon name="lightbulb" :size="12" />关键洞察</div>
          <div class="bullets">
            <div v-for="(bullet, index) in response.insight.bullets" :key="index" class="bullet">
              <span class="n">{{ index + 1 }}</span>
              <span>{{ bullet }}</span>
            </div>
          </div>
        </div>

        <ChartCard
          v-if="hasResult"
          :chart="response.chart || {}"
          :result="response.result"
        />

        <div v-if="response.assumptions?.length" class="assumptions">
          <Icon name="filter" :size="11" />
          <span>口径假设：{{ response.assumptions.join('；') }}</span>
        </div>

        <SqlBlock v-if="response.sql" :sql="response.sql" :result="response.result" />

        <div v-if="response.insight?.followups?.length" class="followups">
          <button
            v-for="followup in response.insight.followups"
            :key="followup"
            class="followup"
            @click="emit('send', followup)"
          >
            <Icon name="sparkles" :size="12" />{{ followup }}
          </button>
        </div>

        <div class="answer-footer">
          <span>{{ response.attempts > 1 ? `自动修复 ${response.attempts - 1} 次 · ` : '' }}生成 {{ response.attempts }} 次 · {{ response.result?.total_rows ?? 0 }} 行结果</span>
          <span class="spacer" />
          <button class="link-btn" @click="emit('open-inspector')">
            <Icon name="panel-left" :size="11" />在检查器中查看 SQL
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
