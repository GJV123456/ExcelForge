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
import { buildContent, extractEquipmentCode } from '../utils/excelParser'
import { deriveEquipmentClassification, inferElectricDamperStatus } from '../utils/equipmentSubtype'
import { downloadGeneration, getGeneration, getGenerations, processExcel } from '../api/excel'
import { downloadResponseBlob } from '../utils/download'
import { getApiErrorMessage } from '../utils/httpError'
import { buildTestLocation, validateFormalLocation } from '../utils/formalLocation'
import { integrationProjects } from '../data/integrations'
import { stationOptions } from '../data/stations'

const excel = useExcelStore()
const loading = ref(false)
const historyLoading = ref(false)
const history = ref([])
const historyExpanded = ref(false)
const visibleHistory = computed(() => historyExpanded.value ? history.value : history.value.slice(0, 5))
const historyDetailLoading = ref(false)
const historyDetailVisible = ref(false)
const historyDetail = ref(null)
const integrationOptions = integrationProjects
const selectedIntegration = computed({
  get: () => excel.selectedIntegration,
  set: (value) => excel.setIntegration(value)
})
const selectedProject = computed(() => integrationOptions.find((item) => item.code === selectedIntegration.value))
const isT19Selected = computed(() => selectedIntegration.value === 'T19')
const isIntegrationSelected = computed(() => Boolean(selectedProject.value))
// 默认按站点测试，并使用站点基础资料中的第一个站点作为开始/结束站点。
// 这样打开工作台后地点配置即可直接使用，同时仍可由用户修改。
const defaultStation = stationOptions[0]?.value || ''
const location = reactive({
  type: '站点',
  direction: '',
  startStation: defaultStation,
  endStation: defaultStation,
  stations: defaultStation ? [defaultStation] : ['']
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
      integrationCode: selectedIntegration.value,
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
      ...classification,
      ...(equipmentStatus ? { equipmentStatus } : {})
    }
  })
})
const preview = computed(() => baseTestContents.value.slice(0, 5).map(({ sortIndex, generatedContent, equipmentType, equipmentSubtype, equipmentStatus, intervalName }) => ({ sortIndex, generatedContent, equipmentType, equipmentSubtype, equipmentStatus, intervalName })))

watch(preview, (value) => excel.setPreview(value), { immediate: true })

const parsed = ({ file, excelType, headers, rows }) => {
  excel.setExcel({ file, excelType, headers, rows })
  excel.setRules(excelType === 'B' ? defaultRuleFields(headers, rows) : [])
  ElMessage.success(excelType === 'A' ? '已识别为人工处理版' : '已识别为原始设备版，请配置生成规则')
}

const clear = () => {
  excel.reset()
}

const validate = () => {
  if (!selectedProject.value) return '请先选择联调项目'
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
      integrationCode: selectedIntegration.value,
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
    <div class="page-title">
      <div><h1>测试内容生成工作台</h1><p>上传 Excel，配置规则，生成系统可导入的正式文件。</p></div>
      <div class="integration-picker">
        <span class="integration-picker-label">联调项目</span>
        <el-select v-model="selectedIntegration" class="integration-select" clearable placeholder="请选择联调项目" aria-label="选择联调项目">
        <el-option v-for="item in integrationOptions" :key="item.code" :label="item.name" :value="item.code" />
        </el-select>
        <span class="integration-picker-hint">{{ selectedProject?.description || '生成文档属于具体联调项目的子系统' }}</span>
      </div>
    </div>
    <el-collapse-transition>
      <div v-if="isIntegrationSelected" class="integration-content">
        <div class="integration-banner"><strong>{{ selectedProject?.name }}</strong><span>当前联调项目</span></div>
        <template v-if="isT19Selected">
        <el-card class="section-card"><template #header><b>1. 测试地点配置</b></template><LocationForm v-model="locationValue" /></el-card>
        <el-card class="section-card"><template #header><b>2. Excel 上传与解析</b></template><UploadExcel @parsed="parsed" @clear="clear" /><el-alert v-if="excel.excelType" class="file-status" type="success" :closable="false" show-icon :title="`已识别：${excel.excelType === 'A' ? '人工处理版（直接使用测试内容）' : '原始设备版（需配置生成规则）'}，共 ${excel.rows.length} 条数据`" /></el-card>
        <el-card v-if="excel.excelType === 'B'" class="section-card"><template #header><b>3. 测试内容生成规则</b></template><RuleBuilder v-model="excel.rules" :available-fields="excel.headers" /></el-card>
        <el-card v-if="excel.excelType" class="section-card"><template #header><b>{{ excel.excelType === 'B' ? '实时预览（前 5 条）' : 'Excel 数据预览（前 5 条）' }}</b></template><ExcelPreview :rows="excel.rows" :excel-type="excel.excelType" :preview="preview" /></el-card>
        <div v-if="excel.excelType" class="submit-panel"><el-button class="submit-button" type="primary" size="large" :icon="DocumentAdd" :loading="loading" :disabled="loading" @click="submit">{{ submitLabel }}</el-button></div>
        </template>
        <div v-else class="integration-placeholder">
          <strong>{{ selectedProject?.name }} 子系统</strong>
          <p>{{ selectedProject?.description || '该联调项目的专属工作区正在配置中。' }}</p>
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
