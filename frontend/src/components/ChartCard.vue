<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import Icon from './Icon.vue'

const props = defineProps({
  chart: { type: Object, default: () => ({}) },
  result: { type: Object, default: () => ({ columns: [], rows: [] }) }
})

// 更丰富的分类色板（品牌绿 + 琥珀 + 珊瑚 + 蓝 + 紫 + 青 + 金 + 灰蓝）
const COLORS = ['#2F6B4F', '#E8A33D', '#D96C5F', '#4C8DAE', '#8B6BB1', '#4FA391', '#C4A45A', '#7C8B9E']
const CHART_TYPES = [
  { type: 'line', label: '折线', icon: 'line-chart' },
  { type: 'bar', label: '柱状', icon: 'bar-chart' },
  { type: 'pie', label: '环形', icon: 'pie-chart' },
  { type: 'table', label: '表格', icon: 'table' }
]
const THEMES = {
  light: {
    bg: '#FFFEFB',
    panel: '#FFFFFF',
    ink: '#2B2823',
    text: '#5E594E',
    muted: '#8C8678',
    axis: '#A8A08F',
    grid: '#EFEBE1',
    split: 'rgba(47,107,79,.10)',
    tooltipBg: 'rgba(38,44,39,.96)',
    tooltipText: '#F4F1E7',
    border: '#F2EEE4'
  },
  dark: {
    bg: '#17201B',
    panel: '#1E2A23',
    ink: '#EDF4EE',
    text: '#C8D8CC',
    muted: '#8FA898',
    axis: '#7B9485',
    grid: 'rgba(255,255,255,.06)',
    split: 'rgba(255,255,255,.08)',
    tooltipBg: 'rgba(245,250,246,.96)',
    tooltipText: '#1F2D24',
    border: '#26352C'
  }
}

const columns = computed(() => props.result?.columns || [])
const rows = computed(() => props.result?.rows || [])
const hasData = computed(() => columns.value.length > 0 && rows.value.length > 0)
const theme = ref('light')
const themeColors = computed(() => THEMES[theme.value])
const chartEl = ref(null)
let instance = null

function isNum(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function hexToRgb(hex) {
  const raw = hex.replace('#', '')
  return [parseInt(raw.slice(0, 2), 16), parseInt(raw.slice(2, 4), 16), parseInt(raw.slice(4, 6), 16)]
}

function rgba(hex, alpha) {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r},${g},${b},${alpha})`
}

function lighten(hex, weight) {
  const [r, g, b] = hexToRgb(hex)
  const mix = (v) => Math.round(v + (255 - v) * weight)
  return `rgb(${mix(r)},${mix(g)},${mix(b)})`
}

function barGradient(color) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color },
    { offset: 1, color: lighten(color, 0.38) }
  ])
}

function areaGradient(color) {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: rgba(color, 0.34) },
    { offset: 1, color: rgba(color, 0.02) }
  ])
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

function looksTemporal(index) {
  const samples = rows.value
    .slice(0, 10)
    .map((row) => String(row[index] ?? ''))
    .filter((text) => text && text !== 'null' && text !== 'undefined')
  if (!samples.length) return false
  const dateLike = samples.filter((text) =>
    /^\d{4}[-/]\d{1,2}([-/]\d{1,2})?/.test(text) ||
    /^\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}/.test(text)
  )
  return dateLike.length / samples.length >= 0.6
}

function inferType() {
  const declared = props.chart?.type
  const valid = ['line', 'bar', 'pie', 'table']
  const temporal = looksTemporal(xIndex.value)
  if (valid.includes(declared)) {
    // 非时间维度的“折线”改柱状，视觉上更有对比感
    if (declared === 'line' && !temporal && rows.value.length <= 12) return 'bar'
    return declared
  }
  if (!rows.value.length) return 'table'
  if (temporal) return 'line'
  const title = String(props.chart?.title || '')
  if (yIndexes.value.length === 1 && rows.value.length <= 8 && /占比|比例|份额|构成|分布/.test(title)) return 'pie'
  return rows.value.length > 0 ? 'bar' : 'table'
}

const type = ref(inferType())

const KIND_LABELS = { line: '趋势分析', bar: '对比分析', pie: '占比分析', table: '数据明细' }
const kindLabel = computed(() => KIND_LABELS[type.value] || '数据分析')

const subtitle = computed(() => {
  const yNames = yIndexes.value.map((i) => columns.value[i]).filter(Boolean)
  const parts = []
  if (yNames.length) parts.push(`指标：${yNames.join(' / ')}`)
  parts.push(`${columns.value.length} 列 · ${rows.value.length} 行${rows.value.length >= 1000 ? '+（已截断）' : ''}`)
  return parts.join(' · ')
})

const yStats = computed(() => {
  if (!hasData.value || !yIndexes.value.length) return null
  const yi = yIndexes.value[0]
  let sum = 0
  let count = 0
  let maxValue = -Infinity
  let minValue = Infinity
  let maxLabel = ''
  let minLabel = ''
  rows.value.forEach((row) => {
    const value = Number(row[yi])
    if (!Number.isFinite(value)) return
    sum += value
    count += 1
    if (value > maxValue) {
      maxValue = value
      maxLabel = String(row[xIndex.value] ?? '')
    }
    if (value < minValue) {
      minValue = value
      minLabel = String(row[xIndex.value] ?? '')
    }
  })
  if (!count) return null
  return { yi, sum, avg: sum / count, maxValue, minValue, maxLabel, minLabel }
})

const kpis = computed(() => {
  if (!yStats.value || type.value === 'table') return []
  const stats = yStats.value
  const metric = columns.value[stats.yi] || '数值'
  return [
    { label: '合计', value: fmt(stats.sum), hint: metric },
    { label: '最高', value: fmt(stats.maxValue), hint: stats.maxLabel },
    { label: '平均', value: fmt(stats.avg), hint: stats.minLabel ? `最低 ${fmt(stats.minValue)}` : '' }
  ]
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
  return text.length > 14 ? text.slice(0, 14) + '…' : text
}

function axisTooltip(params) {
  const th = themeColors.value
  const list = Array.isArray(params) ? params : [params]
  if (!list.length) return ''
  const head = list[0]?.axisValueLabel || list[0]?.name || ''
  const rowsHtml = list.map((item) => {
    const color = COLORS[item.seriesIndex % COLORS.length]
    const value = typeof item.value === 'number' ? fmtFull(item.value) : String(item.value ?? '-')
    return `<div style="display:flex;align-items:center;gap:8px;margin-top:5px"><span style="width:8px;height:8px;border-radius:2px;background:${color};flex:none"></span><span style="flex:1">${item.seriesName || ''}</span><b style="padding-left:16px">${value}</b></div>`
  }).join('')
  return `<div style="min-width:148px;font-size:11px;color:${th.tooltipText}"><div style="opacity:.62;margin-bottom:2px">${head}</div>${rowsHtml}</div>`
}

function baseOption() {
  const th = themeColors.value
  return {
    backgroundColor: 'transparent',
    animationDuration: 900,
    animationEasing: 'cubicOut',
    textStyle: {
      color: th.text,
      fontFamily: 'Inter, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif',
      fontSize: 11
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: th.tooltipBg,
      borderWidth: 0,
      borderColor: 'transparent',
      padding: [9, 12],
      extraCssText: 'border-radius:10px;box-shadow:0 10px 30px -12px rgba(0,0,0,.45);backdrop-filter:blur(6px);',
      textStyle: { color: th.tooltipText, fontSize: 11 },
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47,107,79,.07)' } },
      formatter: axisTooltip
    }
  }
}

function buildOption(kind) {
  const th = themeColors.value
  const cols = columns.value
  const data = rows.value
  const xIdx = xIndex.value
  const ys = yIndexes.value
  if (!hasData.value || !ys.length) return null

  if (kind === 'pie') {
    const yi = ys[0]
    const total = data.reduce((acc, row) => acc + (Number(row[yi]) || 0), 0)
    return {
      ...baseOption(),
      tooltip: {
        ...baseOption().tooltip,
        trigger: 'item',
        formatter: (item) => {
          const color = COLORS[item.dataIndex % COLORS.length]
          return `<div style="font-size:11px;color:${th.tooltipText}"><div style="opacity:.62">${item.name}</div><div style="display:flex;align-items:center;gap:8px;margin-top:4px"><span style="width:8px;height:8px;border-radius:2px;background:${color}"></span><b>${fmtFull(item.value)}</b><span style="opacity:.6">${item.percent}%</span></div></div>`
        }
      },
      legend: {
        bottom: 2,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 14,
        textStyle: { color: th.muted, fontSize: 10 },
        type: 'scroll'
      },
      graphic: [
        {
          type: 'text',
          left: 'center',
          top: '34%',
          silent: true,
          style: { text: fmt(total), fill: th.ink, font: '700 22px "Microsoft YaHei"', textAlign: 'center' }
        },
        {
          type: 'text',
          left: 'center',
          top: '43%',
          silent: true,
          style: { text: '合计', fill: th.muted, font: '12px "Microsoft YaHei"', textAlign: 'center' }
        }
      ],
      series: [{
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['50%', '47%'],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: { borderColor: th.bg, borderWidth: 3, borderRadius: 6 },
        label: {
          color: th.text,
          fontSize: 10,
          formatter: '{b}  {d}%',
          lineHeight: 15
        },
        labelLine: { length: 10, length2: 8, lineStyle: { color: th.axis, opacity: 0.55 } },
        emphasis: {
          scaleSize: 6,
          itemStyle: { shadowBlur: 18, shadowColor: 'rgba(0,0,0,.28)' }
        },
        data: data.map((row, index) => ({
          name: String(row[xIdx] ?? '空值'),
          value: Number(row[yi]) || 0,
          itemStyle: { color: COLORS[index % COLORS.length] }
        }))
      }]
    }
  }

  const categories = data.map((row) => labelOf(row[xIdx]))
  const series = ys.map((yi, seriesIndex) => {
    const color = COLORS[seriesIndex % COLORS.length]
    const values = data.map((row) => Number(row[yi]) || 0)
    if (kind === 'line') {
      return {
        type: 'line',
        name: cols[yi],
        data: values,
        smooth: 0.35,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: values.length <= 40,
        lineStyle: { width: 3, color, cap: 'round' },
        itemStyle: { color, borderColor: th.bg, borderWidth: 2 },
        areaStyle: ys.length === 1 ? { color: areaGradient(color) } : undefined,
        emphasis: { focus: 'series', scale: 1.3 },
        animationDelay: (index) => index * 22,
        markLine: ys.length === 1 && values.length > 2
          ? {
              silent: true,
              symbol: 'none',
              lineStyle: { type: 'dashed', color: th.axis, opacity: 0.6, width: 1 },
              label: { formatter: `均值 ${fmt(yStats.value?.avg)}`, color: th.muted, fontSize: 9, position: 'insideEndTop' },
              data: [{ type: 'average' }]
            }
          : undefined
      }
    }
    return {
      type: 'bar',
      name: cols[yi],
      data: values.map((value, index) => ({
        value,
        itemStyle: {
          color: ys.length === 1 && values.length <= 12
            ? barGradient(COLORS[index % COLORS.length])
            : barGradient(color)
        }
      })),
      barMaxWidth: ys.length > 1 ? 28 : 46,
      barGap: '14%',
      itemStyle: { borderRadius: [7, 7, 2, 2] },
      label: {
        show: ys.length === 1 && values.length <= 12,
        position: 'top',
        color: th.text,
        fontSize: 10,
        formatter: (item) => fmt(item.value)
      },
      emphasis: {
        focus: 'series',
        itemStyle: { shadowBlur: 16, shadowColor: rgba(color, 0.28) }
      },
      animationDelay: (index) => index * 32
    }
  })

  const option = {
    ...baseOption(),
    grid: { left: 8, right: 20, top: ys.length > 1 ? 38 : 26, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: th.axis,
        fontSize: 10,
        hideOverlap: true,
        margin: 12,
        rotate: categories.length > 10 ? 30 : 0,
        formatter: (value) => (value.length > 12 ? value.slice(0, 12) + '…' : value)
      },
      splitArea: { show: false }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: th.split, type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: th.axis, fontSize: 10, formatter: (value) => axisFmt(value) }
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
      itemGap: 14,
      textStyle: { color: th.muted, fontSize: 10 }
    }
  }
  if (categories.length > 40) {
    option.dataZoom = [{ type: 'inside', zoomOnMouseWheel: true }]
  }
  return option
}

function render() {
  if (!chartEl.value) return
  if (type.value === 'table' || !hasData.value) {
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

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  nextTick(render)
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = reject
    image.src = src
  })
}

async function exportImage() {
  if (!instance) return
  const th = themeColors.value
  const chartUrl = instance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: th.bg })
  const image = await loadImage(chartUrl)
  const canvas = document.createElement('canvas')
  const width = 1000
  const height = 620
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = th.bg
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = '#2F6B4F'
  ctx.fillRect(0, 0, width, 6)
  ctx.fillStyle = th.ink
  ctx.font = '600 26px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText(String(props.chart?.title || '查询结果'), 44, 58)
  ctx.fillStyle = th.muted
  ctx.font = '15px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText(`${subtitle.value} · 问数 AskData`, 44, 88)
  const chartWidth = width - 88
  const chartHeight = height - 160
  const ratio = Math.min(chartWidth / image.width, chartHeight / image.height)
  const drawWidth = image.width * ratio
  const drawHeight = image.height * ratio
  ctx.drawImage(image, 44 + (chartWidth - drawWidth) / 2, 110, drawWidth, drawHeight)
  ctx.fillStyle = 'rgba(47,107,79,.07)'
  ctx.fillRect(0, height - 34, width, 34)
  ctx.fillStyle = th.muted
  ctx.font = '12px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText('问数 AskData · 对话式数据分析平台', 44, height - 13)
  const link = document.createElement('a')
  link.href = canvas.toDataURL('image/png')
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

const tableMax = computed(() => {
  const maxMap = {}
  numericIndexes.value.forEach((index) => {
    let max = 0
    rows.value.forEach((row) => {
      const value = Math.abs(Number(row[index]))
      if (Number.isFinite(value) && value > max) max = value
    })
    maxMap[index] = max
  })
  return maxMap
})

function cellBar(index, value) {
  const max = tableMax.value[index] || 0
  if (!max || !Number.isFinite(Number(value))) return {}
  const percent = Math.min(100, Math.round((Math.abs(Number(value)) / max) * 100))
  return { background: `linear-gradient(90deg, rgba(47,107,79,.14) ${percent}%, transparent ${percent}%)` }
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
    type.value = inferType()
    nextTick(render)
  },
  { deep: true }
)
</script>

<template>
  <figure class="card chart-card" :class="`theme-${theme}`">
    <div class="chart-hd">
      <div class="chart-head-left">
        <div class="chart-kicker"><span class="kicker-dot" />{{ kindLabel }}</div>
        <div class="chart-title">{{ chart?.title || '查询结果' }}</div>
        <div class="chart-sub">{{ subtitle }}</div>
      </div>
      <div class="chart-hd-right">
        <button class="chart-theme" :title="theme === 'light' ? '切换深色图表' : '切换浅色图表'" @click="toggleTheme">
          <Icon :name="theme === 'light' ? 'moon' : 'sun'" :size="11" />{{ theme === 'light' ? '深色' : '浅色' }}
        </button>
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
    </div>

    <div v-if="kpis.length" class="chart-kpis">
      <div v-for="item in kpis" :key="item.label" class="chart-kpi">
        <span class="kpi-label">{{ item.label }}</span>
        <b class="kpi-value">{{ item.value }}</b>
        <span class="kpi-hint">{{ item.hint }}</span>
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
              <td v-for="(value, i) in row" :key="i" :class="{ num: typeof value === 'number' }" :style="typeof value === 'number' ? cellBar(i, value) : {}">
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
