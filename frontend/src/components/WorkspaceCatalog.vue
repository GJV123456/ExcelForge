<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getWorkspaceCatalog, saveWorkspaceCatalog, setWorkspaceCatalogStatus } from '../api/workspace'
import { useWorkspaceStore } from '../store/workspace'
import { useUserStore } from '../store/user'
import { getApiErrorMessage } from '../utils/httpError'

const props = defineProps({ category: { type: String, required: true } })
const workspace = useWorkspaceStore()
const user = useUserStore()
const items = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref('')
const sameId = (left, right) => left != null && right != null && String(left) === String(right)
const canEdit = computed(() => user.userInfo.role === 'super_admin'
  || (user.userInfo.role === 'line_admin' && sameId(user.userInfo.lineId, workspace.selectedLineId))
  || (user.userInfo.role === 'professional_configurator' && sameId(user.userInfo.lineId, workspace.selectedLineId)
    && sameId(user.userInfo.professionId, workspace.selectedProfessionId)))
const categoryMeta = computed(() => ({
  equipment_types: { title: '设备类型', description: '维护当前线路、专业和项目独立使用的设备类型。', name: '设备类型名称', example: '例如：垂梯' },
  disciplines: { title: '责任专业', description: '维护当前范围内输出结果的责任专业选项。', name: '专业名称', example: '例如：自动化' },
  stations: { title: '站点信息', description: '维护当前线路、专业和项目独立使用的站点。', name: '站点名称', example: '例如：嘉庚体育馆站' },
}[props.category] || {}))
const form = reactive({ code: '', name: '', description: '', sortOrder: 1, isEnabled: true })
const enabledCount = computed(() => items.value.filter((item) => item.isEnabled).length)
const load = async () => {
  if (!workspace.isSelected) { items.value = []; return }
  loading.value = true
  try {
    const response = await getWorkspaceCatalog({ lineId: workspace.selectedLineId,
      professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId,
      category: props.category, includeDisabled: canEdit.value })
    items.value = response.data?.data || []
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { loading.value = false }
}
const openCreate = () => {
  editingId.value = ''
  Object.assign(form, { code: '', name: '', description: '', sortOrder: Math.max(0, ...items.value.map((row) => row.sortOrder || 0)) + 1, isEnabled: true })
  dialogVisible.value = true
}
const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, { code: row.code || '', name: row.name, description: row.description || '', sortOrder: row.sortOrder, isEnabled: row.isEnabled })
  dialogVisible.value = true
}
const save = async () => {
  if (!form.name.trim()) return ElMessage.warning(`请输入${categoryMeta.value.name}`)
  saving.value = true
  try {
    await saveWorkspaceCatalog(editingId.value || null, { scope: { lineId: workspace.selectedLineId,
      professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId }, category: props.category,
      code: form.code.trim() || form.name.trim(), name: form.name.trim(), description: form.description.trim(), sortOrder: form.sortOrder, isEnabled: form.isEnabled })
    dialogVisible.value = false
    ElMessage.success(editingId.value ? '配置已更新' : '配置已新增')
    await load()
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { saving.value = false }
}
const toggleStatus = async (row, enabled) => {
  const previous = row.isEnabled
  row.isEnabled = enabled
  try {
    await setWorkspaceCatalogStatus(row.id, enabled, { lineId: workspace.selectedLineId,
      professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId, category: props.category })
    ElMessage.success(enabled ? '已启用' : '已停用')
  } catch (error) { row.isEnabled = previous; ElMessage.error(await getApiErrorMessage(error)) }
}
onMounted(load)
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId, props.category], load)
</script>

<template>
  <div class="workspace-catalog" v-loading="loading">
    <div class="catalog-hero">
      <div><el-tag type="primary" effect="light" round>独立配置目录</el-tag><h2>{{ categoryMeta.title }}</h2><p>{{ categoryMeta.description }}</p></div>
      <div class="catalog-stats"><div><strong>{{ items.length }}</strong><span>全部</span></div><div><strong>{{ enabledCount }}</strong><span>启用中</span></div><div><strong>{{ items.length - enabledCount }}</strong><span>已停用</span></div></div>
      <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openCreate">新增{{ categoryMeta.title }}</el-button>
    </div>
    <div class="catalog-toolbar"><span>当前范围：{{ workspace.selectedLine?.name }} / {{ workspace.selectedProfession?.name }} / {{ workspace.selectedProject?.name }}</span><el-button plain :icon="Refresh" :loading="loading" @click="load">刷新</el-button></div>
    <el-table :data="items" stripe class="catalog-table" empty-text="当前范围暂无配置">
      <el-table-column prop="sortOrder" label="排序" width="82" align="center" />
      <el-table-column label="编码" min-width="150"><template #default="{ row }">{{ row.code || '—' }}</template></el-table-column>
      <el-table-column prop="name" :label="categoryMeta.name" min-width="180" />
      <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
      <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column v-if="canEdit" label="操作" width="170" fixed="right" align="center"><template #default="{ row }"><div class="catalog-row-actions"><el-button text type="primary" :icon="EditPen" @click="openEdit(row)">编辑</el-button><el-switch :model-value="row.isEnabled" inline-prompt active-text="启用" inactive-text="停用" @change="(enabled) => toggleStatus(row, enabled)" /></div></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" :title="editingId ? `编辑${categoryMeta.title}` : `新增${categoryMeta.title}`" width="min(620px, calc(100vw - 32px))" destroy-on-close>
      <el-form label-position="top"><div class="catalog-form-grid"><el-form-item label="名称" required><el-input v-model="form.name" :placeholder="categoryMeta.example" /></el-form-item><el-form-item label="编码"><el-input v-model="form.code" placeholder="可选" /></el-form-item><el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="1" controls-position="right" /></el-form-item><el-form-item label="状态"><el-switch v-model="form.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item><el-form-item class="catalog-form-wide" label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item></div></el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.catalog-hero{display:flex;align-items:center;gap:24px;margin:8px 0 18px;padding:22px 24px;border:1px solid #dce8fb;border-radius:15px;background:linear-gradient(135deg,#f4f8ff,#fbfdff 58%,#f1f7ff);box-shadow:0 8px 24px #2c5ba012}.catalog-hero>div:first-child{flex:1}.catalog-hero h2{margin:10px 0 5px;color:#1f3454;font-size:22px}.catalog-hero p{margin:0;color:#71829a;font-size:13px}.catalog-stats{display:flex;gap:10px}.catalog-stats>div{min-width:76px;padding:9px 12px;border:1px solid #dfe8f5;border-radius:10px;background:#ffffffc9;text-align:center}.catalog-stats strong,.catalog-stats span{display:block}.catalog-stats strong{color:#31558d;font-size:20px}.catalog-stats span{margin-top:3px;color:#8190a5;font-size:12px}.catalog-toolbar{display:flex;justify-content:space-between;align-items:center;margin:0 2px 12px;color:#71829a;font-size:13px}.catalog-table{overflow:hidden;border:1px solid #e1e8f2;border-radius:13px;box-shadow:0 7px 22px #233b5f0d}.catalog-table :deep(th.el-table__cell){height:48px;color:#667892;background:#f7f9fc;font-size:13px;font-weight:700}.catalog-table :deep(td.el-table__cell){height:58px;color:#42536c;border-bottom-color:#edf1f6}.catalog-row-actions{display:flex;align-items:center;justify-content:center;gap:10px}.catalog-row-actions .el-button{margin:0}.catalog-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}.catalog-form-grid :deep(.el-input-number){width:100%}.catalog-form-wide{grid-column:1/-1}@media(max-width:720px){.catalog-hero{align-items:stretch;flex-direction:column;padding:18px}.catalog-stats{width:100%}.catalog-stats>div{flex:1}.catalog-toolbar{align-items:stretch;flex-direction:column;gap:8px}.catalog-form-grid{grid-template-columns:1fr}.catalog-form-wide{grid-column:auto}}
</style>
