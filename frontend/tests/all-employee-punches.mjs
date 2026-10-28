import {chromium,expect} from '@playwright/test'
import {readFile,writeFile,mkdir} from 'node:fs/promises'
const manifest=JSON.parse(await readFile(process.env.PUNCH_MANIFEST,'utf8')),base=process.env.E2E_BASE_URL
const browser=await chromium.launch({channel:process.env.E2E_BROWSER_CHANNEL||(process.platform==='win32'?'msedge':undefined),headless:true})
const results=[],sessions={},pageErrors=[]
await mkdir('../docs/screenshots-punch-test',{recursive:true})
const protectedEmployees=manifest.employees.filter(e=>e.expected_access==='allowed')
async function login(page,name){await page.goto(base+'/login');await page.getByLabel('用户名',{exact:true}).fill(name);await page.getByLabel('密码',{exact:true}).fill(manifest.test_password);const responsePromise=page.waitForResponse(r=>r.url()===base+'/api/auth/login'&&r.request().method()==='POST');await page.getByRole('button',{name:'登录平台',exact:true}).click();return await responsePromise}
function ms(value){return Date.parse(value+manifest.utc_offset)}
try{
 for(const employee of manifest.employees){
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage()
  page.on('pageerror',error=>pageErrors.push({employee_no:employee.employee_no,message:error.message}))
  const row={id:employee.id,employee_no:employee.employee_no,name:employee.name,role:employee.role,expected_access:employee.expected_access,status:'failed'}
  try{
   const loginResponse=await login(page,employee.username)
   if(employee.expected_access==='denied'){
    expect(loginResponse.status()).toBe(401);row.login=401
    await expect(page).toHaveURL(base+'/login')
    await context.addCookies([{name:'manshi_session',value:employee.stale_cookie,url:base,httpOnly:true,sameSite:'Lax'}])
    const headers={Origin:base,'X-CSRF-Token':employee.stale_csrf}
    row.blocked_punch_in=(await context.request.post(base+'/api/me/punch-in',{headers})).status()
    row.blocked_punch_out=(await context.request.post(base+'/api/me/punch-out',{headers})).status()
    expect(row.blocked_punch_in).toBe(401);expect(row.blocked_punch_out).toBe(401)
    row.boundary_checks=true;row.status='passed'
   }else{
    expect(loginResponse.status()).toBe(200);row.login=200
    const identity=(await loginResponse.json()).data;expect(identity.employee_id).toBe(employee.id);expect(identity.role).toBe(employee.role)
    const headers={Origin:base,'X-CSRF-Token':identity.csrf_token}
    const other=protectedEmployees.find(e=>e.id!==employee.id)
    const premature=await context.request.post(base+'/api/me/punch-out',{headers,data:{employee_id:other?.id,punch_time:'2000-01-01T00:00:00'}})
    expect(premature.status()).toBe(409);expect((await premature.json()).error.code).toBe('PUNCH_IN_REQUIRED')
    await page.getByRole('link',{name:/我的打卡$/}).click();await expect(page.getByRole('heading',{name:'我的打卡',exact:true})).toBeVisible()
    const beforeIn=Date.now(),inPromise=page.waitForResponse(r=>r.url()===base+'/api/me/punch-in'&&r.request().method()==='POST')
    await page.getByRole('button',{name:'上班打卡',exact:true}).click();const inResponse=await inPromise;row.punch_in=inResponse.status();expect(row.punch_in).toBe(200)
    const inData=(await inResponse.json()).data;row.punch_in_time=inData.punch_time;expect(inData.punch_date).toBe(manifest.business_date)
    expect(ms(inData.punch_time)).toBeGreaterThanOrEqual(beforeIn-1500);expect(ms(inData.punch_time)).toBeLessThanOrEqual(Date.now()+1500)
    const duplicateIn=await context.request.post(base+'/api/me/punch-in',{headers});expect(duplicateIn.status()).toBe(409);expect((await duplicateIn.json()).error.code).toBe('ALREADY_PUNCHED')
    const beforeOut=Date.now(),outPromise=page.waitForResponse(r=>r.url()===base+'/api/me/punch-out'&&r.request().method()==='POST')
    await page.getByRole('button',{name:'下班打卡',exact:true}).click();const outResponse=await outPromise;row.punch_out=outResponse.status();expect(row.punch_out).toBe(200)
    const outData=(await outResponse.json()).data;row.punch_out_time=outData.punch_time;expect(outData.punch_date).toBe(manifest.business_date)
    expect(ms(outData.punch_time)).toBeGreaterThan(ms(inData.punch_time));expect(ms(outData.punch_time)).toBeGreaterThanOrEqual(beforeOut-1500);expect(ms(outData.punch_time)).toBeLessThanOrEqual(Date.now()+1500)
    const duplicateOut=await context.request.post(base+'/api/me/punch-out',{headers});expect(duplicateOut.status()).toBe(409);expect((await duplicateOut.json()).error.code).toBe('ALREADY_PUNCHED')
    const summaryResponse=await context.request.get(base+`/api/me/attendance?month=${manifest.business_date.slice(0,7)}&employee_id=${other?.id}`)
    expect(summaryResponse.status()).toBe(200);const summary=(await summaryResponse.json()).data;expect(summary.employee_id).toBe(employee.id)
    const daily=summary.daily.find(d=>d.date===manifest.business_date);expect(daily?.punch_in).toBe(inData.punch_time);expect(daily?.punch_out).toBe(outData.punch_time)
    const today=page.getByRole('row').filter({has:page.getByText(manifest.business_date,{exact:true})});await expect(today).toContainText(inData.punch_time);await expect(today).toContainText(outData.punch_time)
    row.boundary_checks=true;row.status='passed';row.summary_status=daily.status
    sessions[String(employee.id)]=(await context.cookies(base)).find(c=>c.name==='manshi_session').value
    if(['1','2','31'].includes(employee.employee_no))await page.screenshot({path:`../docs/screenshots-punch-test/employee-${employee.employee_no}.png`,fullPage:true})
   }
  }catch(error){row.reason=error.message;process.exitCode=1;await page.screenshot({path:`../docs/screenshots-punch-test/failure-employee-${employee.id}.png`,fullPage:true}).catch(()=>{})}
  finally{results.push(row);console.log(`${employee.employee_no} ${employee.name}: ${row.status} (${employee.expected_access})`);await context.close()}
 }
 const adminCheck={status:'passed'}
 try{
  for(const account of manifest.system_accounts.filter(a=>a.role==='SYS_ADMIN'&&a.is_active)){
   const context=await browser.newContext(),page=await context.newPage();const response=await login(page,account.username);expect(response.status()).toBe(200)
   const me=(await response.json()).data;const headers={Origin:base,'X-CSRF-Token':me.csrf_token}
   expect((await context.request.post(base+'/api/me/punch-in',{headers})).status()).toBe(403);expect((await context.request.post(base+'/api/me/punch-out',{headers})).status()).toBe(403)
   await context.close()
  }
 }catch(error){adminCheck.status='failed';adminCheck.reason=error.message;process.exitCode=1}
 await writeFile(process.env.PUNCH_RESULTS,JSON.stringify({employees:results,admin_check:adminCheck,page_errors:pageErrors},null,2))
 await writeFile(process.env.PUNCH_SESSIONS,JSON.stringify(sessions))
}finally{await browser.close()}
