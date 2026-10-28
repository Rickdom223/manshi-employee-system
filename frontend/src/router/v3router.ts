import {createRouter,createWebHistory} from 'vue-router'
import {defineComponent,h} from 'vue'
import {auth} from '../stores/auth'
import {http} from '../api/http'
import {pinia} from '../stores/pinia'
import {useTabsStore} from '../stores/tabs'
import {allMenus,menusFor,homeFor} from './v3menus'
import Login from '../views/Login.vue'
import Page from '../views/V3Page.vue'
export const pageComponents=Object.fromEntries(allMenus.map(m=>[m.path,defineComponent({name:m.path,setup:()=>()=>h(Page,{mode:m.path,title:m.title})})]))
export const router=createRouter({history:createWebHistory(),routes:[{path:'/login',component:Login},...allMenus.map(m=>({path:m.path,component:pageComponents[m.path]})),{path:'/',redirect:()=>homeFor(auth.user?.role||'EMPLOYEE')},{path:'/:pathMatch(.*)*',component:defineComponent({setup:()=>()=>h('main','页面不存在')})}]})
router.beforeEach(async to=>{
 if(!auth.ready){try{auth.user=(await http.get('/auth/me',{silent:true})).data;auth.csrf=auth.user.csrf_token}catch{}auth.ready=true}
 if(!auth.user)return to.path==='/login'?true:'/login'
 if(to.path==='/login')return homeFor(auth.user.role)
 const tabs=useTabsStore(pinia)
 if(!menusFor(auth.user.role).some(m=>m.path===to.path))return homeFor(auth.user.role)
 if(tabs.identity!==`${auth.user.id}:${auth.user.role}`)tabs.restoreTabs(auth.user,to.path)
 tabs.openTab(to.path)
})
window.addEventListener('session-expired',()=>router.replace('/login'))
