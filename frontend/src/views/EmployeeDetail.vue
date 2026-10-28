<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http, allRows } from '../api/http'
import EmployeeForm from '../components/EmployeeForm.vue'
import ArchiveDialog from '../components/ArchiveDialog.vue'
const props=defineProps({employeeId:Number})
const id = props.employeeId || useRoute().params.id
const employee = ref(null), busy = ref(false), failed = ref(false), saving = ref(false), editing = ref(false), archive = ref(false)
const skills = ref([]), departments = ref([]), positions = ref([])
const binding = reactive({ skill_id: null, proficiency: 'basic' })
const levels = { basic: '基础', skilled: '熟练', expert: '精通' }
const available = computed(() => skills.value.filter(s => s.is_active && !employee.value?.skills.some(link => link.skill_id === s.id)))
async function load() { busy.value = true; failed.value = false; try { employee.value = (await http.get(`/employees/${id}`)).data } catch { failed.value = true } finally { busy.value = false } }
async function bind() {
  if (!binding.skill_id) { ElMessage.warning('请选择技能'); return }
  saving.value = true
  try { await http.post(`/employees/${id}/skills`, binding); binding.skill_id = null; ElMessage.success('技能已添加'); await load() } catch {} finally { saving.value = false }
}
async function proficiency(row, value) { try { await http.patch(`/employees/${id}/skills/${row.skill_id}`, { proficiency: value }); await load(); ElMessage.success('熟练度已更新') } catch {} }
async function remove(row) {
  try { await ElMessageBox.confirm(`确认解除「${row.skill_name}」关联？技能字典会保留。`, '解除技能关联', { type: 'warning' }) } catch { return }
  try { await http.delete(`/employees/${id}/skills/${row.skill_id}`); ElMessage.success('已解除关联'); await load() } catch {}
}
async function openEdit() { try { [departments.value, positions.value] = await Promise.all(['/departments', '/positions'].map(allRows)); editing.value = true } catch {} }
async function saved() { editing.value = false; archive.value = false; await load() }
async function account(reset=false){try{const r=await ElMessageBox.prompt(reset?'设置新密码（8–10位，包含大小写字母和数字）':'设置员工初始密码（8–10位，包含大小写字母和数字）',reset?'重置员工密码':'开通登录账号',{inputType:'password'});await http.post(`/employees/${id}/${reset?'reset-password':'enable-account'}`,{initial_password:r.value});ElMessage.success('账号操作成功');load()}catch{}}
onMounted(async () => { await load(); try { skills.value = await allRows('/skills') } catch {} })
</script>
<template><div class="page-title"><div><router-link class="back-link" to="/employees">← 返回员工档案</router-link><h1>{{ employee?.full_name || '员工详情' }}</h1><p>档案资料与制琴技能</p></div><div v-if="employee"><el-button v-if="employee.status === 'active'" @click="account(!!employee.account_active)">{{employee.account_active ? '重置员工密码' : '开通登录账号'}}</el-button><el-button @click="openEdit">编辑资料</el-button><el-button v-if="employee.status === 'active'" type="danger" plain @click="archive = true">离职归档</el-button></div></div><div v-loading="busy" class="page-body"><el-result v-if="failed" icon="error" title="档案加载失败或不存在"><template #extra><el-button @click="load">重试</el-button></template></el-result><template v-if="employee"><el-card shadow="never"><template #header><div class="card-title"><b>基本信息</b><el-tag :type="employee.status === 'active' ? 'success' : 'info'">{{ employee.status === 'active' ? '在职' : '离职' }}</el-tag></div></template><el-descriptions :column="3" border><el-descriptions-item label="工号">{{ employee.employee_no }}</el-descriptions-item><el-descriptions-item label="部门">{{employee.department_name}}</el-descriptions-item><el-descriptions-item label="岗位">{{employee.position_name}}</el-descriptions-item><el-descriptions-item label="入职日期">{{employee.hire_date}}</el-descriptions-item><el-descriptions-item label="联系电话">{{employee.phone || '未填写'}}</el-descriptions-item><el-descriptions-item label="离职日期">{{employee.resignation_date || '—'}}</el-descriptions-item><el-descriptions-item label="备注" :span="3">{{employee.remark || '未填写'}}</el-descriptions-item></el-descriptions></el-card>
<el-card class="skills-card" shadow="never"><template #header><div class="card-title"><b>制琴技能</b><span class="muted">一个岗位，多项专长</span></div></template><el-form inline class="filters" @submit.prevent="bind"><el-form-item label="添加技能"><el-select v-model="binding.skill_id" placeholder="选择尚未关联的技能"><el-option v-for="s in available" :key="s.id" :value="s.id" :label="s.name"/></el-select></el-form-item><el-form-item label="熟练度"><el-select v-model="binding.proficiency"><el-option v-for="(label, value) in levels" :key="value" :label="label" :value="value"/></el-select></el-form-item><el-form-item><el-button type="primary" @click="bind" :loading="saving">添加技能</el-button></el-form-item></el-form><el-table :data="employee.skills" empty-text="尚未关联技能"><el-table-column prop="skill_code" label="技能编码"/><el-table-column prop="skill_name" label="技能名称"/><el-table-column label="字典状态"><template #default="{row}"><el-tag :type="row.is_active ? 'success' : 'info'">{{row.is_active ? '启用' : '停用（历史关联）'}}</el-tag></template></el-table-column><el-table-column label="熟练度" width="160"><template #default="{row}"><el-select :model-value="row.proficiency" @change="value => proficiency(row, value)"><el-option v-for="(label, value) in levels" :key="value" :label="label" :value="value"/></el-select></template></el-table-column><el-table-column label="操作" width="110"><template #default="{row}"><el-button link type="danger" @click="remove(row)">解除关联</el-button></template></el-table-column></el-table></el-card></template></div>
<WorkspaceDialog v-model="editing" title="编辑员工" width="640px" destroy-on-close :close-on-click-modal="false"><EmployeeForm v-if="editing" :employee="employee" :departments="departments" :positions="positions" @saved="saved" @cancel="editing = false"/></WorkspaceDialog><WorkspaceDialog v-model="archive" title="离职归档确认" width="500px" destroy-on-close><ArchiveDialog v-if="archive" :employee="employee" @saved="saved" @cancel="archive = false"/></WorkspaceDialog></template>
