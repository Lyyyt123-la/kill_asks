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

async function shot(name) {
  await page.waitForTimeout(900)
  await page.locator('.chart-card').last().screenshot({ path: `${OUT}/${name}` })
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

  await ask('各区域各渠道的销售额')
  await page.waitForSelector('.chart-card', { timeout: 120000 })
  await page.waitForTimeout(2600)
  await shot('08-heatmap.png')
  console.log('推荐文案:', (await page.locator('.chart-reason').last().innerText()).replace(/\n/g, ' '))
  console.log('类型按钮:', (await page.locator('.chart-types').last().innerText()).replace(/\n/g, ' '))

  const tree = page.locator('.chart-type', { hasText: '树图' }).last()
  if (await tree.count()) {
    await tree.click()
    await page.waitForTimeout(1200)
    await shot('09-treemap.png')
  }

  await ask('销售额和订单量的关系')
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 120000 })
  await page.waitForTimeout(2600)
  await shot('10-scatter.png')
  console.log('第二问推荐:', (await page.locator('.chart-reason').last().innerText()).replace(/\n/g, ' '))

  console.log(errors.length ? '浏览器错误：' + errors.slice(0, 6).join(' | ') : '无浏览器错误 ✅')
} catch (error) {
  console.error('失败：', error.message)
  await page.screenshot({ path: `${OUT}/types-error.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
