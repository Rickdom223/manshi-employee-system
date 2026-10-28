<script setup lang="ts">
import {useRouter} from 'vue-router'
import {ref,watch,nextTick} from 'vue'
import {useTabsStore} from '../stores/tabs'
const store=useTabsStore(),router=useRouter()
const bar=ref<HTMLElement>()
watch(()=>[store.activePath,store.tabs.length],async()=>{await nextTick();bar.value?.querySelector('.workspace-tab.active')?.scrollIntoView({block:'nearest',inline:'nearest'})})
async function close(path:string){const next=await store.closeTab(path);if(next)await router.push(next)}
</script>
<template><nav ref="bar" class="workspace-tabs" role="tablist" aria-label="工作区标签"><div v-for="tab in store.tabs" :key="tab.path" class="workspace-tab" :class="{active:store.activePath===tab.path}" :data-path="tab.path"><button role="tab" :aria-label="tab.title" :aria-selected="store.activePath===tab.path" @click="router.push(tab.path)">{{tab.title}}<span v-if="store.dirty[tab.path]" class="dirty-dot"> •</span></button><button v-if="tab.closable" class="tab-close" :aria-label="'关闭'+tab.title" @click.stop="close(tab.path)">×</button></div></nav></template>
