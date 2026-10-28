<script setup>
import {ref,reactive,onActivated,computed} from 'vue'
import {http} from '../api/http'
import {download} from '../api/download'
import Chart from '../components/Chart.vue'
const now=new Date(),filter=reactive({type:'departments',month:`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`}),rows=ref([]),busy=ref(false)
const names={departments:'部门分布',attendance:'月度考勤',payroll:'工资支出',production:'制琴任务完成量'}
const fields={departments:[['department','部门'],['active_count','在职人数']],attendance:[['name','员工姓名'],['department_id','部门编号'],['normal','正常'],['late','迟到'],['early_leave','早退'],['absent','缺勤'],['leave','请假']],payroll:[['department','部门'],['generated_total','已生成工资支出（元）'],['paid_total','已发放工资支出（元）']],production:[['month','月份'],['completed_tasks','完成任务数'],['completed_quantity','完成制作数量']]}
async function load(){busy.value=true;try{rows.value=(await http.get('/reports/'+filter.type,{params:{month:filter.month}})).data}catch{}finally{busy.value=false}}
const option=computed(()=>{
 if(filter.type==='departments')return{tooltip:{trigger:'item'},series:[{type:'pie',radius:'65%',data:rows.value.map(r=>({name:r.department,value:r.active_count}))}]}
 const columns=fields[filter.type],keys=filter.type==='attendance'?columns.slice(2):columns.slice(1)
 return {tooltip:{trigger:'axis'},legend:{},xAxis:{type:'category',data:rows.value.map(r=>r.name||r.department||r.month)},yAxis:{type:'value'},series:keys.map(([key,name])=>({name,type:'bar',data:rows.value.map(r=>r[key])}))}
})
onActivated(load)
</script>
<template><div class="page-title"><div><h1>统计报表</h1><p>图表与导出均来自数据库聚合；工资分别统计已生成与已发放金额。</p></div><el-button @click="download('/reports/export',filter,names[filter.type])">导出 Excel</el-button></div><el-card shadow="never"><el-form inline class="filters"><el-form-item label="报表类型"><el-select v-model="filter.type" @change="load"><el-option v-for="(label,value) in names" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item label="月份"><el-date-picker v-model="filter.month" type="month" value-format="YYYY-MM" :clearable="false"/></el-form-item><el-button @click="load">查询</el-button></el-form><div v-loading="busy"><Chart v-if="rows.length" :option="option"/><el-empty v-else description="暂无统计数据"/><el-table :data="rows"><el-table-column v-for="[key,label] in fields[filter.type]" :key="key" :prop="key" :label="label"/></el-table></div></el-card></template>
