import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { menusFor, homeFor } from '../router/v3menus'
export type Tab = { path:string;title:string;closable:boolean }
export const useTabsStore = defineStore('workspace-tabs',()=>{
  const tabs=ref<Tab[]>([]), activePath=ref(''), identity=ref(''), role=ref('')
  const dirty=ref<Record<string,boolean>>({}), scroll=ref<Record<string,number>>({})
  const key=()=>`manshi-tabs:${identity.value}`
  function resetTabs() {
    for(let i=sessionStorage.length-1;i>=0;i--) { const k=sessionStorage.key(i);if(k?.startsWith('manshi-tabs:'))sessionStorage.removeItem(k) }
    tabs.value=[];activePath.value='';identity.value='';dirty.value={};scroll.value={}
  }
  function persist() { if(identity.value)sessionStorage.setItem(key(),JSON.stringify({paths:tabs.value.map(t=>t.path),activePath:activePath.value})) }
  function openTab(path:string) {
    const menu=menusFor(role.value).find(m=>m.path===path)
    if(!menu)return false
    if(!tabs.value.some(t=>t.path===path))tabs.value.push({path,title:menu.title,closable:!menu.affix})
    activePath.value=path;persist();return true
  }
  function restoreTabs(user:{id:number;role:string},current:string) {
    const next=`${user.id}:${user.role}`
    if(identity.value&&identity.value!==next)resetTabs()
    identity.value=next;role.value=user.role
    for(let i=sessionStorage.length-1;i>=0;i--){const other=sessionStorage.key(i);if(other?.startsWith('manshi-tabs:')&&other!==key())sessionStorage.removeItem(other)}
    let paths:string[]=[]
    try { const saved=JSON.parse(sessionStorage.getItem(key())||'{}');if(Array.isArray(saved.paths))paths=saved.paths.filter((p:unknown)=>typeof p==='string') } catch {}
    tabs.value=[];openTab(homeFor(role.value));paths.forEach(openTab)
    if(!openTab(current))openTab(homeFor(role.value))
    persist()
  }
  function activateTab(path:string) {return openTab(path)}
  async function closeTab(path:string) {
    const index=tabs.value.findIndex(t=>t.path===path)
    if(index<0||!tabs.value[index].closable)return null
    if(dirty.value[path]) {try {await ElMessageBox.confirm('当前页面有未保存的修改，确定关闭吗？','关闭标签',{type:'warning',confirmButtonText:'确定关闭',cancelButtonText:'取消'})}catch{return null} }
    const current=activePath.value===path
    tabs.value.splice(index,1);delete dirty.value[path];delete scroll.value[path]
    if(current)activePath.value=tabs.value[index-1]?.path||tabs.value[index]?.path||homeFor(role.value)
    persist();return current?activePath.value:''
  }
  return {tabs,activePath,identity,role,dirty,scroll,openTab,activateTab,closeTab,restoreTabs,resetTabs}
})
