import { chromium } from 'playwright-core'
import fs from 'node:fs'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
await page.waitForTimeout(900)
await page.screenshot({ path: 'D:/dsworking/真机模拟测试/clean-ui-welcome.png' })
await page.locator('.side .ds-item').filter({ hasText: '双11' }).first().click().catch(() => {})
await page.waitForTimeout(900)
await page.screenshot({ path: 'D:/dsworking/真机模拟测试/clean-ui-dataset.png' })
console.log('screenshots ok')
await browser.close()
