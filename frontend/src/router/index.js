import {createRouter,createWebHistory} from 'vue-router'
import {auth} from '../stores/auth'
import {http} from '../api/http'
import {useTabsStore} from '../stores/tabs'
import {pinia} from '../stores/pinia'
import {menusFor,homeFor} from './menus'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Employees from '../views/Employees.vue'
import Organization from '../views/Organization.vue'
import Attendance from '../views/Attendance.vue'
import Settings from '../views/Settings.vue'
import NotFound from '../views/NotFound.vue'
import Leaves from '../views/Leaves.vue'
import Payroll from '../views/Payroll.vue'
import PersonalProfile from '../views/PersonalProfile.vue'
import MyTasks from '../views/MyTasks.vue'
import Tasks from '../views/Tasks.vue'
import Reports from '../views/Reports.vue'

export const pageComponents={
  '/admin/dashboard':Dashboard,'/admin/employees':Employees,'/admin/departments':Organization,
  '/admin/attendance':Attendance,'/admin/settings':Settings,
  '/admin/leaves':Leaves,'/admin/payroll':Payroll,
  '/admin/tasks':Tasks,'/admin/reports':Reports,
  '/employee/profile':PersonalProfile,'/employee/attendance':Attendance,
  '/employee/leaves':Leaves,'/employee/payroll':Payroll,'/employee/tasks':MyTasks,'/employee/settings':Settings,
}
const routes=[{path:'/login',component:Login},
  ...Object.entries(pageComponents).map(([path,component])=>({path,component,meta:menusFor(path.startsWith('/admin')?'ADMIN':'EMPLOYEE').find(m=>m.path===path)})),
  {path:'/',redirect:()=>homeFor(auth.user?.role||'ADMIN')},
  {path:'/employees',redirect:'/admin/employees'},
  {path:'/employees/:id',redirect:to=>({path:'/admin/employees',query:{detail:to.params.id}})},
  {path:'/departments',redirect:'/admin/departments'},
  {path:'/positions',redirect:to=>({path:'/admin/departments',query:{...to.query,tab:'positions'}})},
  {path:'/skills',redirect:()=>({path:'/admin/departments',query:{tab:'skills'}})},
  {path:'/:pathMatch(.*)*',component:NotFound}]
export const router=createRouter({history:createWebHistory(),routes})
router.beforeEach(async to=>{
  if(to.path.length>1&&to.path.endsWith('/'))return{path:to.path.replace(/\/+$/,''),query:to.query,replace:true}
  if(!auth.ready){try{auth.user=(await http.get('/auth/me',{silent:true})).data;auth.csrf=auth.user.csrf_token}catch{}auth.ready=true}
  if(!auth.user)return to.path==='/login'?true:'/login'
  if(to.path==='/login')return homeFor(auth.user.role)
  const tabs=useTabsStore(pinia),allowed=menusFor(auth.user.role)
  if(to.path.startsWith('/admin/')&&auth.user.role!=='ADMIN')return homeFor(auth.user.role)
  if(to.path.startsWith('/employee/')&&auth.user.role!=='EMPLOYEE')return homeFor(auth.user.role)
  if(!tabs.identity)tabs.restoreTabs(auth.user,to.path)
  if(allowed.some(m=>m.path===to.path))tabs.openTab(to.path)
})
window.addEventListener('session-expired',()=>router.replace('/login'))
