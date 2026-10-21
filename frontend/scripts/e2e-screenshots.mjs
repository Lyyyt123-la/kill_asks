/**
 * 端到端截图脚本：真实点击「载入示例数据 → 提问 → 出图 → 检查器 → 多轮追问」。
 * 复用本机 Chrome（无需下载浏览器），用于开发自查 + 技术文档截图。
 *
 * 运行：cd frontend && node scripts/e2e-screenshots.mjs
 * 前置：后端 8000、前端 5173 已启动
 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const CHROME_CANDIDATES = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe'
]
const executablePath = CHROME_CANDIDATES.find((p) => fs.existsSync(p))
if (!executablePath) {
  console.error('未找到 Chrome/Edge')
  process.exit(1)
}

const BASE_URL = process.env.ASK_BASE_URL || 'http://127.0.0.1:8000'
const OUT = path.resolve('..', 'docs', 'screenshots')
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ executablePath, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 })

const errors = []
page.on('pageerror', (err) => errors.push('pageerror: ' + err.message))
page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push('console: ' + msg.text())
})

async function shot(name) {
  await page.waitForTimeout(450)
  await page.screenshot({ path: path.join(OUT, name) })
  console.log('shot ->', name)
}

async function waitToastGone() {
  await page.locator('.toast').waitFor({ state: 'detached', timeout: 8000 }).catch(() => {})
}

try {
  console.log('open app ...')
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await shot('01-welcome.png')

  console.log('load demo dataset ...')
  await page.locator('.start-card').nth(1).click()
  await page.waitForSelector('.dataset-ready', { timeout: 40000 })
  await waitToastGone()
  await shot('02-dataset-ready.png')

  console.log('click example chip -> should fill composer, NOT send ...')
  const textarea = page.locator('.composer textarea')
  await page.locator('.dr-example').first().click()
  await page.waitForTimeout(500)
  const prefill = await textarea.inputValue()
  const chartsAfterChip = await page.locator('.chart-card').count()
  console.log('  prefill =', JSON.stringify(prefill), '| charts =', chartsAfterChip)
  if (!prefill || chartsAfterChip !== 0) throw new Error('示例问题应只填入输入框、不自动发送')
  await shot('02b-example-filled.png')

  console.log('send question 1 ...')
  await page.keyboard.press('Enter')
  await page.waitForSelector('.chart-card', { timeout: 90000 })
  await page.waitForFunction(() => !document.querySelector('.lstep'), null, { timeout: 90000 })
  await waitToastGone()
  await shot('03-answer-region.png')

  console.log('open inspector ...')
  if (!(await page.locator('.inspector').count())) {
    await page.locator('.icon-btn[title*="检查器"]').click()
  }
  await page.waitForSelector('.inspector', { timeout: 10000 })
  await page.waitForTimeout(500)
  await shot('04-inspector.png')
  await page.locator('.inspector .close').click()
  await page.waitForTimeout(500)

  console.log('ask question 2 (time trend) ...')
  await textarea.fill('双11当天各小时销售额趋势')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 90000 })
  await page.waitForFunction(() => !document.querySelector('.lstep'), null, { timeout: 90000 })
  await page.evaluate(() => { const el = document.querySelector('.chat-scroll'); if (el) el.scrollTop = el.scrollHeight })
  await page.waitForTimeout(700)
  await shot('05-answer-hourly.png')

  console.log('ask question 3 (top categories) ...')
  await textarea.fill('销售额最高的5个品类')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 3, null, { timeout: 90000 })
  await page.waitForFunction(() => !document.querySelector('.lstep'), null, { timeout: 90000 })
  await page.evaluate(() => { const el = document.querySelector('.chat-scroll'); if (el) el.scrollTop = el.scrollHeight })
  await page.waitForTimeout(700)
  await shot('06-answer-top.png')

  console.log('preview dataset ...')
  await page.locator('.topbar .chip.click').click()
  await page.waitForSelector('.preview-table-wrap', { timeout: 15000 })
  await shot('07-dataset-preview.png')
  await page.locator('.modal-close').click()
  await page.waitForTimeout(300)

  console.log('upload excel with Chinese headers ...')
  await page.locator('.hd-add').click()
  await page.waitForSelector('.dropzone', { timeout: 10000 })
  await page.setInputFiles('input[type=file]', 'D:/dsworking/kill_asks/demo_data/双11大促销售数据.xlsx')
  await page.waitForFunction(
    () => document.querySelector('.topbar .crumbs b')?.textContent?.includes('双11大促销售数据'),
    null,
    { timeout: 60000 }
  )
  await page.waitForSelector('.dataset-ready', { timeout: 30000 })
  await waitToastGone()
  await shot('08-upload-excel-ready.png')

  console.log('ask with uploaded Chinese-column dataset ...')
  await textarea.fill('各区域的销售额对比')
  await page.keyboard.press('Enter')
  await page.waitForSelector('.chart-card', { timeout: 90000 })
  await page.waitForFunction(() => !document.querySelector('.lstep'), null, { timeout: 90000 })
  await page.evaluate(() => { const el = document.querySelector('.chat-scroll'); if (el) el.scrollTop = el.scrollHeight })
  await page.waitForTimeout(700)
  await shot('09-upload-excel-answer.png')

  if (errors.length) {
    console.log('\n浏览器错误：')
    errors.slice(0, 10).forEach((e) => console.log('  -', e))
  } else {
    console.log('\n没有浏览器报错 ✅')
  }
} catch (err) {
  console.error('E2E 失败：', err.message)
  await page.screenshot({ path: path.join(OUT, 'error.png') }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
