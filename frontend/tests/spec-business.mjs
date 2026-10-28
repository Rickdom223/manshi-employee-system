import {chromium,expect} from '@playwright/test'
import {mkdir,writeFile} from 'node:fs/promises'
const browser=await chromium.launch({channel:'chrome',headless:true}),context=await browser.newContext({viewport:{width:1366,height:768},acceptDownloads:true}),page=await context.newPage()
const base='http://127.0.0.1:3000',results=[],errors=[],suffix=String(Date.now()).slice(-6),staffName='业务验收员工'+suffix
page.on('response',async r=>{if(r.status()>=400 && !r.url().endsWith('/api/auth/me'))console.log('HTTP '+r.status()+' '+new URL(r.url()).pathname)});
page.on('pageerror',e=>{if(errors.length<2)console.error(e.stack);errors.push(e.message)})
const dialog=name=>page.getByRole('dialog',{name,exact:true})
async function menu(name){await page.getByRole('link',{name:new RegExp(name+'$')}).click()}
async function login(username,password){await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill(username);await page.getByLabel('密码',{exact:true}).fill(password);await page.getByRole('button',{name:'登录平台'}).click();await expect(page.locator('.workspace-tabs')).toBeVisible()}
async function logout(){await page.getByRole('button',{name:'退出登录'}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await expect(page.locator('.login-card')).toBeVisible()}
async function select(label,text,container=page,multiple=false){const item=container.locator('.el-form-item').filter({has:page.locator('.el-form-item__label',{hasText:label})}).first();await item.locator('.el-select').click();const control=await item.locator('[role=combobox]').first().getAttribute('aria-controls');const list=page.locator('#'+control);await list.locator('.el-select-dropdown__item').filter({hasText:text}).first().click();await page.keyboard.press('Escape');await expect(list).not.toBeVisible()}
async function date(placeholder,value,container){const input=container.getByPlaceholder(placeholder);await input.fill(value);await input.press('Enter')}
async function check(id,fn){await fn();results.push({id,status:'通过'});console.log('PASS '+id)}
let staff,cooperator,headers
try{
 await login('ljm','Ljm123')
 await check('WEB-员工创建与开通账号',async()=>{
  await menu('员工信息管理');await page.getByRole('button',{name:'新增员工'}).click();const form=dialog('新增员工')
  await form.getByLabel('姓名',{exact:true}).fill(staffName)
  await select('部门','制琴生产部',form);await select('主要岗位','制琴师',form)
  await form.getByPlaceholder('选择入职日期').fill('2026-10-01');await form.getByLabel('姓名',{exact:true}).click()
  await form.getByLabel('手机号',{exact:true}).fill('13800000002');await form.getByLabel('基本工资（元）',{exact:true}).fill('6000.00')
  await form.locator('.el-switch').click();await form.getByLabel('初始密码（8–10位大小写及数字）',{exact:true}).fill('Test1234')
  await form.getByRole('button',{name:'保存档案'}).click();await expect(form).not.toBeVisible()
  await expect(page.getByRole('row').filter({hasText:staffName})).toBeVisible()
  staff=(await(await page.request.get(base+'/api/employees?keyword='+encodeURIComponent(staffName))).json()).data[0]
  const me=(await(await page.request.get(base+'/api/auth/me')).json()).data;headers={Origin:base,'X-CSRF-Token':me.csrf_token}
  const r=await page.request.post(base+'/api/employees',{headers,data:{name:'协作验收员工'+suffix,phone:'13800000003',hire_date:'2026-10-01',department_id:staff.department_id,position_id:staff.position_id,base_salary:'5000.00'}})
  expect(r.status()).toBe(201);cooperator=(await r.json()).data
 })
 await check('WEB-考勤录入与月度统计',async()=>{
  await menu('考勤管理');await page.getByRole('button',{name:'录入考勤'}).click();const form=dialog('录入考勤')
  await select('员工',staffName,form);await form.locator('.el-date-editor input').first().fill('2026-10-27');await form.getByText('考勤日期',{exact:true}).click()
  await form.getByRole('button',{name:'保存考勤'}).click();await expect(form).not.toBeVisible()
  await expect(page.getByRole('row').filter({hasText:staffName}).first()).toBeVisible()
 })
 await logout();await login(staff.account_username,'Test1234')
 await check('WEB-员工提交请假',async()=>{
  await menu('请假申请');await page.getByRole('button',{name:'申请请假'}).click();const form=dialog('申请请假')
  const inputs=form.locator('.el-date-editor input');await inputs.nth(0).fill('2026-10-28');await form.getByText('开始日期',{exact:true}).click();await inputs.nth(1).fill('2026-10-29');await form.getByText('结束日期',{exact:true}).click()
  await form.getByLabel('请假原因',{exact:true}).fill('业务验收请假'+suffix);await form.getByRole('button',{name:'提交申请'}).click();await expect(form).not.toBeVisible();await expect(page.getByRole('row').filter({hasText:'业务验收请假'+suffix}).getByText('待审批',{exact:true})).toBeVisible()
 })
 await logout();await login('ljm','Ljm123')
 await check('WEB-审批与考勤联动',async()=>{
  await menu('请假审批');const row=page.getByRole('row').filter({hasText:'业务验收请假'+suffix});await row.getByRole('button',{name:'通过',exact:true}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await expect(row).toContainText('已通过')
  await menu('考勤管理');await page.getByLabel('员工姓名',{exact:true}).fill(staffName);await page.getByRole('button',{name:'查询',exact:true}).click();await expect(page.getByRole('row').filter({hasText:staffName}).filter({hasText:'请假'})).toHaveCount(2)
 })
 await check('WEB-工资生成编辑发放导出',async()=>{
  await menu('薪资管理');await page.getByRole('button',{name:'生成工资草稿'}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await page.getByLabel('姓名',{exact:true}).fill(staffName);await page.getByRole('button',{name:'查询',exact:true}).click()
  const row=page.getByRole('row').filter({hasText:staffName});await row.getByRole('button',{name:'编辑',exact:true}).click();const form=dialog('编辑工资');await form.getByLabel('奖金（元）',{exact:true}).fill('123.45');await form.getByLabel('扣款（元）',{exact:true}).fill('23.44');await form.getByRole('button',{name:'保存工资'}).click();await expect(form).not.toBeVisible();await expect(row).toContainText('6100.01')
  await row.getByRole('button',{name:'标记已发放'}).click();await page.getByRole('button',{name:'确定',exact:true}).click();await expect(row).toContainText('已发放')
  const pending=page.waitForEvent('download');await page.getByRole('button',{name:'导出 Excel'}).click();expect((await pending).suggestedFilename()).toMatch(/\.xlsx$/)
 })
 await check('WEB-多人任务生产质检完成',async()=>{
  await menu('制琴任务管理');await page.getByRole('button',{name:'新增制琴任务'}).click();const form=dialog('新增制琴任务')
  await form.getByLabel('任务名称',{exact:true}).fill('MS-01民谣吉他验收'+suffix);await form.getByLabel('吉他型号',{exact:true}).fill('MS-01')
  await form.getByLabel('计划数量',{exact:true}).fill('5');await select('负责人',staffName,form);await select('参与员工',staffName,form,true);await select('参与员工',cooperator.name,form,true)
  const inputs=form.locator('.el-date-editor input');await inputs.nth(0).fill('2026-10-27');await form.getByText('开始日期',{exact:true}).click();await inputs.nth(1).fill('2026-11-15');await form.getByText('预计完成日期',{exact:true}).click()
  await form.getByRole('button',{name:'保存任务'}).click();await expect(form).not.toBeVisible()
  const row=page.getByRole('row').filter({hasText:'MS-01民谣吉他验收'+suffix});await row.getByRole('button',{name:'开始制作'}).click();await dialog('任务状态确认').getByRole('button',{name:'确定',exact:true}).click();await expect(row).toContainText('制作中')
  await row.getByRole('button',{name:'编辑进度'}).click();const edit=dialog('编辑任务进度');await edit.getByLabel('已完成数量',{exact:true}).fill('5');await edit.getByRole('button',{name:'保存任务'}).click();await expect(edit).not.toBeVisible()
  await row.getByRole('button',{name:'提交质检'}).click();await dialog('任务状态确认').getByRole('button',{name:'确定',exact:true}).click();await expect(row).toContainText('待质检')
  await row.getByRole('button',{name:'质检通过',exact:true}).click();const prompt=page.getByRole('dialog',{name:'录入质检结果'});await prompt.locator('textarea').fill('音准与装配检查通过');await prompt.getByRole('button',{name:'确定',exact:true}).click()
  await row.getByRole('button',{name:'确认完成'}).click();await dialog('任务状态确认').getByRole('button',{name:'确定',exact:true}).click();await expect(row).toContainText('已完成')
 })
 await check('WEB-统计图表与报表导出',async()=>{
  await menu('统计报表');await expect(page.locator('.echart canvas')).toBeVisible();const pending=page.waitForEvent('download');await page.getByRole('button',{name:'导出 Excel'}).click();expect((await pending).suggestedFilename()).toMatch(/\.xlsx$/)
  await menu('首页概览');await expect(page.getByText('今日正常出勤人数')).toBeVisible();await expect(page.locator('.echart canvas')).toHaveCount(2)
 })
 await mkdir('../docs/screenshots-spec',{recursive:true});await page.screenshot({path:'../docs/screenshots-spec/final-dashboard.png',fullPage:true})
 await logout();await login(staff.account_username,'Test1234')
 await check('WEB-员工个人业务权限',async()=>{await menu('个人考勤');await expect(page.getByRole('cell',{name:'请假',exact:true})).toHaveCount(2);await menu('我的工资');await expect(page.getByRole('row').filter({hasText:'6100.01'})).toHaveCount(1);await menu('我的任务');await expect(page.getByRole('row').filter({hasText:'MS-01民谣吉他验收'+suffix})).toHaveCount(1);expect((await page.request.get(base+'/api/employees')).status()).toBe(403)})
 expect(errors).toEqual([]);await writeFile('../docs/business-e2e-spec.json',JSON.stringify({results,errors},null,2))
}catch(error){console.error(error.message);await mkdir('../docs/screenshots-spec',{recursive:true});await page.screenshot({path:'../docs/screenshots-spec/business-failure.png',fullPage:true});process.exitCode=1}finally{await browser.close()}
