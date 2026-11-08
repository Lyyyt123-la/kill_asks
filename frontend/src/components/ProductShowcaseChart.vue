<script setup>
import { computed, onMounted, ref } from 'vue'

/**
 * 商品图可视化（商品为主体，浅色比例填充，无边框）
 * - 每个品类一张商品图片（emoji 作为基础商品图）
 * - 图片本身作为主体，底部浅色色块按销售额占比升起
 * - 品类名称居中显示在图片下方，百分比显示在图片上方
 * - 每行最多 4 个，按左→右、上→下排列，不画购物袋、不画边框
 */
const props = defineProps({
  items: { type: Array, default: () => [] },
  theme: { type: String, default: 'light' },
  totalLabel: { type: String, default: '' }
})

const wrapRef = ref(null)
const mounted = ref(false)
onMounted(() => requestAnimationFrame(() => { mounted.value = true }))

const COLS = 4
// 浅色、低饱和的品类色（比例填充用）
const PALETTE = ['#B9D6C5', '#F2D3A2', '#F0B8AE', '#B8D0E3', '#D6C6E8', '#B9DDD4', '#E7DAB2', '#CBD4DE']

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

const W = 900
const H = 520
const AREA = { x: 34, y: 96, w: 832, h: 396 }
const GAP = 18
const COLS_N = computed(() => Math.min(COLS, Math.max(1, nodes.value.length)))
const ITEM_W = computed(() => (AREA.w - GAP * (COLS_N.value - 1)) / COLS_N.value)
const ITEM_H = computed(() => (AREA.h - GAP * (rows.value - 1)) / rows.value)

function posOf(index) {
  const row = Math.floor(index / COLS)
  const col = index % COLS
  return { x: AREA.x + col * (ITEM_W.value + GAP), y: AREA.y + row * (ITEM_H.value + GAP) }
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
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="品类商品图与占比">
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
        :y="62"
        :fill="th.subtle"
        font-size="14"
        font-family="Microsoft YaHei, PingFang SC, sans-serif"
      >商品图片 = 品类 · 浅色区域由下往上表示销售额占比</text>

      <!-- 商品图排列（无边框） -->
      <g v-for="(node, index) in nodes" :key="node.name" :transform="`translate(${posOf(index).x}, ${posOf(index).y})`">
        <title>{{ node.name }}：{{ node.share ? ('占比 ' + node.percent.toFixed(2) + '%') : ('销售额 ' + fmt(node.value) + ' 元') }}</title>

        <!-- 浅色比例区域（从下往上，无描边） -->
        <rect
          :x="0"
          :y="ITEM_H * (1 - Math.min(100, node.percent) / 100)"
          :width="ITEM_W"
          :height="ITEM_H * (Math.min(100, node.percent) / 100)"
          rx="26"
          :fill="node.color"
          fill-opacity="0.55"
          :style="{
            transformBox: 'fill-box',
            transformOrigin: '50% 100%',
            transform: mounted ? 'scaleY(1)' : 'scaleY(0)',
            transition: 'transform .8s cubic-bezier(.2,.7,.2,1)'
          }"
        />

        <!-- 百分比 -->
        <text
          :x="ITEM_W / 2"
          :y="26"
          :fill="th.ink"
          font-size="22"
          font-weight="800"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
        >{{ node.percent.toFixed(1) }}%</text>

        <!-- 商品图片（主体，尽量大） -->
        <text
          :x="ITEM_W / 2"
          :y="ITEM_H * 0.45"
          font-size="66"
          text-anchor="middle"
          dominant-baseline="middle"
        >{{ node.icon }}</text>

        <!-- 品类名称：图片正中下方 -->
        <text
          :x="ITEM_W / 2"
          :y="ITEM_H * 0.78"
          :fill="th.ink"
          font-size="19"
          font-weight="700"
          text-anchor="middle"
          font-family="Microsoft YaHei, PingFang SC, sans-serif"
          stroke="#FFFEFB"
          stroke-width="3"
          paint-order="stroke"
          :stroke-opacity="theme === 'light' ? 0.9 : 0"
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

