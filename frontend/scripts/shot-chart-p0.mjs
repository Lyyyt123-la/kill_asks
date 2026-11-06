/** P0 图表改版视觉验证：生成柱状/环形/深色/折线四张截图。 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const OUT = 'D:/dsworking/chart_p0'
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
const errors = []
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

async function shot(name, full = false) {
  await page.waitForTimeout(600)
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
  await page.waitForTimeout(1200)

  await ask('各区域的销售额对比')
  await page.waitForSelector('.chart-card', { timeout: 120000 })
  await page.waitForTimeout(2500)
  await shot('01-bar-light.png')
  await page.screenshot({ path: `${OUT}/01-full-bar-light.png` })

  await page.locator('.chart-type', { hasText: '环形' }).last().click()
  await page.waitForTimeout(1500)
  await shot('02-pie-light.png')

  await page.locator('.chart-theme').last().click()
  await page.waitForTimeout(1200)
  await shot('03-pie-dark.png')

  await page.locator('.chart-theme').last().click()
  await page.locator('.chart-type', { hasText: '柱状' }).last().click()
  await page.waitForTimeout(600)

  await ask('双11当天各小时销售额趋势')
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 120000 })
  await page.waitForTimeout(2500)
  await shot('04-line-light.png')

  await page.locator('.chart-type', { hasText: '表格' }).last().click()
  await page.waitForTimeout(800)
  await shot('05-table-light.png')

  console.log(errors.length ? '浏览器错误：' + errors.slice(0, 5).join(' | ') : '无浏览器错误 ✅')
} catch (error) {
  console.error('失败：', error.message)
  await page.screenshot({ path: `${OUT}/error.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}

