<script setup>
import {ref} from 'vue'
import {useRoute} from 'vue-router'
import Dictionaries from './Dictionaries.vue'
const route=useRoute()
const active=ref(['positions','skills'].includes(String(route.query.tab))?String(route.query.tab):'departments')
const selectedDepartment=ref(route.query.department_id?Number(route.query.department_id):null)
</script>
<template><el-tabs v-model="active"><el-tab-pane label="部门管理" name="departments"/><el-tab-pane label="岗位管理" name="positions"/><el-tab-pane label="制琴技能字典" name="skills"/></el-tabs><KeepAlive><Dictionaries :key="active" :type="active" :department-id="selectedDepartment" @positions="id=>{selectedDepartment=id;active='positions'}"/></KeepAlive></template>
