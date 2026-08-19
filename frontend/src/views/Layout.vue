<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
const route = useRoute(); const router = useRouter(); const user = useUserStore()
const logout = () => { user.logout(); router.replace('/login') }
</script>
<template>
  <el-container class="app-shell">
    <el-header class="topbar">
      <div class="logo"><span>EF</span> ExcelForge</div>
      <el-menu class="main-nav" mode="horizontal" router :default-active="route.path" :ellipsis="false">
        <el-menu-item index="/workspace">数据处理</el-menu-item>
        <el-menu-item index="/config">基础配置</el-menu-item>
      </el-menu>
      <div class="user-area">
        <span>{{ user.userInfo.name || user.userInfo.username || '当前用户' }}</span>
        <el-button text @click="logout">退出登录</el-button>
      </div>
    </el-header>
    <el-main><router-view /></el-main>
  </el-container>
</template>
