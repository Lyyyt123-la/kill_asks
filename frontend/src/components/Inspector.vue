<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  response: { type: Object, default: null },
  dataset: { type: Object, default: null }
})
const emit = defineEmits(['close', 'preview'])

const tab = ref('result')

const result = computed(() => props.response?.result || null)
const columns = computed(() => result.value?.columns || [])
const rows = computed(() => result.value?.rows || [])
const sqlCopied = ref(false)

async function copySql() {
  if (!props.response?.sql) return
  try {
    await navigator.clipboard.writeText(props.response.sql)
    sqlCopied.value = true
    setTimeout(() => { sqlCopied.value = false }, 1600)
  } catch (e) { /* ignore */ }
}
</script>

<template>
  <aside class="inspector">
    <div class="inspector-hd">
      <span class="inspector-title">检查器</span>
      <button class="close" title="关闭" @click="emit('close')"><Icon name="x" :size="15" /></button>
    </div>
    <div class="tabs">
      <div class="tab" :class="{ on: tab === 'result' }" @click="tab = 'result'">结果</div>
      <div class="tab" :class="{ on: tab === 'sql' }" @click="tab = 'sql'">SQL</div>
      <div class="tab" :class="{ on: tab === 'fields' }" @click="tab = 'fields'">字段</div>
    </div>

    <div class="inspector-body">
      <!-- 结果 -->
      <template v-if="tab === 'result'">
        <template v-if="result">
          <div class="meta-grid">
            <div class="meta-item"><div class="l">结果行数</div><div class="v">{{ Number(result.total_rows || 0).toLocaleString() }}<small> 行</small></div></div>
            <div class="meta-item"><div class="l">执行耗时</div><div class="v">{{ result.elapsed_ms ?? '-' }}<small> ms</small></div></div>
            <div class="meta-item"><div class="l">生成次数</div><div class="v">{{ response?.attempts ?? '-' }}<small> 次</small></div></div>
            <div class="meta-item"><div class="l">模型</div><div class="v" style="font-size:11px;font-family:inherit">{{ response?.model || '-' }}</div></div>
          </div>
          <div class="inspector-section-title"><Icon name="table" :size="11" />查询结果</div>
          <div class="table-scroll">
            <table class="data-table">
              <thead><tr><th v-for="col in columns" :key="col">{{ col }}</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in rows.slice(0, 200)" :key="index">
                  <td v-for="(value, i) in row" :key="i" :class="{ num: typeof value === 'number' }">
                    {{ typeof value === 'number' ? Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : (value ?? '-') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <div v-else class="inspector-empty">
          还没有可展示的查询结果。<br />在左侧提一个问题，这里会显示结果表、SQL 与字段信息。
        </div>
      </template>

      <!-- SQL -->
      <template v-else-if="tab === 'sql'">
        <template v-if="response?.sql">
          <div class="inspector-section-title">
            <Icon name="code" :size="11" />执行的 SQL
            <button class="link-btn" style="margin-left:auto" @click="copySql">
              <Icon name="copy" :size="11" />{{ sqlCopied ? '已复制' : '复制' }}
            </button>
          </div>
          <div class="sql-block" style="border-radius:10px">
            <div class="sql-box" style="border-top:0">
              <pre>{{ response.sql }}</pre>
            </div>
          </div>
          <div class="inspector-section-title" style="margin-top:18px"><Icon name="check-circle" :size="11" />执行信息</div>
          <div class="meta-grid">
            <div class="meta-item"><div class="l">状态</div><div class="v" style="font-size:12px;font-family:inherit;color:#2F6B4F">成功</div></div>
            <div class="meta-item"><div class="l">耗时 / 行数</div><div class="v">{{ result?.elapsed_ms ?? '-' }}<small> ms / {{ result?.total_rows ?? 0 }} 行</small></div></div>
          </div>
        </template>
        <div v-else class="inspector-empty">还没有执行过 SQL。</div>
      </template>

      <!-- 字段 -->
      <template v-else>
        <div v-if="dataset">
          <div class="inspector-section-title">
            <Icon name="database" :size="11" />{{ dataset.name }}
            <button class="link-btn" style="margin-left:auto" @click="emit('preview')">
              <Icon name="eye" :size="11" />预览数据
            </button>
          </div>
          <div class="schema-list">
            <div v-for="col in dataset.columns || []" :key="col.name" class="schema-item">
              <Icon name="hash" :size="11" />
              <span class="name">{{ col.name }}</span>
              <span class="type">{{ col.dtype }}</span>
              <div class="samples">
                样例：{{ (col.samples || []).join(' / ') || '无' }}
                <template v-if="col.enum_values"> · 枚举：{{ col.enum_values.slice(0, 8).join('/') }}</template>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="inspector-empty">还没有选择数据集。</div>
      </template>
    </div>
  </aside>
</template>
