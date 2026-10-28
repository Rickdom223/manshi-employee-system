import {watch,onUnmounted} from 'vue'
import {useRoute} from 'vue-router'
import {useTabsStore} from './tabs'
export function useDirty(source:()=>unknown, enabled:()=>boolean=()=>true){
  const store=useTabsStore(),path=useRoute().path
  const stop=watch(source,()=>{if(enabled())store.dirty[path]=true},{deep:true})
  onUnmounted(()=>{stop();delete store.dirty[path]})
  return ()=>{store.dirty[path]=false}
}
