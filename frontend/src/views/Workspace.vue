<script setup>
import { DocumentAdd } from '@element-plus/icons-vue'
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import LocationForm from '../components/LocationForm.vue'
import UploadExcel from '../components/UploadExcel.vue'
import RuleBuilder from '../components/RuleBuilder.vue'
import ExcelPreview from '../components/ExcelPreview.vue'
import LoadingDialog from '../components/LoadingDialog.vue'
import { useExcelStore } from '../store/excel'
import { buildContent, extractEquipmentCode } from '../utils/excelParser'
import { deriveEquipmentClassification } from '../utils/equipmentSubtype'
import { processExcelV2 } from '../api/excel'
import { downloadResponseBlob } from '../utils/download'
import { getApiErrorMessage } from '../utils/httpError'
import { buildTestLocation, validateFormalLocation } from '../utils/formalLocation'

const excel = useExcelStore()
const loading = ref(false)
const location = reactive({ type: '', direction: '', startStation: '', endStation: '' })
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
const baseTestContents = computed(() => excel.rows.map((row, index) => ({
  equipmentChinese: row['设备中文'] || row['测试内容'] || '',
  signalDescription: row['信号描述'] || '',
  additionalCode: row['附加编号'] || '',
  sortIndex: row.sortIndex || index + 1,
  generatedContent: excel.excelType === 'B' ? buildContent(row, excel.rules) : (row['测试内容'] || '[空]'),
  equipmentCode: excel.excelType === 'A' ? extractEquipmentCode(row['测试内容']) : (row['设备编码'] || ''),
  equipmentType: excel.excelType === 'A' ? (row['类型'] || '') : (row['设备类型'] || ''),
  ...deriveEquipmentClassification({
    equipmentType: excel.excelType === 'A' ? (row['类型'] || '') : (row['设备类型'] || ''),
    equipmentCode: excel.excelType === 'A' ? extractEquipmentCode(row['测试内容']) : (row['设备编码'] || ''),
    equipmentChinese: row['设备中文'] || row['测试内容'] || '',
    signalDescription: row['信号描述'] || '',
    testContent: excel.excelType === 'A' ? (row['测试内容'] || '') : buildContent(row, excel.rules)
  })
})))
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
  const locationMessage = validateFormalLocation(location)
  if (locationMessage) return locationMessage
  if (!excel.rows.length) return '请先上传并解析 Excel 文件'
  return ''
}

const submit = async () => {
  if (loading.value) return
  const message = validate()
  if (message) return ElMessage.warning(message)
  const testContents = baseTestContents.value
  loading.value = true
  try {
    const response = await processExcelV2({ testLocation: buildTestLocation(location), testContents })
    if (!response.data || response.data.size === 0) throw Object.assign(new Error('empty file'), { publicMessage: '文件生成失败' })
    downloadResponseBlob(response)
    ElMessage.success('正式文件生成成功，已开始下载')
  } catch (error) {
    ElMessage.error(await getApiErrorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="workspace">
    <div class="page-title"><div><h1>测试内容生成工作台</h1><p>上传 Excel，配置规则，生成系统可导入的正式文件。</p></div></div>
    <el-card class="section-card"><template #header><b>1. 测试地点配置</b></template><LocationForm v-model="locationValue" /></el-card>
    <el-card class="section-card"><template #header><b>2. Excel 上传与解析</b></template><UploadExcel @parsed="parsed" @clear="clear" /><el-alert v-if="excel.excelType" class="file-status" type="success" :closable="false" show-icon :title="`已识别：${excel.excelType === 'A' ? '人工处理版（直接使用测试内容）' : '原始设备版（需配置生成规则）'}，共 ${excel.rows.length} 条数据`" /></el-card>
    <el-card v-if="excel.excelType === 'B'" class="section-card"><template #header><b>3. 测试内容生成规则</b></template><RuleBuilder v-model="excel.rules" :available-fields="excel.headers" /></el-card>
    <el-card v-if="excel.excelType" class="section-card"><template #header><b>{{ excel.excelType === 'B' ? '实时预览（前 5 条）' : 'Excel 数据预览（前 5 条）' }}</b></template><ExcelPreview :rows="excel.rows" :excel-type="excel.excelType" :preview="preview" /></el-card>
    <div v-if="excel.excelType" class="submit-panel"><el-button class="submit-button" type="primary" size="large" :icon="DocumentAdd" :loading="loading" :disabled="loading" @click="submit">{{ submitLabel }}</el-button></div>
    <LoadingDialog :visible="loading" />
  </div>
</template>
