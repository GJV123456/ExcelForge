<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { CopyDocument, EditPen, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getWorkspaceContext, getWorkspaceUsers, createWorkspaceUser,
  updateWorkspaceUser,
  createWorkspaceLine, updateWorkspaceLine, createWorkspaceProfessions,
  updateWorkspaceProfession, createWorkspaceProject, updateWorkspaceProject
} from '../api/workspace'
import { getApiErrorMessage } from '../utils/httpError'
import { useWorkspaceStore } from '../store/workspace'

const activeTab = ref('accounts')
const workspace = useWorkspaceStore()
const context = ref({ lines: [], professions: [], projects: [] })
const users = ref([])
const loading = ref(false)
const saving = ref(false)
const userDialogVisible = ref(false)
const entityDialogVisible = ref(false)
const entityType = ref('line')
const projectCopyMode = ref(false)
const professionBatchText = ref('')
const editingUserId = ref(null)
const userForm = reactive({ username: '', password: '', displayName: '', role: 'line_admin', lineId: null, professionId: null, isEnabled: true })
const enabledLines = computed(() => context.value.lines.filter((item) => item.isEnabled))
const enabledProfessions = computed(() => context.value.professions.filter((item) => item.isEnabled))
const isSuperAdmin = computed(() => context.value.currentUser?.role === 'super_admin')
const isLineAdmin = computed(() => context.value.currentUser?.role === 'line_admin')
const projectLines = computed(() => isSuperAdmin.value
  ? context.value.lines
  : context.value.lines.filter((item) => String(item.id) === String(context.value.currentUser?.lineId)))
const managedProjects = computed(() => context.value.projects.filter((item) => canEditProject(item)))
const canEditProject = (item) => isSuperAdmin.value || (String(item.lineId) === String(context.value.currentUser?.lineId) && ['line_admin', 'professional_configurator'].includes(context.value.currentUser?.role))
const sortedManagedProjects = computed(() => [...managedProjects.value].sort((left, right) => {
  const leftLine = context.value.lines.find((line) => String(line.id) === String(left.lineId))
  const rightLine = context.value.lines.find((line) => String(line.id) === String(right.lineId))
  return compareSortOrder(leftLine || {}, rightLine || {}) || compareSortOrder(left, right)
}))
const managedProjectGroups = computed(() => {
  const groups = new Map()
  for (const project of sortedManagedProjects.value) {
    const line = context.value.lines.find((item) => String(item.id) === String(project.lineId))
    const key = String(project.lineId ?? 'none')
    if (!groups.has(key)) groups.set(key, { key, lineName: line?.name || '未分配线路', projects: [] })
    groups.get(key).projects.push(project)
  }
  return [...groups.values()]
})
const lineProjects = (lineId) => managedProjects.value
  .filter((item) => String(item.lineId) === String(lineId))
  .sort(compareSortOrder)
const lineForm = reactive({ id: null, code: '', name: '', sortOrder: 1, isEnabled: true })
const professionForm = reactive({ id: null, code: '', name: '', sortOrder: 1, isEnabled: true })
const projectForm = reactive({ id: null, lineId: null, professionId: null, code: '', name: '', description: '', engineCode: '', sortOrder: 1, isEnabled: true })
const groupedUsers = computed(() => {
  const groups = new Map()
  for (const account of users.value) {
    const key = `${account.lineName || '全局账号'} / ${account.professionName || (account.role === 'super_admin' ? '超级管理员' : '全专业')}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(account)
  }
  return [...groups].map(([label, members]) => ({ label, members }))
})
const editingLine = computed(() => lineForm.id != null)
const editingProfession = computed(() => professionForm.id != null)
const editingProject = computed(() => projectForm.id != null)
const entityDialogTitle = computed(() => {
  const editing = entityType.value === 'line' ? editingLine.value : entityType.value === 'profession' ? editingProfession.value : editingProject.value
  if (entityType.value === 'project' && !editing && projectCopyMode.value) return '复制其他线路项目'
  return `${editing ? '编辑' : '新增'}${entityType.value === 'line' ? '线路' : entityType.value === 'profession' ? '专业' : '联调项目'}`
})

const errorMessage = async (error, fallback) => {
  const parsed = await getApiErrorMessage(error)
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.at(-1) || '字段'}：${item.msg}`).join('；') || parsed
  return parsed || fallback
}
const compareSortOrder = (left, right) => {
  const orderDifference = Number(left.sortOrder ?? left.sort_order ?? 0) - Number(right.sortOrder ?? right.sort_order ?? 0)
  return orderDifference || String(left.code ?? '').localeCompare(String(right.code ?? ''), 'zh-CN', { numeric: true }) || Number(left.id ?? 0) - Number(right.id ?? 0)
}
const load = async () => {
  loading.value = true
  try {
    const workspaceResponse = await getWorkspaceContext({ includeDisabled: true })
    const data = workspaceResponse.data?.data || context.value
    context.value = {
      ...data,
      lines: [...(data.lines || [])].sort(compareSortOrder),
      professions: [...(data.professions || [])].sort(compareSortOrder),
      projects: [...(data.projects || [])].sort((left, right) =>
        (Number(left.lineId) || 0) - (Number(right.lineId) || 0) || compareSortOrder(left, right)),
    }
    if (context.value.currentUser?.role === 'super_admin') users.value = (await getWorkspaceUsers()).data?.data || []
    else { users.value = []; activeTab.value = 'projects' }
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
    const payload = { ...fields }
    if (id != null) await updateWorkspaceLine(id, payload)
    else await createWorkspaceLine(payload)
    ElMessage.success(id != null ? '线路已保存' : '线路已新增')
    entityDialogVisible.value = false
    Object.assign(lineForm, { id: null, code: '', name: '', isEnabled: true })
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '线路保存失败')) } finally { saving.value = false }
}
const saveProfession = async () => {
  saving.value = true
  try {
    if (professionForm.id != null) {
      if (!professionForm.code.trim() || !professionForm.name.trim()) return ElMessage.warning('请填写专业编码和专业名称')
      const { id, ...payload } = professionForm
      await updateWorkspaceProfession(id, payload)
      ElMessage.success('专业已保存')
    } else {
      const lines = professionBatchText.value.split(/\r?\n/)
        .map((value, index) => ({ value: value.trim(), lineNumber: index + 1 }))
        .filter((item) => item.value)
      if (!lines.length) return ElMessage.warning('请至少填写一条专业信息')
      const rows = []
      const invalidLineNumbers = []
      lines.forEach(({ value: line, lineNumber }, index) => {
        const separator = line.search(/[\t,，|]/)
        if (separator < 1 || !line.slice(separator + 1).trim()) {
          invalidLineNumbers.push(lineNumber)
          return
        }
        rows.push({
          code: line.slice(0, separator).trim(),
          name: line.slice(separator + 1).trim(),
          sortOrder: Number(professionForm.sortOrder) + index,
          isEnabled: professionForm.isEnabled,
        })
      })
      if (invalidLineNumbers.length) return ElMessage.warning(`第 ${invalidLineNumbers.join('、')} 行格式不正确，请按“专业编码,专业名称”填写`)
      const duplicatedCodes = rows.map((item) => item.code.toLocaleLowerCase())
      const duplicatedNames = rows.map((item) => item.name.toLocaleLowerCase())
      if (new Set(duplicatedCodes).size !== rows.length || new Set(duplicatedNames).size !== rows.length) return ElMessage.warning('新增列表中存在重复的专业编码或名称')
      await createWorkspaceProfessions({ professions: rows })
      ElMessage.success(`已新增 ${rows.length} 个专业`)
    }
    entityDialogVisible.value = false
    Object.assign(professionForm, { id: null, code: '', name: '', sortOrder: 1, isEnabled: true })
    professionBatchText.value = ''
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '专业保存失败')) } finally { saving.value = false }
}
const saveProject = async () => {
  if (!projectForm.lineId || !projectForm.code.trim() || !projectForm.name.trim()) return ElMessage.warning('请填写所属线路、项目编码和项目名称')
  saving.value = true
  try {
    const { id, ...payload } = projectForm
    payload.sortOrder = Number(payload.sortOrder) || context.value.projects.length + 1
    let savedProject
    if (id != null) savedProject = (await updateWorkspaceProject(id, payload)).data?.data
    else savedProject = (await createWorkspaceProject(payload)).data?.data
    ElMessage.success(id != null ? '联调项目已保存' : '联调项目已新增')
    entityDialogVisible.value = false
    Object.assign(projectForm, { id: null, professionId: null, code: '', name: '', description: '', engineCode: '', isEnabled: true })
    await workspace.reload()
    if (savedProject) {
      workspace.setLine(savedProject.lineId)
      workspace.setProject(savedProject.id)
    }
    await load()
  } catch (error) { ElMessage.error(await errorMessage(error, '联调项目保存失败')) } finally { saving.value = false }
}
const toggleLine = async (item, isEnabled) => saveEnabledState(item, isEnabled, updateWorkspaceLine, '线路')
const toggleProfession = async (item, isEnabled) => saveEnabledState(item, isEnabled, updateWorkspaceProfession, '专业')
const toggleProject = async (item, isEnabled) => saveEnabledState(item, isEnabled, updateWorkspaceProject, '联调项目')
const saveEnabledState = async (item, isEnabled, update, label) => {
  saving.value = true
  try {
    const { id, ...payload } = item
    await update(id, { ...payload, isEnabled })
    item.isEnabled = isEnabled
    ElMessage.success(`${label}已${isEnabled ? '启用' : '停用'}`)
    await load()
    await workspace.reload()
  } catch (error) {
    ElMessage.error(await errorMessage(error, `${label}状态更新失败`))
    await load()
  } finally { saving.value = false }
}
const openCreateEntity = (type, copyProject = false) => {
  entityType.value = type
  projectCopyMode.value = type === 'project' && copyProject
  if (type === 'line') Object.assign(lineForm, { id: null, code: '', name: '', sortOrder: context.value.lines.length + 1, isEnabled: true })
  if (type === 'profession') {
    Object.assign(professionForm, {
      id: null, code: '', name: '',
      sortOrder: Math.max(0, ...context.value.professions.map((item) => Number(item.sortOrder) || 0)) + 1,
      isEnabled: true,
    })
    professionBatchText.value = ''
  }
  if (type === 'project') {
    const lineId = context.value.lines.find((item) => String(item.id) === String(context.value.currentUser?.lineId))?.id ?? workspace.selectedLineId ?? context.value.lines.find((item) => item.isEnabled)?.id ?? null
    const nextProjectOrder = Math.max(0, ...lineProjects(lineId).map((item) => Number(item.sortOrder) || 0)) + 1
    Object.assign(projectForm, { id: null, lineId, professionId: context.value.professions.find((item) => String(item.id) === String(context.value.currentUser?.professionId))?.id ?? workspace.selectedProfessionId ?? context.value.professions.find((item) => item.isEnabled)?.id ?? null, code: '', name: '', description: '', engineCode: '', sortOrder: nextProjectOrder, isEnabled: true })
  }
  entityDialogVisible.value = true
}
const editLine = (item) => { entityType.value = 'line'; Object.assign(lineForm, { id: item.id, code: item.code, name: item.name, sortOrder: item.sortOrder, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
const editProfession = (item) => { entityType.value = 'profession'; professionBatchText.value = ''; Object.assign(professionForm, { id: item.id, code: item.code, name: item.name, sortOrder: item.sortOrder, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
const editProject = (item) => { entityType.value = 'project'; Object.assign(projectForm, { id: item.id, lineId: item.lineId, professionId: item.professionId, code: item.code, name: item.name, description: item.description, engineCode: item.engineCode, sortOrder: item.sortOrder, isEnabled: item.isEnabled }); entityDialogVisible.value = true }
onMounted(load)
</script>

<template>
  <div class="workspace admin-page">
    <header class="page-title admin-title">
      <div><h1>系统管理</h1><p>管理系统账号和线路、专业、联调项目基础信息。</p></div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </header>
    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane v-if="isSuperAdmin" label="账号管理" name="accounts">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="账号按照角色绑定线路和专业，配置权限由工作范围自动控制。" />
        <el-card class="section-card admin-card">
          <template #header><div class="table-header"><strong>账号列表</strong><el-button type="primary" :icon="Plus" @click="openCreateUser">新增账号</el-button></div></template>
          <el-collapse v-loading="loading" accordion class="account-groups"><el-collapse-item v-for="group in groupedUsers" :key="group.label" :title="`${group.label}（${group.members.length}）`" :name="group.label"><el-table :data="group.members" stripe><el-table-column prop="username" label="用户名" min-width="150" /><el-table-column prop="displayName" label="显示名称" min-width="140" /><el-table-column label="角色" min-width="150"><template #default="{ row }">{{ { super_admin: '超级管理员', line_admin: '线路管理员', professional_configurator: '专业配置员' }[row.role] || row.role }}</template></el-table-column><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'">{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="90" fixed="right" align="center"><template #default="{ row }"><el-button text type="primary" :icon="EditPen" @click="editUser(row)">编辑</el-button></template></el-table-column></el-table></el-collapse-item><el-empty v-if="!groupedUsers.length" description="暂无账号" /></el-collapse>
        </el-card>
      </el-tab-pane>
      <el-tab-pane v-if="isSuperAdmin" label="线路管理" name="lines">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="线路是配置数据的第一层范围；不同线路之间的数据相互隔离。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>线路列表</strong><span class="table-hint">共 {{ context.lines.length }} 条线路</span></div><el-button type="primary" :icon="Plus" @click="openCreateEntity('line')">新增线路</el-button></div></template><el-table v-loading="loading || saving" :data="[...context.lines].sort(compareSortOrder)" stripe empty-text="暂无线路"><el-table-column prop="name" label="线路名称" min-width="180" /><el-table-column prop="code" label="线路编码" min-width="120" /><el-table-column prop="sortOrder" label="排序" width="90" /><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="180" fixed="right" align="center"><template #default="{ row }"><div class="entity-row-actions"><el-button text type="primary" :icon="EditPen" @click="editLine(row)">编辑</el-button><el-switch :model-value="row.isEnabled" inline-prompt active-text="启用" inactive-text="停用" @change="toggleLine(row, $event)" /></div></template></el-table-column></el-table></el-card>
      </el-tab-pane>
      <el-tab-pane label="专业管理" name="professions">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="专业目录目前由所有线路共用；新增、修改或停用会影响全系统专业选择。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>专业列表</strong><span class="table-hint">共 {{ context.professions.length }} 个专业</span></div><el-button v-if="isSuperAdmin || isLineAdmin" type="primary" :icon="Plus" @click="openCreateEntity('profession')">新增专业</el-button></div></template><el-table v-loading="loading || saving" :data="[...context.professions].sort(compareSortOrder)" stripe empty-text="暂无专业"><el-table-column prop="name" label="专业名称" min-width="180" /><el-table-column prop="code" label="专业编码" min-width="120" /><el-table-column prop="sortOrder" label="排序" width="90" /><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column v-if="isSuperAdmin || isLineAdmin" label="操作" width="180" fixed="right" align="center"><template #default="{ row }"><div class="entity-row-actions"><el-button text type="primary" :icon="EditPen" @click="editProfession(row)">编辑</el-button><el-switch :model-value="row.isEnabled" inline-prompt active-text="启用" inactive-text="停用" @change="toggleProfession(row, $event)" /></div></template></el-table-column></el-table></el-card>
      </el-tab-pane>
      <el-tab-pane label="联调项目管理" name="projects">
        <el-alert class="admin-notice" type="info" :closable="false" show-icon title="联调项目按线路管理；停用后会从工作范围选择器中隐藏，但仍可在此列表查看并重新启用。" />
        <el-card shadow="never" class="section-card admin-card"><template #header><div class="table-header"><div><strong>联调项目列表</strong><span class="table-hint">当前授权线路 {{ managedProjects.length }} 个项目</span></div><div class="project-actions"><el-button :icon="CopyDocument" @click="openCreateEntity('project', true)">复制其他线路项目</el-button><el-button type="primary" :icon="Plus" @click="openCreateEntity('project')">新增联调项目</el-button></div></div></template><el-collapse v-loading="loading || saving" accordion class="project-groups"><el-collapse-item v-for="group in managedProjectGroups" :key="group.key" :name="group.key" :title="`${group.lineName}（${group.projects.length}）`"><el-table :data="group.projects" stripe empty-text="该线路暂无联调项目"><el-table-column prop="name" label="项目名称" min-width="190" /><el-table-column prop="code" label="项目编码" min-width="120" /><el-table-column prop="sortOrder" label="排序" width="90" /><el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="180" fixed="right" align="center"><template #default="{ row }"><div class="entity-row-actions"><el-button v-if="canEditProject(row)" text type="primary" :icon="EditPen" @click="editProject(row)">编辑</el-button><el-switch v-if="canEditProject(row)" :model-value="row.isEnabled" inline-prompt active-text="启用" inactive-text="停用" @change="toggleProject(row, $event)" /></div></template></el-table-column></el-table></el-collapse-item><el-empty v-if="!managedProjectGroups.length" description="当前授权线路暂无联调项目" /></el-collapse></el-card>
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
      <template v-if="entityType === 'line'"><div class="admin-grid admin-grid-two"><el-form-item label="线路编码" required><el-input v-model="lineForm.code" placeholder="例如 9" /></el-form-item><el-form-item label="线路名称" required><el-input v-model="lineForm.name" placeholder="例如 9号线" /></el-form-item><el-form-item label="排序" required><el-input-number v-model="lineForm.sortOrder" :min="1" :precision="0" controls-position="right" /></el-form-item><el-form-item label="状态"><el-switch v-model="lineForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></div></template>
      <template v-else-if="entityType === 'profession'"><template v-if="professionForm.id != null"><div class="admin-grid admin-grid-two"><el-form-item label="专业编码" required><el-input v-model="professionForm.code" placeholder="例如 ZDH" /></el-form-item><el-form-item label="专业名称" required><el-input v-model="professionForm.name" placeholder="例如 自动化" /></el-form-item><el-form-item label="排序" required><el-input-number v-model="professionForm.sortOrder" :min="1" :precision="0" controls-position="right" /></el-form-item><el-form-item label="状态"><el-switch v-model="professionForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></div></template><template v-else><el-form-item label="专业编码、专业名称" required><el-input v-model="professionBatchText" type="textarea" :rows="6" resize="vertical" placeholder="每行填写一条，格式：专业编码,专业名称&#10;例如：&#10;ZDH,自动化&#10;TX,通信&#10;FSD,风水电" /></el-form-item><div class="batch-entry-footer"><el-form-item label="起始排序" required><el-input-number v-model="professionForm.sortOrder" :min="1" :precision="0" controls-position="right" /></el-form-item><el-form-item label="新增后状态"><el-switch v-model="professionForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item><span class="batch-entry-hint">每行新增一条，排序号按输入顺序递增。</span></div></template></template>
      <template v-else>
        <el-alert v-if="editingProject" class="admin-notice" type="info" :closable="false" show-icon title="项目按线路归属；修改项目编码只影响后续新增配置，已有业务显示 ID 保持不变。" />
        <div v-if="!editingProject" class="admin-grid admin-grid-two">
          <el-form-item :label="projectCopyMode ? '选择来源项目' : '从其他线路复制项目（可选）'">
            <el-select filterable clearable placeholder="选择已启用项目，复制名称和编码后保存为本线路项目" @change="(id) => { const source = context.projects.find((item) => String(item.id) === String(id)); if (source) Object.assign(projectForm, { code: source.code, name: source.name, description: source.description, engineCode: source.engineCode }) }">
              <el-option v-for="item in context.projects.filter((project) => project.isEnabled !== false && String(project.lineId) !== String(projectForm.lineId))" :key="item.id" :label="`${context.lines.find((line) => line.id === item.lineId)?.name || ''} / ${item.code} · ${item.name}`" :value="item.id" />
            </el-select>
          </el-form-item>
        </div>
        <div class="admin-grid admin-grid-two">
          <el-form-item label="所属线路" required><el-select v-model="projectForm.lineId" :disabled="isSuperAdmin ? false : projectLines.length <= 1" placeholder="选择线路"><el-option v-for="item in projectLines" :key="item.id" :label="item.name" :value="item.id" :disabled="item.isEnabled === false && String(item.id) !== String(projectForm.lineId)" /></el-select></el-form-item>
          <el-form-item label="项目编码" required><el-input v-model="projectForm.code" placeholder="例如 T19" /></el-form-item>
          <el-form-item label="项目名称" required><el-input v-model="projectForm.name" placeholder="例如 FAS系统测试" /></el-form-item>
          <el-form-item label="排序" required><el-input-number v-model="projectForm.sortOrder" :min="1" :precision="0" controls-position="right" /></el-form-item>
        </div>
        <el-form-item label="项目说明"><el-input v-model="projectForm.description" placeholder="选填" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="projectForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item>
      </template>
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
.project-groups :deep(.el-collapse-item__header) { height: 50px; padding: 0 18px; color: #29466e; font-weight: 700; background: #f7f9fc; }
.project-groups :deep(.el-collapse-item__wrap) { border-bottom: 0; }
.project-groups :deep(.el-collapse-item__content) { padding: 0; }
.project-groups :deep(.el-table) { border: 0; }
.admin-card :deep(.el-card__header) { padding: 17px 22px; }
.card-heading strong { display: block; color: #2d405e; font-size: 15px; }
.card-heading span { display: block; margin-top: 5px; color: #8a98aa; font-size: 12px; }
.table-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.project-actions { display:flex;align-items:center;gap:8px; }
.entity-row-actions { display:flex;align-items:center;justify-content:center;gap:12px; }
.batch-entry-footer { display:grid;grid-template-columns:160px 180px 1fr;align-items:end;gap:18px; }
.batch-entry-footer :deep(.el-form-item) { margin-bottom:0; }
.batch-entry-footer :deep(.el-input-number) { width:100%; }
.batch-entry-hint { padding-bottom:11px;color:#8491a5;font-size:12px; }
.table-header > div { display:flex;align-items:center;gap:10px; }.table-hint { color:#8a98aa;font-size:12px;font-weight:400; }
.admin-form { max-width: 100%; }
.admin-grid { display: grid; gap: 0 18px; }
.admin-grid-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.admin-grid-two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.admin-page :deep(.el-input__wrapper), .admin-page :deep(.el-select__wrapper), .admin-page :deep(.el-input-number) { min-height: 40px; }
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
@media (max-width: 700px) { .batch-entry-footer { grid-template-columns:1fr 1fr; }.batch-entry-hint { grid-column:1 / -1;padding-bottom:0; } }
@media (max-width: 560px) { .admin-grid-three, .admin-grid-two, .batch-entry-footer { grid-template-columns: 1fr; }.admin-title { align-items: center; }.project-actions { flex-wrap:wrap; }.batch-entry-hint { grid-column:auto; } }
</style>
