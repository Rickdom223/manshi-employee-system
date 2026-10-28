<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'
import {useDirty} from '../stores/dirty'
const props = defineProps({ employee: Object, departments: Array, positions: Array })
const emit = defineEmits(['saved', 'cancel'])
const original = props.employee
const model = reactive({ employee_no: '', full_name: '', department_id: null, position_id: null, hire_date: '', phone: '', remark: '', birth_date:null,base_salary:'0.00',create_account:false,initial_password:'',...original })
const resetDirty=useDirty(()=>model)
const busy = ref(false), form = ref()
const required = field => ({ required: true, message: '请填写' + field, trigger: 'change' })
const rules = { employee_no: [required('工号'), { pattern: /^[A-Za-z0-9_-]{2,20}$/, message: '工号为2–20位英数字、横线或下划线' }], full_name: [required('姓名'), { max: 50, message: '姓名最多50字' }], department_id: [required('部门')], position_id: [required('岗位')], hire_date: [required('入职日期')] }
const departments = computed(() => props.departments.filter(d => d.is_active || d.id === original?.department_id))
const positions = computed(() => props.positions.filter(p => p.department_id === model.department_id && (p.is_active || p.id === original?.position_id)))
watch(() => model.department_id, () => { model.position_id = null })
async function save() {
  if (!await form.value.validate().catch(() => false)) return
  const body = { full_name: model.full_name.trim(), department_id: model.department_id, position_id: model.position_id, hire_date: model.hire_date, phone: model.phone?.trim() || null, remark: model.remark?.trim() || null,birth_date:model.birth_date,base_salary:model.base_salary }
  if (!original) {body.create_account=model.create_account;if(model.create_account)body.initial_password=model.initial_password}
  busy.value = true
  try {
    const result = original ? await http.patch(`/employees/${original.id}`, body) : await http.post('/employees', body)
    resetDirty();ElMessage.success('员工档案已保存'); emit('saved', result.data)
  } catch {} finally { busy.value = false }
}
</script>
<template><el-form ref="form" :model="model" :rules="rules" label-position="top" @submit.prevent="save"><div class="form-grid"><el-form-item label="工号" ><el-input v-model="model.employee_no" disabled maxlength="20" placeholder="保存后自动生成" /></el-form-item><el-form-item label="姓名" prop="full_name"><el-input v-model="model.full_name" maxlength="50" /></el-form-item><el-form-item label="部门" prop="department_id"><el-select v-model="model.department_id" placeholder="选择部门"><el-option v-for="d in departments" :key="d.id" :value="d.id" :label="d.name + (d.is_active ? '' : '（停用历史）')" :disabled="!d.is_active && d.id !== original?.department_id" /></el-select></el-form-item><el-form-item label="主要岗位" prop="position_id"><el-select v-model="model.position_id" placeholder="先选择部门"><el-option v-for="p in positions" :key="p.id" :value="p.id" :label="p.name + (p.is_active ? '' : '（停用历史）')" /></el-select></el-form-item><el-form-item label="入职日期" prop="hire_date"><el-date-picker v-model="model.hire_date" value-format="YYYY-MM-DD" type="date" placeholder="选择入职日期" /></el-form-item><el-form-item label="手机号" prop="phone" required><el-input v-model="model.phone" maxlength="25" placeholder="可留空" /></el-form-item><el-form-item label="基本工资（元）" required><el-input v-model="model.base_salary"/></el-form-item><el-form-item label="出生日期"><el-date-picker v-model="model.birth_date" value-format="YYYY-MM-DD"/></el-form-item><el-form-item v-if="!original" label="同时创建登录账号"><el-switch v-model="model.create_account"/></el-form-item><el-form-item v-if="!original && model.create_account" label="初始密码（8–10位大小写及数字）" required><el-input v-model="model.initial_password" type="password" show-password/></el-form-item></div><el-form-item label="备注"><el-input v-model="model.remark" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item><div class="dialog-actions"><el-button @click="emit('cancel')">取消</el-button><el-button type="primary" native-type="submit" :loading="busy">保存档案</el-button></div></el-form></template>
