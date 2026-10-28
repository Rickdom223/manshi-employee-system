export type Role = 'ADMIN' | 'EMPLOYEE'
export type Menu = { path: string; title: string; role: Role; affix?: boolean }
export const phase = 3
const admin: Menu[] = [
  { path:'/admin/dashboard',title:'首页概览',role:'ADMIN',affix:true },
  { path:'/admin/employees',title:'员工信息管理',role:'ADMIN' },
  { path:'/admin/departments',title:'部门与岗位管理',role:'ADMIN' },
  { path:'/admin/attendance',title:'考勤管理',role:'ADMIN' },
  { path:'/admin/leaves',title:'请假审批',role:'ADMIN' },
  { path:'/admin/payroll',title:'薪资管理',role:'ADMIN' },
  { path:'/admin/tasks',title:'制琴任务管理',role:'ADMIN' },
  { path:'/admin/reports',title:'统计报表',role:'ADMIN' },
  { path:'/admin/settings',title:'系统设置',role:'ADMIN' },
]
const employee: Menu[] = [
  {path:'/employee/profile',title:'个人信息',role:'EMPLOYEE',affix:true},
  {path:'/employee/attendance',title:'个人考勤',role:'EMPLOYEE'},
  {path:'/employee/leaves',title:'请假申请',role:'EMPLOYEE'},
  {path:'/employee/payroll',title:'我的工资',role:'EMPLOYEE'},
  {path:'/employee/tasks',title:'我的任务',role:'EMPLOYEE'},
  {path:'/employee/settings',title:'账号设置',role:'EMPLOYEE'},
]
export function menusFor(role:string):Menu[] {
  if(role==='EMPLOYEE') return employee
  return phase<3 ? admin.filter(m=>!['/admin/tasks','/admin/reports'].includes(m.path)&&(phase>1||!['/admin/leaves','/admin/payroll'].includes(m.path))):admin
}
export function homeFor(role:string) { return role==='EMPLOYEE'?'/employee/profile':'/admin/dashboard' }
