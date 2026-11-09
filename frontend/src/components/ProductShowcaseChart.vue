<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 商品图可视化（完善版）
 * - 用 Canvas 自绘统一风格的商品图形（不依赖系统 emoji）
 * - 商品图整体灰色做底，彩色只在图像内部按占比从下往上填充
 * - 百分比数字随填充一起从 0 涨到实际值
 * - 每行最多 4 个；窄屏自动 3/2 列；不画袋子、不画边框
 */
const props = defineProps({
  items: { type: Array, default: () => [] },
  theme: { type: String, default: 'light' },
  totalLabel: { type: String, default: '' }
})

const wrapRef = ref(null)
const growth = ref(0)
const revealed = ref(false)
const hovered = ref(-1)
const wrapWidth = ref(900)
const uid = Math.random().toString(36).slice(2, 8)
const emit = defineEmits(['select'])
let observer = null

function startGrowth() {
  const started = performance.now()
  const duration = 820
  const tick = (now) => {
    const progress = Math.min(1, (now - started) / duration)
    growth.value = 1 - Math.pow(1 - progress, 3)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined' && wrapRef.value) {
    observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect?.width
      if (width) wrapWidth.value = width
    })
    observer.observe(wrapRef.value)
  }
  requestAnimationFrame(() => { revealed.value = true })
  startGrowth()
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})

// 低饱和浅色（图像内部占比色）
const FILL_COLORS = ['#8FC5A8', '#EAC17C', '#E5A79B', '#8FB8D6', '#BBA1D8', '#8FCBBE', '#D8C892', '#AEBFD2']
const GRAY_FILL = '#B9B5AC'

const THEMES = {
  light: { bg: '#FFFEFB', ink: '#2B2823', muted: '#7A7468', subtle: '#A39C8D' },
  dark: { bg: '#17201B', ink: '#EDF4EE', muted: '#9DB7A6', subtle: '#7B9485' }
}
const th = computed(() => THEMES[props.theme] || THEMES.light)

// 品类 → 自绘商品图形
const KIND_RULES = [
  [/女装|连衣裙|裙|女鞋/, 'dress'],
  [/男装|男鞋|衬衫/, 'shirt'],
  [/美妆|化妆|护肤|口红/, 'lipstick'],
  [/食品|零食|生鲜|水果/, 'apple'],
  [/3C|数码|手机|电脑|电子/, 'phone'],
  [/家居|家纺|家具/, 'sofa'],
  [/母婴|婴童|奶粉|饮料|酒|水/, 'bottle'],
  [/运动|户外|健身|鞋|靴/, 'shoe'],
  [/箱包|包/, 'bag'],
  [/图书|书/, 'book'],
  [/家电|电器|冰箱/, 'fridge'],
  [/珠宝|饰品/, 'ring'],
  [/宠物/, 'paw'],
  [/汽车|车品/, 'car']
]

function kindOf(name) {
  for (const [pattern, kind] of KIND_RULES) {
    if (pattern.test(String(name))) return kind
  }
  return 'box'
}

// 用 100×100 归一化坐标绘制商品形状，便于统一风格
function drawProduct(ctx, kind, size, color) {
  const scale = size / 100
  ctx.save()
  ctx.scale(scale, scale)
  ctx.fillStyle = color
  ctx.strokeStyle = color
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'

  const fillRound = (x, y, w, h, r = 0) => {
    ctx.beginPath()
    ctx.roundRect(x, y, w, h, r)
    ctx.fill()
  }

  switch (kind) {
    case 'phone': {
      fillRound(28, 6, 44, 88, 10)
      ctx.globalCompositeOperation = 'destination-out'
      ctx.beginPath()
      ctx.arc(50, 17, 4.2, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillRect(38, 80, 24, 4)
      ctx.globalCompositeOperation = 'source-over'
      break
    }
    case 'sofa': {
      fillRound(12, 38, 76, 34, 10)
      fillRound(5, 50, 90, 24, 8)
      fillRound(5, 44, 15, 30, 7)
      fillRound(80, 44, 15, 30, 7)
      fillRound(19, 74, 9, 12, 3)
      fillRound(72, 74, 9, 12, 3)
      break
    }
    case 'dress': {
      ctx.beginPath()
      ctx.moveTo(40, 8)
      ctx.lineTo(60, 8)
      ctx.lineTo(67, 28)
      ctx.lineTo(56, 34)
      ctx.lineTo(66, 52)
      ctx.lineTo(75, 84)
      ctx.lineTo(64, 92)
      ctx.lineTo(36, 92)
      ctx.lineTo(25, 84)
      ctx.lineTo(34, 52)
      ctx.lineTo(44, 34)
      ctx.lineTo(33, 28)
      ctx.closePath()
      ctx.fill()
      break
    }
    case 'shirt': {
      ctx.beginPath()
      ctx.moveTo(38, 10)
      ctx.lineTo(50, 18)
      ctx.lineTo(62, 10)
      ctx.lineTo(78, 24)
      ctx.lineTo(70, 42)
      ctx.lineTo(62, 38)
      ctx.lineTo(62, 88)
      ctx.lineTo(38, 88)
      ctx.lineTo(38, 38)
      ctx.lineTo(30, 42)
      ctx.lineTo(22, 24)
      ctx.closePath()
      ctx.fill()
      break
    }
    case 'lipstick': {
      ctx.beginPath()
      ctx.moveTo(38, 44)
      ctx.lineTo(55, 10)
      ctx.lineTo(70, 17)
      ctx.lineTo(53, 48)
      ctx.closePath()
      ctx.fill()
      fillRound(33, 46, 32, 38, 4)
      fillRound(30, 82, 38, 10, 3)
      break
    }
    case 'apple': {
      ctx.beginPath()
      ctx.arc(41, 57, 26, 0, Math.PI * 2)
      ctx.arc(59, 57, 24, 0, Math.PI * 2)
      ctx.fill()
      fillRound(49, 20, 4, 16, 2)
      ctx.save()
      ctx.translate(59, 25)
      ctx.rotate(-0.55)
      ctx.beginPath()
      ctx.ellipse(0, 0, 13, 7, 0, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
      break
    }
    case 'bottle': {
      fillRound(41, 22, 18, 18, 5)
      fillRound(33, 36, 34, 54, 8)
      fillRound(39, 12, 22, 14, 4)
      break
    }
    case 'shoe': {
      ctx.beginPath()
      ctx.moveTo(12, 70)
      ctx.lineTo(24, 50)
      ctx.lineTo(44, 42)
      ctx.lineTo(52, 56)
      ctx.lineTo(78, 62)
      ctx.quadraticCurveTo(88, 64, 88, 74)
      ctx.lineTo(16, 78)
      ctx.closePath()
      ctx.fill()
      break
    }
    case 'bag': {
      fillRound(30, 36, 40, 48, 7)
      ctx.lineWidth = 6
      ctx.beginPath()
      ctx.arc(50, 38, 13, Math.PI, 0)
      ctx.stroke()
      break
    }
    case 'book': {
      fillRound(28, 16, 44, 68, 5)
      ctx.globalCompositeOperation = 'destination-out'
      ctx.fillRect(33, 16, 3, 68)
      ctx.fillRect(52, 16, 2, 68)
      ctx.globalCompositeOperation = 'source-over'
      break
    }
    case 'fridge': {
      fillRound(30, 10, 40, 80, 6)
      ctx.globalCompositeOperation = 'destination-out'
      ctx.fillRect(30, 40, 40, 3)
      ctx.fillRect(62, 26, 4, 10)
      ctx.fillRect(62, 54, 4, 10)
      ctx.globalCompositeOperation = 'source-over'
      break
    }
    case 'ring': {
      ctx.lineWidth = 7
      ctx.beginPath()
      ctx.arc(50, 62, 17, 0, Math.PI * 2)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(50, 20)
      ctx.lineTo(62, 34)
      ctx.lineTo(50, 48)
      ctx.lineTo(38, 34)
      ctx.closePath()
      ctx.fill()
      break
    }
    case 'paw': {
      fillRound(34, 44, 32, 30, 14)
      ctx.beginPath()
      ctx.arc(28, 34, 9, 0, Math.PI * 2)
      ctx.arc(44, 24, 9, 0, Math.PI * 2)
      ctx.arc(60, 24, 9, 0, Math.PI * 2)
      ctx.arc(72, 34, 9, 0, Math.PI * 2)
      ctx.fill()
      break
    }
    case 'car': {
      ctx.beginPath()
      ctx.moveTo(10, 62)
      ctx.lineTo(20, 46)
      ctx.lineTo(42, 42)
      ctx.lineTo(52, 54)
      ctx.lineTo(76, 58)
      ctx.lineTo(88, 66)
      ctx.lineTo(88, 74)
      ctx.lineTo(10, 74)
      ctx.closePath()
      ctx.fill()
      ctx.globalCompositeOperation = 'destination-out'
      ctx.beginPath()
      ctx.arc(28, 76, 8, 0, Math.PI * 2)
      ctx.arc(72, 76, 8, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalCompositeOperation = 'source-over'
      break
    }
    default: {
      ctx.beginPath()
      ctx.moveTo(20, 36)
      ctx.lineTo(50, 20)
      ctx.lineTo(80, 36)
      ctx.lineTo(80, 72)
      ctx.lineTo(50, 88)
      ctx.lineTo(20, 72)
      ctx.closePath()
      ctx.fill()
      ctx.globalCompositeOperation = 'destination-out'
      ctx.fillRect(50, 26, 3, 62)
      ctx.globalCompositeOperation = 'source-over'
      break
    }
  }
  ctx.restore()
}

const RENDER_SIZE = 240

/** 在商品图形上添加深色细节线条（屏幕/缝线/衣褶等） */
function drawDetails(ctx, kind, size) {
  const scale = size / 100
  ctx.save()
  ctx.scale(scale, scale)
  ctx.globalAlpha = 0.72
  ctx.strokeStyle = '#4B4740'
  ctx.fillStyle = '#4B4740'
  ctx.lineWidth = 1.7
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  const line = (x1, y1, x2, y2) => {
    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.lineTo(x2, y2)
    ctx.stroke()
  }
  const strokeRound = (x, y, w, h, r) => {
    ctx.beginPath()
    ctx.roundRect(x, y, w, h, r)
    ctx.stroke()
  }
  const dot = (x, y, r) => {
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  switch (kind) {
    case 'phone':
      strokeRound(34, 25, 32, 56, 4)
      line(40, 38, 60, 38)
      dot(50, 17.5, 1.6)
      line(43, 84, 57, 84)
      break
    case 'sofa':
      line(16, 51, 84, 51)
      line(38, 51, 38, 71)
      line(62, 51, 62, 71)
      line(19, 78, 19, 84)
      line(81, 78, 81, 84)
      break
    case 'dress':
      ctx.beginPath()
      ctx.arc(50, 20, 8, 0.1 * Math.PI, 0.9 * Math.PI)
      ctx.stroke()
      line(35, 52, 65, 52)
      line(44, 60, 42, 84)
      line(58, 60, 60, 84)
      break
    case 'shirt':
      line(50, 18, 50, 40)
      line(38, 12, 50, 26)
      line(62, 12, 50, 26)
      strokeRound(56, 48, 10, 9, 2)
      dot(50, 48, 1.4)
      dot(50, 58, 1.4)
      break
    case 'lipstick':
      line(38, 44, 66, 44)
      line(33, 64, 65, 64)
      line(33, 70, 65, 70)
      break
    case 'apple':
      line(51, 22, 51, 30)
      ctx.beginPath()
      ctx.moveTo(53, 30)
      ctx.quadraticCurveTo(58, 22, 68, 24)
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(50, 56, 18, 1.15 * Math.PI, 1.45 * Math.PI)
      ctx.stroke()
      break
    case 'bottle':
      line(41, 30, 59, 30)
      strokeRound(36, 46, 28, 24, 4)
      break
    case 'shoe':
      line(18, 78, 88, 76)
      line(30, 58, 48, 52)
      line(36, 64, 52, 58)
      line(42, 70, 56, 64)
      break
    case 'bag':
      strokeRound(30, 48, 40, 36, 4)
      dot(50, 58, 1.8)
      break
    case 'book':
      strokeRound(39, 18, 45, 64, 2)
      line(33, 24, 33, 76)
      break
    case 'fridge':
      line(30, 40, 70, 40)
      line(62, 26, 62, 36)
      line(62, 54, 62, 64)
      break
    case 'ring':
      ctx.beginPath()
      ctx.arc(50, 62, 17, 1.1 * Math.PI, 1.4 * Math.PI)
      ctx.stroke()
      line(50, 22, 50, 48)
      line(38, 34, 62, 34)
      break
    case 'paw':
      dot(34, 58, 3)
      dot(50, 60, 3)
      dot(66, 58, 3)
      break
    case 'car':
      line(22, 66, 86, 66)
      line(42, 42, 50, 54)
      line(74, 58, 74, 74)
      break
    default:
      line(20, 36, 80, 36)
      line(50, 20, 50, 88)
      break
  }
  ctx.restore()
}

function renderProduct(kind, color) {
  const canvas = document.createElement('canvas')
  canvas.width = RENDER_SIZE
  canvas.height = RENDER_SIZE
  const ctx = canvas.getContext('2d')
  drawProduct(ctx, kind, RENDER_SIZE, color)
  drawDetails(ctx, kind, RENDER_SIZE)
  return canvas.toDataURL('image/png')
}

/** 检测商品图形实际像素范围，保证颜色只填进图形内部 */
function measureProduct(kind) {
  const canvas = document.createElement('canvas')
  canvas.width = RENDER_SIZE
  canvas.height = RENDER_SIZE
  const ctx = canvas.getContext('2d')
  drawProduct(ctx, kind, RENDER_SIZE, GRAY_FILL)
  const data = ctx.getImageData(0, 0, RENDER_SIZE, RENDER_SIZE).data
  let minX = RENDER_SIZE
  let minY = RENDER_SIZE
  let maxX = 0
  let maxY = 0
  for (let y = 0; y < RENDER_SIZE; y += 1) {
    for (let x = 0; x < RENDER_SIZE; x += 1) {
      if (data[(y * RENDER_SIZE + x) * 4 + 3] > 12) {
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
    const color = FILL_COLORS[index % FILL_COLORS.length]
    const kind = kindOf(item.name)
    return {
      name: String(item.name ?? '未分类'),
      value,
      share: Boolean(item.share),
      percent,
      color,
      kind,
      bbox: measureProduct(kind),
      graySrc: renderProduct(kind, GRAY_FILL),
      colorSrc: renderProduct(kind, color)
    }
  })
)

// ---------------- 布局 ----------------
const MAX_COLS = 4
const W = 900
const H = 480
const AREA = { x: 34, y: 106, w: 832, h: 336 }
const GAP = 18

const cols = computed(() => {
  if (nodes.value.length <= 1) return 1
  if (wrapWidth.value >= 620) return Math.min(MAX_COLS, nodes.value.length)
  if (wrapWidth.value >= 470) return Math.min(3, nodes.value.length)
  return Math.min(2, nodes.value.length)
})
const rows = computed(() => Math.max(1, Math.ceil(nodes.value.length / cols.value)))
const ITEM_W = computed(() => (AREA.w - GAP * (cols.value - 1)) / cols.value)
const ITEM_H = computed(() => (AREA.h - GAP * (rows.value - 1)) / rows.value)

function posOf(index) {
  const row = Math.floor(index / cols.value)
  const col = index % cols.value
  return { x: AREA.x + col * (ITEM_W.value + GAP), y: AREA.y + row * (ITEM_H.value + GAP) }
}

const iconSizeOf = computed(() => Math.max(56, Math.min(112, ITEM_H.value - 62)))

function clipId(index) {
  return `${uid}-clip-${index}`
}

function growthPercent(node) {
  return node.percent * growth.value
}

function clipRect(index) {
  const node = nodes.value[index]
  if (!node) return { x: 0, y: 0, width: 0, height: 0 }
  const pos = posOf(index)
  const size = iconSizeOf.value
  const imageX = pos.x + (ITEM_W.value - size) / 2
  const imageY = pos.y + 34
  const boxX = imageX + node.bbox.x * size
  const boxY = imageY + node.bbox.y * size
  const boxW = Math.max(1, node.bbox.w * size)
  const boxH = Math.max(1, node.bbox.h * size)
  const percent = Math.max(0, Math.min(100, growthPercent(node))) / 100
  return {
    x: boxX,
    y: boxY + boxH * (1 - percent),
    width: boxW,
    height: Math.max(0, boxH * percent)
  }
}

/** 入场动画：从中心向外扩散、羽化边缘、透明到不透明，逐项错峰 */
function itemStyle(index) {
  const delay = index * 90
  const scale = hovered.value === index ? 1.06 : 1
  return {
    cursor: 'pointer',
    opacity: revealed.value ? 1 : 0,
    transformBox: 'fill-box',
    transformOrigin: 'center',
    transform: revealed.value ? `scale(${scale})` : 'scale(0.55)',
    filter: revealed.value ? 'blur(0px)' : 'blur(10px)',
    transition: `opacity .75s ease ${delay}ms, transform .85s cubic-bezier(.2,.7,.2,1) ${delay}ms, filter .85s ease ${delay}ms`
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
          <rect v-bind="clipRect(index)" />
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
      >灰色商品图做底 · 颜色在图像内部由下往上显示占比 · 悬停查看，点击可下钻</text>

      <!-- 商品图排列（无边框） -->
      <g
        v-for="(node, index) in nodes"
        :key="node.name"
        :style="itemStyle(index)"
        @mouseenter="hovered = index"
        @mouseleave="hovered = -1"
        @click="emit('select', node)"
      >
        <title>{{ node.name }}：{{ node.share ? ('占比 ' + node.percent.toFixed(2) + '%') : ('销售额 ' + fmt(node.value) + ' 元') }}</title>

        <!-- 百分比（数字随填充上涨） -->
        <text
          :x="posOf(index).x + ITEM_W / 2"
          :y="posOf(index).y + 24"
          :fill="th.ink"
          font-size="22"
          font-weight="800"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ growthPercent(node).toFixed(1) }}%</text>

        <!-- 灰色商品图做底 -->
        <image
          :href="node.graySrc"
          :x="posOf(index).x + (ITEM_W - iconSizeOf) / 2"
          :y="posOf(index).y + 34"
          :width="iconSizeOf"
          :height="iconSizeOf"
          preserveAspectRatio="xMidYMid meet"
        />

        <!-- 图像内部的彩色占比（彩色剪影 + 按图形实际范围裁剪） -->
        <image
          :href="node.colorSrc"
          :x="posOf(index).x + (ITEM_W - iconSizeOf) / 2"
          :y="posOf(index).y + 34"
          :width="iconSizeOf"
          :height="iconSizeOf"
          preserveAspectRatio="xMidYMid meet"
          :clip-path="`url(#${clipId(index)})`"
        />

        <!-- 品类名称：图片正中下方 -->
        <text
          :x="posOf(index).x + ITEM_W / 2"
          :y="posOf(index).y + 34 + iconSizeOf + 26"
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
