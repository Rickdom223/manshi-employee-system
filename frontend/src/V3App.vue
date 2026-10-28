<script setup lang="ts">
import {computed,onMounted,onUnmounted} from 'vue'
import {useRouter,useRoute} from 'vue-router'
import {auth,clearAuth} from './stores/auth'
import {http} from './api/http'
import {menusFor,roles} from './router/v3menus'
import {pageComponents} from './router/v3router'
import {useTabsStore} from './stores/tabs'
import WorkspaceTabs from './components/WorkspaceTabs.vue'
import TabPane from './components/TabPane.vue'
const router=useRouter(),route=useRoute(),tabs=useTabsStore()
const nav=computed(()=>menusFor(auth.user?.role||''))
async function logout(){await http.post('/auth/logout');clearAuth();router.replace('/login')}
let timer:ReturnType<typeof setInterval>
async function checkSession(){if(auth.user)try{const next=(await http.get('/auth/me',{silent:true})).data;if(next.role!==auth.user.role){tabs.resetTabs();auth.user=next;router.replace('/')}else{auth.user=next;auth.csrf=next.csrf_token}}catch{}}
onMounted(()=>{timer=setInterval(checkSession,30000);window.addEventListener('focus',checkSession)})
onUnmounted(()=>{clearInterval(timer);window.removeEventListener('focus',checkSession)})
</script>
<template><router-view v-if="!auth.user||route.path==='/login'"/><div v-else class="shell" :key="`${auth.user.id}:${auth.user.role}`"><aside><div class="brand"><span class="brand-mark">满</span><div>满氏吉他制琴<small>企业员工管理系统</small></div></div><div class="nav-caption">{{roles[auth.user.role]}}</div><router-link v-for="(m,i) in nav" :key="m.path" :to="m.path" :class="{selected:route.path===m.path}"><span class="nav-number">{{String(i+1).padStart(2,'0')}}</span>{{m.title}}</router-link><div class="aside-note">满氏吉他制琴有限公司<br>人员 · 组织 · 协作</div></aside><section class="workspace"><header><span>满氏吉他制琴有限公司企业员工管理系统</span><div><span>{{auth.user.display_name||auth.user.username}} · {{roles[auth.user.role]}}</span><el-button text @click="logout">退出登录</el-button></div></header><WorkspaceTabs/><div class="workspace-content"><TabPane v-for="tab in tabs.tabs" :key="tab.path" :path="tab.path" :active="route.path===tab.path" :component="pageComponents[tab.path]"/></div></section></div></template>
<style>aside{overflow-y:auto}aside>a{padding:10px 12px;flex-shrink:0}.brand{padding-bottom:24px}aside .nav-caption{margin-bottom:10px}.v3-toolbar{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}.v3-toolbar .el-input,.v3-toolbar .el-select{width:180px}.v3-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:20px 0}.v3-cards strong{display:block;font-size:30px;color:#25745a;margin-top:14px}.v3-section{margin:20px 0}.v3-pagination{margin-top:20px}.v3-note{color:#718077;font-size:13px;line-height:1.8}.v3-form .el-select,.v3-form .el-date-editor{width:100%}.v3-charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}@media(max-width:900px){.v3-charts{grid-template-columns:1fr}header>span{display:none}}</style>
