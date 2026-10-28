<script setup lang="ts">
import {ref,computed,onMounted,watch,inject} from 'vue'
import {http,allRows} from '../api/http'
const props=defineProps<{personal:boolean;employeeId?:number;search?:string}>()
const employees=ref<any[]>([]),page=ref(1),active=inject<any>('workspace-active',ref(true))
async function load(){employees.value=props.personal?[(await http.get('/me/employee')).data]:await allRows('/employees')}
const filtered=computed(()=>employees.value.filter(e=>(!props.employeeId||e.id===props.employeeId)&&(!props.search||e.name.includes(props.search)||e.employee_no.includes(props.search))))
const activeTotal=computed(()=>{
 const cents=employees.value.filter(e=>e.status==='ACTIVE').reduce((sum,e)=>{const [whole,fraction='']=String(e.base_salary||'0').split('.');return sum+BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'))},0n)
 return `${cents/100n}.${String(cents%100n).padStart(2,'0')}`
})
watch(()=>[props.employeeId,props.search],()=>page.value=1)
onMounted(load);watch(active,(value:boolean)=>{if(value)load()})
</script>
<template><el-card class="v3-section" shadow="never"><template #header><div class="card-title"><span>税前月基本工资 · 档案参考</span><el-button text @click="load">刷新基本工资</el-button></div></template><p class="v3-note">按员工档案保存的月基本工资。此数值不等于某个工资月份的最终实发金额，不包含奖金、扣款及税费计算。</p><template v-if="personal"><strong class="base-salary-amount">¥ {{employees[0]?.base_salary||'0.00'}}</strong></template><template v-else><div class="v3-toolbar"><el-tag>在职 {{employees.filter(e=>e.status==='ACTIVE').length}} 人</el-tag><el-tag type="info">离职 {{employees.filter(e=>e.status==='LEFT').length}} 人</el-tag><strong>在职月基本工资合计：¥ {{activeTotal}}</strong></div><el-table :data="filtered.slice((page-1)*10,page*10)"><el-table-column prop="employee_no" label="工号" width="75"/><el-table-column prop="name" label="姓名"/><el-table-column prop="department_name" label="部门" min-width="130"/><el-table-column prop="position_name" label="职位" min-width="130"/><el-table-column prop="grade" label="职级" width="80"/><el-table-column prop="base_salary" label="税前月基本工资（元）" min-width="180"/><el-table-column label="状态"><template #default="{row}">{{row.status==='ACTIVE'?'在职':'离职前基本工资'}}</template></el-table-column></el-table><el-pagination v-if="filtered.length>10" class="v3-pagination" layout="prev,pager,next,total" :total="filtered.length" :page-size="10" v-model:current-page="page"/></template></el-card></template>
<style scoped>.base-salary-amount{font-size:30px;color:#25745a}</style>
