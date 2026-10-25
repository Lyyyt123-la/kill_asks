/**
 * 自动录制演示视频（页面截图逐帧编码，不受桌面窗口干扰）。
 * 输出：docs/demo_recording.mp4（无声录屏素材）
 *
 * 运行：cd frontend && node scripts/record-frames.mjs
 */
import { chromium } from 'playwright-core'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const FFMPEG = path.resolve('node_modules/@ffmpeg-installer/win32-x64/ffmpeg.exe')
const OUT = path.resolve('..', 'docs', 'demo_recording.mp4')
const FRAMES = path.resolve('..', 'docs', '_frames')
const LOG = path.resolve('..', 'docs', '_recording.log')
const DOCS = path.resolve('..', 'demo_data', 'documents')
const FPS = 5
const FRAME_INTERVAL = 190
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const log = (message) => {
  const line = `${new Date().toLocaleTimeString('zh-CN')} ${message}`
  fs.appendFileSync(LOG, line + '\n', 'utf-8')
  console.log(line)
}

fs.writeFileSync(LOG, '', 'utf-8')
fs.rmSync(FRAMES, { recursive: true, force: true })
fs.mkdirSync(FRAMES, { recursive: true })
if (fs.existsSync(OUT)) fs.unlinkSync(OUT)

const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 })
const page = await context.newPage()
await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)

let frameIndex = 0
let capturing = false
let captureTask = null

async function captureLoop() {
  while (capturing) {
    const file = path.join(FRAMES, `frame_${String(frameIndex).padStart(6, '0')}.png`)
    try {
      await page.screenshot({ path: file, animations: 'disabled', timeout: 5000 })
      frameIndex += 1
    } catch (error) {
      // 页面切换瞬间偶发截图失败，跳过该帧
    }
    await sleep(FRAME_INTERVAL)
  }
}

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
  capturing = true
  captureTask = captureLoop()
  await sleep(2500)

  await step('载入示例数据', async () => {
    await page.locator('.start-card').nth(1).click()
    await page.waitForSelector('.dataset-ready', { timeout: 60000 })
    await page.waitForTimeout(5000)
  })

  await step('区域销售额对比', async () => {
    await typeAndSend('各区域的销售额对比')
    await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 1, null, { timeout: 60000 })
    await page.waitForTimeout(5500)
  })

  await step('展开 SQL', async () => {
    await page.locator('.sql-summary').first().click()
    await page.waitForTimeout(5000)
    await page.locator('.sql-summary').first().click()
    await page.waitForTimeout(1500)
  })

  await step('最低的三个品类（多轮追问）', async () => {
    await typeAndSend('销售额最低的3个品类')
    await page.waitForFunction(() => document.querySelectorAll('.chart-card').length >= 2, null, { timeout: 60000 })
    await page.waitForTimeout(5500)
  })

  await step('打开检查器', async () => {
    await page.locator('.icon-btn[title*="检查器"]').click()
    await page.waitForSelector('.inspector', { timeout: 10000 })
    await page.waitForTimeout(5500)
    await page.locator('.inspector .close').click()
    await page.waitForTimeout(1500)
  })

  await step('上传 PDF 财报', async () => {
    await page.locator('.side .side-sec').nth(0).locator('.hd-add').click()
    await page.waitForSelector('.dropzone', { timeout: 10000 })
    await page.setInputFiles('input[type=file]', path.join(DOCS, '2025年Q3经营情况报告.pdf'))
    await page.waitForSelector('.doc-ready', { timeout: 90000 })
    await page.waitForTimeout(5500)
  })

  await step('文档问答', async () => {
    await typeAndSend('这份报告里华东区 Q3 的销售额和同比是多少？')
    await page.waitForSelector('.doc-answer-text', { timeout: 120000 })
    await page.waitForTimeout(6000)
  })

  await step('上传图片截图', async () => {
    await page.locator('.side .side-sec').nth(1).locator('.hd-add').click()
    await page.waitForSelector('.dropzone', { timeout: 10000 })
    await page.setInputFiles('input[type=file]', path.join(DOCS, '各渠道退款率截图.png'))
    await page.waitForSelector('.doc-ready', { timeout: 150000 })
    await page.waitForTimeout(5500)
  })

  await step('图片数据问答', async () => {
    await typeAndSend('截图里哪个渠道退款率最高？是多少？')
    await page.waitForSelector('.doc-answer-text', { timeout: 150000 })
    await page.waitForTimeout(6000)
  })

  await step('切换数据集并演示澄清', async () => {
    const demoItem = page.locator('.side .side-sec').nth(0).locator('.ds-item').filter({ hasText: '双11大促销售数据' }).first()
    await demoItem.click()
    await page.waitForSelector('.dataset-ready', { timeout: 30000 })
    await page.waitForTimeout(3000)
    await typeAndSend('最近卖得怎么样')
    await page.waitForSelector('.clarify-card', { timeout: 90000 })
    await page.waitForTimeout(6000)
  })

  log('录制流程结束')
} catch (error) {
  log('录制异常：' + error.message)
} finally {
  await sleep(1200)
  capturing = false
  await captureTask
  await browser.close()
}

log(`共捕获 ${frameIndex} 帧，开始编码 ...`)
try {
  execFileSync(
    FFMPEG,
    [
      '-hide_banner', '-loglevel', 'error',
      '-framerate', String(FPS),
      '-i', path.join(FRAMES, 'frame_%06d.png'),
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24',
      '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
      '-y', OUT
    ],
    { stdio: 'ignore' }
  )
  const size = (fs.statSync(OUT).size / 1024 / 1024).toFixed(1)
  log(`视频输出 ${OUT} (${size} MB)`)
} catch (error) {
  log('编码失败：' + error.message)
  process.exitCode = 1
}
fs.rmSync(FRAMES, { recursive: true, force: true })
