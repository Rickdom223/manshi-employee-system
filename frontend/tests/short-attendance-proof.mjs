import {chromium,expect} from '@playwright/test'
import {readFile,mkdir} from 'node:fs/promises'
const proof=JSON.parse(await readFile(process.env.SHORT_ATTENDANCE_PROOF,'utf8'))
const browser=await chromium.launch({channel:process.env.E2E_BROWSER_CHANNEL||(process.platform==='win32'?'msedge':undefined),headless:true})
try{
 await mkdir('../docs/screenshots-short-attendance',{recursive:true})
 for(const row of proof.rows){
  const context=await browser.newContext({viewport:{width:1500,height:1100}})
  await context.addCookies([{name:'manshi_session',value:row.cookie,url:proof.base,httpOnly:true,sameSite:'Lax'}])
  const page=await context.newPage();await page.goto(proof.base+'/my/attendance')
  await expect(page.getByRole('heading',{name:'我的打卡',exact:true})).toBeVisible()
  const cards=page.locator('.today-punch-cards');await expect(cards).toBeVisible()
  await expect(cards).toContainText(row.punch_in?.slice(11,19)||'未打卡');await expect(cards).toContainText(row.punch_out?.slice(11,19)||'未打卡')
  const first=page.locator('.el-table__body tr').first();await expect(first).toContainText(proof.date);await expect(first).toContainText(row.status)
  await expect(page.getByText('含测试记录',{exact:true})).toHaveCount(0)
  await page.screenshot({path:`../docs/screenshots-short-attendance/${row.scenario}.png`,fullPage:true})
  console.log(`网页已验证：${row.name} -> ${row.status}`);await context.close()
 }
}finally{await browser.close()}
