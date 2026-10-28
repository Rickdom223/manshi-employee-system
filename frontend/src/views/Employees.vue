<script setup>
import { ref, reactive, onMounted, onActivated } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { http, allRows } from '../api/http'
import {download} from '../api/download'
import EmployeeForm from '../components/EmployeeForm.vue'
import ArchiveDialog from '../components/ArchiveDialog.vue'
import EmployeeDetail from './EmployeeDetail.vue'
const router = useRouter()
const detailId=ref(null),route=useRoute()
const rows = ref([]), total = ref(0), busy = ref(false), failed = ref(false)
const departments = ref([]), positions = ref([]), skills = ref([]), editing = ref(null), dialog = ref(false), archiving = ref(null)
const filter = reactive({ keyword: '', department_id: null, status: 'active', skill_id: null, page: 1, page_size: 10 })
async function load() { busy.value = true; failed.value = false; try { const result = await http.get('/employees', { params: filter }); rows.value = result.data; total.value = result.total } catch { failed.value = true } finally { busy.value = false } }
async function options() { [departments.value, positions.value, skills.value] = await Promise.all(['/departments', '/positions', '/skills'].map(allRows)) }
function search() { filter.page = 1; load() }
function reset() { Object.assign(filter, { keyword: '', department_id: null, status: 'active', skill_id: null, page: 1 }); load() }
async function openEdit(row) { try { await options(); editing.value = row ? (await http.get(`/employees/${row.id}`)).data : null; dialog.value = true } catch {} }
async function saved() { dialog.value = false; archiving.value = null; await load() }
onActivated(async () => { await load(); try { await options() } catch {};if(route.query.detail)detailId.value=Number(route.query.detail) })
</script>
<template><div class="page-title"><div><div class="eyebrow">PEOPLE</div><h1>员工信息管理</h1><p>一个主要岗位，多项制琴专长；在这里维护完整的人员记录。</p></div><div><el-button @click="download('/employees/export',filter,'员工信息')">导出 Excel</el-button><el-button type="primary" @click="openEdit(null)">＋ 新增员工</el-button></div></div>
<el-card shadow="never"><el-form class="filters" inline @submit.prevent="search"><el-form-item label="搜索"><el-input v-model="filter.keyword" placeholder="姓名 / 工号" clearable @keyup.enter="search"/></el-form-item><el-form-item label="部门"><el-select v-model="filter.department_id" clearable placeholder="全部部门"><el-option v-for="d in departments" :key="d.id" :value="d.id" :label="d.name" /></el-select></el-form-item><el-form-item label="状态"><el-select v-model="filter.status"><el-option label="在职" value="active"/><el-option label="离职" value="resigned"/><el-option label="全部" value="all"/></el-select></el-form-item><el-form-item label="技能"><el-select v-model="filter.skill_id" clearable placeholder="全部技能"><el-option v-for="s in skills" :key="s.id" :value="s.id" :label="s.name"/></el-select></el-form-item><el-form-item><el-button type="primary" @click="search">查询</el-button><el-button @click="reset">重置</el-button></el-form-item></el-form>
<el-alert v-if="failed" type="error" :closable="false" title="列表加载失败，请点击查询重试"/>
<el-table v-loading="busy" :data="rows" empty-text="没有符合条件的员工" stripe><el-table-column prop="employee_no" label="工号" min-width="120"/><el-table-column prop="full_name" label="姓名" min-width="120"/><el-table-column prop="phone" label="手机号" width="130"/><el-table-column prop="department_name" label="部门" min-width="150"/><el-table-column prop="position_name" label="主要岗位" min-width="140"/><el-table-column prop="hire_date" label="入职日期" width="115"/><el-table-column label="状态" width="85"><template #default="{row}"><el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="light">{{ row.status === 'active' ? '在职' : '离职' }}</el-tag></template></el-table-column><el-table-column label="操作" width="190" fixed="right"><template #default="{row}"><el-button link type="primary" @click="detailId = row.id">详情</el-button><el-button link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-if="row.status === 'active'" link type="danger" @click="archiving = row">归档</el-button></template></el-table-column></el-table>
<div class="pagination"><span class="muted">共 {{total}} 条员工档案</span><el-pagination v-model:current-page="filter.page" v-model:page-size="filter.page_size" :page-sizes="[10,20,50,100]" :total="total" layout="sizes, prev, pager, next" @current-change="load" @size-change="search" /></div></el-card>
<WorkspaceDialog v-model="dialog" :title="editing ? '编辑员工' : '新增员工'" width="640px" destroy-on-close :close-on-click-modal="false"><EmployeeForm v-if="dialog" :employee="editing" :departments="departments" :positions="positions" @saved="saved" @cancel="dialog = false"/></WorkspaceDialog>
<WorkspaceDialog :model-value="!!archiving" title="离职归档确认" width="500px" destroy-on-close @close="archiving = null"><ArchiveDialog v-if="archiving" :employee="archiving" @saved="saved" @cancel="archiving = null"/></WorkspaceDialog><WorkspaceDialog kind="drawer" :model-value="!!detailId" title="员工详情" size="78%" destroy-on-close @close="detailId = null"><EmployeeDetail v-if="detailId" :employee-id="detailId"/></WorkspaceDialog></template>
