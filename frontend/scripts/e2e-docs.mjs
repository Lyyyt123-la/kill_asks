/**
 * 文档能力 E2E：上传 PDF → 提取表格 → 表格转数据集 → 文档问答 → 上传图片走视觉识别。
 * 运行：cd frontend && node scripts/e2e-docs.mjs
 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe'
].find((p) => fs.existsSync(p))

const BASE_URL = process.env.ASK_BASE_URL || 'http://127.0.0.1:8000'
const OUT = path.resolve('..', 'docs', 'screenshots')
const DOCS = path.resolve('..', 'demo_data', 'documents')
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 })
const errors = []
page.on('pageerror', (err) => errors.push('pageerror: ' + err.message))
page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()) })

async function shot(name) {
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT, name) })
  console.log('shot ->', name)
}

async function waitToastGone() {
  await page.locator('.toast').waitFor({ state: 'detached', timeout: 10000 }).catch(() => {})
}

async function ask(text) {
  const textarea = page.locator('.composer textarea')
  await textarea.fill(text)
  await page.keyboard.press('Enter')
  await page.waitForSelector('.doc-answer-text', { timeout: 120000 })
  await page.waitForFunction(() => !document.querySelector('.lstep'), null, { timeout: 120000 })
}

try {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await page.waitForTimeout(700)
  await shot('01-welcome.png')

  console.log('--- 上传 PDF 财报 ---')
  await page.locator('.start-card.primary').click()
  await page.waitForSelector('.dropzone', { timeout: 10000 })
  await page.setInputFiles('input[type=file]', path.join(DOCS, '2025年Q3经营情况报告.pdf'))
  await waitToastGone()
  await page.waitForSelector('.doc-ready', { timeout: 60000 })
  await shot('10-doc-ready.png')

  console.log('--- 提取表格转为数据集分析 ---')
  await page.locator('.doc-table-row .btn-ghost').first().click()
  await page.waitForSelector('.dataset-ready', { timeout: 30000 })
  await shot('12-doc-table-dataset.png')

  console.log('--- 回到文档问答 ---')
  await page.locator('.side .side-sec').nth(1).locator('.ds-item').filter({ hasText: '2025年Q3' }).first().click()
  await page.waitForSelector('.doc-ready', { timeout: 30000 })
  await ask('这份报告里华东区 Q3 的销售额和同比是多少？')
  await shot('11-doc-answer.png')

  console.log('--- 上传图片截图（视觉识别） ---')
  await page.locator('.side .side-sec').nth(1).locator('.hd-add').click()
  await page.waitForSelector('.dropzone', { timeout: 10000 })
  await page.setInputFiles('input[type=file]', path.join(DOCS, '各渠道退款率截图.png'))
  await waitToastGone()
  await page.waitForSelector('.doc-ready', { timeout: 120000 })
  await shot('13-image-extracted.png')

  await ask('截图里哪个渠道退款率最高？是多少？')
  await shot('14-image-qa.png')

  console.log('--- 上传 Word 报告（验证格式兼容） ---')
  await page.locator('.side .side-sec').nth(1).locator('.hd-add').click()
  await page.waitForSelector('.dropzone', { timeout: 10000 })
  await page.setInputFiles('input[type=file]', path.join(DOCS, '双11大促复盘摘要.docx'))
  await waitToastGone()
  await page.waitForSelector('.doc-ready', { timeout: 60000 })
  await shot('15-word-ready.png')

  if (errors.length) {
    console.log('\n浏览器错误：')
    errors.slice(0, 8).forEach((item) => console.log('  -', item))
  } else {
    console.log('\n没有浏览器报错 ✅')
  }
} catch (err) {
  console.error('E2E 失败：', err.message)
  await page.screenshot({ path: path.join(OUT, 'doc-error.png') }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
