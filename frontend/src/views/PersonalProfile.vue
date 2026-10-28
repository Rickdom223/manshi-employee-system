<script setup>
import {ref,onActivated} from 'vue'
import {http} from '../api/http'
import {ElMessage} from 'element-plus'
import {useDirty} from '../stores/dirty'
import {useTabsStore} from '../stores/tabs'
const tabs=useTabsStore()
const employee=ref(null),phone=ref(''),loading=ref(true)
const resetDirty=useDirty(()=>phone.value,()=>!loading.value)
async function load(){if(tabs.dirty['/employee/profile'])return;loading.value=true;try{employee.value=(await http.get('/employee/me')).data;phone.value=employee.value.phone;await Promise.resolve();resetDirty()}catch{}finally{loading.value=false}}
async function save(){try{await http.patch('/employee/me',{phone:phone.value});resetDirty();ElMessage.success('联系方式已保存')}catch{}}
onActivated(load)
</script>
<template><div class="page-title"><div><h1>个人信息</h1><p>本人档案只读，可维护自己的联系方式。</p></div></div><el-card v-loading="loading" shadow="never"><el-descriptions v-if="employee" :column="2" border><el-descriptions-item label="员工编号">{{employee.employee_code}}</el-descriptions-item><el-descriptions-item label="姓名">{{employee.name}}</el-descriptions-item><el-descriptions-item label="部门">{{employee.department_name}}</el-descriptions-item><el-descriptions-item label="岗位">{{employee.position_name}}</el-descriptions-item><el-descriptions-item label="入职日期">{{employee.hire_date}}</el-descriptions-item><el-descriptions-item label="状态">在职</el-descriptions-item></el-descriptions><el-form label-position="top" class="settings-form" style="margin-top:24px"><el-form-item label="本人手机号"><el-input v-model="phone" maxlength="11"/></el-form-item><el-button type="primary" @click="save">保存联系方式</el-button></el-form></el-card></template>
