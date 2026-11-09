<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import Icon from './Icon.vue'
import ProductShowcaseChart from './ProductShowcaseChart.vue'

const props = defineProps({
  chart: { type: Object, default: () => ({}) },
  result: { type: Object, default: () => ({ columns: [], rows: [] }) }
})
const emit = defineEmits(['fill'])

// 更丰富的分类色板（品牌绿 + 琥珀 + 珊瑚 + 蓝 + 紫 + 青 + 金 + 灰蓝）
const COLORS = ['#2F6B4F', '#E8A33D', '#D96C5F', '#4C8DAE', '#8B6BB1', '#4FA391', '#C4A45A', '#7C8B9E']
const TYPES = [
  { type: 'bag', label: '商品图', icon: 'image' },
  { type: 'line', label: '折线', icon: 'line-chart' },
  { type: 'bar', label: '柱状', icon: 'bar-chart' },
  { type: 'pie', label: '环形', icon: 'pie-chart' },
  { type: 'scatter', label: '散点', icon: 'scatter' },
  { type: 'heatmap', label: '热力', icon: 'heatmap' },
  { type: 'treemap', label: '树图', icon: 'treemap' }
]
const KIND_LABELS = { bag: '商品展示', line: '趋势分析', bar: '对比分析', pie: '占比分析', scatter: '相关性', heatmap: '矩阵分布', treemap: '层级占比', table: '数据明细' }
const THEMES = {
  light: {
    bg: '#FFFEFB', panel: '#FFFFFF', ink: '#2B2823', text: '#5E594E', muted: '#8C8678',
    axis: '#A8A08F', grid: '#EFEBE1', split: 'rgba(47,107,79,.10)',
    tooltipBg: 'rgba(38,44,39,.96)', tooltipText: '#F4F1E7', border: '#F2EEE4'
  },
  dark: {
    bg: '#17201B', panel: '#1E2A23', ink: '#EDF4EE', text: '#C8D8CC', muted: '#8FA898',
    axis: '#7B9485', grid: 'rgba(255,255,255,.06)', split: 'rgba(255,255,255,.08)',
    tooltipBg: 'rgba(245,250,246,.96)', tooltipText: '#1F2D24', border: '#26352C'
  }
}

const columns = computed(() => props.result?.columns || [])
const rows = computed(() => props.result?.rows || [])
const hasData = computed(() => columns.value.length > 0 && rows.value.length > 0)
const theme = ref('light')
const themeColors = computed(() => THEMES[theme.value])
const chartEl = ref(null)
const bagRef = ref(null)
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

function isShareColumn(name) {
  return /占比|比例|百分比|份额|%/.test(String(name || ''))
}

function isRateColumn(name) {
  return /率/.test(String(name || ''))
}

// 购物袋图优先使用“销售额”这类绝对值列，而不是已经算好的占比列
const bagMetric = computed(() => {
  const nums = numericIndexes.value
  const nonShare = nums.filter((index) => !isShareColumn(columns.value[index]))
  return (nonShare.length ? nonShare : nums)[0] ?? -1
})
const bagShareMode = computed(() => bagMetric.value >= 0 && isShareColumn(columns.value[bagMetric.value]))

const categoricalIndexes = computed(() =>
  columns.value.map((_, index) => index).filter((index) => !numericIndexes.value.includes(index))
)
const hasTwoNumeric = computed(() => numericIndexes.value.length >= 2)
const numericUniques = computed(() =>
  numericIndexes.value.map((index) => new Set(rows.value.map((row) => Number(row[index])).filter((value) => Number.isFinite(value))).size)
)
const scatterReady = computed(() => {
  if (!hasTwoNumeric.value) return false
  return Math.min(numericUniques.value[0] ?? 0, numericUniques.value[1] ?? 0) >= 6
})
const hasHeatmapShape = computed(() => categoricalIndexes.value.length >= 2 && numericIndexes.value.length >= 1)

/** 当前数据可用的图表类型 */
const availableTypes = computed(() => {
  if (!hasData.value) return []
  const list = []
  if (hasHeatmapShape.value) list.push('heatmap')
  if (scatterReady.value) list.push('scatter')
  if (categoricalIndexes.value.length === 1 && numericIndexes.value.length >= 1) list.push('treemap')
  list.push('bag', 'line', 'bar', 'pie')
  return [...new Set(list)].map((type) => TYPES.find((item) => item.type === type)).filter(Boolean)
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

/** 根据「数据类型 + 问题意图」推荐默认图表 */
const recommendation = computed(() => {
  if (!hasData.value) return { type: 'table', reason: '暂无数据，先展示数据明细' }
  const title = String(props.chart?.title || '')
  const temporal = looksTemporal(xIndex.value)
  const single = yIndexes.value.length === 1
  const count = rows.value.length

  if (hasHeatmapShape.value) return { type: 'heatmap', reason: '两个分类维度 + 一个数值 → 热力图看矩阵分布' }
  if (scatterReady.value && (numericIndexes.value.includes(xIndex.value) || categoricalIndexes.value.length === 0)) {
    return { type: 'scatter', reason: '两个连续数值字段 → 散点图看相关关系' }
  }
  if (temporal) return { type: 'line', reason: '检测到时间字段 → 趋势用折线更直观' }
  if (single && count > 12) return { type: 'line', reason: '数据点较多 → 折线图更能看清变化' }
  if (single && /品类|商品|类目|类别/.test(title) && count >= 4 && count <= 12) {
    return { type: 'bag', reason: '品类构成 → 商品图展示更有画面感' }
  }
  if (single && /占比|比例|份额|构成|分布|贡献|结构/.test(title) && count <= 10) {
    return { type: 'pie', reason: '占比关系 → 环形图更直观' }
  }
  if (single && count <= 12) return { type: 'bar', reason: '分类对比 → 柱状图更清晰' }
  if (!single) return { type: 'bar', reason: '多指标对比 → 分组柱状图更合适' }
  return { type: 'table', reason: '字段较多，先展示明细' }
})

const type = ref(recommendation.value.type)
const showTable = ref(recommendation.value.type === 'table')
const orderedTypes = computed(() => {
  const rec = recommendation.value.type
  const pool = availableTypes.value.length ? availableTypes.value : TYPES
  const first = pool.find((item) => item.type === rec) || TYPES.find((item) => item.type === rec)
  const rest = pool.filter((item) => item.type !== rec)
  return first ? [first, ...rest] : rest
})
const kindLabel = computed(() => KIND_LABELS[showTable.value ? 'table' : type.value] || '数据分析')
const isRecommended = computed(() => !showTable.value && type.value === recommendation.value.type)
const reasonLabel = computed(() => recommendation.value.reason)

const subtitle = computed(() => {
  const yNames = yIndexes.value.map((i) => columns.value[i]).filter(Boolean)
  const parts = []
  if (yNames.length) parts.push(`指标：${yNames.join(' / ')}`)
  parts.push(`${columns.value.length} 列 · ${rows.value.length} 行${rows.value.length >= 1000 ? '+（已截断）' : ''}`)
  return parts.join(' · ')
})

const yStats = computed(() => {
  if (!hasData.value) return null
  const yi = type.value === 'bag' ? bagMetric.value : (yIndexes.value[0] ?? -1)
  if (yi === undefined || yi === null || yi < 0) return null
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
  if (!yStats.value || showTable.value) return []
  const stats = yStats.value
  const metric = columns.value[stats.yi] || '数值'
  const share = isShareColumn(metric)
  const rate = isRateColumn(metric)
  const fmtValue = (value) => (share || rate ? `${Math.min(100, Number(value) || 0).toFixed(1)}%` : fmt(value))
  if (rate) {
    return [
      { label: '平均', value: fmtValue(stats.avg), hint: metric },
      { label: '最高', value: fmtValue(stats.maxValue), hint: stats.maxLabel },
      { label: '最低', value: fmtValue(stats.minValue), hint: stats.minLabel }
    ]
  }
  return [
    { label: '合计', value: share ? '100%' : fmt(stats.sum), hint: metric },
    { label: '最高', value: fmtValue(stats.maxValue), hint: stats.maxLabel },
    { label: '平均', value: fmtValue(stats.avg), hint: stats.minLabel ? `最低 ${fmtValue(stats.minValue)}` : '' }
  ]
})

const bagItems = computed(() => {
  if (!hasData.value || bagMetric.value < 0) return []
  const yi = bagMetric.value
  const raw = rows.value
    .map((row) => ({ name: String(row[xIndex.value] ?? '未分类'), value: Number(row[yi]) }))
    .filter((item) => Number.isFinite(item.value) && item.value > 0)
    .sort((a, b) => b.value - a.value)
  let items = raw
  if (raw.length > 12) {
    const top = raw.slice(0, 11)
    const restValue = raw.slice(11).reduce((sum, item) => sum + item.value, 0)
    if (restValue > 0) top.push({ name: '其他', value: restValue })
    items = top
  }
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1
  return items.map((item) => ({
    ...item,
    percent: bagShareMode.value ? Math.min(100, item.value) : (item.value / total) * 100,
    share: bagShareMode.value
  }))
})

const bagTotalLabel = computed(() => {
  if (!bagItems.value.length) return ''
  if (bagShareMode.value) return `共 ${bagItems.value.length} 个品类`
  const total = bagItems.value.reduce((sum, item) => sum + item.value, 0)
  return `合计 ${fmt(total)} 元`
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
    return `<div style="display:flex;align-items:center;gap:8px;margin-top:6px"><span style="width:9px;height:9px;border-radius:2px;background:${color};flex:none"></span><span style="flex:1">${item.seriesName || ''}</span><b style="padding-left:16px">${value}</b></div>`
  }).join('')
  return `<div style="min-width:150px;font-size:12px;color:${th.tooltipText}"><div style="opacity:.62;margin-bottom:2px">${head}</div>${rowsHtml}</div>`
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
      fontSize: 12
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: th.tooltipBg,
      borderWidth: 0,
      borderColor: 'transparent',
      padding: [10, 13],
      extraCssText: 'border-radius:10px;box-shadow:0 10px 30px -12px rgba(0,0,0,.45);backdrop-filter:blur(6px);',
      textStyle: { color: th.tooltipText, fontSize: 12 },
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

  if (kind === 'scatter') {
    const xi = numericIndexes.value[0]
    const yi = numericIndexes.value[1]
    if (xi === undefined || yi === undefined) return null
    const points = data
      .map((row) => [Number(row[xi]), Number(row[yi])])
      .filter((pair) => Number.isFinite(pair[0]) && Number.isFinite(pair[1]))
    return {
      ...baseOption(),
      grid: { left: 18, right: 26, top: 34, bottom: 14, containLabel: true },
      tooltip: {
        ...baseOption().tooltip,
        trigger: 'item',
        formatter: (item) => `<div style="font-size:12px;color:${th.tooltipText}"><div style="opacity:.62;margin-bottom:4px">${cols[xi]} / ${cols[yi]}</div><div><b>${fmtFull(item.value[0])}</b> · <b>${fmtFull(item.value[1])}</b></div></div>`
      },
      xAxis: {
        type: 'value', name: cols[xi],
        nameTextStyle: { color: th.muted, fontSize: 11 },
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: th.axis, fontSize: 11.5, formatter: axisFmt },
        splitLine: { lineStyle: { color: th.split, type: 'dashed' } }
      },
      yAxis: {
        type: 'value', name: cols[yi],
        nameTextStyle: { color: th.muted, fontSize: 11 },
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: th.axis, fontSize: 11.5, formatter: axisFmt },
        splitLine: { lineStyle: { color: th.split, type: 'dashed' } }
      },
      series: [{
        type: 'scatter',
        data: points,
        symbolSize: 10,
        itemStyle: { color: COLORS[0], opacity: 0.78, borderColor: th.bg, borderWidth: 1.5 },
        emphasis: { scale: 1.5, itemStyle: { shadowBlur: 12, shadowColor: 'rgba(47,107,79,.35)' } }
      }]
    }
  }

  if (kind === 'treemap') {
    const yi = ys[0]
    const totalValue = data.reduce((sum, row) => sum + (Number(row[yi]) || 0), 0) || 1
    return {
      ...baseOption(),
      tooltip: {
        ...baseOption().tooltip,
        trigger: 'item',
        formatter: (item) => `<div style="font-size:12px;color:${th.tooltipText}"><div style="opacity:.62">${item.name}</div><div style="margin-top:4px"><b>${fmtFull(item.value)}</b></div></div>`
      },
      series: [{
        type: 'treemap',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        left: 12,
        right: 12,
        top: 12,
        bottom: 12,
        label: {
          show: true,
          formatter: (params) => `${params.name}\n${Number(params.data?.percent || 0).toFixed(1)}%`,
          color: '#FFFFFF',
          fontSize: 14,
          lineHeight: 20,
          fontWeight: 600,
          textShadowColor: 'rgba(0,0,0,.35)',
          textShadowBlur: 3
        },
        itemStyle: { borderColor: th.bg, borderWidth: 2, gapWidth: 2, borderRadius: 6 },
        emphasis: { itemStyle: { shadowBlur: 14, shadowColor: 'rgba(0,0,0,.3)' } },
        data: data.map((row, index) => {
          const value = Number(row[yi]) || 0
          return {
            name: String(row[xIdx] ?? '未分类'),
            value,
            percent: (value / totalValue) * 100,
            itemStyle: { color: COLORS[index % COLORS.length] }
          }
        })
      }]
    }
  }

  if (kind === 'heatmap') {
    const cats = categoricalIndexes.value
    if (cats.length < 2 || !numericIndexes.value.length) return null
    const catX = cats[0]
    const catY = cats[1]
    const valueIndex = numericIndexes.value[0]
    const xValues = [...new Set(data.map((row) => String(row[catX] ?? '-')))]
    const yValues = [...new Set(data.map((row) => String(row[catY] ?? '-')))]
    // 同一个 (行, 列) 可能有多条记录，先聚合，避免标签叠在一起
    const cellMap = new Map()
    data.forEach((row) => {
      const x = xValues.indexOf(String(row[catX] ?? '-'))
      const y = yValues.indexOf(String(row[catY] ?? '-'))
      const value = Number(row[valueIndex]) || 0
      if (x < 0 || y < 0) return
      const key = `${x}|${y}`
      if (!cellMap.has(key)) {
        cellMap.set(key, { x, y, sum: value, count: 1 })
      } else {
        const cell = cellMap.get(key)
        cell.sum += value
        cell.count += 1
      }
    })
    const points = [...cellMap.values()].map((cell) => [cell.x, cell.y, cell.sum / cell.count])
    const values = points.map((point) => point[2])
    const min = Math.min(...values, 0)
    const max = Math.max(...values, 1)
    return {
      ...baseOption(),
      tooltip: {
        ...baseOption().tooltip,
        trigger: 'item',
        formatter: (item) => `<div style="font-size:12px;color:${th.tooltipText}"><div style="opacity:.62">${xValues[item.value[0]]} · ${yValues[item.value[1]]}</div><div style="margin-top:4px"><b>${fmtFull(item.value[2])}</b></div></div>`
      },
      grid: { left: 18, right: 26, top: 34, bottom: 54, containLabel: true },
      xAxis: {
        type: 'category', data: xValues,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: th.axis, fontSize: 11.5, interval: 0 }
      },
      yAxis: {
        type: 'category', data: yValues,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: th.axis, fontSize: 11.5 }
      },
      visualMap: {
        min, max,
        orient: 'horizontal', left: 'center', bottom: 0,
        itemWidth: 10, itemHeight: 90,
        textStyle: { color: th.muted, fontSize: 10.5 },
        inRange: { color: ['#E9F1EC', '#9CC5AC', '#2F6B4F'] }
      },
      series: [{
        type: 'heatmap',
        animation: false,
        labelLayout: { hideOverlap: true },
        data: points,
        label: { show: true, color: th.ink, fontSize: 10.5, formatter: (item) => fmt(item.value[2]) },
        itemStyle: { borderColor: th.bg, borderWidth: 2, borderRadius: 4 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(47,107,79,.35)' } }
      }]
    }
  }

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
          return `<div style="font-size:12px;color:${th.tooltipText}"><div style="opacity:.62">${item.name}</div><div style="display:flex;align-items:center;gap:8px;margin-top:5px"><span style="width:9px;height:9px;border-radius:2px;background:${color}"></span><b>${fmtFull(item.value)}</b><span style="opacity:.6">${item.percent}%</span></div></div>`
        }
      },
      legend: {
        bottom: 2, icon: 'circle', itemWidth: 9, itemHeight: 9, itemGap: 14,
        textStyle: { color: th.muted, fontSize: 11.5 }, type: 'scroll'
      },
      graphic: [
        { type: 'text', left: 'center', top: '35%', silent: true, style: { text: fmt(total), fill: th.ink, font: '700 24px "Microsoft YaHei"', textAlign: 'center' } },
        { type: 'text', left: 'center', top: '44%', silent: true, style: { text: '合计', fill: th.muted, font: '13px "Microsoft YaHei"', textAlign: 'center' } }
      ],
      series: [{
        type: 'pie',
        radius: ['50%', '72%'],
        center: ['50%', '47%'],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: { borderColor: th.bg, borderWidth: 3, borderRadius: 6 },
        label: { color: th.text, fontSize: 11.5, formatter: '{b}  {d}%', lineHeight: 16 },
        labelLine: { length: 10, length2: 8, lineStyle: { color: th.axis, opacity: 0.55 } },
        emphasis: { scaleSize: 6, itemStyle: { shadowBlur: 18, shadowColor: 'rgba(0,0,0,.28)' } },
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
        type: 'line', name: cols[yi], data: values,
        smooth: 0.35, symbol: 'circle', symbolSize: 6, showSymbol: values.length <= 40,
        lineStyle: { width: 3, color, cap: 'round' },
        itemStyle: { color, borderColor: th.bg, borderWidth: 2 },
        areaStyle: ys.length === 1 ? { color: areaGradient(color) } : undefined,
        emphasis: { focus: 'series', scale: 1.3 },
        animationDelay: (index) => index * 22,
        markLine: ys.length === 1 && values.length > 2
          ? {
              silent: true, symbol: 'none',
              lineStyle: { type: 'dashed', color: th.axis, opacity: 0.6, width: 1 },
              label: { formatter: `均值 ${fmt(yStats.value?.avg)}`, color: th.muted, fontSize: 10, position: 'insideEndTop' },
              data: [{ type: 'average' }]
            }
          : undefined
      }
    }
    return {
      type: 'bar', name: cols[yi],
      data: values.map((value, index) => ({
        value,
        itemStyle: {
          color: ys.length === 1 && values.length <= 12
            ? barGradient(COLORS[index % COLORS.length])
            : barGradient(color)
        }
      })),
      barMaxWidth: ys.length > 1 ? 30 : 46,
      barGap: '14%',
      itemStyle: { borderRadius: [7, 7, 2, 2] },
      label: { show: ys.length === 1 && values.length <= 12, position: 'top', color: th.text, fontSize: 11.5, formatter: (item) => fmt(item.value) },
      emphasis: { focus: 'series', itemStyle: { shadowBlur: 16, shadowColor: rgba(color, 0.28) } },
      animationDelay: (index) => index * 32
    }
  })

  const option = {
    ...baseOption(),
    grid: { left: 8, right: 20, top: ys.length > 1 ? 42 : 28, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category', data: categories,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: {
        color: th.axis, fontSize: 11.5, hideOverlap: true, margin: 13,
        rotate: categories.length > 10 ? 30 : 0,
        formatter: (value) => (value.length > 12 ? value.slice(0, 12) + '…' : value)
      }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: th.split, type: 'dashed' } },
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: th.axis, fontSize: 11.5, formatter: (value) => axisFmt(value) }
    },
    series
  }
  if (ys.length > 1) {
    option.legend = { top: 0, right: 0, icon: 'circle', itemWidth: 9, itemHeight: 9, itemGap: 14, textStyle: { color: th.muted, fontSize: 11.5 } }
  }
  if (categories.length > 40) {
    option.dataZoom = [{ type: 'inside', zoomOnMouseWheel: true }]
  }
  return option
}

function render() {
  if (!chartEl.value) return
  if (showTable.value || type.value === 'bag' || !hasData.value) return
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
  showTable.value = false
  type.value = nextType
  nextTick(render)
}

function toggleTable() {
  showTable.value = !showTable.value
  if (!showTable.value) {
    if (type.value === 'table') {
      type.value = recommendation.value.type === 'table' ? 'bar' : recommendation.value.type
    }
    nextTick(render)
  }
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
  const th = themeColors.value
  let chartUrl = ''
  if (type.value === 'bag' && !showTable.value) {
    if (!bagRef.value) return
    chartUrl = await bagRef.value.toDataURL(th.bg)
  } else {
    if (!instance) return
    chartUrl = instance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: th.bg })
  }
  const image = await loadImage(chartUrl)
  const canvas = document.createElement('canvas')
  const width = 1000
  const height = 660
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = th.bg
  ctx.fillRect(0, 0, width, height)
  ctx.fillStyle = '#2F6B4F'
  ctx.fillRect(0, 0, width, 6)
  ctx.fillStyle = th.ink
  ctx.font = '600 27px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText(String(props.chart?.title || '查询结果'), 44, 60)
  ctx.fillStyle = th.muted
  ctx.font = '16px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText(`${subtitle.value} · 问数 AskData`, 44, 92)
  const chartWidth = width - 88
  const chartHeight = height - 170
  const ratio = Math.min(chartWidth / image.width, chartHeight / image.height)
  const drawWidth = image.width * ratio
  const drawHeight = image.height * ratio
  ctx.drawImage(image, 44 + (chartWidth - drawWidth) / 2, 116, drawWidth, drawHeight)
  ctx.fillStyle = 'rgba(47,107,79,.07)'
  ctx.fillRect(0, height - 36, width, 36)
  ctx.fillStyle = th.muted
  ctx.font = '13px "Microsoft YaHei", "PingFang SC", sans-serif'
  ctx.fillText('问数 AskData · 对话式数据分析平台', 44, height - 14)
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

function onSelectProduct(node) {
  if (!node) return
  emit('fill', `查看「${node.name}」的销售明细`)
}

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
    const rec = recommendation.value
    type.value = rec.type
    showTable.value = rec.type === 'table'
    nextTick(render)
  },
  { deep: true }
)
</script>

<template>
  <figure class="card chart-card" :class="[`theme-${theme}`, { 'is-table': showTable }]">
    <div class="chart-hd">
      <div class="chart-head-left">
        <div class="chart-kicker">
          <span class="kicker-dot" />{{ showTable ? '数据明细' : (isRecommended ? '推荐视图 · ' + kindLabel : '探索视图 · ' + kindLabel) }}
        </div>
        <div class="chart-title">{{ chart?.title || '查询结果' }}</div>
        <div class="chart-sub">{{ subtitle }}</div>
      </div>
      <div class="chart-hd-right">
        <button class="chart-theme" :title="theme === 'light' ? '切换深色图表' : '切换浅色图表'" @click="toggleTheme">
          <Icon :name="theme === 'light' ? 'moon' : 'sun'" :size="12" />{{ theme === 'light' ? '深色' : '浅色' }}
        </button>
        <div class="chart-types">
          <button
            v-for="item in orderedTypes"
            :key="item.type"
            class="chart-type"
            :class="{ on: !showTable && type === item.type, recommended: item.type === recommendation.type }"
            @click="switchType(item.type)"
          >
            <Icon :name="item.icon" :size="12" />{{ item.label }}
            <span v-if="item.type === recommendation.type" class="rec-badge">推荐</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="!showTable" class="chart-reason"><b>推荐</b>{{ reasonLabel }}</div>

    <div v-if="kpis.length" class="chart-kpis">
      <div v-for="item in kpis" :key="item.label" class="chart-kpi">
        <span class="kpi-label">{{ item.label }}</span>
        <b class="kpi-value">{{ item.value }}</b>
        <span class="kpi-hint">{{ item.hint }}</span>
      </div>
    </div>

    <div class="chart-body">
      <div v-show="!showTable && type !== 'bag'" ref="chartEl" class="echart" />
      <ProductShowcaseChart
        v-if="!showTable && type === 'bag'"
        ref="bagRef"
        :items="bagItems"
        :theme="theme"
        :total-label="bagTotalLabel"
        @select="onSelectProduct"
      />
      <div v-if="!hasData" class="chart-empty">没有查询到符合条件的数据</div>
      <div v-if="showTable && hasData" class="table-scroll">
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
      <Icon name="database" :size="12" />
      数据来自当前数据集
      <div class="chart-actions">
        <button class="btn-mini" @click="toggleTable">
          <Icon :name="showTable ? 'line-chart' : 'table'" :size="12" />{{ showTable ? '返回图表' : '数据明细' }}
        </button>
        <button class="btn-mini" @click="showTable ? exportData() : exportImage()">
          <Icon name="download" :size="12" />{{ showTable ? '导出 CSV' : '导出图片' }}
        </button>
        <button class="btn-mini" @click="exportData"><Icon name="copy" :size="12" />下载数据</button>
      </div>
    </div>
  </figure>
</template>

