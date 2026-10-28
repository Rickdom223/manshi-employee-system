<script setup>
import {computed} from 'vue'
import {useRoute,useRouter} from 'vue-router'
import {ElMessageBox} from 'element-plus'
import {auth,clearAuth} from './stores/auth'
import {http} from './api/http'
import {menusFor} from './router/menus'
import {pageComponents} from './router'
import {useTabsStore} from './stores/tabs'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import TabPane from './components/TabPane.vue'
const route=useRoute(),router=useRouter(),tabs=useTabsStore()
const nav=computed(()=>menusFor(auth.user?.role||'ADMIN'))
async function logout(){try{await ElMessageBox.confirm('确认退出当前账号？未保存的输入将被清除。','退出登录',{type:'warning'})}catch{return}try{await http.post('/auth/logout');clearAuth();router.replace('/login')}catch{}}
</script>
<template><router-view v-if="!auth.user||route.path==='/login'"/><div v-else class="shell" :key="auth.user.id"><aside><div class="brand"><span class="brand-mark">满</span><div>满氏吉他制琴<small>企业员工管理系统</small></div></div><div class="nav-caption">{{auth.user.role==='ADMIN'?'组织与业务':'个人工作台'}}</div><router-link v-for="(menu,i) in nav" :key="menu.path" :to="menu.path" :class="{selected:route.path===menu.path}"><span class="nav-number">{{String(i+1).padStart(2,'0')}}</span>{{menu.title}}</router-link><div class="aside-note">所有业务数据持久化保存<br>满氏吉他制琴有限公司</div></aside><section class="workspace"><header><span>满氏吉他制琴有限公司企业员工管理系统</span><div><span class="account">{{auth.user.display_name||auth.user.username}}</span><el-button text @click="logout">退出登录</el-button></div></header><WorkspaceTabs/><div class="workspace-content"><TabPane v-for="tab in tabs.tabs" :key="tab.path" :path="tab.path" :active="route.path===tab.path" :component="pageComponents[tab.path]"/><router-view v-if="!pageComponents[route.path]"/></div></section></div></template>
