<script setup>
import { DocumentAdd, Download, Refresh, View } from '@element-plus/icons-vue'
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import LocationForm from '../components/LocationForm.vue'
import UploadExcel from '../components/UploadExcel.vue'
import RuleBuilder from '../components/RuleBuilder.vue'
import ExcelPreview from '../components/ExcelPreview.vue'
import LoadingDialog from '../components/LoadingDialog.vue'
import { useExcelStore } from '../store/excel'
import { useWorkspaceStore } from '../store/workspace'
import { buildContent, extractEquipmentCode } from '../utils/excelParser'
import { deriveEquipmentClassification, inferElectricDamperStatus } from '../utils/equipmentSubtype'
import { downloadGeneration, getGeneration, getGenerations, processExcel } from '../api/excel'
import { downloadWorkspaceTemplate } from '../api/workspace'
import { downloadResponseBlob } from '../utils/download'
import { getApiErrorMessage } from '../utils/httpError'
import { buildTestLocation, validateFormalLocation } from '../utils/formalLocation'
import { integrationProjects } from '../data/integrations'
import { getWorkspaceConfigs } from '../api/workspace'

const excel = useExcelStore()
const workspace = useWorkspaceStore()
const loading = ref(false)
const historyLoading = ref(false)
const history = ref([])
const historyExpanded = ref(false)
const visibleHistory = computed(() => historyExpanded.value ? history.value : history.value.slice(0, 5))
const historyDetailLoading = ref(false)
const historyDetailVisible = ref(false)
const historyDetail = ref(null)
const workspaceConfigs = ref([])
const workspaceConfigsLoading = ref(false)
let workspaceConfigRequestId = 0
const integrationOptions = integrationProjects
const availableProjects = computed(() => workspace.projects.filter((item) => !item.lineId || String(item.lineId) === String(workspace.selectedLineId)))
const selectedIntegration = computed({
  get: () => excel.selectedIntegration,
  set: (value) => excel.setIntegration(value)
})
const selectedProject = computed(() => {
  const project = availableProjects.value.find((item) => String(item.id) === String(workspace.selectedProjectId))
  if (!project) return null
  const legacy = integrationOptions.find((item) => item.code === (project.engineCode || project.code))
  return { ...project, code: project.engineCode || project.code, classificationProfile: legacy?.classificationProfile }
})
const isT19Selected = computed(() => Boolean(selectedProject.value?.engineCode === 'T19' || selectedProject.value?.code === 'T19'))
const isIntegrationSelected = computed(() => Boolean(workspace.selectedLineId && workspace.selectedProfessionId))
const isWorkbenchAvailable = computed(() => Boolean(selectedProject.value && (isT19Selected.value || workspaceConfigs.value.length)))
const effectiveProfessionId = computed(() => workspace.selectedProfessionId)
const effectiveIntegrationCode = computed(() => selectedProject.value?.engineCode || selectedProject.value?.code || selectedIntegration.value)
// 默认按站点测试，并使用站点基础资料中的第一个站点作为开始/结束站点。
// 这样打开工作台后地点配置即可直接使用，同时仍可由用户修改。
const location = reactive({
  type: '站点',
  direction: '',
  startStation: '',
  endStation: '',
  stations: ['']
})
const locationValue = computed({ get: () => location, set: (value) => Object.assign(location, value) })
const submitLabel = computed(() => loading.value ? '正在生成正式文件...' : '生成正式文件')
const isSpecialModuleSheet = (rows = []) => rows[0]?.['设备类型'] === '特殊模块'
const defaultRuleFields = (headers = [], rows = []) => {
  if (isSpecialModuleSheet(rows)) return [{ type: 'field', value: '设备中文' }]
  return [
    { type: 'field', value: '设备中文' },
    { type: 'field', value: '设备类型' },
    { type: 'field', value: '设备编码' },
    ...(headers.includes('信号描述') ? [{ type: 'field', value: '信号描述', optional: true }] : []),
    ...(headers.includes('附加编号') ? [{ type: 'field', value: '附加编号', optional: true }] : [])
  ]
}
const baseTestContents = computed(() => {
  const damperOccurrences = new Map()
  return excel.rows.map((row, index) => {
    const equipmentCode = excel.excelType === 'A' ? extractEquipmentCode(row['测试内容']) : (row['设备编码'] || '')
    const equipmentType = excel.excelType === 'A' ? (row['类型'] || '') : (row['设备类型'] || '')
    const equipmentChinese = row['设备中文'] || row['测试内容'] || ''
    const signalDescription = row['信号描述'] || ''
    const testContent = excel.excelType === 'A' ? (row['测试内容'] || '') : buildContent(row, excel.rules)
    const classification = deriveEquipmentClassification({
      equipmentType,
      equipmentCode,
      equipmentChinese,
      signalDescription,
      testContent,
      integrationCode: effectiveIntegrationCode.value,
      classificationProfile: selectedProject.value?.classificationProfile
    })
    const damperKey = String(equipmentCode || equipmentChinese || testContent).trim().toUpperCase()
    const occurrenceIndex = classification.equipmentSubtype === '电动防火阀'
      ? (damperOccurrences.get(damperKey) || 0)
      : -1
    if (classification.equipmentSubtype === '电动防火阀') damperOccurrences.set(damperKey, occurrenceIndex + 1)
    const equipmentStatus = inferElectricDamperStatus(classification, occurrenceIndex)
    return {
      equipmentChinese,
      signalDescription,
      additionalCode: row['附加编号'] || '',
      sortIndex: row.sortIndex || index + 1,
      generatedContent: excel.excelType === 'B' ? buildContent(row, excel.rules) : (row['测试内容'] || '[空]'),
      equipmentCode,
      equipmentType,
      integrationConfigCode: row['联调配置编码'] || '',
      ...classification,
      ...(equipmentStatus ? { equipmentStatus } : {})
    }
  })
})
const preview = computed(() => baseTestContents.value.slice(0, 5).map(({ sortIndex, generatedContent, equipmentType, equipmentSubtype, equipmentStatus, intervalName }) => ({ sortIndex, generatedContent, equipmentType, equipmentSubtype, equipmentStatus, intervalName })))
const matchStats = computed(() => {
  const total = excel.rows.length
  const byCode = new Map()
  workspaceConfigs.value.forEach((item) => {
    byCode.set(String(item.configCode).trim().toLowerCase(), item)
    ;(item.aliases || []).forEach((alias) => byCode.set(String(alias).trim().toLowerCase(), item))
  })
  let matched = 0; let unmatched = 0; let disabled = 0
  excel.rows.forEach((row) => {
    const code = String(row['联调配置编码'] || '').trim().toLowerCase()
    if (!code) return
    const item = byCode.get(code)
    if (!item) unmatched += 1
    else if (!item.isEnabled) disabled += 1
    else matched += 1
  })
  if (!excel.rows.some((row) => String(row['联调配置编码'] || '').trim()) && isT19Selected.value) matched = total
  return { total, matched, unmatched, disabled }
})

watch(preview, (value) => excel.setPreview(value), { immediate: true })
watch(selectedProject, (project) => {
  if (project) excel.setIntegration(project.engineCode || project.code || '')
}, { immediate: true })
const loadWorkspaceConfigs = async () => {
  const requestId = ++workspaceConfigRequestId
  if (!selectedProject.value || !effectiveProfessionId.value) { workspaceConfigs.value = []; return }
  const params = { lineId: workspace.selectedLineId, professionId: effectiveProfessionId.value, projectId: selectedProject.value.id, includeDisabled: true }
  workspaceConfigsLoading.value = true
  try {
    const result = (await getWorkspaceConfigs(params)).data?.data || []
    if (requestId === workspaceConfigRequestId) workspaceConfigs.value = result
  } catch {
    if (requestId === workspaceConfigRequestId) workspaceConfigs.value = []
  } finally {
    if (requestId === workspaceConfigRequestId) workspaceConfigsLoading.value = false
  }
}
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId], loadWorkspaceConfigs, { immediate: true })

const parsed = ({ file, excelType, headers, rows }) => {
  excel.setExcel({ file, excelType, headers, rows })
  excel.setRules(excelType === 'B' ? defaultRuleFields(headers, rows) : [])
  ElMessage.success(excelType === 'A' ? '已识别为人工处理版' : '已识别为原始设备版，请配置生成规则')
}

const clear = () => {
  excel.reset()
}

const validate = () => {
  if (!selectedProject.value) return '请先选择当前联调项目'
  const locationMessage = validateFormalLocation(location)
  if (locationMessage) return locationMessage
  if (!excel.rows.length) return '请先上传并解析 Excel 文件'
  return ''
}

const responseList = (response) => {
  const body = response?.data
  if (Array.isArray(body)) return body
  if (Array.isArray(body?.data)) return body.data
  return []
}

const loadHistory = async () => {
  if (!isT19Selected.value) {
    history.value = []
    return
  }
  historyLoading.value = true
  try {
    history.value = responseList(await getGenerations({ limit: 20, integrationCode: selectedIntegration.value }))
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  } finally {
    historyLoading.value = false
  }
}

const formatGeneratedAt = (value) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

const downloadHistory = async (item) => {
  try {
    const response = await downloadGeneration(item.id)
    downloadResponseBlob(response)
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  }
}

const downloadInputTemplate = async () => {
  try {
    downloadResponseBlob(await downloadWorkspaceTemplate())
    ElMessage.success('测试数据导入模板已下载')
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  }
}

const viewHistory = async (item) => {
  historyDetailVisible.value = true
  historyDetailLoading.value = true
  historyDetail.value = null
  try {
    historyDetail.value = (await getGeneration(item.id)).data?.data || null
  } catch (error) {
    historyDetailVisible.value = false
    ElMessage.error(await getApiErrorMessage(error))
  } finally {
    historyDetailLoading.value = false
  }
}

const submit = async () => {
  if (loading.value) return
  const message = validate()
  if (message) return ElMessage.warning(message)
  // Preserve the parsed interval context so the backend can render the
  // correct 上行/下行 rule when the source text is customized.
  const testContents = baseTestContents.value
  loading.value = true
  try {
    const response = await processExcel({
      integrationCode: effectiveIntegrationCode.value,
      lineId: workspace.selectedLineId,
      professionId: effectiveProfessionId.value,
      projectId: selectedProject.value.id,
      sourceFilename: excel.file?.name || '',
      testLocation: buildTestLocation(location),
      testContents
    })
    if (!response.data || response.data.size === 0) throw Object.assign(new Error('empty file'), { publicMessage: '文件生成失败' })
    downloadResponseBlob(response)
    await loadHistory()
    ElMessage.success('正式文件生成成功，已开始下载')
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  } finally {
    loading.value = false
  }
}

watch(selectedIntegration, (value) => {
  if (value === 'T19') loadHistory()
  else history.value = []
})
</script>

<template>
  <div class="workspace">
    <div class="workspace-title-block">
      <div class="page-title workspace-title"><div><h1>测试内容生成工作台</h1><p>上传 Excel，配置规则，生成系统可导入的正式文件。</p></div></div>
    </div>
    <el-collapse-transition>
      <div v-if="isIntegrationSelected" class="integration-content">
        <div class="integration-banner"><span>当前联调项目</span><el-select :model-value="workspace.selectedProjectId" class="project-select" placeholder="请选择联调项目" @change="workspace.setProject"><el-option v-for="project in availableProjects" :key="project.id" :label="`${project.code || project.engineCode} · ${project.name}`" :value="project.id" /></el-select></div>
        <el-skeleton v-if="workspaceConfigsLoading" :rows="3" animated />
        <template v-else-if="isWorkbenchAvailable">
        <el-card class="section-card"><template #header><b>1. 测试地点配置</b></template><LocationForm v-model="locationValue" /></el-card>
        <el-card class="section-card"><template #header><div class="upload-card-header"><b>2. Excel 上传与解析</b><el-button :icon="Download" @click="downloadInputTemplate">下载测试数据模板</el-button></div></template><UploadExcel @parsed="parsed" @clear="clear" /><el-alert v-if="excel.excelType" class="file-status" type="success" :closable="false" show-icon :title="`已识别：${excel.excelType === 'A' ? '人工处理版（直接使用测试内容）' : '原始设备版（需配置生成规则）'}，共 ${excel.rows.length} 条数据`" /><div v-if="excel.excelType && excel.headers.includes('联调配置编码')" class="match-stats"><span>源数据共：<b>{{ matchStats.total }}</b> 条</span><span class="stat-success">已匹配：<b>{{ matchStats.matched }}</b> 条</span><span class="stat-warning">未匹配：<b>{{ matchStats.unmatched }}</b> 条</span><span class="stat-muted">配置已停用：<b>{{ matchStats.disabled }}</b> 条</span></div></el-card>
        <el-card v-if="excel.excelType === 'B'" class="section-card"><template #header><b>3. 测试内容生成规则</b></template><RuleBuilder v-model="excel.rules" :available-fields="excel.headers" /></el-card>
        <el-card v-if="excel.excelType" class="section-card"><template #header><b>{{ excel.excelType === 'B' ? '实时预览（前 5 条）' : 'Excel 数据预览（前 5 条）' }}</b></template><ExcelPreview :rows="excel.rows" :excel-type="excel.excelType" :preview="preview" /></el-card>
        <div v-if="excel.excelType" class="submit-panel"><el-button class="submit-button" type="primary" size="large" :icon="DocumentAdd" :loading="loading" :disabled="loading" @click="submit">{{ submitLabel }}</el-button></div>
        </template>
        <div v-else class="integration-placeholder">
          <el-alert type="warning" :closable="false" show-icon title="该联调项目暂未配置联调表单规则，请联系线路管理员完成配置后再进行处理。" />
        </div>
      </div>
    </el-collapse-transition>
    <el-card v-if="isT19Selected" class="section-card generation-history">
      <template #header>
        <div class="history-heading"><b>近期生成文件</b><div class="history-heading-actions"><el-button v-if="history.length > 5" text type="primary" @click="historyExpanded = !historyExpanded">{{ historyExpanded ? '收起' : '查看更多' }}</el-button><el-button text type="primary" :icon="Refresh" :loading="historyLoading" @click="loadHistory">刷新记录</el-button></div></div>
      </template>
      <el-table v-if="history.length" v-loading="historyLoading" :data="visibleHistory" stripe>
        <el-table-column label="生成时间" min-width="180"><template #default="{ row }">{{ formatGeneratedAt(row.generatedAt) }}</template></el-table-column>
        <el-table-column label="文件名" min-width="260" show-overflow-tooltip><template #default="{ row }"><code>{{ row.filename }}</code></template></el-table-column>
        <el-table-column label="地点" min-width="150"><template #default="{ row }">{{ row.testLocation?.startStation || row.testLocation?.type || '—' }}</template></el-table-column>
        <el-table-column label="数据量" width="90" align="center"><template #default="{ row }">{{ row.counts?.testContents || 0 }} 条</template></el-table-column>
        <el-table-column label="操作" width="176" fixed="right" align="center">
          <template #default="{ row }"><div class="history-actions"><el-button text type="primary" :icon="View" @click="viewHistory(row)">查看</el-button><el-button text type="primary" :icon="Download" @click="downloadHistory(row)">下载</el-button></div></template>
        </el-table-column>
      </el-table>
      <el-empty v-else :image-size="72" description="暂无生成记录" />
    </el-card>
    <el-dialog v-model="historyDetailVisible" title="生成文件详情" width="min(860px, calc(100vw - 32px))">
      <el-skeleton v-if="historyDetailLoading" :rows="5" animated />
      <template v-else-if="historyDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">{{ historyDetail.filename }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatGeneratedAt(historyDetail.generatedAt) }}</el-descriptions-item>
          <el-descriptions-item label="地点">{{ historyDetail.testLocation?.startStation || historyDetail.testLocation?.type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="测试内容">{{ historyDetail.counts?.testContents || 0 }} 条</el-descriptions-item>
        </el-descriptions>
        <div class="history-detail-list">
          <div v-for="content in historyDetail.testContents" :key="content.sequenceIndex" class="history-detail-item">
            <strong>{{ content.sequenceIndex }}. {{ content.generatedContent }}</strong>
            <span>{{ content.operationSteps?.length || 0 }} 个操作步骤 · {{ content.equipmentType || '未分类' }}</span>
          </div>
        </div>
      </template>
    </el-dialog>
    <LoadingDialog :visible="loading" />
  </div>
</template>

<style scoped>
.workspace-title-block { display:flex;flex-direction:column;align-items:flex-start;gap:10px;margin-bottom:16px; }
.workspace-title { gap: 18px; }
.integration-banner { display:flex;align-items:center;justify-content:flex-start;gap:10px;margin:0 0 14px;color:#73829a;font-size:13px; }
.integration-banner > span { flex:none; }
.project-select { width:min(360px, 100%); }
.upload-card-header { display:flex;align-items:center;justify-content:space-between;gap:12px; }
@media (max-width: 760px) { .workspace-title { align-items: flex-start; flex-direction: column; gap: 10px; } }
@media (max-width: 520px) { .integration-banner { align-items:flex-start;flex-direction:column;gap:4px; } }
@media (max-width: 520px) { .upload-card-header { align-items:flex-start;flex-direction:column; } }
.match-stats { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 14px; color: #62728a; font-size: 13px; }
.match-stats span { padding: 7px 11px; border: 1px solid #e4eaf3; border-radius: 7px; background: #f8fbff; }
.match-stats b { color: #2f486e; }
.match-stats .stat-success b { color: #2f9568; }
.match-stats .stat-warning b { color: #c37b25; }
.match-stats .stat-muted b { color: #8b97a8; }
</style>
