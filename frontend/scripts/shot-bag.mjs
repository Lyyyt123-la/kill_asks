/** 购物袋图 + 推荐图表验证截图。 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const OUT = 'D:/dsworking/chart_bag'
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
const errors = []
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

async function shot(name, full = false) {
  await page.waitForTimeout(800)
  if (full) await page.screenshot({ path: `${OUT}/${name}`, fullPage: true })
  else await page.locator('.chart-card').last().screenshot({ path: `${OUT}/${name}` })
  console.log('shot ->', name)
}

async function ask(text) {
  const textarea = page.locator('.composer textarea')
  await textarea.fill('')
  await textarea.fill(text)
  await page.keyboard.press('Enter')
}

try {
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await page.locator('.start-card').nth(1).click()
  await page.waitForSelector('.dataset-ready', { timeout: 60000 })
  await page.waitForTimeout(1000)

  await ask('各品类销售额占比')
  await page.waitForSelector('.chart-card', { timeout: 120000 })
  await page.waitForFunction(() => document.querySelectorAll('.product-showcase svg').length >= 1, null, { timeout: 60000 })
  await page.waitForTimeout(2200)
  await shot('01-bag-card.png')
  await page.screenshot({ path: `${OUT}/01-bag-full.png` })

  // 检查推荐文案与按钮顺序
  const reason = await page.locator('.chart-reason').last().innerText()
  const firstButton = await page.locator('.chart-type').last().locator('..').locator('button').first().innerText().catch(() => '')
  console.log('推荐文案:', reason.replace(/\n/g, ' '))
  console.log('首个图表类型:', firstButton.replace(/\n/g, ' '))

  // 数据明细（表格从主切换移走）
  await page.locator('.btn-mini', { hasText: '数据明细' }).last().click()
  await page.waitForTimeout(900)
  await shot('02-table.png')
  await page.locator('.btn-mini', { hasText: '返回图表' }).last().click()
  await page.waitForTimeout(700)

  // 区域对比：推荐柱状
  await ask('各区域的销售额对比')
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 120000 })
  await page.waitForTimeout(2500)
  await shot('03-bar-recommended.png')

  console.log(errors.length ? '浏览器错误：' + errors.slice(0, 6).join(' | ') : '无浏览器错误 ✅')
} catch (error) {
  console.error('失败：', error.message)
  await page.screenshot({ path: `${OUT}/error.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}

