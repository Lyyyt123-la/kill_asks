<script setup>
import { computed, onMounted, ref } from 'vue'

/**
 * 购物袋创意可视化（SVG 自绘）
 * - 购物袋代表“全部品类销售额 = 100%”
 * - 每个品类一个商品图标，图标名称居中显示在图标下方
 * - 图标底部液面按销售额占比填充，不同品类不同颜色
 * - 每行最多 4 个，超出按左→右、上→下换行
 */
const props = defineProps({
  items: { type: Array, default: () => [] },
  theme: { type: String, default: 'light' },
  totalLabel: { type: String, default: '' }
})

const bagRef = ref(null)
const mounted = ref(false)
onMounted(() => requestAnimationFrame(() => { mounted.value = true }))

const COLS = 4
const PALETTE = ['#2F6B4F', '#E8A33D', '#D96C5F', '#4C8DAE', '#8B6BB1', '#4FA391', '#C4A45A', '#7C8B9E']

const ICON_MAP = [
  [/女装|连衣裙|裙|女鞋/, '👗'],
  [/男装|男鞋|衬衫/, '👔'],
  [/美妆|化妆|护肤|口红/, '💄'],
  [/食品|零食|生鲜|水果/, '🍎'],
  [/3C|数码|手机|电脑|电子/, '📱'],
  [/家居|家纺|家具/, '🛋️'],
  [/母婴|婴童|奶粉/, '🍼'],
  [/运动|户外|健身/, '⚽'],
  [/鞋|靴/, '👟'],
  [/箱包|包/, '👜'],
  [/图书|书/, '📚'],
  [/家电|电器/, '🔌'],
  [/宠物/, '🐾'],
  [/汽车|车品/, '🚗'],
  [/珠宝|饰品/, '💍'],
  [/饮料|酒/, '🥤']
]

function iconOf(name) {
  for (const [pattern, icon] of ICON_MAP) {
    if (pattern.test(String(name))) return icon
  }
  return '🛍️'
}

const THEMES = {
  light: {
    bg: '#FFFEFB',
    bag: '#F6F3EA',
    bagStroke: '#D9D2C2',
    tile: '#E9E5DA',
    ink: '#2B2823',
    muted: '#7A7468',
    subtle: '#A39C8D',
    textOnFill: '#FFFFFF',
    darkText: '#2B2823'
  },
  dark: {
    bg: '#17201B',
    bag: '#1E2A23',
    bagStroke: '#31443A',
    tile: '#2A3A30',
    ink: '#EDF4EE',
    muted: '#9DB7A6',
    subtle: '#7B9485',
    textOnFill: '#FFFFFF',
    darkText: '#EDF4EE'
  }
}
const th = computed(() => THEMES[props.theme] || THEMES.light)

const sorted = computed(() =>
  [...props.items]
    .filter((item) => Number.isFinite(Number(item.value)) && Number(item.value) > 0)
    .sort((a, b) => Number(b.value) - Number(a.value))
)
const total = computed(() => sorted.value.reduce((sum, item) => sum + Number(item.value), 0) || 1)

const nodes = computed(() =>
  sorted.value.map((item, index) => {
    const value = Number(item.value)
    const percent = Number.isFinite(Number(item.percent)) ? Number(item.percent) : (value / total.value) * 100
    return {
      name: String(item.name ?? '未分类'),
      value,
      share: Boolean(item.share),
      percent,
      color: PALETTE[index % PALETTE.length],
      icon: iconOf(item.name)
    }
  })
)

const rows = computed(() => Math.max(1, Math.ceil(nodes.value.length / COLS)))

// 画布与布局
const W = 860
const H = 600
const BAG = { x: 74, y: 108, w: 712, h: 456, r: 46 }
const PAD = 36
const GAP = 18
const HEADER_H = 58
const TILE_W = (BAG.w - PAD * 2 - GAP * (COLS - 1)) / COLS
const TILE_H = computed(() => {
  const available = BAG.h - PAD * 2 - HEADER_H
  return Math.min(168, (available - GAP * (rows.value - 1)) / rows.value)
})

function posOf(index) {
  const row = Math.floor(index / COLS)
  const col = index % COLS
  return {
    x: BAG.x + PAD + col * (TILE_W + GAP),
    y: BAG.y + PAD + HEADER_H + row * (TILE_H.value + GAP)
  }
}

function fillPercent(node) {
  return Math.max(0, Math.min(100, node.percent))
}

function textColorAt(node, yRatio) {
  // 液面从底部升起，文字位置低于液面时用白色，否则用深色
  return yRatio >= 1 - node.percent / 100 ? th.value.textOnFill : th.value.ink
}

function fmt(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万'
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function toDataURL(backgroundColor) {
  const svg = bagRef.value?.querySelector('svg')
  if (!svg) return ''
  const clone = svg.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const source = new XMLSerializer().serializeToString(clone)
  const svgUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(source)
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const scale = 2
      const canvas = document.createElement('canvas')
      canvas.width = W * scale
      canvas.height = H * scale
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = backgroundColor || th.value.bg
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/png'))
    }
    image.onerror = reject
    image.src = svgUrl
  })
}

defineExpose({ toDataURL })
</script>

<template>
  <div ref="bagRef" class="bag-chart">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="品类销售额购物袋图">
      <!-- 提手 -->
      <path
        :d="`M ${BAG.x + BAG.w * 0.28} ${BAG.y + 10} C ${BAG.x + BAG.w * 0.3} ${BAG.y - 46}, ${BAG.x + BAG.w * 0.7} ${BAG.y - 46}, ${BAG.x + BAG.w * 0.72} ${BAG.y + 10}`"
        fill="none"
        :stroke="th.bagStroke"
        stroke-width="20"
        stroke-linecap="round"
      />
      <!-- 袋子主体 -->
      <rect
        :x="BAG.x"
        :y="BAG.y"
        :width="BAG.w"
        :height="BAG.h"
        :rx="BAG.r"
        :fill="th.bag"
        :stroke="th.bagStroke"
        stroke-width="3"
      />
      <rect
        :x="BAG.x + 10"
        :y="BAG.y + 10"
        :width="BAG.w - 20"
        :height="BAG.h - 20"
        :rx="BAG.r - 7"
        fill="none"
        :stroke="th.bagStroke"
        stroke-width="1"
        stroke-dasharray="7 9"
        opacity="0.55"
      />
      <!-- 袋内标题 -->
      <text
        :x="BAG.x + PAD"
        :y="BAG.y + 44"
        :fill="th.ink"
        font-size="23"
        font-weight="700"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >品类销售构成 · 100%</text>
      <text
        :x="BAG.x + BAG.w - PAD"
        :y="BAG.y + 44"
        :fill="th.muted"
        font-size="16"
        text-anchor="end"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >{{ totalLabel || ('合计 ' + fmt(total) + ' 元') }}</text>
      <text
        :x="BAG.x + PAD"
        :y="BAG.y + 68"
        :fill="th.subtle"
        font-size="15"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >每个图标代表一个品类 · 液面高度 = 销售额占比 · 按左→右、上→下排列</text>

      <!-- 品类图标格 -->
      <g v-for="(node, index) in nodes" :key="node.name" :transform="`translate(${posOf(index).x}, ${posOf(index).y})`">
        <title>{{ node.name }}：{{ node.share ? ('占比 ' + node.percent.toFixed(2) + '%') : ('销售额 ' + fmt(node.value) + ' 元') }}</title>
        <!-- 灰色底 -->
        <rect :width="TILE_W" :height="TILE_H" rx="18" :fill="th.tile" />
        <!-- 百分比液面（从下往上） -->
        <rect
          :width="TILE_W"
          :height="TILE_H"
          rx="18"
          :fill="node.color"
          opacity="0.94"
          :style="{
            transformBox: 'fill-box',
            transformOrigin: '50% 100%',
            transform: mounted ? `scaleY(${fillPercent(node) / 100})` : 'scaleY(0)',
            transition: 'transform .85s cubic-bezier(.2,.7,.2,1)'
          }"
        />
        <!-- 百分比 -->
        <text
          :x="TILE_W / 2"
          :y="TILE_H * 0.24"
          :fill="textColorAt(node, 0.24)"
          font-size="20"
          font-weight="800"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ node.percent.toFixed(1) }}%</text>
        <!-- 商品图标 -->
        <text
          :x="TILE_W / 2"
          :y="TILE_H * 0.53"
          font-size="36"
          text-anchor="middle"
          dominant-baseline="middle"
        >{{ node.icon }}</text>
        <!-- 图标名称（居中在图标下方） -->
        <text
          :x="TILE_W / 2"
          :y="TILE_H * 0.78"
          :fill="textColorAt(node, 0.78)"
          font-size="16"
          font-weight="700"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ node.name }}</text>
        <!-- 颜色标识线 -->
        <rect :x="TILE_W / 2 - 16" :y="TILE_H - 20" width="32" height="4" rx="2" :fill="node.color" opacity="0.95" />
      </g>

      <!-- 空态 -->
      <text
        v-if="!nodes.length"
        :x="W / 2"
        :y="H / 2"
        :fill="th.muted"
        font-size="18"
        text-anchor="middle"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >没有可用于占比展示的品类数据</text>
    </svg>
  </div>
</template>

<style scoped>
.bag-chart {
  width: 100%;
  padding: 0 4px;
}
.bag-chart svg {
  width: 100%;
  height: auto;
  display: block;
}
</style>

