<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ArrowDown, CopyDocument, Download, EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'
import { useWorkspaceStore } from '../store/workspace'
import { useUserStore } from '../store/user'
import { batchCopyWorkspaceConfigs, createWorkspaceConfig, downloadWorkspaceConfigTemplate, downloadWorkspaceTemplate, getWorkspaceCatalog, getWorkspaceConfigs, importWorkspaceConfigs, setWorkspaceConfigStatus, updateWorkspaceConfig } from '../api/workspace'
import { downloadResponseBlob } from '../utils/download'
import { getApiErrorMessage } from '../utils/httpError'
import WorkspaceScopePicker from '../components/WorkspaceScopePicker.vue'
import LegacyConfig from './LegacyConfig.vue'
import WorkspaceCatalog from '../components/WorkspaceCatalog.vue'
import './config-page.css'

const workspace = useWorkspaceStore(); const user = useUserStore()
const sameId = (left, right) => left != null && right != null && String(left) === String(right)
const configs = ref([]); const loading = ref(false); const saving = ref(false); const dialogVisible = ref(false); const copyVisible = ref(false); const filter = ref(''); const editingId = ref(''); const selectedConfigId = ref(null); const sourceConfigs = ref([]); const copySelection = ref([])
const scope = computed(() => ({ lineId: workspace.selectedLineId, professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId }))
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
const visibleConfigs = computed(() => { const keyword = filter.value.trim().toLowerCase(); return keyword ? configs.value.filter((item) => [item.businessId, item.configCode, item.deviceType, item.description].join(' ').toLowerCase().includes(keyword)) : configs.value })
const selectedConfig = computed(() => visibleConfigs.value.find((item) => item.id === selectedConfigId.value) || visibleConfigs.value[0] || null)
const form = reactive({ professionId: null, projectId: null, configCode: '', deviceType: '', description: '', isEnabled: true, steps: [] })
const equipmentTypeOptions = ref([])
const responsibleDisciplineOptions = ref([])
let editorCatalogRequestId = 0
const editableProfessions = computed(() => {
  if (user.userInfo.role === 'super_admin' || user.userInfo.role === 'line_admin') return workspace.professions
  return workspace.professions.filter((item) => item.id === user.userInfo.professionId)
})
const formProjects = computed(() => workspace.projects.filter((item) => sameId(item.professionId, form.professionId)))
let editorItemSequence = 0
const editorKey = () => `editor-item-${++editorItemSequence}`
const onFormProfessionChange = () => { form.projectId = formProjects.value[0]?.id ?? null }
const loadEquipmentTypeOptions = async () => {
  const requestId = ++editorCatalogRequestId
  if (!dialogVisible.value || !workspace.selectedLineId || !form.professionId || !form.projectId) {
    equipmentTypeOptions.value = []
    responsibleDisciplineOptions.value = []
    return
  }
  try {
    const base = { lineId: workspace.selectedLineId, professionId: form.professionId, projectId: form.projectId }
    const [equipmentResponse, disciplineResponse] = await Promise.all([
      getWorkspaceCatalog({ ...base, category: 'equipment_types' }),
      getWorkspaceCatalog({ ...base, category: 'disciplines' })
    ])
    if (requestId === editorCatalogRequestId) {
      equipmentTypeOptions.value = (equipmentResponse.data?.data || []).filter((item) => item.isEnabled !== false)
        .map((item) => ({ value: item.name }))
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
      equipmentTypeOptions.value = []
      responsibleDisciplineOptions.value = []
    }
  }
}
const queryEquipmentTypes = (query, callback) => {
  const keyword = String(query || '').trim().toLocaleLowerCase()
  callback(keyword ? equipmentTypeOptions.value.filter((item) => item.value.toLocaleLowerCase().includes(keyword)) : equipmentTypeOptions.value)
}
const setResultDiscipline = (result, value) => {
  result.responsibleDisciplines = value ? [value] : []
}
const blankStep = () => ({ _editorKey: editorKey(), description: '', ratioChange: '否', sortOrder: 1, isEnabled: true, results: [{ _editorKey: editorKey(), description: '', responsibleDisciplines: [] }] })
const resetForm = () => { editingId.value = ''; Object.assign(form, { professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId, configCode: '', deviceType: '', description: '', isEnabled: true, steps: [blankStep()] }) }
const openCreate = () => { resetForm(); dialogVisible.value = true }
const openEdit = (row) => {
  editingId.value = row.id
  const data = JSON.parse(JSON.stringify({ professionId: row.professionId, projectId: row.projectId, configCode: row.configCode, deviceType: row.deviceType, description: row.description, isEnabled: row.isEnabled, steps: row.steps }))
  data.steps = data.steps.map((step) => ({ ...step, _editorKey: editorKey(), results: step.results.map((result) => ({ ...result, _editorKey: editorKey() })) }))
  Object.assign(form, data)
  dialogVisible.value = true
}
const addStep = () => form.steps.push({ ...blankStep(), sortOrder: form.steps.length + 1 })
const removeStep = (index) => { if (form.steps.length > 1) form.steps.splice(index, 1) }
const addResult = (step) => step.results.push({ _editorKey: editorKey(), description: '', responsibleDisciplines: [] })
const removeResult = (step, index) => { if (step.results.length > 1) step.results.splice(index, 1) }
const load = async () => { if (!workspace.isSelected) return; loading.value = true; try { configs.value = (await getWorkspaceConfigs({ ...scope.value, includeDisabled: true })).data?.data || []; if (!configs.value.some((item) => item.id === selectedConfigId.value)) selectedConfigId.value = configs.value[0]?.id ?? null } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { loading.value = false } }
const save = async () => {
  if (!form.professionId) return ElMessage.warning('请选择所属专业')
  if (!form.projectId) return ElMessage.warning('请选择联调项目')
  if (!form.configCode.trim()) return ElMessage.warning('请输入联调配置编码')
  if (!form.steps.length || form.steps.some((step) => !step.description.trim() || step.results.some((result) => !result.description.trim()))) return ElMessage.warning('每个配置必须填写操作步骤和预期结果')
  saving.value = true
  try {
    const selectedScope = { lineId: workspace.selectedLineId, professionId: form.professionId, projectId: form.projectId }
    const payload = { scope: selectedScope, configCode: form.configCode.trim(), deviceType: form.deviceType, description: form.description, isEnabled: form.isEnabled, steps: form.steps.map((step, index) => ({ description: step.description.trim(), ratioChange: step.ratioChange || '否', sortOrder: index + 1, isEnabled: step.isEnabled ?? true, results: step.results.map((result) => ({ description: result.description.trim(), responsibleDisciplines: result.responsibleDisciplines || [] })) })) }
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
const loadCopyCandidates = async () => { const lines = workspace.lines.filter((line) => line.id !== workspace.selectedLineId); const responses = await Promise.all(lines.map((line) => getWorkspaceConfigs({ lineId: line.id, professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId }))); sourceConfigs.value = responses.flatMap((response) => response.data?.data || []); copySelection.value = []; copyVisible.value = true }
const copySelected = async () => { if (!copySelection.value.length) return ElMessage.warning('请选择要复制的配置'); try { await batchCopyWorkspaceConfigs({ sourceConfigIds: copySelection.value, target: scope.value }); copyVisible.value = false; ElMessage.success('配置复制完成'); await load() } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } }
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
    const response = await importWorkspaceConfigs({ scope: scope.value, rows })
    const importedCount = response.data?.data?.length || 0
    ElMessage.success(`已校验并导入 ${importedCount} 条联调配置（${rows.length} 行结果）`)
    await load()
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) }
}
onMounted(load)
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId], load)
watch(() => [dialogVisible.value, workspace.selectedLineId, form.professionId, form.projectId], ([isOpen]) => {
  if (isOpen) loadEquipmentTypeOptions()
  else editorCatalogRequestId += 1
})
</script>

<template>
  <div class="workspace workspace-config-page">
    <div class="config-page-heading">
      <div class="config-heading-row">
        <div><h1>联调表单配置管理</h1><p>管理当前线路、专业和联调项目下的配置编码、操作步骤和预期结果。</p></div>
        <WorkspaceScopePicker compact />
      </div>
      <div class="config-toolbar">
        <div class="config-toolbar-group"><el-input v-model="filter" clearable placeholder="搜索编码、设备类型" /><el-button :icon="Refresh" @click="load">刷新</el-button></div>
        <div class="config-toolbar-group config-toolbar-actions">
          <el-dropdown @command="downloadTemplateChoice"><el-button :icon="Download">模板下载<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="data">测试数据导入模板</el-dropdown-item><el-dropdown-item command="config">联调配置规范模板（含样例）</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
          <label v-if="canEdit" class="upload-config-button"><input type="file" accept=".xlsx,.xls,.csv" @change="importConfigFile" />导入配置规范表</label>
          <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreate">新增配置</el-button>
          <el-button v-if="canEdit" :icon="CopyDocument" @click="loadCopyCandidates">复制其他线路配置</el-button>
        </div>
      </div>
    </div>
    <el-tabs v-model="activeConfigTab" class="config-tabs">
      <el-tab-pane label="联调表单配置规则" name="workspace">
        <nav class="config-submenu" aria-label="配置管理子菜单">
          <button v-for="item in [{ key: 'config', label: '规则配置' }, { key: 'equipment_types', label: '设备类型' }, { key: 'disciplines', label: '责任专业' }, { key: 'stations', label: '站点信息' }]" :key="item.key" type="button" :class="{ active: activeSubmenu === item.key }" :aria-current="activeSubmenu === item.key ? 'page' : undefined" @click="activeSubmenu = item.key">{{ item.label }}</button>
        </nav>
        <div class="config-section-content">
        <WorkspaceCatalog v-if="activeSubmenu !== 'config'" :category="activeSubmenu" />
        <div v-else class="config-code-content">
        <!-- <el-alert type="info" :closable="false" show-icon title="联调配置编码在当前线路、专业和项目下必须唯一；业务显示 ID 由系统自动生成且不可修改。导入时每行填写一个输出结果，用步骤序号把多个结果归到同一个操作步骤。" /> -->
        <div v-loading="loading" class="config-workbench">
          <aside class="config-sidebar">
            <div class="config-sidebar-heading"><strong>{{ selectedConfig?.deviceType || '联调配置' }}</strong><span>{{ visibleConfigs.length }} 条</span></div>
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
              <div class="config-summary-grid"><div class="config-summary-item"><span>设备类型</span><strong>{{ selectedConfig.deviceType || '—' }}</strong></div><div class="config-summary-item"><span>操作步骤</span><strong>{{ selectedConfig.steps?.length || 0 }} 个</strong></div><div class="config-summary-item config-summary-wide"><span>说明</span><strong>{{ selectedConfig.description || '暂无说明' }}</strong></div></div>
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
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑联调配置' : '新增联调配置'" width="min(860px, calc(100vw - 28px))" class="config-editor-dialog"><el-form label-position="top"><div class="rule-base-grid"><el-form-item label="所属专业" required><el-select v-model="form.professionId" :disabled="Boolean(editingId) || editableProfessions.length <= 1" placeholder="请选择专业" @change="onFormProfessionChange"><el-option v-for="item in editableProfessions" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="联调项目" required><el-select v-model="form.projectId" :disabled="Boolean(editingId)" placeholder="请选择联调项目"><el-option v-for="item in formProjects" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="联调配置编码" required><el-input v-model="form.configCode" placeholder="例如：FAS-垂梯-状态反馈" /></el-form-item><el-form-item label="设备类型"><el-autocomplete v-model="form.deviceType" :fetch-suggestions="queryEquipmentTypes" :debounce="0" :trigger-on-focus="true" fit-input-width clearable placeholder="请输入或选择设备类型" /></el-form-item><el-form-item class="description-field" label="说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item></div><div class="steps-heading"><strong>操作步骤和预期结果</strong><el-button type="primary" plain :icon="Plus" @click="addStep">新增步骤</el-button></div><draggable v-model="form.steps" item-key="_editorKey" handle=".step-drag-handle" ghost-class="drag-ghost" chosen-class="drag-chosen" class="step-editor-list"><template #item="{ element: step, index }"><section class="step-editor"><div class="step-editor-title"><span class="step-drag-handle drag-grip" title="拖动调整步骤顺序" aria-label="拖动调整步骤顺序">⠿</span><span>步骤 {{ index + 1 }}</span><el-button v-if="form.steps.length > 1" text type="danger" @click="removeStep(index)">删除步骤</el-button></div><el-input v-model="step.description" placeholder="操作步骤" /><draggable v-model="step.results" item-key="_editorKey" handle=".result-drag-handle" ghost-class="drag-ghost" chosen-class="drag-chosen" class="result-editor-list"><template #item="{ element: result, index: resultIndex }"><div class="result-editor"><span class="result-drag-handle drag-grip" title="拖动调整输出结果顺序" aria-label="拖动调整输出结果顺序">⠿</span><span class="result-order">{{ resultIndex + 1 }}</span><el-input v-model="result.description" placeholder="预期结果" /><el-select :model-value="result.responsibleDisciplines?.[0] || ''" filterable clearable placeholder="选择责任专业" @update:model-value="setResultDiscipline(result, $event)"><el-option v-for="item in responsibleDisciplineOptions" :key="item.value" :label="item.value" :value="item.value" /></el-select><el-button text type="danger" @click="removeResult(step, resultIndex)">删除</el-button></div></template></draggable><el-button text type="primary" @click="addResult(step)">新增结果</el-button></section></template></draggable><el-form-item label="状态"><el-switch v-model="form.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存完整配置</el-button></template></el-dialog>
    <el-dialog v-model="copyVisible" title="批量复制其他线路配置" width="min(760px, calc(100vw - 28px))"><p class="copy-tip">只显示其他线路中相同专业、相同联调项目的独立配置，不会复制整个项目。</p><el-checkbox-group v-model="copySelection" class="copy-list"><el-checkbox v-for="item in sourceConfigs" :key="item.id" :value="item.id"><code>{{ item.businessId }}</code><span>{{ item.configCode }}</span></el-checkbox></el-checkbox-group><el-empty v-if="!sourceConfigs.length" description="其他线路暂无可复制配置" /><template #footer><el-button @click="copyVisible = false">取消</el-button><el-button type="primary" @click="copySelected">复制选中配置</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.tree-heading { display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin:22px 0 14px; }.tree-heading h3 { margin:0;color:#243653;font-size:17px; }.tree-heading p { margin:6px 0 0;color:#8290a4;font-size:13px; }.readonly-step-card { background:#fff; }.readonly-step-description { padding:18px 16px 12px;color:#2c3e5d;font-size:15px;line-height:1.7; }.readonly-result-row { grid-template-columns:28px minmax(0,1fr) auto; }.readonly-result-description { color:#3a4b66;line-height:1.6; }.discipline-tags { display:flex;justify-content:flex-end;flex-wrap:wrap;gap:5px; }.discipline-tags :deep(.el-tag) { margin:0; }.config-editor-dialog .step-editor { padding:16px;border:1px solid #dfe7f3;border-radius:12px;background:#fbfcff; }.config-editor-dialog .result-editor { padding-left:14px; }.config-editor-dialog .steps-heading { margin:8px 0 14px; }
.config-editor-dialog .result-editor :deep(.el-select) { flex:0 0 164px;width:164px; }
.step-editor-list,.result-editor-list { display:grid;gap:12px; }.drag-grip { display:inline-flex;align-items:center;justify-content:center;flex:0 0 24px;width:24px;height:28px;border:1px solid #dbe6f5;border-radius:6px;background:#fff;color:#8a9bb3;font-size:19px;line-height:1;cursor:grab;user-select:none; }.drag-grip:active { cursor:grabbing; }.config-editor-dialog .step-editor-title { justify-content:flex-start;gap:8px; }.config-editor-dialog .step-editor-title .el-button { margin-left:auto; }.config-editor-dialog .result-editor-list { margin-top:10px; }.config-editor-dialog .result-editor { display:flex;align-items:center;gap:8px;margin:0;padding:0; }.config-editor-dialog .result-editor :deep(.el-input) { flex:1;min-width:120px; }.result-order { display:inline-flex;align-items:center;justify-content:center;flex:0 0 24px;width:24px;height:24px;border-radius:50%;background:#edf4ff;color:#4a76b8;font-size:12px;font-weight:700; }.drag-ghost { opacity:.45;background:#edf4ff!important;border-color:#8db2fa!important; }.drag-chosen { box-shadow:0 8px 24px #31558d24; }
@media (max-width: 680px) { .config-editor-dialog .result-editor { align-items:stretch;flex-wrap:wrap;padding-left:0; }.config-editor-dialog .result-editor :deep(.el-input) { flex:1 1 100%; }.config-editor-dialog .result-editor :deep(.el-select) { flex:1 1 180px;width:auto; } }
</style>
