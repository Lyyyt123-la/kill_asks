/** 渲染 docs/architecture.html 为 PNG（用于技术文档与视频素材） */
import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'
].find((p) => fs.existsSync(p))

const out = path.resolve('..', 'docs', 'screenshots', '00-architecture.png')
const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 2 })
await page.goto('file:///' + path.resolve('..', 'docs', 'architecture.html').replace(/\\/g, '/'))
await page.waitForTimeout(600)
await page.screenshot({ path: out, fullPage: true })
console.log('architecture shot ->', out)
await browser.close()
