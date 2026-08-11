<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import LocationForm from '../components/LocationForm.vue'
import UploadExcel from '../components/UploadExcel.vue'
import RuleBuilder from '../components/RuleBuilder.vue'
import ExcelPreview from '../components/ExcelPreview.vue'
import LoadingDialog from '../components/LoadingDialog.vue'
import { useExcelStore } from '../store/excel'
import { buildContent, extractEquipmentCode } from '../utils/excelParser'
import { processExcel } from '../api/excel'

const excel = useExcelStore(); const loading = ref(false)
const location = reactive({ type: '', direction: '', startStation: '', endStation: '' })
const locationValue = computed({ get: () => location, set: (value) => Object.assign(location, value) })
const submitLabel = computed(() => loading.value ? '后端处理中...' : '提交后端处理并下载')
const preview = computed(() => excel.rows.slice(0, 5).map((row, index) => ({ sortIndex: row.sortIndex || index + 1, generatedContent: excel.excelType === 'B' ? buildContent(row, excel.rules) : row['测试内容'] || '[空]' })))
watch(preview, (value) => excel.setPreview(value), { immediate: true })
const parsed = ({ file, excelType, headers, rows }) => { excel.setExcel({ file, excelType, headers, rows }); excel.setRules(excelType === 'B' ? [{ type: 'field', value: '设备中文' }, { type: 'field', value: '设备类型' }, { type: 'field', value: '设备编码' }] : []); ElMessage.success(excelType === 'A' ? '已识别为人工处理版' : '已识别为原始设备版，请配置生成规则') }
const clear = () => excel.reset()
const validate = () => {
  if (Object.values(location).some((value) => !String(value).trim())) return '请完整填写测试地点配置'
  if (!excel.rows.length) return '请先上传并解析 Excel 文件'
  if (excel.excelType === 'B' && !excel.rules.length) return '请配置测试内容生成规则'
}
const downloadBlob = (blob) => { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = '最终导入表.xlsx'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url) }
const submit = async () => {
  const message = validate(); if (message) return ElMessage.warning(message)
  const testContents = excel.rows.map((row, index) => ({ sortIndex: row.sortIndex || index + 1, generatedContent: excel.excelType === 'B' ? buildContent(row, excel.rules) : (row['测试内容'] || '[空]'), equipmentCode: excel.excelType === 'A' ? extractEquipmentCode(row['测试内容']) : (row['设备编码'] || ''), equipmentType: excel.excelType === 'A' ? (row['类型'] || '') : (row['设备类型'] || '') }))
  loading.value = true
  try { const response = await processExcel({ testLocation: { ...location }, testContents }); if (!response.data || response.data.size === 0) throw new Error('文件生成失败'); downloadBlob(response.data); ElMessage.success('文件生成成功，已开始下载') }
  catch (error) { ElMessage.error(error.response ? '文件生成失败' : '服务器连接失败') }
  finally { loading.value = false }
}
</script>
<template><div class="workspace"><div class="page-title"><div><h1>测试内容生成工作台</h1><p>上传 Excel，配置规则，生成学校系统可导入的正式文件。</p></div></div><el-card class="section-card"><template #header><b>1. 测试地点配置</b></template><LocationForm v-model="locationValue" /></el-card><el-card class="section-card"><template #header><b>2. Excel 上传与解析</b></template><UploadExcel @parsed="parsed" @clear="clear" /><el-alert v-if="excel.excelType" class="file-status" type="success" :closable="false" show-icon :title="`已识别：${excel.excelType === 'A' ? '人工处理版（直接使用测试内容）' : '原始设备版（需配置生成规则）'}，共 ${excel.rows.length} 条数据`" /></el-card><el-card v-if="excel.excelType === 'B'" class="section-card"><template #header><b>3. 测试内容生成规则</b></template><RuleBuilder v-model="excel.rules" /></el-card><el-card v-if="excel.excelType" class="section-card"><template #header><b>{{ excel.excelType === 'B' ? '实时预览（前 5 条）' : 'Excel 数据预览（前 5 条）' }}</b></template><ExcelPreview :rows="excel.rows" :excel-type="excel.excelType" :preview="preview" /></el-card><div v-if="excel.excelType" class="submit-panel"><el-button type="primary" size="large" :loading="loading" @click="submit">{{ submitLabel }}</el-button></div><LoadingDialog :visible="loading" /></div></template>
