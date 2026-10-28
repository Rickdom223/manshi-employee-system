<script setup lang="ts">
import {ref} from 'vue'
import {http} from '../api/http'
const props=defineProps<{employee:any}>(),data=ref<any>(),show=ref(false)
async function open(){data.value=(await http.get(`/employees/${props.employee.id}`)).data;show.value=true}
const labels:Record<string,string>={employee_no:'工号',name:'姓名',department_name:'部门',position_name:'职位',grade:'职级',hire_date:'入职日期',status:'在职状态',left_date:'离职日期',account_username:'登录用户名',phone:'电话',base_salary:'税前月基本工资（元）',remarks:'备注'}
</script>
<template><el-button text @click="open">详情</el-button><el-dialog v-model="show" title="员工档案详情" width="620px" destroy-on-close><el-descriptions v-if="data" :column="2" border><el-descriptions-item v-for="(label,key) in labels" :key="key" :label="label">{{key==='status'?(data[key]==='ACTIVE'?'在职':'离职'):data[key]||'—'}}</el-descriptions-item></el-descriptions></el-dialog></template>
