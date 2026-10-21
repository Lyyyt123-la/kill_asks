<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import Icon from './Icon.vue'

const props = defineProps({
  chart: { type: Object, default: () => ({}) },
  result: { type: Object, default: () => ({ columns: [], rows: [] }) }
})

const PALETTE = ['#2F6B4F', '#B45309', '#7EA88F', '#C9A227', '#6B7280', '#4A7C6A']
const CHART_TYPES = [
  { type: 'line', label: '折线', icon: 'line-chart' },
  { type: 'bar', label: '柱状', icon: 'bar-chart' },
  { type: 'pie', label: '环形', icon: 'pie-chart' },
  { type: 'table', label: '表格', icon: 'table' }
]

const columns = computed(() => props.result?.columns || [])
const rows = computed(() => props.result?.rows || [])
const hasData = computed(() => columns.value.length > 0 && rows.value.length > 0)

const initialType = ['line', 'bar', 'pie'].includes(props.chart?.type) ? props.chart.type : 'table'
const type = ref(initialType)
const chartEl = ref(null)
let instance = null

function isNum(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

const numericIndexes = computed(() => {
  if (!rows.value.length) return []
  return columns.value
    .map((_, index) => index)
    .filter((index) => {
      const values = rows.value.slice(0, 8).map((row) => row[index]).filter((v) => v !== null && v !== undefined)
      return values.length > 0 && values.every(isNum)
    })
})

const xIndex = computed(() => {
  if (!columns.value.length) return 0
  const named = props.chart?.x ? columns.value.indexOf(props.chart.x) : -1
  if (named >= 0) return named
  const nonNumeric = columns.value.map((_, i) => i).filter((i) => !numericIndexes.value.includes(i))
  return nonNumeric.length ? nonNumeric[0] : 0
})

const yIndexes = computed(() => {
  const named = (props.chart?.y || [])
    .map((name) => columns.value.indexOf(name))
    .filter((index) => index >= 0 && numericIndexes.value.includes(index))
  if (named.length) return named
  return numericIndexes.value.slice(0, 2)
})

const subtitle = computed(() => {
  const cols = columns.value.length
  const rowCount = rows.value.length
  return `${cols} 列 · ${rowCount} 行${rows.value.length >= 1000 ? '+（已截断）' : ''}`
})

function fmt(value) {
  if (value === null || value === undefined) return '-'
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  const abs = Math.abs(n)
  if (abs >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (abs >= 1e4) return (n / 1e4).toFixed(2) + '万'
  if (abs >= 1000) return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  return String(Math.round(n * 100) / 100)
}

function fmtFull(value) {
  if (value === null || value === undefined) return '-'
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function axisFmt(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  const abs = Math.abs(n)
  if (abs >= 1e8) return (n / 1e8).toFixed(1) + '亿'
  if (abs >= 1e4) return (n / 1e4).toFixed(abs >= 1e6 ? 0 : 1) + '万'
  if (abs >= 1000) return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
  return String(Math.round(n * 100) / 100)
}

function labelOf(value) {
  const text = String(value ?? '')
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(text)) return text.slice(5, 16)
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text)) return text.slice(5, 16).replace('T', ' ')
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(5, 10)
  if (/^\d{4}-\d{2}$/.test(text)) return text
  return text.length > 16 ? text.slice(0, 16) + '…' : text
}

function baseOption() {
  return {
    color: PALETTE,
    animationDuration: 450,
    textStyle: {
      color: '#8C8678',
      fontFamily: 'Inter, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif',
      fontSize: 11
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(42,42,37,.94)',
      borderWidth: 0,
      padding: [8, 11],
      textStyle: { color: '#F4F1E7', fontSize: 11 },
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47,107,79,.06)' } }
    }
  }
}

function buildOption(kind) {
  const cols = columns.value
  const data = rows.value
  const xIdx = xIndex.value
  const ys = yIndexes.value
  if (!hasData.value || !ys.length) return null

  if (kind === 'pie') {
    const yi = ys[0]
    return {
      ...baseOption(),
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(42,42,37,.94)',
        borderWidth: 0,
        textStyle: { color: '#F4F1E7', fontSize: 11 },
        formatter: (params) => `${params.name}<br/>${fmtFull(params.value)}（${params.percent}%）`
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 14,
        textStyle: { color: '#8C8678', fontSize: 10 }
      },
      series: [{
        type: 'pie',
        radius: ['48%', '70%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#FFFEFB', borderWidth: 2 },
        label: { color: '#5E594E', fontSize: 10, formatter: '{b}\n{d}%' },
        labelLine: { length: 8, length2: 6, lineStyle: { color: '#D9D2C2' } },
        data: data.map((row) => ({ name: String(row[xIdx] ?? '空值'), value: Number(row[yi]) || 0 }))
      }]
    }
  }

  const categories = data.map((row) => labelOf(row[xIdx]))
  const series = ys.map((yi) => ({
    name: cols[yi],
    type: kind === 'line' ? 'line' : 'bar',
    data: data.map((row) => row[yi]),
    smooth: kind === 'line' ? 0.18 : undefined,
    symbol: kind === 'line' ? 'circle' : undefined,
    symbolSize: kind === 'line' ? 4.5 : undefined,
    lineStyle: kind === 'line' ? { width: 2.2 } : undefined,
    areaStyle: kind === 'line' && ys.length === 1 ? { opacity: 0.09 } : undefined,
    barMaxWidth: 34,
    itemStyle: { borderRadius: kind === 'bar' ? [4, 4, 0, 0] : 0 }
  }))

  const option = {
    ...baseOption(),
    grid: { left: 4, right: 18, top: ys.length > 1 ? 34 : 22, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: '#E9E4D8' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#A8A08F',
        fontSize: 10,
        hideOverlap: true,
        rotate: categories.length > 14 ? 32 : 0,
        formatter: (value) => (value.length > 12 ? value.slice(0, 12) + '…' : value)
      }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#F1EDE3', type: 'dashed' } },
      axisLabel: { color: '#A8A08F', fontSize: 10, formatter: (value) => axisFmt(value) }
    },
    series
  }
  if (ys.length > 1) {
    option.legend = {
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#8C8678', fontSize: 10 }
    }
  }
  if (categories.length > 80) {
    option.dataZoom = [{ type: 'inside', zoomOnMouseWheel: true }]
  }
  return option
}

function render() {
  if (!chartEl.value || type.value === 'table' || !hasData.value) {
    if (instance) instance.clear()
    return
  }
  if (!instance) instance = echarts.init(chartEl.value)
  const option = buildOption(type.value)
  if (!option) {
    instance.clear()
    return
  }
  instance.setOption(option, true)
  instance.resize()
}

function resize() {
  if (instance) instance.resize()
}

function switchType(nextType) {
  type.value = nextType
  nextTick(render)
}

function exportImage() {
  if (!instance) return
  const url = instance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#FFFEFB' })
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.chart?.title || 'chart'}.png`
  link.click()
}

function tableCsv() {
  const escape = (v) => {
    const text = String(v ?? '')
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const lines = [columns.value.map(escape).join(',')]
  rows.value.forEach((row) => lines.push(row.map(escape).join(',')))
  return lines.join('\n')
}

function exportData() {
  const blob = new Blob(['\ufeff' + tableCsv()], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.chart?.title || 'query_result'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  window.addEventListener('resize', resize)
  nextTick(render)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (instance) instance.dispose()
  instance = null
})

watch(
  () => [props.result, props.chart],
  () => {
    const next = ['line', 'bar', 'pie'].includes(props.chart?.type) ? props.chart.type : 'table'
    type.value = next
    nextTick(render)
  },
  { deep: true }
)
</script>

<template>
  <figure class="card chart-card">
    <div class="chart-hd">
      <div>
        <div class="chart-title">{{ chart?.title || '查询结果' }}</div>
        <div class="chart-sub">{{ subtitle }}</div>
      </div>
      <div class="chart-types">
        <button
          v-for="item in CHART_TYPES"
          :key="item.type"
          class="chart-type"
          :class="{ on: type === item.type }"
          @click="switchType(item.type)"
        >
          <Icon :name="item.icon" :size="11" />{{ item.label }}
        </button>
      </div>
    </div>

    <div class="chart-body">
      <div v-show="type !== 'table' && hasData" ref="chartEl" class="echart" />
      <div v-if="!hasData" class="chart-empty">没有查询到符合条件的数据</div>
      <div v-if="type === 'table' && hasData" class="table-scroll">
        <table class="data-table">
          <thead>
            <tr><th v-for="col in columns" :key="col">{{ col }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in rows.slice(0, 200)" :key="index">
              <td v-for="(value, i) in row" :key="i" :class="{ num: typeof value === 'number' }">
                {{ typeof value === 'number' ? fmtFull(value) : (value ?? '-') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="chart-ft">
      <Icon name="database" :size="11" />
      数据来自当前数据集
      <div class="chart-actions">
        <button class="btn-mini" @click="type === 'table' ? exportData() : exportImage()">
          <Icon name="download" :size="11" />{{ type === 'table' ? '导出 CSV' : '导出图片' }}
        </button>
        <button class="btn-mini" @click="exportData"><Icon name="copy" :size="11" />下载数据</button>
      </div>
    </div>
  </figure>
</template>
