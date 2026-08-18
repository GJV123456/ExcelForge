<script setup>
import { extractEquipmentCode } from '../utils/excelParser'

defineProps({ rows: { type: Array, default: () => [] }, excelType: { type: String, default: '' }, preview: { type: Array, default: () => [] } })
</script>
<template>
  <el-table v-if="excelType === 'B'" :data="preview" stripe max-height="280"><el-table-column prop="sortIndex" label="序号" width="90" /><el-table-column prop="generatedContent" label="生成内容" /><el-table-column prop="equipmentType" label="设备类型" width="140"><template #default="{ row }">{{ row.equipmentType || '[空]' }}</template></el-table-column><el-table-column prop="equipmentSubtype" label="子类型" width="140"><template #default="{ row }">{{ row.equipmentSubtype || '[空]' }}</template></el-table-column><el-table-column prop="equipmentStatus" label="状态/动作" min-width="180"><template #default="{ row }">{{ row.equipmentStatus || '[空]' }}</template></el-table-column></el-table>
  <el-table v-else :data="rows.slice(0, 5)" stripe max-height="280"><el-table-column prop="sortIndex" label="序号" width="90" /><el-table-column prop="测试内容" label="测试内容" /><el-table-column label="设备编号" width="140"><template #default="{ row }">{{ extractEquipmentCode(row['测试内容']) || '[空]' }}</template></el-table-column><el-table-column prop="类型" label="类型" /></el-table>
</template>
