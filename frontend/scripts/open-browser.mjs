/** 打开一个 1600×1000 的 Chrome 应用窗口，用于 ffmpeg 窗口录制测试/正式录制。 */
import { chromium } from 'playwright-core'
import fs from 'node:fs'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const WAIT_MS = Number(process.env.WAIT_MS || 45000)

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: false,
  args: [
    '--app=http://127.0.0.1:8000',
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
await page.waitForTimeout(1200)
console.log('browser ready')
await page.waitForTimeout(WAIT_MS)
await browser.close()
