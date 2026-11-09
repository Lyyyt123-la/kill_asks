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

  await ask('各区域各渠道的退款率')
  await page.waitForSelector('.chart-card', { timeout: 120000 })
  await page.waitForTimeout(2800)
  await page.locator('.chart-card').last().screenshot({ path: `${OUT}/11-heatmap-fixed.png` })
  console.log('KPI:', (await page.locator('.chart-kpi').allInnerTexts()).join(' | ').replace(/\n/g, ' '))
  console.log('推荐:', (await page.locator('.chart-reason').last().innerText()).replace(/\n/g, ' '))

  // 切换同一数据源，消息应保留
  const before = await page.locator('.ai-wrap, .msg-user').count()
  await page.locator('.side .ds-item').filter({ hasText: '双11' }).first().click()
  await page.waitForTimeout(900)
  const after = await page.locator('.ai-wrap, .msg-user').count()
  console.log('切换前后消息节点数:', before, '->', after)
  await page.screenshot({ path: `${OUT}/12-keep-conversation.png` })

  // 重置数据源（接受 confirm）
  page.on('dialog', (dialog) => dialog.accept())
  await page.locator('.top-actions .chip', { hasText: '重置数据源' }).click()
  await page.waitForTimeout(2500)
  const toast = await page.locator('.toast').innerText().catch(() => '')
  console.log('重置提示:', toast)
  await page.screenshot({ path: `${OUT}/13-after-reset.png` })

  console.log(errors.length ? '浏览器错误：' + errors.slice(0, 6).join(' | ') : '无浏览器错误 ✅')
} catch (error) {
  console.error('失败：', error.message)
  await page.screenshot({ path: `${OUT}/fixes-error.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
