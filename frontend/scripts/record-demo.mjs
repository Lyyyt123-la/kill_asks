/**
 * 自动录制演示视频：Chrome 窗口置顶 + ffmpeg 录制屏幕左上角区域（1600×1000）。
 * 输出：docs/demo_recording.mp4（无声录屏素材，可在剪映中加 AI 配音/字幕）
 *
 * 运行：cd frontend && node scripts/record-demo.mjs
 * 前提：后端 http://127.0.0.1:8000 已启动，数据已重置为示例数据。
 */
import { chromium } from 'playwright-core'
import { spawn, execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const FFMPEG = path.resolve('node_modules/@ffmpeg-installer/win32-x64/ffmpeg.exe')
const TOPMOST = path.resolve('scripts/topmost.ps1')
const OUT = path.resolve('..', 'docs', 'demo_recording.mp4')
const LOG = path.resolve('..', 'docs', '_recording.log')
const DOCS = path.resolve('..', 'demo_data', 'documents')
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const log = (message) => {
  const line = `${new Date().toLocaleTimeString('zh-CN')} ${message}`
  fs.appendFileSync(LOG, line + '\n', 'utf-8')
  console.log(line)
}

fs.writeFileSync(LOG, '', 'utf-8')
if (fs.existsSync(OUT)) fs.unlinkSync(OUT)

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: false,
  args: [
    '--window-position=0,0',
    '--window-size=1600,1000',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-features=Translate',
    '--force-device-scale-factor=1'
  ]
})
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } })
const page = await context.newPage()
await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
await page.evaluate(() => { document.title = 'AskData Demo' })
await page.waitForTimeout(1800)
await page.bringToFront()

// Chrome 窗口置顶，避免被其他窗口遮挡（桌面区域录制）
try {
  const result = execSync(`powershell -NoProfile -ExecutionPolicy Bypass -File "${TOPMOST}"`, { encoding: 'utf-8' })
  log('置顶：' + result.trim())
} catch (error) {
  log('置顶失败：' + error.message)
}
await sleep(800)

const ffmpeg = spawn(
  FFMPEG,
  [
    '-hide_banner', '-loglevel', 'error',
    '-f', 'gdigrab', '-framerate', '10',
    '-offset_x', '0', '-offset_y', '0',
    '-video_size', '1600x1000',
    '-i', 'desktop',
    '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26',
    '-y', OUT
  ],
  { stdio: ['pipe', 'ignore', 'pipe'] }
)
ffmpeg.stderr.on('data', (chunk) => {
  const text = String(chunk).trim()
  if (text) log('[ffmpeg] ' + text.slice(0, 200))
})
await sleep(2000)

const textarea = page.locator('.composer textarea')

async function typeAndSend(question) {
  await textarea.fill('')
  await textarea.fill(question)
  await page.keyboard.press('Enter')
  log('发送：' + question)
}

async function step(name, fn) {
  try {
    log('步骤开始：' + name)
    await fn()
    log('步骤完成：' + name)
  } catch (error) {
    log('步骤跳过：' + name + ' -> ' + error.message)
  }
}

try {
  log('录制开始')
  await page.waitForTimeout(3000)

  await step('载入示例数据', async () => {
    await page.locator('.start-card').nth(1).click()
    await page.waitForSelector('.dataset-ready', { timeout: 60000 })
    await page.waitForTimeout(4000)
  })

  await step('区域销售额对比', async () => {
    await typeAndSend('各区域的销售额对比')
    await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 1, null, { timeout: 60000 })
    await page.waitForTimeout(3500)
  })

  await step('展开 SQL', async () => {
    await page.locator('.sql-summary').first().click()
    await page.waitForTimeout(4200)
    await page.locator('.sql-summary').first().click()
    await page.waitForTimeout(1200)
  })

  await step('最低的三个品类（多轮追问）', async () => {
    await typeAndSend('销售额最低的3个品类')
    await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 60000 })
    await page.waitForTimeout(3500)
  })

  await step('打开检查器', async () => {
    await page.locator('.icon-btn[title*="检查器"]').click()
    await page.waitForSelector('.inspector', { timeout: 10000 })
    await page.waitForTimeout(4500)
    await page.locator('.inspector .close').click()
    await page.waitForTimeout(1500)
  })

  await step('上传 PDF 财报', async () => {
    await page.locator('.side .side-sec').nth(0).locator('.hd-add').click()
    await page.waitForSelector('.dropzone', { timeout: 10000 })
    await page.setInputFiles('input[type=file]', path.join(DOCS, '2025年Q3经营情况报告.pdf'))
    await page.waitForSelector('.doc-ready', { timeout: 90000 })
    await page.waitForTimeout(4500)
  })

  await step('文档问答', async () => {
    await typeAndSend('这份报告里华东区 Q3 的销售额和同比是多少？')
    await page.waitForSelector('.doc-answer-text', { timeout: 120000 })
    await page.waitForTimeout(4500)
  })

  await step('上传图片截图', async () => {
    await page.locator('.side .side-sec').nth(1).locator('.hd-add').click()
    await page.waitForSelector('.dropzone', { timeout: 10000 })
    await page.setInputFiles('input[type=file]', path.join(DOCS, '各渠道退款率截图.png'))
    await page.waitForSelector('.doc-ready', { timeout: 150000 })
    await page.waitForTimeout(4500)
  })

  await step('图片数据问答', async () => {
    await typeAndSend('截图里哪个渠道退款率最高？是多少？')
    await page.waitForSelector('.doc-answer-text', { timeout: 150000 })
    await page.waitForTimeout(4500)
  })

  await step('切换数据集并演示澄清', async () => {
    const demoItem = page.locator('.side .side-sec').nth(0).locator('.ds-item').filter({ hasText: '双11大促销售数据' }).first()
    await demoItem.click()
    await page.waitForSelector('.dataset-ready', { timeout: 30000 })
    await page.waitForTimeout(2500)
    await typeAndSend('最近卖得怎么样')
    await page.waitForSelector('.clarify-card', { timeout: 90000 })
    await page.waitForTimeout(4500)
  })

  log('录制流程结束')
} catch (error) {
  log('录制异常：' + error.message)
} finally {
  await sleep(800)
  ffmpeg.stdin.write('q')
  await new Promise((resolve) => {
    const timer = setTimeout(() => { try { ffmpeg.kill() } catch (error) {} ; resolve() }, 15000)
    ffmpeg.on('close', () => { clearTimeout(timer); resolve() })
  })
  await sleep(800)
  await browser.close()
}

if (fs.existsSync(OUT)) {
  const size = (fs.statSync(OUT).size / 1024 / 1024).toFixed(1)
  log(`视频输出 ${OUT} (${size} MB)`)
} else {
  log('未生成视频文件')
  process.exitCode = 1
}
