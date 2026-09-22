<script setup>
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { parseExcel } from '../utils/excelParser'

const emit = defineEmits(['parsed', 'clear'])
const uploadRef = ref()
const resetUpload = () => {
  uploadRef.value?.clearFiles()
  emit('clear')
}
const validateFile = (file) => {
  const name = file.name.toLowerCase()
  const isExcelFile = name.endsWith('.xlsx') || name.endsWith('.xls')
  if (!isExcelFile) { ElMessage.error('仅支持xlsx或xls文件'); return false }
  if (file.size > 100 * 1024 * 1024) { ElMessage.error('文件大小不能超过100MB'); return false }
  return true
}
const beforeUpload = (file) => {
  const valid = validateFile(file)
  if (!valid) resetUpload()
  return valid
}
const parseFile = async (file) => {
  if (!validateFile(file)) return resetUpload()
  emit('clear')
  try { emit('parsed', { file, ...(await parseExcel(file)) }) }
  catch (error) {
    // 清空 Element Plus 内部文件列表，保留工作台上已填写的地点等状态，允许立即重新选择同一文件。
    resetUpload()
    ElMessage({ type: 'error', message: error.message || 'Excel格式错误，请修正后重新上传', duration: 8000, showClose: true })
  }
}
const handleChange = async (uploadFile) => parseFile(uploadFile.raw)
const handleExceed = async (files) => {
  uploadRef.value?.clearFiles()
  parseFile(files[0])
}
</script>

<template>
  <el-upload ref="uploadRef" drag accept=".xlsx,.xls" :auto-upload="false" :limit="1" :before-upload="beforeUpload" :on-change="handleChange" :on-exceed="handleExceed" :on-remove="() => emit('clear')">
    <el-icon class="upload-icon"><UploadFilled /></el-icon><div class="el-upload__text">拖拽 Excel 文件到此处，或 <em>点击上传</em></div>
    <template #tip><div class="el-upload__tip">支持 .xlsx / .xls 文件，大小不超过 100MB</div></template>
  </el-upload>
</template>
