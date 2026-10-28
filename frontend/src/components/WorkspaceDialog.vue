<script setup lang="ts">
import {inject,ref,useAttrs,computed,onMounted} from 'vue'
import {ElDialog,ElDrawer} from 'element-plus'
defineOptions({inheritAttrs:false})
const props=defineProps<{modelValue:boolean;kind?:string}>(),emit=defineEmits(['update:modelValue','close','closed'])
const active=inject('workspace-active',ref(true)),attrs=useAttrs()
const host=ref<HTMLElement|null>(null)
onMounted(()=>{host.value=document.querySelector('.workspace-content') as HTMLElement||document.body})
const forwarded=computed(()=>Object.fromEntries(Object.entries(attrs).filter(([k])=>!['destroy-on-close','append-to'].includes(k))))
function change(value:boolean){if(active.value)emit('update:modelValue',value)}
</script>
<template><component v-if="host" :is="kind==='drawer'?ElDrawer:ElDialog" v-bind="forwarded" :model-value="modelValue && active" :destroy-on-close="false" :append-to="host" @update:model-value="change" @close="active && emit('close')" @closed="active && emit('closed')"><slot/><template v-if="$slots.footer" #footer><slot name="footer"/></template></component></template>
