<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getWorkspaceContext, getWorkspaceUsers, createWorkspaceUser,
  updateWorkspaceUser,
  createWorkspaceLine, updateWorkspaceLine, createWorkspaceProfession,
  updateWorkspaceProfession, createWorkspaceProject, updateWorkspaceProject
} from '../api/workspace'
import { getApiErrorMessage } from '../utils/httpError'

const activeTab = ref('accounts')
const context = ref({ lines: [], professions: [], projects: [] })
const users = ref([])
const loading = ref(false)
const saving = ref(false)
const userDialogVisible = ref(false)
const entityDialogVisible = ref(false)
const entityType = ref('line')
const editingUserId = ref(null)
const userForm = reactive({ username: '', password: '', displayName: '', role: 'line_admin', lineId: null, professionId: null, isEnabled: true })
const enabledLines = computed(() => context.value.lines.filter((item) => item.isEnabled))
const enabledProfessions = computed(() => context.value.professions.filter((item) => item.isEnabled))
const lineForm = reactive({ id: null, code: '', name: '', isEnabled: true })
const professionForm = reactive({ id: null, code: '', name: '', isEnabled: true })
const projectForm = reactive({ id: null, professionId: null, code: '', name: '', description: '', engineCode: '', isEnabled: true })
const editingLine = computed(() => lineForm.id != null)
const editingProfession = computed(() => professionForm.id != null)
const editingProject = computed(() => projectForm.id != null)
const entityDialogTitle = computed(() => {
  const editing = entityType.value === 'line' ? editingLine.value : entityType.value === 'profession' ? editingProfession.value : editingProject.value
  return `${editing ? '编辑' : '新增'}${entityType.value === 'line' ? '线路' : entityType.value === 'profession' ? '专业' : '联调项目'}`
})

const errorMessage = async (error, fallback) => {
  const parsed = await getApiErrorMessage(error)
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.at(-1) || '字段'}：${item.msg}`).join('；') || parsed
  return parsed || fallback
}
const load = async () => {
  loading.value = true
  try {
    const [workspaceResponse, usersResponse] = await Promise.all([getWorkspaceContext({ includeDisabled: true }), getWorkspaceUsers()])
    context.value = workspaceResponse.data?.data || context.value
    users.value = usersResponse.data?.data || []
  } catch (error) {
    ElMessage.error(await errorMessage(error, '管理数据加载失败'))
  } finally { loading.value = false }
}
const saveUser = async () => {
  if (!userForm.username.trim() || !userForm.displayName.trim()) return ElMessage.warning('请填写用户名和显示名称')
  if (editingUserId.value == null && userForm.password == null) return ElMessage.warning('请填写初始密码')
  if (userForm.role !== 'super_admin' && !userForm.lineId) return ElMessage.warning('请选择所属线路')
  if (userForm.role === 'professional_configurator' && !userForm.professionId) return ElMessage.warning('请选择所属专业')
  saving.value = true
  try {
    const payload = { ...userForm }
    if (editingUserId.value != null && !payload.password) delete payload.password
    if (userForm.role === 'super_admin') { payload.lineId = null; payload.professionId = null }
    else if (userForm.role === 'line_admin') payload.professionId = null
    if (editingUserId.value != null) await updateWorkspaceUser(editingUserId.value, payload)
    else await createWorkspaceUser(payload)
    ElMessage.success(editingUserId.value == null ? '账号已创建' : '账号已保存')
    userDialogVisible.value = false
    editingUserId.value = null
    Object.assign(userForm, { username: '', password: '', displayName: '', role: 'line_admin', lineId: null, professionId: null, isEnabled: true })
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '账号创建失败')) } finally { saving.value = false }
}
const openCreateUser = () => {
  editingUserId.value = null
  Object.assign(userForm, { username: '', password: '', displayName: '', role: 'line_admin', lineId: null, professionId: null, isEnabled: true })
  userDialogVisible.value = true
}
const editUser = (item) => {
  editingUserId.value = item.id
  Object.assign(userForm, { username: item.username, password: '', displayName: item.displayName, role: item.role, lineId: item.lineId, professionId: item.professionId, isEnabled: item.isEnabled })
  userDialogVisible.value = true
}
const saveLine = async () => {
  if (!lineForm.code.trim() || !lineForm.name.trim()) return ElMessage.warning('请填写线路编码和线路名称')
  saving.value = true
  try {
    const { id, ...fields } = lineForm
    const payload = { ...fields, sortOrder: 1 }
    if (id != null) await updateWorkspaceLine(id, payload)
    else await createWorkspaceLine(payload)
    ElMessage.success(id != null ? '线路已保存' : '线路已新增')
    entityDialogVisible.value = false
    Object.assign(lineForm, { id: null, code: '', name: '', isEnabled: true })
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '线路保存失败')) } finally { saving.value = false }
}
const saveProfession = async () => {
  if (!professionForm.code.trim() || !professionForm.name.trim()) return ElMessage.warning('请填写专业编码和专业名称')
  saving.value = true
  try {
    const { id, ...fields } = professionForm
    const payload = { ...fields, sortOrder: 1 }
    if (id != null) await updateWorkspaceProfession(id, payload)
    else await createWorkspaceProfession(payload)
    ElMessage.success(id != null ? '专业已保存' : '专业已新增')
    entityDialogVisible.value = false
    Object.assign(professionForm, { id: null, code: '', name: '', isEnabled: true })
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '专业保存失败')) } finally { saving.value = false }
}
const saveProject = async () => {
  if (!projectForm.professionId || !projectForm.code.trim() || !projectForm.name.trim()) return ElMessage.warning('请填写所属专业、项目编码和项目名称')
  saving.value = true
  try {
    const { id, ...fields } = projectForm
    const payload = { ...fields, sortOrder: 1 }
    if (id != null) await updateWorkspaceProject(id, payload)
    else await createWorkspaceProject(payload)
    ElMessage.success(id != null ? '联调项目已保存' : '联调项目已新增')
    entityDialogVisible.value = false
    Object.assign(projectForm, { id: null, professionId: null, code: '', name: '', description: '', engineCode: '', isEnabled: true })
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '联调项目保存失败')) } finally { saving.value = false }
}
const openCreateEntity = (type) => {
  entityType.value = type
  if (type === 'line') Object.assign(lineForm, { id: null, code: '', name: '', isEnabled: true })
  if (type === 'profession') Object.assign(professionForm, { id: null, code: '', name: '', isEnabled: true })
  if (type === 'project') Object.assign(projectForm, { id: null, professionId: context.value.professions.find((item) => item.isEnabled)?.id ?? null, code: '', name: '', description: '', engineCode: '', isEnabled: true })
  entityDialogVisible.value = true
}
const editLine = (item) => { entityType.value = 'line'; Object.assign(lineForm, { id: item.id, code: item.code, name: item.name, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
const editProfession = (item) => { entityType.value = 'profession'; Object.assign(professionForm, { id: item.id, code: item.code, name: item.name, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
const editProject = (item) => { entityType.value = 'project'; Object.assign(projectForm, { id: item.id, professionId: item.professionId, code: item.code, name: item.name, description: item.description, engineCode: item.engineCode, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
onMounted(load)
</script>

<template>
  <div class="workspace admin-page">
    <header class="page-title admin-title">
      <div><h1>系统管理</h1><p>管理系统账号和线路、专业、联调项目基础信息。</p></div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </header>
    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane label="账号管理" name="accounts">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="账号按照角色绑定线路和专业，配置权限由工作范围自动控制。" />
        <el-card class="section-card admin-card">
          <template #header><div class="table-header"><strong>账号列表</strong><el-button type="primary" :icon="Plus" @click="openCreateUser">新增账号</el-button></div></template>
          <el-table v-loading="loading" :data="users" stripe empty-text="暂无账号"><el-table-column prop="username" label="用户名" min-width="150" /><el-table-column prop="displayName" label="显示名称" min-width="140" /><el-table-column label="角色" min-width="150"><template #default="{ row }">{{ { super_admin: '超级管理员', line_admin: '线路管理员', professional_configurator: '专业配置员' }[row.role] || row.role }}</template></el-table-column><el-table-column prop="lineName" label="线路" min-width="120" /><el-table-column prop="professionName" label="专业" min-width="120" /><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'">{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="90" fixed="right"><template #default="{ row }"><el-button text type="primary" :icon="EditPen" @click="editUser(row)">编辑</el-button></template></el-table-column></el-table>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="线路管理" name="lines">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="线路是配置数据的第一层范围；不同线路之间的数据相互隔离。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>线路列表</strong><span class="table-hint">共 {{ context.lines.length }} 条线路</span></div><el-button type="primary" :icon="Plus" @click="openCreateEntity('line')">新增线路</el-button></div></template><el-table v-loading="loading" :data="context.lines" stripe empty-text="暂无线路"><el-table-column prop="name" label="线路名称" min-width="180" /><el-table-column prop="code" label="线路编码" min-width="120" /><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button text type="primary" :icon="EditPen" @click="editLine(row)">编辑</el-button></template></el-table-column></el-table></el-card>
      </el-tab-pane>
      <el-tab-pane label="专业管理" name="professions">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="专业是配置数据的第二层范围；专业目录可在同一线路下共享使用。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>专业列表</strong><span class="table-hint">共 {{ context.professions.length }} 个专业</span></div><el-button type="primary" :icon="Plus" @click="openCreateEntity('profession')">新增专业</el-button></div></template><el-table v-loading="loading" :data="context.professions" stripe empty-text="暂无专业"><el-table-column prop="name" label="专业名称" min-width="180" /><el-table-column prop="code" label="专业编码" min-width="120" /><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button text type="primary" :icon="EditPen" @click="editProfession(row)">编辑</el-button></template></el-table-column></el-table></el-card>
      </el-tab-pane>
      <el-tab-pane label="联调项目管理" name="projects">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="联调项目归属于专业；停用后会从工作范围选择器中隐藏。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>联调项目列表</strong><span class="table-hint">共 {{ context.projects.length }} 个项目</span></div><el-button type="primary" :icon="Plus" @click="openCreateEntity('project')">新增联调项目</el-button></div></template><el-table v-loading="loading" :data="context.projects" stripe empty-text="暂无联调项目"><el-table-column prop="name" label="项目名称" min-width="190" /><el-table-column label="所属专业" min-width="150"><template #default="{ row }">{{ context.professions.find((item) => item.id === row.professionId)?.name || '—' }}</template></el-table-column><el-table-column prop="code" label="项目编码" min-width="120" /><el-table-column prop="engineCode" label="处理引擎" min-width="120"><template #default="{ row }">{{ row.engineCode || '—' }}</template></el-table-column><el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button text type="primary" :icon="EditPen" @click="editProject(row)">编辑</el-button></template></el-table-column></el-table></el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
  <el-dialog v-model="userDialogVisible" :title="editingUserId == null ? '新增账号' : '编辑账号'" width="min(720px, calc(100vw - 28px))">
    <el-form label-position="top">
      <div class="admin-grid admin-grid-two">
        <el-form-item label="用户名" required><el-input v-model="userForm.username" placeholder="登录用户名" /></el-form-item>
        <el-form-item label="显示名称" required><el-input v-model="userForm.displayName" placeholder="页面显示名称" /></el-form-item>
        <el-form-item :label="editingUserId == null ? '初始密码' : '重置密码'"><el-input v-model="userForm.password" type="password" show-password :placeholder="editingUserId == null ? '请设置初始密码' : '留空则保持原密码'" /></el-form-item>
        <el-form-item label="角色" required><el-select v-model="userForm.role"><el-option label="线路管理员" value="line_admin" /><el-option label="专业配置员" value="professional_configurator" /><el-option label="超级管理员" value="super_admin" /></el-select></el-form-item>
        <el-form-item v-if="userForm.role !== 'super_admin'" label="所属线路" required><el-select v-model="userForm.lineId" placeholder="选择线路"><el-option v-for="item in enabledLines" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item v-if="userForm.role === 'professional_configurator'" label="所属专业" required><el-select v-model="userForm.professionId" placeholder="选择专业"><el-option v-for="item in enabledProfessions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
      </div>
      <el-form-item label="账号状态"><el-switch v-model="userForm.isEnabled" active-text="启用" inactive-text="停用" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveUser">{{ editingUserId == null ? '创建账号' : '保存修改' }}</el-button></template>
  </el-dialog>
  <el-dialog v-model="entityDialogVisible" :title="entityDialogTitle" width="min(620px, calc(100vw - 28px))" destroy-on-close>
    <el-form label-position="top">
      <template v-if="entityType === 'line'"><div class="admin-grid admin-grid-two"><el-form-item label="线路编码" required><el-input v-model="lineForm.code" placeholder="例如 9" /></el-form-item><el-form-item label="线路名称" required><el-input v-model="lineForm.name" placeholder="例如 9号线" /></el-form-item></div><el-form-item label="状态"><el-switch v-model="lineForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></template>
      <template v-else-if="entityType === 'profession'"><div class="admin-grid admin-grid-two"><el-form-item label="专业编码" required><el-input v-model="professionForm.code" placeholder="例如 ZDH" /></el-form-item><el-form-item label="专业名称" required><el-input v-model="professionForm.name" placeholder="例如 自动化" /></el-form-item></div><el-form-item label="状态"><el-switch v-model="professionForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></template>
      <template v-else><div class="admin-grid admin-grid-two"><el-form-item label="所属专业" required><el-select v-model="projectForm.professionId" placeholder="选择专业"><el-option v-for="item in context.professions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="项目编码" required><el-input v-model="projectForm.code" placeholder="例如 FAS" /></el-form-item><el-form-item label="项目名称" required><el-input v-model="projectForm.name" placeholder="例如 火灾自动报警" /></el-form-item><el-form-item label="处理引擎代码"><el-input v-model="projectForm.engineCode" placeholder="例如 T19" /></el-form-item></div><el-form-item label="项目说明"><el-input v-model="projectForm.description" placeholder="选填" /></el-form-item><el-form-item label="状态"><el-switch v-model="projectForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></template>
    </el-form>
    <template #footer><el-button @click="entityDialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="entityType === 'line' ? saveLine() : entityType === 'profession' ? saveProfession() : saveProject()">保存</el-button></template>
  </el-dialog>
</template>

<style scoped>
.admin-page { padding: 4px 0 42px; }
.admin-title { align-items: flex-start; }
.admin-title h1 { margin: 0; color: #243653; font-size: 25px; }
.admin-title p { margin: 7px 0 0; color: #8491a5; font-size: 13px; }
.admin-tabs { margin-top: 10px; }
.admin-notice { margin: 10px 0 18px; }
.admin-card { margin-bottom: 18px; }
.admin-card :deep(.el-card__header) { padding: 17px 22px; }
.card-heading strong { display: block; color: #2d405e; font-size: 15px; }
.card-heading span { display: block; margin-top: 5px; color: #8a98aa; font-size: 12px; }
.table-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.table-header > div { display:flex;align-items:center;gap:10px; }.table-hint { color:#8a98aa;font-size:12px;font-weight:400; }
.admin-form { max-width: 100%; }
.admin-grid { display: grid; gap: 0 18px; }
.admin-grid-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.admin-grid-two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.admin-page :deep(.el-input__wrapper), .admin-page :deep(.el-select__wrapper) { min-height: 40px; }
.admin-page :deep(.el-input__inner), .admin-page :deep(.el-select__placeholder), .admin-page :deep(.el-select__selected-item) { line-height: 40px; }
.admin-page :deep(.el-input__wrapper), .admin-page :deep(.el-select__wrapper), .admin-page :deep(.el-textarea__inner) { font-size: 14px; }
.admin-grid :deep(.el-select), .admin-form :deep(.el-select), .admin-card :deep(.el-select) { width: 100%; }
.admin-entity-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
.project-card { grid-column: 1 / -1; }
.entity-stats { margin: 14px 0 18px; }.entity-stats :deep(.el-card__body) { padding: 14px 18px; }.entity-stats :deep(.el-statistic__head) { color:#7b8aa0;font-size:12px; }.entity-stats :deep(.el-statistic__content) { color:#2f5487;font-size:24px;font-weight:700; }.entity-tables { row-gap:16px; }.entity-card { border-color:#e3eaf4;border-radius:14px; }.entity-card :deep(.el-card__header) { padding:16px 18px; }.entity-card-heading { display:flex;align-items:center;justify-content:space-between;gap:12px; }.entity-card-heading strong,.entity-card-heading span { display:block; }.entity-card-heading strong { color:#29466e;font-size:15px; }.entity-card-heading span { margin-top:4px;color:#8a98ad;font-size:12px; }.entity-card :deep(.el-table th.el-table__cell) { color:#61728a;background:#f7f9fc;font-weight:700; }.entity-card :deep(.el-table td.el-table__cell) { height:54px; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin: 4px 0 18px; }
.admin-table { margin-top: 14px; }
.admin-table :deep(.el-table__inner-wrapper::before) { display: none; }
@media (max-width: 850px) { .admin-grid-three { grid-template-columns: repeat(2, minmax(0, 1fr)); }.admin-entity-grid { grid-template-columns: 1fr; }.project-card { grid-column: auto; } }
@media (max-width: 560px) { .admin-grid-three, .admin-grid-two { grid-template-columns: 1fr; }.admin-title { align-items: center; } }
</style>
