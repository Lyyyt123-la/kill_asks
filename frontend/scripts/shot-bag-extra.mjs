import { chromium } from 'playwright-core'
import fs from 'node:fs'

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p))
const OUT = 'D:/dsworking/chart_bag'
const browser = await chromium.launch({ executablePath: CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
try {
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  await page.locator('.start-card').nth(1).click()
  await page.waitForSelector('.dataset-ready', { timeout: 60000 })
  const textarea = page.locator('.composer textarea')
  await textarea.fill('各品类销售额占比')
  await page.keyboard.press('Enter')
  await page.waitForSelector('.product-showcase svg', { timeout: 120000 })
  await page.waitForTimeout(2500)
  // 悬停第一件商品
  const groups = page.locator('.product-showcase svg > g')
  await groups.nth(1).hover()
  await page.waitForTimeout(500)
  await page.locator('.chart-card').last().screenshot({ path: `${OUT}/06-hover.png` })
  // 点击第一件商品，应把下钻问题填入输入框
  await groups.nth(1).click()
  await page.waitForTimeout(400)
  const value = await textarea.inputValue()
  console.log('点击后输入框:', value)
  await page.screenshot({ path: `${OUT}/07-click.png` })
} catch (error) {
  console.error('失败：', error.message)
} finally {
  await browser.close()
}
