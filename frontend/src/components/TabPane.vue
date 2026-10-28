<script setup lang="ts">
import {ref,nextTick,onMounted,watch,provide,computed} from 'vue'
import {useTabsStore} from '../stores/tabs'
const props=defineProps<{active:boolean;path:string;component:any}>()
const store=useTabsStore(),container=ref<HTMLElement>()
provide('workspace-active',computed(()=>props.active))
watch(()=>props.active,async active=>{if(active){await nextTick();if(container.value)container.value.scrollTop=store.scroll[props.path]||0}else if(container.value)store.scroll[props.path]=container.value.scrollTop})
</script>
<template><section v-show="active" ref="container" class="tab-pane" :aria-hidden="!active"><KeepAlive><component :is="component" v-if="active"/></KeepAlive></section></template>
