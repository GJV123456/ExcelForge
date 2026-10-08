<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login, register } from '../api/auth'
import { useUserStore } from '../store/user'
import loginBackground from '../assets/images/login-bg.png'

const router = useRouter()
const route = useRoute()
const user = useUserStore()
const formRef = ref()
const loading = ref(false)
const mode = ref('login')
const rememberKey = 'excelforge_login_remember'
const getRememberedLogin = () => {
  try { return JSON.parse(localStorage.getItem(rememberKey) || '{}') }
  catch { return {} }
}
const rememberedLogin = getRememberedLogin()
const form = reactive({
  username: rememberedLogin.username || '',
  password: '',
  displayName: '',
  confirmPassword: '',
  agree: true,
  remember: Boolean(rememberedLogin.remember)
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  displayName: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请再次输入密码', trigger: 'blur' }],
  agree: [{ validator: (_, value, callback) => value ? callback() : callback(new Error('请先同意服务条款')), trigger: 'change' }]
}
const isRegister = computed(() => mode.value === 'register')
const pageTitle = computed(() => isRegister.value ? '创建首个账号' : '账户登录')
const submitLabel = computed(() => isRegister.value ? '创建账号' : '登录')
const switchMode = () => { mode.value = isRegister.value ? 'login' : 'register'; form.confirmPassword = '' }
const syncRememberedLogin = () => {
  if (!form.remember) {
    localStorage.removeItem(rememberKey)
    return
  }
  localStorage.setItem(rememberKey, JSON.stringify({
    username: form.username,
    remember: true
  }))
}
const submit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  if (!form.remember) localStorage.removeItem(rememberKey)
  loading.value = true
  try {
    const requestPayload = isRegister.value
      ? {
          username: form.username,
          password: form.password,
          confirmPassword: form.confirmPassword,
          displayName: form.displayName,
          agree: form.agree
        }
      : {
          username: form.username,
          password: form.password,
          agree: form.agree,
          remember: form.remember
        }
    const { data } = await (isRegister.value ? register(requestPayload) : login(requestPayload))
    const responsePayload = data?.data || data
    if (!responsePayload?.token) throw new Error(data?.message || '登录失败')
    syncRememberedLogin()
    user.setUser(responsePayload.token, responsePayload.userInfo || responsePayload.user || {})
    ElMessage.success(isRegister.value ? '账号创建成功' : '登录成功')
    router.replace(route.query.redirect || '/')
  } catch (error) { ElMessage.error(error.response ? (error.response.data?.detail || error.response.data?.message || '登录失败') : (error.message || '服务器连接失败')) }
  finally { loading.value = false }
}
</script>

<template>
  <main class="login-page">
    <header class="login-header"><div class="header-inner"><div class="brand"><span class="brand-mark">EF</span><strong>ExcelForge</strong><span class="header-title">欢迎登录</span></div><span class="entry-link">Excel 数据格式转换与测试内容生成工具</span></div></header>
    <section class="login-section" :style="{ backgroundImage: `url(${loginBackground})` }"><div class="login-wrapper"><nav><span>{{ pageTitle }}</span><small>ExcelForge</small></nav><div class="account-box"><el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit"><el-form-item prop="username"><el-input v-model="form.username" size="large" placeholder="请输入用户名"><template #prefix><el-icon><User /></el-icon></template></el-input></el-form-item><el-form-item v-if="isRegister" prop="displayName"><el-input v-model="form.displayName" size="large" placeholder="请输入显示名称" /></el-form-item><el-form-item prop="password"><el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码（至少 8 位）" @keyup.enter="submit"><template #prefix><el-icon><Lock /></el-icon></template></el-input></el-form-item><el-form-item v-if="isRegister" prop="confirmPassword"><el-input v-model="form.confirmPassword" size="large" type="password" show-password placeholder="请再次输入密码" /></el-form-item><el-form-item class="agree-row" prop="agree"><el-checkbox v-model="form.agree">我已阅读 <a href="javascript:void(0)">《隐私条款》</a> 和 <a href="javascript:void(0)">《服务条款》</a></el-checkbox></el-form-item><el-button class="submit-button" type="primary" :loading="loading" @click="submit">{{ submitLabel }}</el-button></el-form><div class="account-actions"><el-checkbox v-if="!isRegister" v-model="form.remember">记住账号</el-checkbox><el-button text @click="switchMode">{{ isRegister ? '返回登录' : '首次使用？创建账号' }}</el-button></div></div></div></section>
    <footer class="login-footer"><p><a href="javascript:void(0)">奋进</a><a href="javascript:void(0)">专业</a><a href="javascript:void(0)">卓越</a><a href="javascript:void(0)">自豪</a></p><p>Copyright © ExcelForge</p></footer>
  </main>
</template>

<style scoped>
.login-page{min-height:100vh;background:#fff;display:flex;flex-direction:column}.login-header{height:126px;border-bottom:1px solid #e4e4e4;background:#fff}.header-inner{width:min(1200px,calc(100% - 48px));height:100%;margin:auto;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:12px;color:#263650}.brand-mark{display:grid;place-items:center;width:46px;height:46px;border-radius:12px;background:#18a89e;color:#fff;font-size:15px;font-weight:800}.brand strong{font-size:26px}.header-title{padding-left:25px;border-left:1px solid #d9e0e3;font-size:23px;color:#66727a}.entry-link{font-size:14px;color:#68757d}.login-section{height:488px;position:relative;background-repeat:no-repeat;background-position:center;background-size:cover}.login-wrapper{width:382px;position:absolute;left:50%;top:54px;transform:translateX(250px);background:#fff;box-shadow:0 1px 14px #00000026}.login-wrapper nav{height:55px;border-bottom:1px solid #f0f0f0;padding:0 40px;display:flex;align-items:center;justify-content:space-between}.login-wrapper nav span{color:#1aa79e;font-size:18px;font-weight:650}.login-wrapper nav small{font-size:13px;color:#9aa3a8}.account-box{padding:28px 40px 25px}.account-box :deep(.el-form-item){margin-bottom:20px}.account-box :deep(.el-input__wrapper){border-radius:0;box-shadow:0 0 0 1px #cfcdcd inset;padding-left:12px}.account-box :deep(.el-input__wrapper.is-focus){box-shadow:0 0 0 1px #18a89e inset}.account-box :deep(.el-input__prefix){font-size:18px;color:#a9b0b4;margin-right:8px}.agree-row{margin-top:3px!important;margin-bottom:22px!important}.agree-row :deep(.el-form-item__content){line-height:1.35}.agree-row :deep(.el-checkbox__label){font-size:12px;padding-left:5px;white-space:normal}.agree-row a{color:#167c98;text-decoration:none}.submit-button{width:100%;height:40px;border-radius:0;background:#1cac9f;border-color:#1cac9f}.submit-button:hover{background:#15998f;border-color:#15998f}.account-actions{display:flex;justify-content:space-between;align-items:center;margin-top:16px;color:#a0a0a0;font-size:12px}.account-actions :deep(.el-checkbox){height:auto;color:#888;font-size:12px;font-weight:400}.account-actions :deep(.el-checkbox__label){font-size:12px;color:#888;font-weight:400;line-height:1}.account-actions :deep(.el-button){padding:0;color:#888;font-size:12px;font-weight:400}.login-footer{padding:30px 20px 45px;color:#999;text-align:center;font-size:13px}.login-footer p{margin:14px 0}.login-footer a{color:#999;text-decoration:none;padding:0 12px;border-right:1px solid #ddd}.login-footer a:last-child{border-right:0}@media(max-width:1050px){.login-wrapper{transform:translateX(15px)}}@media(max-width:760px){.login-header{height:78px}.header-inner{width:calc(100% - 40px)}.brand strong{font-size:20px}.brand-mark{width:36px;height:36px;border-radius:9px;font-size:12px}.header-title,.entry-link{display:none}.login-section{min-height:570px;height:auto;background-position:45% center;display:flex;align-items:center;justify-content:center;padding:28px 20px}.login-wrapper{position:static;transform:none;width:min(100%,382px)}.login-footer{margin-top:auto;padding:22px 12px}.login-footer a{padding:0 7px;font-size:12px}}
</style>

<style>
/* 覆盖全局旧登录页样式，确保 Flex 子元素始终占满可用宽度。 */
.login-page { align-items: stretch; padding: 0; background: linear-gradient(135deg, #f5f8ff 0%, #eef4ff 48%, #f8fbff 100%); }
.login-header { height: 88px; border-bottom-color: #e4eaf3; background: rgba(255, 255, 255, .88); backdrop-filter: blur(14px); }
.brand-mark { background: linear-gradient(135deg, #2864e8, #5e91fa); border-radius: 13px; box-shadow: 0 8px 18px rgba(40, 100, 232, .2); }
.brand strong { color: #1d2b44; }
.header-title { color: #718096; }
.login-section { height: 540px; background-color: #edf4ff; }
.login-wrapper { border: 1px solid rgba(219, 230, 246, .9); border-radius: 18px; overflow: hidden; box-shadow: 0 18px 50px rgba(35, 59, 95, .16); }
.login-wrapper nav { background: linear-gradient(180deg, #fbfdff, #f7faff); }
.login-wrapper nav span { color: #2864e8; }
.account-box :deep(.el-input__wrapper) { border-radius: 10px; background: #fbfdff; box-shadow: 0 0 0 1px #dbe4f0 inset; }
.account-box :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #5d8ff2 inset, 0 0 0 3px rgba(93, 143, 242, .12); }
.account-box :deep(.el-input__prefix) { color: #6b8fd5; }
.account-box .submit-button { border: 0; border-radius: 10px; background: linear-gradient(135deg, #2864e8, #4f86ff); box-shadow: 0 9px 22px rgba(40, 100, 232, .24); }
.account-box .submit-button:hover { background: linear-gradient(135deg, #1f57d6, #3f78f7); }
.login-footer { color: #8190a5; }
.login-footer a { color: #8190a5; }
</style>
