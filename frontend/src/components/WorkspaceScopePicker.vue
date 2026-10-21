<script setup>
import { computed } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useWorkspaceStore } from '../store/workspace'
import { useExcelStore } from '../store/excel'

defineProps({ compact: { type: Boolean, default: false } })

const workspace = useWorkspaceStore()
const excel = useExcelStore()
const projectsForProfession = computed(() => workspace.projects.filter((item) => item.professionId === workspace.selectedProfessionId))
const syncEngineProject = () => {
  const project = workspace.selectedProject
  excel.setIntegration(project?.engineCode || project?.code || '')
}
const retry = async () => {
  try {
    await workspace.reload()
    syncEngineProject()
    ElMessage.success('工作区数据已刷新')
  } catch (error) {
    ElMessage.error(workspace.error || error.message || '工作区数据加载失败')
  }
}
</script>

<template>
  <div v-if="compact" class="scope-picker-compact" aria-label="当前工作范围">
    <el-select v-model="workspace.selectedLineId" :loading="workspace.loading" :disabled="workspace.loading" placeholder="线路" aria-label="线路" no-data-text="暂无线路，请先到系统管理新增" @change="workspace.setLine">
      <el-option v-for="item in workspace.lines" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
    <el-select v-model="workspace.selectedProfessionId" :loading="workspace.loading" :disabled="workspace.loading" placeholder="专业" aria-label="专业" no-data-text="暂无专业，请先到系统管理新增" @change="workspace.setProfession">
      <el-option v-for="item in workspace.professions" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
    <el-select v-model="workspace.selectedProjectId" :loading="workspace.loading" :disabled="workspace.loading || !workspace.selectedProfessionId" placeholder="联调项目" aria-label="联调项目" no-data-text="当前专业暂无联调项目" @change="workspace.setProject">
      <el-option v-for="item in projectsForProfession" :key="item.id" :label="item.name" :value="item.id" />
    </el-select>
    <el-alert v-if="workspace.error" type="error" :closable="false" show-icon class="scope-compact-alert" :title="workspace.error" />
  </div>
  <section v-else class="scope-picker" aria-label="当前工作范围">
    <div class="scope-picker-heading">
      <div>
        <span class="scope-picker-title">选择工作范围</span>
        <span class="scope-picker-hint">先选择线路、专业，再进入对应联调项目</span>
      </div>
      <el-button text type="primary" :icon="Refresh" :loading="workspace.loading" @click="retry">刷新</el-button>
    </div>
    <el-alert v-if="workspace.error" type="error" :closable="false" show-icon class="scope-alert" :title="workspace.error">
      <template #default><span>请确认后端已启动并使用正确的数据库路径。</span></template>
    </el-alert>
    <div class="scope-fields">
      <label>
        <span>线路</span>
        <el-select v-model="workspace.selectedLineId" :loading="workspace.loading" :disabled="workspace.loading" placeholder="请选择线路" no-data-text="暂无线路，请先到系统管理新增" @change="workspace.setLine">
          <el-option v-for="item in workspace.lines" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </label>
      <label>
        <span>专业</span>
        <el-select v-model="workspace.selectedProfessionId" :loading="workspace.loading" :disabled="workspace.loading" placeholder="请选择专业" no-data-text="暂无专业，请先到系统管理新增" @change="workspace.setProfession">
          <el-option v-for="item in workspace.professions" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </label>
      <label>
        <span>联调项目</span>
        <el-select v-model="workspace.selectedProjectId" :loading="workspace.loading" :disabled="workspace.loading || !workspace.selectedProfessionId" placeholder="请选择联调项目" no-data-text="当前专业暂无联调项目" @change="workspace.setProject">
          <el-option v-for="item in projectsForProfession" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </label>
    </div>
    <div v-if="!workspace.loading && !workspace.error && (!workspace.lines.length || !workspace.professions.length || !workspace.projects.length)" class="scope-empty">
      暂无可用层级，请超级管理员进入“系统管理”配置线路、专业和联调项目。
    </div>
  </section>
</template>

<style scoped>
.scope-picker { margin: 18px 0 22px; padding: 18px 20px 20px; border: 1px solid #dfe8f5; border-radius: 14px; background: linear-gradient(135deg, #fbfdff, #f5f8ff); box-shadow: 0 8px 24px rgba(47, 78, 125, .06); }
.scope-picker-compact { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 0 0 auto; }
.scope-picker-compact :deep(.el-select:nth-of-type(1)) { width: 104px; }
.scope-picker-compact :deep(.el-select:nth-of-type(2)) { width: 116px; }
.scope-picker-compact :deep(.el-select:nth-of-type(3)) { width: 112px; }
.scope-picker-compact :deep(.el-select__wrapper) { min-height: 36px; padding-right: 9px; padding-left: 11px; }
.scope-compact-alert { position: absolute; top: 100%; right: 0; z-index: 10; width: min(420px, 90vw); }
.scope-picker-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 15px; }
.scope-picker-title { display: block; color: #243653; font-size: 16px; font-weight: 700; }
.scope-picker-hint { display: block; margin-top: 4px; color: #8491a5; font-size: 12px; }
.scope-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.scope-fields label { display: grid; gap: 7px; color: #62728a; font-size: 13px; font-weight: 600; }
.scope-fields :deep(.el-select) { width: 100%; }
.scope-alert { margin-bottom: 14px; }
.scope-empty { margin-top: 14px; color: #b07a2b; font-size: 13px; }
@media (max-width: 720px) { .scope-fields { grid-template-columns: 1fr; } .scope-picker-heading { align-items: flex-start; } }
@media (max-width: 760px) { .scope-picker-compact { flex-wrap: wrap; justify-content: flex-start; gap: 6px; }.scope-picker-compact :deep(.el-select:nth-of-type(n)) { width: auto; min-width: 92px; flex: 1; } }
</style>
