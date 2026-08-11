<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
const router = useRouter(); const user = useUserStore()
const logout = () => { user.logout(); router.replace('/login') }
</script>
<template><el-container class="app-shell"><el-header class="topbar"><div class="logo"><span>EF</span> ExcelForge</div><div class="user-area"><span>{{ user.userInfo.name || user.userInfo.username || '当前用户' }}</span><el-button text @click="logout">退出登录</el-button></div></el-header><el-main><router-view /></el-main></el-container></template>
