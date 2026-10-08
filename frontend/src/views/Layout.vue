<script setup>
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { useExcelStore } from '../store/excel'
import { getIntegrationProject } from '../data/integrations'
import { changePassword, logout as logoutRequest } from '../api/auth'
import { getApiErrorMessage } from '../utils/httpError'
const route = useRoute(); const router = useRouter(); const user = useUserStore(); const excel = useExcelStore()
const selectedProject = computed(() => getIntegrationProject(excel.selectedIntegration))
const canOpenConfig = computed(() => selectedProject.value?.configRoute === '/config')
const passwordDialogVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const openPasswordDialog = () => {
  Object.assign(passwordForm, { currentPassword: '', newPassword: '', confirmPassword: '' })
  passwordDialogVisible.value = true
}
const savePassword = async () => {
  if (passwordForm.newPassword.length < 8) return ElMessage.warning('新密码长度不能少于 8 位')
  if (passwordForm.newPassword !== passwordForm.confirmPassword) return ElMessage.warning('两次输入的密码不一致')
  passwordSaving.value = true
  try {
    await changePassword(passwordForm)
    passwordDialogVisible.value = false
    ElMessage.success('密码修改成功，请重新登录')
    await logout()
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  } finally { passwordSaving.value = false }
}
const logout = async () => {
  try { await logoutRequest() } catch { /* 本地退出仍需完成 */ }
  excel.setIntegration(''); user.logout(); router.replace('/login')
}
</script>
<template>
  <el-container class="app-shell">
    <el-header class="topbar">
      <div class="logo"><span>EF</span> ExcelForge</div>
      <el-menu class="main-nav" mode="horizontal" router :default-active="route.path" :ellipsis="false">
        <el-menu-item index="/workspace">数据处理</el-menu-item>
        <el-menu-item v-if="canOpenConfig" index="/config">基础配置</el-menu-item>
      </el-menu>
      <div class="user-area">
        <span>{{ user.userInfo.name || user.userInfo.username || '当前用户' }}</span>
        <el-button text @click="openPasswordDialog">修改密码</el-button>
        <el-button text @click="logout">退出登录</el-button>
      </div>
    </el-header>
    <el-main><router-view /></el-main>
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="min(460px, calc(100vw - 32px))">
      <el-form label-position="top">
        <el-form-item label="当前密码" required><el-input v-model="passwordForm.currentPassword" type="password" show-password /></el-form-item>
        <el-form-item label="新密码" required><el-input v-model="passwordForm.newPassword" type="password" show-password /></el-form-item>
        <el-form-item label="确认新密码" required><el-input v-model="passwordForm.confirmPassword" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer><el-button @click="passwordDialogVisible = false">取消</el-button><el-button type="primary" :loading="passwordSaving" @click="savePassword">保存</el-button></template>
    </el-dialog>
  </el-container>
</template>
