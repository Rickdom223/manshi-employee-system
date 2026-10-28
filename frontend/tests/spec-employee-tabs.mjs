import {chromium,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
const browser=await chromium.launch({channel:'chrome',headless:true}),context=await browser.newContext({viewport:{width:1366,height:768}}),page=await context.newPage()
const base='http://127.0.0.1:3000',results=[]
async function login(username,password){await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill(username);await page.getByLabel('密码',{exact:true}).fill(password);await page.getByRole('button',{name:'登录平台'}).click();await expect(page.locator('.workspace-tabs')).toBeVisible()}
async function menu(name){await page.getByRole('link',{name:new RegExp(name+'$')}).click()}
async function logout(){await page.getByRole('button',{name:'退出登录'}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await expect(page.getByRole('heading',{name:'账号登录'})).toBeVisible()}
try{
 await login('ljm','Ljm123')
 const me=(await(await page.request.get(base+'/api/auth/me')).json()).data
 const headers={Origin:base,'X-CSRF-Token':me.csrf_token}
 const deps=(await(await page.request.get(base+'/api/departments?page_size=100')).json()).data
 const department=deps.find(d=>d.name==='制琴生产部')
 const positions=(await(await page.request.get(base+'/api/positions?department_id='+department.id)).json()).data
 const response=await page.request.post(base+'/api/employees',{headers,data:{name:'标签验收员工',phone:'13800000001',hire_date:'2026-10-27',department_id:department.id,position_id:positions[0].id,base_salary:'6000.00',create_account:true,initial_password:'Test1234'}})
 expect(response.status()).toBe(201);const staff=(await response.json()).data
 await menu('员工信息管理');await menu('薪资管理');await logout()
 expect(await page.evaluate(()=>Object.keys(sessionStorage).filter(k=>k.startsWith('manshi-tabs:')))).toEqual([])
 await login(staff.account_username,'Test1234')
 await expect(page.locator('aside')).not.toContainText('薪资管理')
 await expect(page.getByRole('tab',{name:'员工信息管理',exact:true})).toHaveCount(0)
 await page.goto(base+'/admin/payroll');await expect(page).toHaveURL(base+'/employee/profile')
 results.push({id:'UI-TAB-07-switch-account',status:'通过'})
 await menu('个人考勤');await menu('我的任务');await expect(page.locator('.workspace-tab')).toHaveCount(3)
 await page.getByRole('tab',{name:'个人信息',exact:true}).click();await expect(page).toHaveURL(base+'/employee/profile')
 await page.reload();await expect(page.getByRole('tab',{name:'我的任务',exact:true})).toBeVisible()
 results.push({id:'UI-TAB-09',status:'通过'})
 await context.clearCookies();await menu('个人考勤');await expect(page.getByRole('heading',{name:'账号登录'})).toBeVisible()
 expect(await page.evaluate(()=>Object.keys(sessionStorage).filter(k=>k.startsWith('manshi-tabs:')))).toEqual([])
 results.push({id:'UI-TAB-07-expired',status:'通过'})
 await mkdir('../docs/screenshots-spec',{recursive:true});await page.screenshot({path:'../docs/screenshots-spec/expired-login.png'})
 await writeFile('../docs/ui-tab-stage2.json',JSON.stringify({results},null,2));results.forEach(r=>console.log('PASS '+r.id))
}catch(error){console.error(error.message);await mkdir('../docs/screenshots-spec',{recursive:true});await page.screenshot({path:'../docs/screenshots-spec/employee-tabs-failure.png'});process.exitCode=1}finally{await browser.close()}
