<script setup lang="ts">
import {ref,onMounted,inject,watch} from 'vue'
import {http} from '../api/http'
const attendance=ref<any>(),leaves=ref<any[]>([]),active=inject<any>('workspace-active',ref(true))
const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date())
async function load(){attendance.value=(await http.get('/me/attendance',{params:{month:today.slice(0,7)}})).data;leaves.value=(await http.get('/me/leaves',{params:{page:1,page_size:5}})).data}
onMounted(load);watch(active,(v:boolean)=>{if(v)load()})
</script>
<template><div class="v3-section"><h3>今日打卡 · {{today}}</h3><div class="v3-cards"><el-card>上班打卡<strong style="font-size:20px">{{attendance?.daily?.find((d:any)=>d.date===today)?.punch_in?.slice(11)||'未打卡'}}</strong></el-card><el-card>下班打卡<strong style="font-size:20px">{{attendance?.daily?.find((d:any)=>d.date===today)?.punch_out?.slice(11)||'未打卡'}}</strong></el-card></div><h3>最近请假</h3><el-table :data="leaves"><el-table-column prop="leave_type" label="类型"/><el-table-column prop="start_date" label="开始日期"/><el-table-column prop="end_date" label="结束日期"/><el-table-column label="状态"><template #default="{row}">{{({PENDING:'待审批',APPROVED:'已通过',REJECTED:'已驳回',CANCELLED:'已撤销'} as any)[row.status]}}</template></el-table-column></el-table></div></template>
