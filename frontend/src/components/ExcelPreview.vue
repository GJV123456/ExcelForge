<script setup>
import { computed } from 'vue'
import { extractEquipmentCode } from '../utils/excelParser'

const props = defineProps({ rows: { type: Array, default: () => [] }, excelType: { type: String, default: '' }, preview: { type: Array, default: () => [] } })
const showIntervalColumn = computed(() => props.preview.some((row) => row.intervalName))
</script>
<template>
  <el-table v-if="excelType === 'B'" :data="preview" stripe max-height="280"><el-table-column prop="sortIndex" label="序号" width="90" align="center" header-align="center" /><el-table-column prop="generatedContent" label="生成内容" align="center" header-align="center" /><el-table-column prop="equipmentType" label="设备类型" width="140" align="center" header-align="center"><template #default="{ row }">{{ row.equipmentType || '-' }}</template></el-table-column><el-table-column prop="equipmentSubtype" label="子类型" width="140" align="center" header-align="center"><template #default="{ row }">{{ row.equipmentSubtype || '-' }}</template></el-table-column><el-table-column prop="equipmentStatus" label="状态/动作" min-width="180" align="center" header-align="center"><template #default="{ row }">{{ row.equipmentStatus || '-' }}</template></el-table-column><el-table-column v-if="showIntervalColumn" prop="intervalName" label="区间名称" width="130" align="center" header-align="center"><template #default="{ row }">{{ row.intervalName }}</template></el-table-column></el-table>
  <el-table v-else :data="rows.slice(0, 5)" stripe max-height="280"><el-table-column prop="sortIndex" label="序号" width="90" align="center" header-align="center" /><el-table-column prop="测试内容" label="测试内容" align="center" header-align="center" /><el-table-column label="设备编号" width="140" align="center" header-align="center"><template #default="{ row }">{{ extractEquipmentCode(row['测试内容']) || '-' }}</template></el-table-column><el-table-column prop="类型" label="类型" align="center" header-align="center" /></el-table>
</template>
