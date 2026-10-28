<script setup>
import {reactive,ref,onMounted} from 'vue'
import {ElMessage} from 'element-plus'
import {auth} from '../stores/auth'
import {http} from '../api/http'
import {useDirty} from '../stores/dirty'
const form=reactive({old_password:'',new_password:'',confirm_password:''}),profile=reactive({display_name:auth.user?.display_name||auth.user?.username||''})
const busy=ref(false),resetDirty=useDirty(()=>[form,profile])
async function change(){busy.value=true;try{await http.put('/auth/password',form);ElMessage.success('密码已修改');Object.assign(form,{old_password:'',new_password:'',confirm_password:''});await Promise.resolve();resetDirty()}catch{}finally{busy.value=false}}
async function save(){try{await http.patch('/auth/profile',profile);auth.user.display_name=profile.display_name;ElMessage.success('资料已保存');resetDirty()}catch{}}
</script>
<template><div class="page-title"><div><h1>{{auth.user?.role==='ADMIN'?'系统设置':'账号设置'}}</h1><p>满氏吉他制琴有限公司 · 员工管理系统 V2.0</p></div></div><el-card shadow="never"><el-form label-position="top" class="settings-form" @submit.prevent="save"><el-form-item label="当前账号"><el-input :model-value="auth.user?.username" disabled/></el-form-item><el-form-item label="显示名称"><el-input v-model="profile.display_name" maxlength="50"/></el-form-item><el-button type="primary" native-type="submit">保存基本资料</el-button></el-form></el-card><el-card shadow="never" class="skills-card"><h3>修改密码</h3><p class="muted">新密码8–10位，包含大写字母、小写字母和数字。首次部署请修改初始密码。</p><el-form label-position="top" class="settings-form" @submit.prevent="change"><el-form-item label="旧密码" required><el-input v-model="form.old_password" type="password" show-password/></el-form-item><el-form-item label="新密码" required><el-input v-model="form.new_password" type="password" show-password/></el-form-item><el-form-item label="确认新密码" required><el-input v-model="form.confirm_password" type="password" show-password/></el-form-item><el-button type="primary" native-type="submit" :loading="busy">修改密码</el-button></el-form></el-card></template>
