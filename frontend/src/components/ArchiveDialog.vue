<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '../api/http'
const props = defineProps({ employee: Object })
const emit = defineEmits(['saved', 'cancel'])
const date = ref(''), busy = ref(false)
async function archive() {
  if (!date.value) { ElMessage.warning('请选择离职日期'); return }
  busy.value = true
  try { await http.post(`/employees/${props.employee.id}/archive`, { resignation_date: date.value }); ElMessage.success('员工已归档'); emit('saved') }
  catch {} finally { busy.value = false }
}
</script>
<template><el-alert :closable="false" type="warning" title="归档后状态变为离职，员工档案与技能记录会保留。本版不提供恢复在职操作。"/><p>确认将「{{ employee.full_name }}」归档？</p><el-form label-position="top"><el-form-item label="离职日期（不得早于入职日期）" required><el-date-picker v-model="date" value-format="YYYY-MM-DD" placeholder="选择离职日期" /></el-form-item></el-form><div class="dialog-actions"><el-button @click="emit('cancel')">取消</el-button><el-button type="danger" :loading="busy" @click="archive">确认归档</el-button></div></template>
