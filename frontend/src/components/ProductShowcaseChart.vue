<script setup>
import { computed, onMounted, ref } from 'vue'

/**
 * 商品图可视化（第三版，按反馈重做）
 * - 商品图像本身作为底：整体灰度渲染
 * - 颜色在“图像内部”按占比从下往上填充（彩色剪影遮罩 + 底部裁剪）
 * - 不同品类不同颜色，低饱和浅色
 * - 不画购物袋、不画边框；每行 4 个，左→右、上→下排列
 */
const props = defineProps({
  items: { type: Array, default: () => [] },
  theme: { type: String, default: 'light' },
  totalLabel: { type: String, default: '' }
})

const wrapRef = ref(null)
const growth = ref(0)
const uid = Math.random().toString(36).slice(2, 8)

onMounted(() => {
  const started = performance.now()
  const duration = 800
  const tick = (now) => {
    const progress = Math.min(1, (now - started) / duration)
    growth.value = 1 - Math.pow(1 - progress, 3)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})

// 低饱和浅色（图像内部占比色）
const FILL_COLORS = ['#8FC5A8', '#EAC17C', '#E5A79B', '#8FB8D6', '#BBA1D8', '#8FCBBE', '#D8C892', '#AEBFD2']

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
  light: { bg: '#FFFEFB', ink: '#2B2823', muted: '#7A7468', subtle: '#A39C8D' },
  dark: { bg: '#17201B', ink: '#EDF4EE', muted: '#9DB7A6', subtle: '#7B9485' }
}
const th = computed(() => THEMES[props.theme] || THEMES.light)

const sorted = computed(() =>
  [...props.items]
    .filter((item) => Number.isFinite(Number(item.value)) && Number(item.value) > 0)
    .sort((a, b) => Number(b.value) - Number(a.value))
)
const total = computed(() => sorted.value.reduce((sum, item) => sum + Number(item.value), 0) || 1)

const EMOJI_FONT = '"Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Microsoft YaHei", sans-serif'
const RENDER_SIZE = 240

function drawEmoji(ctx, icon, size) {
  ctx.font = `${Math.round(size * 0.82)}px ${EMOJI_FONT}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(icon, size / 2, size / 2 + size * 0.03)
}

/** 灰度商品图 */
function grayImage(icon) {
  const canvas = document.createElement('canvas')
  canvas.width = RENDER_SIZE
  canvas.height = RENDER_SIZE
  const ctx = canvas.getContext('2d')
  ctx.filter = 'grayscale(1) contrast(0.96) brightness(1.14)'
  drawEmoji(ctx, icon, RENDER_SIZE)
  return canvas.toDataURL('image/png')
}

/** 纯色剪影（用商品图 alpha 做遮罩，内部填充品类颜色） */
function colorSilhouette(icon, color) {
  const canvas = document.createElement('canvas')
  canvas.width = RENDER_SIZE
  canvas.height = RENDER_SIZE
  const ctx = canvas.getContext('2d')
  drawEmoji(ctx, icon, RENDER_SIZE)
  ctx.globalCompositeOperation = 'source-in'
  ctx.fillStyle = color
  ctx.fillRect(0, 0, RENDER_SIZE, RENDER_SIZE)
  return canvas.toDataURL('image/png')
}

/** 检测 emoji 实际像素范围（避免把颜色裁到图形之外） */
function measureEmoji(icon) {
  const canvas = document.createElement('canvas')
  canvas.width = RENDER_SIZE
  canvas.height = RENDER_SIZE
  const ctx = canvas.getContext('2d')
  drawEmoji(ctx, icon, RENDER_SIZE)
  const data = ctx.getImageData(0, 0, RENDER_SIZE, RENDER_SIZE).data
  let minX = RENDER_SIZE
  let minY = RENDER_SIZE
  let maxX = 0
  let maxY = 0
  for (let y = 0; y < RENDER_SIZE; y += 1) {
    for (let x = 0; x < RENDER_SIZE; x += 1) {
      const alpha = data[(y * RENDER_SIZE + x) * 4 + 3]
      if (alpha > 12) {
        if (x < minX) minX = x
        if (y < minY) minY = y
        if (x > maxX) maxX = x
        if (y > maxY) maxY = y
      }
    }
  }
  if (maxX <= minX || maxY <= minY) return { x: 0, y: 0, w: 1, h: 1 }
  return {
    x: minX / RENDER_SIZE,
    y: minY / RENDER_SIZE,
    w: (maxX - minX + 1) / RENDER_SIZE,
    h: (maxY - minY + 1) / RENDER_SIZE
  }
}

const nodes = computed(() =>
  sorted.value.map((item, index) => {
    const value = Number(item.value)
    const percent = Number.isFinite(Number(item.percent)) ? Number(item.percent) : (value / total.value) * 100
    const color = FILL_COLORS[index % FILL_COLORS.length]
    const icon = iconOf(item.name)
    return {
      name: String(item.name ?? '未分类'),
      value,
      share: Boolean(item.share),
      percent,
      color,
      icon,
      bbox: measureEmoji(icon),
      graySrc: grayImage(icon),
      colorSrc: colorSilhouette(icon, color)
    }
  })
)

// ---------------- 布局 ----------------
const COLS = 4
const W = 900
const H = 480
const AREA = { x: 34, y: 106, w: 832, h: 336 }
const GAP = 18
const rows = computed(() => Math.max(1, Math.ceil(nodes.value.length / COLS)))
const COLS_N = computed(() => Math.min(COLS, Math.max(1, nodes.value.length)))
const ITEM_W = computed(() => (AREA.w - GAP * (COLS_N.value - 1)) / COLS_N.value)
const ITEM_H = computed(() => (AREA.h - GAP * (rows.value - 1)) / rows.value)

function posOf(index) {
  const row = Math.floor(index / COLS)
  const col = index % COLS
  return { x: AREA.x + col * (ITEM_W.value + GAP), y: AREA.y + row * (ITEM_H.value + GAP) }
}

const iconSizeOf = computed(() => Math.max(72, Math.min(112, ITEM_H.value - 62)))
const iconYOf = computed(() => Math.round((ITEM_H.value - iconSizeOf.value) / 2) + 8)

function clipId(index) {
  return `${uid}-clip-${index}`
}

function effectivePercent(node) {
  return Math.max(0, Math.min(100, node.percent * growth.value))
}

/** 依据商品图实际像素范围计算“液面裁剪区域” */
function clipRect(index) {
  const node = nodes.value[index]
  if (!node) return { x: 0, y: 0, width: 0, height: 0 }
  const pos = posOf(index)
  const size = iconSizeOf.value
  const imageX = pos.x + (ITEM_W.value - size) / 2
  const imageY = pos.y + iconYOf.value
  const boxX = imageX + node.bbox.x * size
  const boxY = imageY + node.bbox.y * size
  const boxW = Math.max(1, node.bbox.w * size)
  const boxH = Math.max(1, node.bbox.h * size)
  const percent = effectivePercent(node) / 100
  return {
    x: boxX,
    y: boxY + boxH * (1 - percent),
    width: boxW,
    height: Math.max(0, boxH * percent)
  }
}

function fmt(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(2) + '万'
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function toDataURL(backgroundColor) {
  const svg = wrapRef.value?.querySelector('svg')
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
  <div ref="wrapRef" class="product-showcase">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="商品图内部占比可视化">
      <defs>
        <clipPath v-for="(node, index) in nodes" :id="clipId(index)" :key="clipId(index)" clipPathUnits="userSpaceOnUse">
          <rect
            v-bind="clipRect(index)"
          />
        </clipPath>
      </defs>

      <!-- 顶部标题，无边框 -->
      <text
        :x="AREA.x"
        :y="34"
        :fill="th.ink"
        font-size="22"
        font-weight="700"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >品类销售构成 · 100%</text>
      <text
        :x="AREA.x + AREA.w"
        :y="34"
        :fill="th.muted"
        font-size="16"
        text-anchor="end"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >{{ totalLabel || ('合计 ' + fmt(total) + ' 元') }}</text>
      <text
        :x="AREA.x"
        :y="64"
        :fill="th.subtle"
        font-size="14"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >灰色商品图做底 · 颜色在图像内部由下往上显示占比</text>

      <!-- 商品图排列（无边框） -->
      <g v-for="(node, index) in nodes" :key="node.name">
        <title>{{ node.name }}：{{ node.share ? ('占比 ' + node.percent.toFixed(2) + '%') : ('销售额 ' + fmt(node.value) + ' 元') }}</title>

        <!-- 百分比 -->
        <text
          :x="posOf(index).x + ITEM_W / 2"
          :y="posOf(index).y + 24"
          :fill="th.ink"
          font-size="22"
          font-weight="800"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ node.percent.toFixed(1) }}%</text>

        <!-- 灰色商品图做底 -->
        <image
          :href="node.graySrc"
          :x="posOf(index).x + (ITEM_W - iconSizeOf) / 2"
          :y="posOf(index).y + iconYOf"
          :width="iconSizeOf"
          :height="iconSizeOf"
          preserveAspectRatio="xMidYMid meet"
        />

        <!-- 图像内部的彩色占比（彩色剪影 + 底部裁剪） -->
        <image
          :href="node.colorSrc"
          :x="posOf(index).x + (ITEM_W - iconSizeOf) / 2"
          :y="posOf(index).y + iconYOf"
          :width="iconSizeOf"
          :height="iconSizeOf"
          preserveAspectRatio="xMidYMid meet"
          :clip-path="`url(#${clipId(index)})`"
        />

        <!-- 品类名称：图片正中下方 -->
        <text
          :x="posOf(index).x + ITEM_W / 2"
          :y="posOf(index).y + iconYOf + iconSizeOf + 28"
          :fill="th.ink"
          font-size="19"
          font-weight="700"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ node.name }}</text>
      </g>

      <text
        v-if="!nodes.length"
        :x="W / 2"
        :y="H / 2"
        :fill="th.muted"
        font-size="18"
        text-anchor="middle"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >没有可用于展示的商品数据</text>
    </svg>
  </div>
</template>

<style scoped>
.product-showcase {
  width: 100%;
  padding: 0 4px;
}
.product-showcase svg {
  width: 100%;
  height: auto;
  display: block;
}
</style>
