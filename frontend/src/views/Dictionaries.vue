<script setup>
import { ref, reactive, computed, onMounted,onActivated,watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http, allRows } from '../api/http'
import {useDirty} from '../stores/dirty'
const props = defineProps({ type: String,departmentId:Number })
const emit=defineEmits(['positions'])
const router = useRouter(), route = useRoute()
const title = computed(() => ({ departments: '部门', positions: '岗位', skills: '技能' })[props.type])
const rows = ref([]), departments = ref([]), total = ref(0), busy = ref(false), saving = ref(false), failed = ref(false), dialog = ref(false), editing = ref(null), form = ref()
const filter = reactive({ page: 1, page_size: 10, department_id:props.departmentId || (route.query.department_id ? Number(route.query.department_id) : null) })
const model = reactive({ code: '', name: '', department_id: null, is_active: true,description:'' })
const resetDirty=useDirty(()=>model,()=>dialog.value)
const rules = { code: [{ required: true, message: '请输入编码' }, { pattern: /^[A-Za-z0-9_-]{2,20}$/, message: '编码为2–20位英数字、横线或下划线' }], name: [{ required: true, message: '请输入名称' }, { max: 50, message: '名称最多50字' }], department_id: [{ required: true, message: '请选择部门' }] }
async function load() { busy.value = true; failed.value = false; try { const result = await http.get('/' + props.type, { params: filter }); rows.value = result.data; total.value = result.total } catch { failed.value = true } finally { busy.value = false } }
async function open(row) { editing.value = row; Object.assign(model, { code: row?.code || '', name: row?.name || '', department_id: row?.department_id || props.departmentId || null, is_active: row?.is_active ?? true,description:row?.description||'' }); try { if (props.type === 'positions') departments.value = await allRows('/departments'); dialog.value = true } catch {} }
async function remove(row){try{await ElMessageBox.confirm('确定删除此资料？有历史关联时将拒绝删除。','删除确认',{type:'warning'})}catch{return}try{await http.delete(`/${props.type}/${row.id}`);ElMessage.success('已删除');load()}catch{}}
async function save() {
  if (!await form.value.validate().catch(() => false)) return
  const body = { code: model.code.trim()||undefined, name: model.name.trim(), is_active: model.is_active }
  if(props.type!=='skills')body.description=model.description.trim()||null
  if (props.type === 'positions') body.department_id = model.department_id
  saving.value = true
  try { if (editing.value) await http.patch(`/${props.type}/${editing.value.id}`, body); else await http.post('/' + props.type, body); ElMessage.success('资料已保存'); dialog.value = false;resetDirty(); await load() } catch {} finally { saving.value = false }
}
async function toggle(row) {
  try { await ElMessageBox.confirm(`确认${row.is_active ? '停用' : '启用'}「${row.name}」？停用后历史关联保留，新分配将受限。`, '状态调整', { type: 'warning' }) } catch { return }
  try { await http.patch(`/${props.type}/${row.id}`, { is_active: !row.is_active }); ElMessage.success('状态已更新'); await load() } catch {}
}
function search() { filter.page = 1; load() }
watch(()=>props.departmentId,value=>{if(props.type==='positions'){filter.department_id=value||null;search()}})
onActivated(async () => { await load(); if (props.type === 'positions') { try { departments.value = await allRows('/departments') } catch {} } })
</script>
<template><div class="page-title"><div><div class="eyebrow">{{type === 'skills' ? 'CRAFT & SKILLS' : 'ORGANIZATION'}}</div><h1>{{title}}管理</h1><p>{{type === 'skills' ? '维护制琴技能字典，在员工详情中分配和调整专长。' : '维护清晰的组织结构，停用资料后仍保留历史关联。'}}</p></div><el-button type="primary" @click="open(null)">＋ 新增{{title}}</el-button></div><el-card shadow="never"><el-form v-if="type === 'positions'" inline class="filters"><el-form-item label="所属部门"><el-select v-model="filter.department_id" clearable placeholder="全部部门" @change="search"><el-option v-for="d in departments" :key="d.id" :value="d.id" :label="d.name"/></el-select></el-form-item></el-form><el-alert v-if="failed" type="error" :closable="false" title="资料加载失败"><el-button @click="load">重试</el-button></el-alert><el-table v-loading="busy" :data="rows" empty-text="还没有资料，请点击右上角新增" stripe><el-table-column prop="code" label="编码" min-width="130"/><el-table-column prop="name" :label="title + '名称'" min-width="170"/><el-table-column v-if="type === 'positions'" label="所属部门" min-width="150"><template #default="{row}">{{departments.find(d => d.id === row.department_id)?.name || '—'}}</template></el-table-column><el-table-column v-if="type === 'departments'" prop="employee_count" label="在职人数" width="100"/><el-table-column label="状态" width="110"><template #default="{row}"><el-tag :type="row.is_active ? 'success' : 'info'">{{row.is_active ? '启用' : '停用'}}</el-tag></template></el-table-column><el-table-column label="操作" width="240"><template #default="{row}"><el-button link type="primary" @click="open(row)">编辑</el-button><el-button link :type="row.is_active ? 'danger' : 'success'" @click="toggle(row)">{{row.is_active ? '停用' : '启用'}}</el-button><el-button v-if="type !== 'skills'" link type="danger" @click="remove(row)">删除</el-button><el-button v-if="type === 'departments'" link type="primary" @click="emit('positions',row.id)">查看岗位</el-button></template></el-table-column></el-table><div class="pagination"><span class="muted">共 {{total}} 条{{title}}资料</span><el-pagination v-model:current-page="filter.page" v-model:page-size="filter.page_size" :total="total" layout="prev, pager, next" @current-change="load"/></div></el-card>
<WorkspaceDialog v-model="dialog" :title="(editing ? '编辑' : '新增') + title" width="500px" destroy-on-close :close-on-click-modal="false"><el-form ref="form" :model="model" :rules="rules" label-position="top" @submit.prevent="save"><el-form-item label="编码" prop="code"><el-input v-model="model.code" maxlength="20"/></el-form-item><el-form-item :label="title + '名称'" prop="name"><el-input v-model="model.name" maxlength="50"/></el-form-item><el-form-item v-if="type === 'positions'" label="所属部门" prop="department_id"><el-select v-model="model.department_id"><el-option v-for="d in departments" :key="d.id" :value="d.id" :label="d.name + (d.is_active ? '' : '（停用）')" :disabled="!d.is_active && d.id !== editing?.department_id"/></el-select></el-form-item><el-form-item v-if="type !== 'skills'" label="说明"><el-input v-model="model.description" type="textarea" maxlength="1000"/></el-form-item><el-form-item label="状态"><el-switch v-model="model.is_active" active-text="启用" inactive-text="停用"/></el-form-item><div class="dialog-actions"><el-button @click="dialog = false">取消</el-button><el-button type="primary" native-type="submit" :loading="saving">保存</el-button></div></el-form></WorkspaceDialog></template>
