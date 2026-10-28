<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'
import { auth, clearAuth } from '../stores/auth'
import { homeFor } from '../router/v3menus'
const router = useRouter(), busy = ref(false), form = ref()
const credentials = reactive({ username: '', password: '' })
const rules = { username: [{ required: true, message: '请输入用户名', trigger: 'blur' }], password: [{ required: true, message: '请输入密码', trigger: 'blur' }] }
async function login() {
  if (!await form.value.validate().catch(() => false)) return
  busy.value = true
  try {
    const result = await http.post('/auth/login', credentials)
    auth.user = result.data;auth.csrf=result.data.csrf_token;auth.ready=true
    router.replace(homeFor(result.data.role))
  } catch { clearAuth() }
  finally { busy.value = false }
}
</script>
<template><div class="login-screen"><div class="login-story"><div class="eyebrow">MANSHI · PEOPLE & CRAFT</div><h1>匠心制琴，<br>从每一位同事开始。</h1><p>集中管理人员档案、组织岗位与制琴技能，<br>让团队的每一份专长被看见。</p><div class="story-line"></div><small>满氏吉他制琴有限公司</small></div>
  <el-card class="login-card" shadow="never"><div class="eyebrow">员工管理平台</div><h2>账号登录</h2><p class="muted">欢迎回来，请使用账号登录</p><el-form ref="form" :model="credentials" :rules="rules" label-position="top" @submit.prevent="login"><el-form-item label="用户名" prop="username"><el-input v-model="credentials.username" autocomplete="username" placeholder="输入用户名" /></el-form-item><el-form-item label="密码" prop="password"><el-input v-model="credentials.password" type="password" show-password autocomplete="current-password" placeholder="输入密码" /></el-form-item><el-button class="login-button" type="primary" native-type="submit" :loading="busy">登录平台</el-button></el-form></el-card></div></template>
