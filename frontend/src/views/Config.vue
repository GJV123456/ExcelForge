<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowDown, CopyDocument, Download, EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'
import { useWorkspaceStore } from '../store/workspace'
import { useUserStore } from '../store/user'
import { batchCopyWorkspaceConfigs, createWorkspaceConfig, downloadWorkspaceConfigTemplate, downloadWorkspaceTemplate, getWorkspaceCatalog, getWorkspaceConfigs, getWorkspaceDebugItems, importWorkspaceConfigs, previewWorkspaceConfigImport, setWorkspaceConfigStatus, updateWorkspaceConfig } from '../api/workspace'
import { downloadResponseBlob } from '../utils/download'
import { getApiErrorMessage } from '../utils/httpError'
import WorkspaceScopePicker from '../components/WorkspaceScopePicker.vue'
import LegacyConfig from './LegacyConfig.vue'
import WorkspaceCatalog from '../components/WorkspaceCatalog.vue'
import WorkspaceDebugCatalog from '../components/WorkspaceDebugCatalog.vue'
import './config-page.css'

const workspace = useWorkspaceStore(); const user = useUserStore()
const sameId = (left, right) => left != null && right != null && String(left) === String(right)
const configs = ref([]); const loading = ref(false); const saving = ref(false); const copying = ref(false); const copyCandidatesLoading = ref(false); const dialogVisible = ref(false); const copyVisible = ref(false); const importPreviewVisible = ref(false); const filter = ref(''); const editingId = ref(''); const selectedConfigId = ref(null); const sourceConfigs = ref([]); const copySelection = ref([]); const copySearchInput = ref(''); const copySearchKeyword = ref(''); const expandedCopyGroupKey = ref(null); const importRows = ref([]); const importPreview = ref({ conflicts: [], newCodes: [] }); const importDecisions = reactive({})
const scope = computed(() => ({ lineId: workspace.selectedLineId, professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId, debugSubitemId: workspace.selectedDebugSubitemId, debugDivisionId: workspace.selectedDebugDivisionId }))
const canEdit = computed(() => user.userInfo.role === 'super_admin' || (user.userInfo.role === 'line_admin' && sameId(user.userInfo.lineId, workspace.selectedLineId)) || (user.userInfo.role === 'professional_configurator' && sameId(user.userInfo.lineId, workspace.selectedLineId) && sameId(user.userInfo.professionId, workspace.selectedProfessionId)))
const isLegacyConfigAllowed = computed(() => {
  if (user.userInfo.role === 'super_admin') return true
  const legacyLine = workspace.lines.find((item) => item.code === '9')
  const legacyProfession = workspace.professions.find((item) => item.code.toUpperCase() === 'ZDH')
  if (!legacyLine || !legacyProfession) return false
  if (user.userInfo.role === 'line_admin') return sameId(user.userInfo.lineId, legacyLine.id) && sameId(workspace.selectedLineId, legacyLine.id) && sameId(workspace.selectedProfessionId, legacyProfession.id)
  return user.userInfo.role === 'professional_configurator'
    && sameId(user.userInfo.lineId, legacyLine.id)
    && sameId(user.userInfo.professionId, legacyProfession.id)
    && sameId(workspace.selectedLineId, legacyLine.id)
    && sameId(workspace.selectedProfessionId, legacyProfession.id)
})
const activeConfigTab = ref('workspace')
const activeSubmenu = ref('config')
let configRequestId = 0
const visibleConfigs = computed(() => { const keyword = filter.value.trim().toLowerCase(); return keyword ? configs.value.filter((item) => [item.businessId, item.configCode, item.description].join(' ').toLowerCase().includes(keyword)) : configs.value })
const selectedConfig = computed(() => visibleConfigs.value.find((item) => item.id === selectedConfigId.value) || visibleConfigs.value[0] || null)
const filteredCopyConfigs = computed(() => {
  const keyword = copySearchKeyword.value.trim().toLocaleLowerCase()
  if (!keyword) return sourceConfigs.value
  return sourceConfigs.value.filter((item) => [item.configCode, item.businessId, item.sourceLineName, item.sourceProfessionName, item.sourceProjectCode, item.sourceProjectName].join(' ').toLocaleLowerCase().includes(keyword))
})
const copyConfigGroups = computed(() => {
  const groups = new Map()
  filteredCopyConfigs.value.forEach((item) => {
    const key = `${item.lineId}::${item.projectId}`
    if (!groups.has(key)) groups.set(key, { key, line: item.sourceLineName, code: item.sourceProjectCode, name: item.sourceProjectName, items: [] })
    groups.get(key).items.push(item)
  })
  return [...groups.values()]
})
const allVisibleCopySelected = computed(() => filteredCopyConfigs.value.length > 0 && filteredCopyConfigs.value.every((item) => copySelection.value.includes(item.id)))
const form = reactive({ professionId: null, projectId: null, debugSubitemId: null, debugDivisionId: null, configCode: '', description: '', isEnabled: true, steps: [] })
const responsibleDisciplineOptions = ref([])
const formSubitems = ref([])
const formDivisions = ref([])
let editorCatalogRequestId = 0
const editableProfessions = computed(() => {
  if (user.userInfo.role === 'super_admin' || user.userInfo.role === 'line_admin') return workspace.professions
  return workspace.professions.filter((item) => item.id === user.userInfo.professionId)
})
const formProjects = computed(() => workspace.projects.filter((item) => !item.lineId || sameId(item.lineId, workspace.selectedLineId)))
let editorItemSequence = 0
const editorKey = () => `editor-item-${++editorItemSequence}`
const onFormProfessionChange = () => { form.projectId = formProjects.value[0]?.id ?? null }
const loadEditorCatalogOptions = async () => {
  const requestId = ++editorCatalogRequestId
  if (!dialogVisible.value || !workspace.selectedLineId || !form.professionId || !form.projectId) {
    responsibleDisciplineOptions.value = []
    return
  }
  try {
    const base = { lineId: workspace.selectedLineId, professionId: form.professionId, projectId: form.projectId }
    const [disciplineResponse, subitemResponse] = await Promise.all([
      getWorkspaceCatalog({ ...base, category: 'disciplines' }),
      getWorkspaceDebugItems({ ...base, category: 'debug_subitems' })
    ])
    if (requestId === editorCatalogRequestId) {
      formSubitems.value = subitemResponse.data?.data || []
      if (form.debugSubitemId && !formSubitems.value.some((item) => item.id === form.debugSubitemId)) form.debugSubitemId = null
      formDivisions.value = form.debugSubitemId
        ? (await getWorkspaceDebugItems({ ...base, category: 'debug_divisions', parentId: form.debugSubitemId })).data?.data || []
        : []
      if (form.debugDivisionId && !formDivisions.value.some((item) => item.id === form.debugDivisionId)) form.debugDivisionId = null
      responsibleDisciplineOptions.value = (disciplineResponse.data?.data || []).filter((item) => item.isEnabled !== false)
        .map((item) => ({ value: item.name }))
      const defaultDiscipline = responsibleDisciplineOptions.value.find((item) => item.value === '自动化')?.value
      if (defaultDiscipline) {
        form.steps.forEach((step) => step.results.forEach((result) => {
          if (!result.responsibleDisciplines?.length) result.responsibleDisciplines = [defaultDiscipline]
        }))
      }
    }
  } catch {
    if (requestId === editorCatalogRequestId) {
      responsibleDisciplineOptions.value = []
    }
  }
}
const setResultDiscipline = (result, value) => {
  result.responsibleDisciplines = value ? [value] : []
}
const onFormSubitemChange = async () => {
  form.debugDivisionId = null
  formDivisions.value = []
  if (!form.debugSubitemId || !workspace.selectedLineId || !form.professionId || !form.projectId) return
  const base = { lineId: workspace.selectedLineId, professionId: form.professionId, projectId: form.projectId }
  formDivisions.value = (await getWorkspaceDebugItems({ ...base, category: 'debug_divisions', parentId: form.debugSubitemId })).data?.data || []
}
const blankStep = () => ({ _editorKey: editorKey(), description: '', ratioChange: '否', sortOrder: 1, isEnabled: true, results: [{ _editorKey: editorKey(), description: '', responsibleDisciplines: [] }] })
const resetForm = () => { editingId.value = ''; Object.assign(form, { professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId, debugSubitemId: workspace.selectedDebugSubitemId, debugDivisionId: workspace.selectedDebugDivisionId, configCode: '', description: '', isEnabled: true, steps: [blankStep()] }) }
const openCreate = () => { resetForm(); dialogVisible.value = true }
const openEdit = (row) => {
  editingId.value = row.id
  const data = JSON.parse(JSON.stringify({ professionId: row.professionId, projectId: row.projectId, debugSubitemId: row.debugSubitemId, debugDivisionId: row.debugDivisionId, configCode: row.configCode, description: row.description, isEnabled: row.isEnabled, steps: row.steps }))
  data.steps = data.steps.map((step) => ({ ...step, _editorKey: editorKey(), results: step.results.map((result) => ({ ...result, _editorKey: editorKey() })) }))
  Object.assign(form, data)
  dialogVisible.value = true
}
const addStep = () => form.steps.push({ ...blankStep(), sortOrder: form.steps.length + 1 })
const removeStep = (index) => { if (form.steps.length > 1) form.steps.splice(index, 1) }
const addResult = (step) => step.results.push({ _editorKey: editorKey(), description: '', responsibleDisciplines: [] })
const removeResult = (step, index) => { if (step.results.length > 1) step.results.splice(index, 1) }
const load = async () => {
  const requestId = ++configRequestId
  if (!workspace.isSelected) { configs.value = []; selectedConfigId.value = null; loading.value = false; return }
  loading.value = true
  try {
    const response = await getWorkspaceConfigs({ ...scope.value, includeDisabled: true })
    if (requestId !== configRequestId) return
    configs.value = response.data?.data || []
    if (!configs.value.some((item) => item.id === selectedConfigId.value)) selectedConfigId.value = configs.value[0]?.id ?? null
  } catch (error) {
    if (requestId === configRequestId) ElMessage.error(await getApiErrorMessage(error))
  } finally {
    if (requestId === configRequestId) loading.value = false
  }
}
const save = async () => {
  if (!form.professionId) return ElMessage.warning('请选择所属专业')
  if (!form.projectId) return ElMessage.warning('请选择联调项目')
  if (!form.debugSubitemId) return ElMessage.warning('请选择调试子项')
  if (!form.configCode.trim()) return ElMessage.warning('请输入联调配置编码')
  if (!form.steps.length || form.steps.some((step) => !step.description.trim() || step.results.some((result) => !result.description.trim()))) return ElMessage.warning('每个配置必须填写操作步骤和预期结果')
  saving.value = true
  try {
    const selectedScope = { lineId: workspace.selectedLineId, professionId: form.professionId, projectId: form.projectId, debugSubitemId: form.debugSubitemId, debugDivisionId: form.debugDivisionId }
    const payload = { scope: selectedScope, debugSubitemId: form.debugSubitemId, debugDivisionId: form.debugDivisionId, configCode: form.configCode.trim(), description: form.description, isEnabled: form.isEnabled, steps: form.steps.map((step, index) => ({ description: step.description.trim(), ratioChange: step.ratioChange || '否', sortOrder: index + 1, isEnabled: step.isEnabled ?? true, results: step.results.map((result) => ({ description: result.description.trim(), responsibleDisciplines: result.responsibleDisciplines || [] })) })) }
    if (editingId.value) await updateWorkspaceConfig(editingId.value, payload); else await createWorkspaceConfig(payload)
    if (!editingId.value) {
      workspace.setProfession(form.professionId)
      workspace.setProject(form.projectId)
    }
    dialogVisible.value = false; ElMessage.success('配置已保存'); await load()
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { saving.value = false }
}
const toggle = async (row, enabled) => { const previous = row.isEnabled; row.isEnabled = enabled; try { await setWorkspaceConfigStatus(row.id, enabled); ElMessage.success(enabled ? '配置已启用' : '配置已停用') } catch (error) { row.isEnabled = previous; ElMessage.error(await getApiErrorMessage(error)) } }
const editSelected = () => { if (selectedConfig.value) openEdit(selectedConfig.value) }
const loadCopyCandidates = async () => {
    const projects = workspace.projects
  const linesById = new Map(workspace.lines.map((item) => [String(item.id), item]))
  const professionsById = new Map(workspace.professions.map((item) => [String(item.id), item]))
  copyVisible.value = true
  copyCandidatesLoading.value = true
  try {
    const sources = projects.flatMap((project) => workspace.professions.map((profession) => ({ project, profession })))
    const responses = new Array(sources.length)
    let nextProjectIndex = 0
    const workers = Array.from({ length: Math.min(8, sources.length) }, async () => {
      while (nextProjectIndex < sources.length) {
        const index = nextProjectIndex++
        const { project, profession } = sources[index]
        const response = await getWorkspaceConfigs({ lineId: project.lineId, professionId: profession.id, projectId: project.id })
        const line = linesById.get(String(project.lineId))
        responses[index] = (response.data?.data || []).map((item) => ({
          ...item,
          sourceLineName: line?.name || `线路 ${project.lineId}`,
          sourceProfessionName: profession?.name || `专业 ${project.professionId}`,
          sourceProjectCode: project.code,
          sourceProjectName: project.name,
        }))
      }
    })
    await Promise.all(workers)
    sourceConfigs.value = responses.flat().filter((item) => item.lineId !== workspace.selectedLineId || item.professionId !== workspace.selectedProfessionId || item.projectId !== workspace.selectedProjectId)
    expandedCopyGroupKey.value = copyConfigGroups.value[0]?.key || null
    copySelection.value = []
    copySearchInput.value = ''
    copySearchKeyword.value = ''
  } catch (error) { copyVisible.value = false; ElMessage.error(await getApiErrorMessage(error)) } finally { copyCandidatesLoading.value = false }
}
const applyCopySearch = () => { copySearchKeyword.value = copySearchInput.value }
const selectVisibleCopyConfigs = (selected) => {
  const visibleIds = filteredCopyConfigs.value.map((item) => item.id)
  const selectedIds = new Set(copySelection.value)
  if (selected) visibleIds.forEach((id) => selectedIds.add(id))
  else visibleIds.forEach((id) => selectedIds.delete(id))
  copySelection.value = [...selectedIds]
}
const selectCopyGroup = (group, selected) => {
  const ids = new Set(copySelection.value)
  group.items.forEach((item) => selected ? ids.add(item.id) : ids.delete(item.id))
  copySelection.value = [...ids]
}
const toggleCopyGroup = (key) => { expandedCopyGroupKey.value = expandedCopyGroupKey.value === key ? null : key }
const copySelected = async () => {
  if (!copySelection.value.length) return ElMessage.warning('请选择要复制的配置')
  copying.value = true
  try {
    const response = await batchCopyWorkspaceConfigs({ sourceConfigIds: copySelection.value, target: scope.value })
    const copied = response.data?.data || []
    copyVisible.value = false
    workspace.setDebugSubitem(null)
    await load()
    ElMessage.success(copied.length ? `已复制或补齐 ${copied.length} 条配置，列表已更新` : '所选配置已存在于当前项目，未重复复制')
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { copying.value = false }
}
const downloadTemplate = async () => { try { downloadResponseBlob(await downloadWorkspaceTemplate()); ElMessage.success('测试数据导入模板已下载') } catch { ElMessage.error('测试数据导入模板下载失败') } }
const downloadConfigTemplate = async () => { try { downloadResponseBlob(await downloadWorkspaceConfigTemplate(scope.value)); ElMessage.success('联调配置规范模板（含样例）已下载') } catch { ElMessage.error('联调配置规范模板下载失败') } }
const downloadTemplateChoice = (choice) => choice === 'config' ? downloadConfigTemplate() : downloadTemplate()
const importConfigFile = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' })
    if (!rows.length) return ElMessage.warning('配置规范表没有可导入的数据')
    importRows.value = rows
    Object.keys(importDecisions).forEach((key) => delete importDecisions[key])
    const preview = await previewWorkspaceConfigImport({ scope: scope.value, rows })
    importPreview.value = preview.data?.data || { conflicts: [], newCodes: [] }
    ;(importPreview.value.conflicts || []).forEach((item) => { importDecisions[item.configCode.toLowerCase()] = 'skip' })
    if ((importPreview.value.conflicts || []).length) importPreviewVisible.value = true
    else { const response = await importWorkspaceConfigs({ scope: scope.value, rows, decisions: {} }); ElMessage.success(`已导入 ${response.data?.data?.length || 0} 条联调配置（${rows.length} 行结果）`); await load() }
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) }
}
const setAllImportDecisions = (decision) => {
  const conflicts = importPreview.value.conflicts || []
  conflicts.forEach((item) => {
    importDecisions[item.configCode.toLowerCase()] = decision
  })
  ElMessage.success(decision === 'overwrite'
    ? `已选择全部覆盖（${conflicts.length} 条）`
    : `已选择全部跳过（${conflicts.length} 条）`)
}
const importConflictCount = computed(() => (importPreview.value.conflicts || []).length)
const importNewCount = computed(() => (importPreview.value.newCodes || []).length)
const importOverwriteCount = computed(() => (importPreview.value.conflicts || []).filter((item) => importDecisions[item.configCode.toLowerCase()] === 'overwrite').length)
const commitImport = async () => {
  saving.value = true
  try { const response = await importWorkspaceConfigs({ scope: scope.value, rows: importRows.value, decisions: { ...importDecisions } }); importPreviewVisible.value = false; ElMessage.success(`已导入 ${response.data?.data?.length || 0} 条联调配置，冲突项按选择处理`); await load() }
  catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { saving.value = false }
}
onMounted(load)
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId, workspace.selectedDebugSubitemId, workspace.selectedDebugDivisionId], load)
watch(() => [dialogVisible.value, workspace.selectedLineId, form.professionId, form.projectId], ([isOpen]) => {
  if (isOpen) loadEditorCatalogOptions()
  else editorCatalogRequestId += 1
})
</script>

<template>
  <div class="workspace workspace-config-page">
    <div class="config-page-heading">
      <div class="config-heading-row">
        <div><h1>联调表单配置管理</h1><p>管理当前线路、专业和联调项目下的配置编码、操作步骤和预期结果。</p></div>
      </div>
      <div class="config-toolbar">
        <div class="config-toolbar-group"><el-input v-model="filter" clearable placeholder="搜索配置编码" /><el-button :icon="Refresh" @click="load">刷新</el-button></div>
        <div class="config-toolbar-group config-toolbar-actions">
          <el-dropdown @command="downloadTemplateChoice"><el-button :icon="Download">模板下载<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="data">测试数据导入模板</el-dropdown-item><el-dropdown-item command="config">联调配置规范模板（含样例）</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
          <label v-if="canEdit" class="upload-config-button"><input type="file" accept=".xlsx,.xls,.csv" @change="importConfigFile" />导入配置规范表</label>
          <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreate">新增配置</el-button>
          <el-button v-if="canEdit" :icon="CopyDocument" @click="loadCopyCandidates">复制其他线路联调规则配置</el-button>
        </div>
      </div>
    </div>
    <el-tabs v-model="activeConfigTab" class="config-tabs">
      <el-tab-pane label="联调表单配置规则" name="workspace">
        <nav class="config-submenu" aria-label="配置管理子菜单">
          <button v-for="item in [{ key: 'config', label: '联调规则配置' }, { key: 'debug', label: '联调项管理' }, { key: 'stations', label: '站点信息' }, { key: 'disciplines', label: '责任专业' }]" :key="item.key" type="button" :class="{ active: activeSubmenu === item.key }" :aria-current="activeSubmenu === item.key ? 'page' : undefined" @click="activeSubmenu = item.key">{{ item.label }}</button>
        </nav>
        <WorkspaceScopePicker compact :line-only="activeSubmenu === 'stations' || activeSubmenu === 'disciplines'" />
        <div class="config-section-content">
        <WorkspaceDebugCatalog v-if="activeSubmenu === 'debug'" />
        <WorkspaceCatalog v-else-if="activeSubmenu === 'stations'" :category="activeSubmenu" />
        <WorkspaceCatalog v-else-if="activeSubmenu === 'disciplines'" :category="activeSubmenu" />
        <div v-else class="config-code-content">
        <!-- <el-alert type="info" :closable="false" show-icon title="联调配置编码在当前线路、专业和项目下必须唯一；业务显示 ID 由系统自动生成且不可修改。导入时每行填写一个输出结果，用步骤序号把多个结果归到同一个操作步骤。" /> -->
        <div v-loading="loading" class="config-workbench">
          <aside class="config-sidebar">
            <div class="config-sidebar-heading"><strong>联调配置编码</strong><span>{{ visibleConfigs.length }} 条</span></div>
            <div class="config-menu">
              <button v-for="item in visibleConfigs" :key="item.id" type="button" class="config-menu-item" :class="{ active: selectedConfig?.id === item.id }" @click="selectedConfigId = item.id">
                <span class="config-menu-title">{{ item.configCode }}</span>
                <span class="config-menu-meta"><code>{{ item.businessId }}</code><span>{{ item.steps?.length || 0 }} 个步骤</span></span>
                <el-tag size="small" :type="item.isEnabled ? 'success' : 'info'" effect="plain">{{ item.isEnabled ? '启用' : '停用' }}</el-tag>
              </button>
              <el-empty v-if="!loading && !visibleConfigs.length" :image-size="72" description="当前范围暂无联调配置" />
            </div>
          </aside>
          <main class="config-detail">
            <el-empty v-if="!selectedConfig" :image-size="88" description="选择一条联调配置，或新增配置开始维护">
              <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreate">新增配置</el-button>
            </el-empty>
            <template v-else>
              <div class="config-detail-heading">
                <div><div class="config-detail-title"><h2>{{ selectedConfig.configCode }}</h2><el-tag :type="selectedConfig.isEnabled ? 'success' : 'info'" effect="plain">{{ selectedConfig.isEnabled ? '启用' : '停用' }}</el-tag></div><p>业务显示 ID：<code>{{ selectedConfig.businessId }}</code></p></div>
                <div class="config-detail-actions"><el-switch v-if="canEdit" :model-value="selectedConfig.isEnabled" active-text="启用" inactive-text="停用" inline-prompt @change="(enabled) => toggle(selectedConfig, enabled)" /><el-button v-if="canEdit" type="primary" :icon="EditPen" @click="editSelected">编辑配置</el-button></div>
              </div>
              <div class="config-summary-grid"><div class="config-summary-item"><span>配置编码</span><strong>{{ selectedConfig.configCode }}</strong></div><div class="config-summary-item"><span>操作步骤</span><strong>{{ selectedConfig.steps?.length || 0 }} 个</strong></div><div class="config-summary-item config-summary-wide"><span>说明</span><strong>{{ selectedConfig.description || '暂无说明' }}</strong></div></div>
              <div class="tree-heading"><div><h3>操作步骤与输出结果</h3><p>以下为当前配置的完整内容。</p></div></div>
              <div v-if="selectedConfig.steps?.length" class="steps-list">
                <section v-for="(step, stepIndex) in selectedConfig.steps" :key="step.id || stepIndex" class="step-card readonly-step-card">
                  <div class="step-heading"><strong class="step-number">步骤 {{ stepIndex + 1 }}</strong><div class="step-heading-summary"><el-tag size="small" effect="plain">是否变比：{{ step.ratioChange || '否' }}</el-tag><span class="result-count">{{ step.results?.length || 0 }} 个输出结果</span></div></div>
                  <p class="readonly-step-description">{{ step.description }}</p>
                  <div class="results-list"><article v-for="(result, resultIndex) in step.results || []" :key="result.id || resultIndex" class="result-row readonly-result-row"><span class="result-index">{{ resultIndex + 1 }}</span><span class="readonly-result-description">{{ result.description }}</span><span class="discipline-tags"><el-tag v-for="discipline in (result.responsibleDisciplines?.length ? result.responsibleDisciplines : ['自动化'])" :key="discipline" size="small" effect="plain">{{ discipline }}</el-tag></span></article></div>
                </section>
              </div>
              <el-empty v-else :image-size="72" description="该配置尚未添加操作步骤" />
            </template>
          </main>
        </div>
        </div>
        </div>
      </el-tab-pane>
      <el-tab-pane v-if="isLegacyConfigAllowed" label="原有设备与测试规则" name="legacy"><LegacyConfig v-if="activeConfigTab === 'legacy'" /></el-tab-pane>
    </el-tabs>
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑联调配置' : '新增联调配置'" width="min(860px, calc(100vw - 28px))" class="config-editor-dialog"><el-form label-position="top"><div class="rule-base-grid"><el-form-item label="所属专业" required><el-select v-model="form.professionId" :disabled="Boolean(editingId) || editableProfessions.length <= 1" placeholder="请选择专业" @change="onFormProfessionChange"><el-option v-for="item in editableProfessions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="联调项目" required><el-select v-model="form.projectId" :disabled="Boolean(editingId)" placeholder="请选择联调项目"><el-option v-for="item in formProjects" :key="item.id" :label="item.code" :value="item.id" /></el-select></el-form-item><el-form-item label="联调配置编码" required><el-input v-model="form.configCode" placeholder="例如：FAS-垂梯-状态反馈" /></el-form-item><el-form-item label="调试子项" required><el-select v-model="form.debugSubitemId" placeholder="请选择调试子项" @change="onFormSubitemChange"><el-option v-for="item in formSubitems" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="调试分项（可不选）"><el-select v-model="form.debugDivisionId" clearable placeholder="不选表示规则直接归属调试子项"><el-option v-for="item in formDivisions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item class="description-field" label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item></div><div class="steps-heading"><strong>操作步骤和预期结果</strong><el-button type="primary" plain :icon="Plus" @click="addStep">新增步骤</el-button></div><draggable v-model="form.steps" item-key="_editorKey" handle=".step-drag-handle" ghost-class="drag-ghost" chosen-class="drag-chosen" class="step-editor-list"><template #item="{ element: step, index }"><section class="step-editor"><div class="step-editor-title"><span class="step-drag-handle drag-grip" title="拖动调整步骤顺序" aria-label="拖动调整步骤顺序">⠿</span><span>步骤 {{ index + 1 }}</span><el-button v-if="form.steps.length > 1" text type="danger" @click="removeStep(index)">删除步骤</el-button></div><el-input v-model="step.description" placeholder="操作步骤" /><draggable v-model="step.results" item-key="_editorKey" handle=".result-drag-handle" ghost-class="drag-ghost" chosen-class="drag-chosen" class="result-editor-list"><template #item="{ element: result, index: resultIndex }"><div class="result-editor"><span class="result-drag-handle drag-grip" title="拖动调整输出结果顺序" aria-label="拖动调整输出结果顺序">⠿</span><span class="result-order">{{ resultIndex + 1 }}</span><el-input v-model="result.description" placeholder="预期结果" /><el-select :model-value="result.responsibleDisciplines?.[0] || ''" filterable clearable placeholder="选择责任专业" @update:model-value="setResultDiscipline(result, $event)"><el-option v-for="item in responsibleDisciplineOptions" :key="item.value" :label="item.value" :value="item.value" /></el-select><el-button text type="danger" @click="removeResult(step, resultIndex)">删除</el-button></div></template></draggable><el-button text type="primary" @click="addResult(step)">新增结果</el-button></section></template></draggable><el-form-item label="状态"><el-switch v-model="form.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存完整配置</el-button></template></el-dialog>
    <el-dialog v-model="importPreviewVisible" title="导入配置确认" width="min(760px, calc(100vw - 28px))" class="import-preview-dialog">
      <div class="import-preview-summary"><div><span>文件编码总数</span><strong>{{ importPreview.totalCodes || 0 }}</strong></div><div><span>已存在</span><strong class="is-warning">{{ importConflictCount }}</strong></div><div><span>可新增</span><strong class="is-success">{{ importNewCount }}</strong></div><div><span>已选择覆盖</span><strong>{{ importOverwriteCount }}</strong></div></div>
      <p class="import-preview-tip">以下编码已存在。选择覆盖会完整替换对应的操作步骤、输出结果和责任专业；未冲突编码会直接导入。</p>
      <div class="import-conflict-list"><div v-for="item in importPreview.conflicts" :key="item.configCode" class="import-conflict-row"><div class="import-conflict-code"><strong>{{ item.configCode }}</strong><el-tag size="small" type="warning" effect="plain">已存在</el-tag></div><el-radio-group v-model="importDecisions[item.configCode.toLowerCase()]"><el-radio-button label="skip">跳过</el-radio-button><el-radio-button label="overwrite">覆盖</el-radio-button></el-radio-group></div></div>
      <template #footer><el-button @click="importPreviewVisible = false">取消</el-button><el-button :type="importOverwriteCount === importConflictCount && importConflictCount ? 'primary' : 'default'" @click="setAllImportDecisions('overwrite')">{{ importOverwriteCount === importConflictCount && importConflictCount ? `已全部覆盖（${importConflictCount}）` : `全部覆盖（${importConflictCount}）` }}</el-button><el-button @click="setAllImportDecisions('skip')">{{ importOverwriteCount === 0 && importConflictCount ? `已全部跳过（${importConflictCount}）` : `全部跳过（${importConflictCount}）` }}</el-button><el-button type="primary" :loading="saving" @click="commitImport">确认导入</el-button></template>
    </el-dialog>
    <el-dialog v-model="copyVisible" title="复制其他线路 / 专业配置" width="min(820px, calc(100vw - 28px))" class="copy-config-dialog">
      <p class="copy-tip">按线路和联调项目分类展示。复制时会关联同名调试子项、分项；目标已有同编码时只补齐层级关联，保留已有步骤和结果。</p>
      <div class="copy-search-bar"><el-input v-model="copySearchInput" clearable placeholder="搜索项目、线路、专业或配置编码" @keyup.enter="applyCopySearch" @clear="applyCopySearch" /><el-button type="primary" plain @click="applyCopySearch">搜索</el-button></div>
      <div v-if="filteredCopyConfigs.length" class="copy-selection-toolbar"><el-checkbox :model-value="allVisibleCopySelected" @change="selectVisibleCopyConfigs">全选当前结果（{{ filteredCopyConfigs.length }}）</el-checkbox><span>已选 {{ copySelection.length }} 条</span></div>
      <div v-loading="copyCandidatesLoading" v-if="copyConfigGroups.length" class="copy-project-groups">
        <section v-for="group in copyConfigGroups" :key="group.key" class="copy-project-group">
          <header class="copy-project-heading" :aria-expanded="expandedCopyGroupKey === group.key" @click="toggleCopyGroup(group.key)" @keydown.enter.prevent="toggleCopyGroup(group.key)" tabindex="0" role="button"><div class="copy-project-title"><el-icon class="copy-project-chevron" :class="{ 'is-expanded': expandedCopyGroupKey === group.key }"><ArrowDown /></el-icon><strong>{{ group.line }} · {{ group.code }}<span v-if="group.name"> · {{ group.name }}</span></strong><small>{{ group.items.length }} 条配置</small></div><el-checkbox :model-value="group.items.every((item) => copySelection.includes(item.id))" @click.stop @change="selectCopyGroup(group, $event)">全选此项目</el-checkbox></header>
          <div v-if="expandedCopyGroupKey === group.key" class="copy-project-items"><el-checkbox v-for="item in group.items" :key="item.id" :model-value="copySelection.includes(item.id)" @change="(checked) => selectCopyGroup({ items: [item] }, checked)"><code>{{ item.configCode }}</code><span>{{ item.sourceLineName }} · {{ item.sourceProfessionName }}</span></el-checkbox></div>
        </section>
      </div>
      <el-empty v-else-if="!copyCandidatesLoading" :description="sourceConfigs.length ? '没有匹配的配置' : '其他线路或专业暂无可复制配置'" />
      <template #footer><el-button @click="copyVisible = false">取消</el-button><el-button type="primary" :loading="copying" :disabled="!copySelection.length" @click="copySelected">复制选中配置（{{ copySelection.length }}）</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tree-heading { display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin:22px 0 14px; }.tree-heading h3 { margin:0;color:#243653;font-size:17px; }.tree-heading p { margin:6px 0 0;color:#8290a4;font-size:13px; }.readonly-step-card { background:#fff; }.readonly-step-description { padding:18px 16px 12px;color:#2c3e5d;font-size:15px;line-height:1.7; }.readonly-result-row { grid-template-columns:28px minmax(0,1fr) auto; }.readonly-result-description { color:#3a4b66;line-height:1.6; }.discipline-tags { display:flex;justify-content:flex-end;flex-wrap:wrap;gap:5px; }.discipline-tags :deep(.el-tag) { margin:0; }.config-editor-dialog .step-editor { padding:16px;border:1px solid #dfe7f3;border-radius:12px;background:#fbfcff; }.config-editor-dialog .result-editor { padding-left:14px; }.config-editor-dialog .steps-heading { margin:8px 0 14px; }
.config-editor-dialog .result-editor :deep(.el-select) { flex:0 0 164px;width:164px; }
.step-editor-list,.result-editor-list { display:grid;gap:12px; }.drag-grip { display:inline-flex;align-items:center;justify-content:center;flex:0 0 24px;width:24px;height:28px;border:1px solid #dbe6f5;border-radius:6px;background:#fff;color:#8a9bb3;font-size:19px;line-height:1;cursor:grab;user-select:none; }.drag-grip:active { cursor:grabbing; }.config-editor-dialog .step-editor-title { justify-content:flex-start;gap:8px; }.config-editor-dialog .step-editor-title .el-button { margin-left:auto; }.config-editor-dialog .result-editor-list { margin-top:10px; }.config-editor-dialog .result-editor { display:flex;align-items:center;gap:8px;margin:0;padding:0; }.config-editor-dialog .result-editor :deep(.el-input) { flex:1;min-width:120px; }.result-order { display:inline-flex;align-items:center;justify-content:center;flex:0 0 24px;width:24px;height:24px;border-radius:50%;background:#edf4ff;color:#4a76b8;font-size:12px;font-weight:700; }.drag-ghost { opacity:.45;background:#edf4ff!important;border-color:#8db2fa!important; }.drag-chosen { box-shadow:0 8px 24px #31558d24; }
.import-preview-dialog :deep(.el-dialog__header) { margin-right:0;padding:22px 24px 14px;border-bottom:1px solid #edf1f6; }
.import-preview-dialog :deep(.el-dialog__body) { padding:20px 24px 8px; }
.import-preview-dialog :deep(.el-dialog__footer) { padding:14px 24px 20px;border-top:1px solid #edf1f6; }
.import-preview-summary { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px; }
.import-preview-summary > div { display:flex;flex-direction:column;gap:7px;padding:13px 15px;border:1px solid #e7edf5;border-radius:10px;background:#f8faff; }
.import-preview-summary span { color:#71819a;font-size:12px; }
.import-preview-summary strong { color:#253957;font-size:22px;line-height:1.15; }
.import-preview-summary strong.is-warning { color:#c27a16; }
.import-preview-summary strong.is-success { color:#2f8c68; }
.import-preview-tip { margin:16px 0 12px;color:#687992;font-size:13px;line-height:1.6; }
.import-conflict-list { display:grid;gap:8px;max-height:min(48vh,420px);overflow:auto;padding:2px 4px 4px 0; }
.import-conflict-row { display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:54px;padding:9px 12px;border:1px solid #e7edf5;border-radius:9px;background:#fff;transition:border-color .16s,background-color .16s; }
.import-conflict-row:has(.is-checked) { border-color:#91b7f5;background:#f6f9ff; }
.import-conflict-code { display:flex;align-items:center;gap:9px;min-width:0; }
.import-conflict-code strong { overflow-wrap:anywhere;color:#2d405d;font-size:13px;font-weight:600; }
.import-preview-dialog :deep(.el-radio-button__inner) { min-width:62px; }
.copy-config-dialog :deep(.el-dialog__body) { padding-top:14px; }
.copy-tip { margin:0 0 14px;color:#71829a;font-size:13px;line-height:1.6; }
.copy-search-bar { display:flex;gap:8px;margin-bottom:12px; }
.copy-search-bar .el-input { max-width:460px; }
.copy-selection-toolbar { display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;padding:9px 12px;border:1px solid #e4eaf3;border-radius:8px;background:#f8faff;color:#65758d;font-size:13px; }
.copy-project-groups { display:grid;gap:10px;max-height:min(52vh,480px);overflow:auto;padding:2px 4px 2px 0; }
.copy-project-group { overflow:hidden;border:1px solid #e3eaf4;border-radius:10px;background:#fff; }
.copy-project-group > header { display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 13px;background:#f8faff;cursor:pointer; }
.copy-project-title { display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;min-width:0; }
.copy-project-chevron { align-self:center;color:#8595ab;transition:transform .16s; }.copy-project-chevron.is-expanded { transform:rotate(180deg); }
.copy-project-group > header strong { color:#2f4260;font-size:14px; }
.copy-project-group > header strong span { color:#667891;font-weight:500; }
.copy-project-group > header small { color:#8a98ab;font-size:12px; }
.copy-project-items { display:grid; }
.copy-project-items :deep(.el-checkbox) { display:flex;align-items:flex-start;gap:8px;margin:0;padding:9px 13px;border-bottom:1px solid #f0f3f7; }
.copy-project-items :deep(.el-checkbox:last-child) { border-bottom:0; }
.copy-project-items :deep(.el-checkbox__label) { display:flex;flex:1;align-items:center;justify-content:space-between;gap:10px;min-width:0;white-space:normal; }
.copy-project-items code { overflow-wrap:anywhere;color:#3f5f91;font-size:12px; }
.copy-project-items span { flex:0 0 auto;color:#8390a3;font-size:12px; }
@media (max-width: 620px) { .import-preview-summary { grid-template-columns:repeat(2,minmax(0,1fr)); }.import-conflict-row { align-items:flex-start;flex-direction:column;gap:8px; }.import-preview-dialog :deep(.el-dialog__footer .el-button) { margin:4px; } }
@media (max-width: 680px) { .config-editor-dialog .result-editor { align-items:stretch;flex-wrap:wrap;padding-left:0; }.config-editor-dialog .result-editor :deep(.el-input) { flex:1 1 100%; }.config-editor-dialog .result-editor :deep(.el-select) { flex:1 1 180px;width:auto; } }
</style>
