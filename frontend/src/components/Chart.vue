<script setup lang="ts">
import {ref,onMounted,onActivated,onBeforeUnmount,watch,nextTick} from 'vue'
import * as echarts from 'echarts'
const props=defineProps<{option:any}>(),root=ref<HTMLElement>()
let chart:echarts.ECharts|undefined,observer:ResizeObserver|undefined
function render(){chart?.setOption(props.option,true);chart?.resize()}
onMounted(()=>{if(root.value){chart=echarts.init(root.value);observer=new ResizeObserver(()=>chart?.resize());observer.observe(root.value);render()}})
onActivated(async()=>{await nextTick();render()})
watch(()=>props.option,render,{deep:true})
onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose()})
</script>
<template><div ref="root" class="echart" style="height:310px;width:100%" role="img" aria-label="数据库统计图表"/></template>
