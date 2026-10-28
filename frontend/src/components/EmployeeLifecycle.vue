<script setup lang="ts">
import {ref} from 'vue'
import {http} from '../api/http'
import {ElMessage} from 'element-plus'
const props=defineProps<{employee:any}>(),emit=defineEmits(['changed'])
const show=ref(false),day=ref(''),note=ref(''),form=ref<any>()
async function save(){if(!await form.value.validate().catch(()=>false))return;const r=await http.post(`/employees/${props.employee.id}/${props.employee.status==='ACTIVE'?'leave':'rehire'}`,{event_date:day.value,note:note.value||null});show.value=false;ElMessage.success(r.message||'离职已办理，关联账号立即停用');emit('changed')}
</script>
<template><el-button text @click="show=true;day='';note=''">{{employee.status==='ACTIVE'?'办理离职':'办理复职'}}</el-button><el-dialog v-model="show" :title="employee.status==='ACTIVE'?'办理离职':'办理复职'" width="480px" append-to-body destroy-on-close><p class="v3-note">{{employee.status==='ACTIVE'?'离职将立即停用员工账号并撤销所有会话，保留业务历史。':'复职保留原账号与历史，角色恢复为普通员工；管理员核验后重新启用账号。'}}</p><el-form ref="form" :model="{day}" label-position="top" @submit.prevent="save"><el-form-item :label="employee.status==='ACTIVE'?'离职日期':'复职日期'" prop="day" :rules="[{required:true,message:'请选择日期'}]"><el-date-picker v-model="day" value-format="YYYY-MM-DD"/></el-form-item><el-form-item label="说明"><el-input v-model="note" type="textarea"/></el-form-item><div class="dialog-actions"><el-button @click="show=false">取消</el-button><el-button type="primary" native-type="submit">确认办理</el-button></div></el-form></el-dialog></template>
