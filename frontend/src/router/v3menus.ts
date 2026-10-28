export type Role='SYS_ADMIN'|'HR'|'SUPERVISOR'|'EMPLOYEE'
export type Menu={path:string;title:string;affix?:boolean}
const personal:Menu[]=[{path:'/home',title:'个人工作台',affix:true},{path:'/my/profile',title:'我的档案'},{path:'/my/attendance',title:'我的打卡'},{path:'/my/leaves',title:'我的请假'},{path:'/my/salaries',title:'我的薪资'}]
const hr:Menu[]=[{path:'/hr/dashboard',title:'人事数据看板',affix:true},{path:'/hr/departments',title:'固定部门'},{path:'/hr/positions',title:'职位与职级'},{path:'/hr/employees',title:'员工档案'},{path:'/hr/attendance/rules',title:'考勤规则'},{path:'/hr/attendance/monthly',title:'月度考勤'},{path:'/hr/leaves',title:'全员请假记录'},{path:'/hr/salaries',title:'薪资管理'}]
const admin:Menu[]=[{path:'/admin/home',title:'系统概览',affix:true},{path:'/admin/users',title:'用户管理'},{path:'/admin/departed-users',title:'离职账号管理'},{path:'/admin/supervisors',title:'部门主管配置'},{path:'/admin/bootstrap-hr',title:'初始化／恢复 HR'},{path:'/admin/audit-logs',title:'操作审计'}]
export const roles:Record<string,string>={SYS_ADMIN:'系统管理员',HR:'HR',SUPERVISOR:'部门主管',EMPLOYEE:'普通员工'}
export function menusFor(role:string):Menu[]{
 const modules=role==='SYS_ADMIN'?admin:role==='HR'?[...hr,...personal.map(m=>({...m,affix:false}))]:role==='SUPERVISOR'?[...personal,{path:'/supervisor/employees',title:'本部门员工'},{path:'/supervisor/leaves',title:'本部门请假审批'}]:role==='EMPLOYEE'?personal:[]
 return [...modules,{path:'/account',title:'账号设置'}]
}
export function homeFor(role:string){return role==='SYS_ADMIN'?'/admin/home':role==='HR'?'/hr/dashboard':'/home'}
export const allMenus=[...new Map(['SYS_ADMIN','HR','SUPERVISOR','EMPLOYEE'].flatMap(menusFor).map(m=>[m.path,m])).values()]
