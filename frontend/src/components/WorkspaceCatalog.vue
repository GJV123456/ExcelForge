<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { createWorkspaceStationsBatch, getWorkspaceCatalog, saveWorkspaceCatalog, setWorkspaceCatalogStatus } from '../api/workspace'
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
const copyDialogVisible = ref(false)
const copySourceProjectId = ref(null)
const copySourceItems = ref([])
const copying = ref(false)
const editingId = ref('')
const batchNames = ref('')
const sameId = (left, right) => left != null && right != null && String(left) === String(right)
const canEdit = computed(() => user.userInfo.role === 'super_admin'
  || (user.userInfo.role === 'line_admin' && sameId(user.userInfo.lineId, workspace.selectedLineId))
  || (user.userInfo.role === 'professional_configurator' && sameId(user.userInfo.lineId, workspace.selectedLineId)
    && sameId(user.userInfo.professionId, workspace.selectedProfessionId)))
const categoryMeta = computed(() => ({
  equipment_types: { title: '设备类型', description: '维护当前线路、专业和项目独立使用的设备类型。', name: '设备类型名称', example: '例如：垂梯' },
  disciplines: { title: '责任专业', description: '维护当前线路共享的输出结果责任专业选项。', name: '专业名称', example: '例如：自动化' },
  stations: { title: '站点信息', description: '维护当前线路共享的站点信息。', name: '站点名称', example: '例如：嘉庚体育馆站' },
}[props.category] || {}))
const form = reactive({ code: '', name: '', description: '', sortOrder: 1, isEnabled: true })
const enabledCount = computed(() => items.value.filter((item) => item.isEnabled).length)
const catalogProjectId = computed(() => workspace.selectedProjectId || workspace.projects[0]?.id || 1)
const sortCatalogItems = (rows) => [...rows].sort((left, right) =>
  (Number(left.sortOrder) || 0) - (Number(right.sortOrder) || 0)
  || String(left.name || '').localeCompare(String(right.name || ''), 'zh-CN', { numeric: true })
  || String(left.id).localeCompare(String(right.id)))
const isLineSharedCategory = computed(() => ['disciplines', 'stations'].includes(props.category))
const hasCatalogScope = computed(() => props.category === 'disciplines'
  ? Boolean(workspace.selectedLineId && workspace.selectedProfessionId)
  : props.category === 'stations'
    ? Boolean(workspace.selectedLineId)
  : workspace.isSelected)
const scopePayload = () => ({ lineId: workspace.selectedLineId,
  professionId: workspace.selectedProfessionId, projectId: catalogProjectId.value })
const load = async () => {
  if (!hasCatalogScope.value) { items.value = []; return }
  loading.value = true
  try {
    const response = await getWorkspaceCatalog({ ...scopePayload(),
      category: props.category, includeDisabled: canEdit.value })
    items.value = sortCatalogItems(response.data?.data || [])
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { loading.value = false }
}
const openCreate = () => {
  editingId.value = ''
  batchNames.value = ''
  Object.assign(form, { code: '', name: '', description: '', sortOrder: Math.max(0, ...items.value.map((row) => row.sortOrder || 0)) + 1, isEnabled: true })
  dialogVisible.value = true
}
const openEdit = (row) => {
  editingId.value = row.id
  batchNames.value = ''
  Object.assign(form, { code: row.code || '', name: row.name, description: row.description || '', sortOrder: row.sortOrder, isEnabled: row.isEnabled })
  dialogVisible.value = true
}
const save = async () => {
  const names = props.category === 'stations' && !editingId.value
    ? batchNames.value.split(/\r?\n/).map((name) => name.trim()).filter(Boolean)
    : [form.name.trim()]
  if (!names.length) return ElMessage.warning(`请输入${categoryMeta.value.name}`)
  if (new Set(names.map((name) => name.toLocaleLowerCase())).size !== names.length) return ElMessage.warning('输入内容中有重复名称，请修改后再保存')
  saving.value = true
  let savedCount = 0
  try {
    if (props.category === 'stations' && !editingId.value) {
      await createWorkspaceStationsBatch({ scope: scopePayload(), names, description: form.description.trim(),
        sortOrder: Number(form.sortOrder), isEnabled: form.isEnabled })
      savedCount = names.length
    } else {
      for (const [index, name] of names.entries()) {
        await saveWorkspaceCatalog(editingId.value || null, { scope: scopePayload(), category: props.category,
          code: editingId.value ? (form.code.trim() || name) : name, name, description: form.description.trim(), sortOrder: editingId.value ? form.sortOrder : form.sortOrder + index, isEnabled: form.isEnabled })
        savedCount += 1
        if (editingId.value) break
      }
    }
    dialogVisible.value = false
    ElMessage.success(editingId.value ? '配置已更新' : `已新增 ${savedCount} 个${categoryMeta.value.title}`)
    await load()
  } catch (error) { ElMessage.error(savedCount ? `已新增 ${savedCount} 个，其余保存失败：${await getApiErrorMessage(error)}` : await getApiErrorMessage(error)) } finally { saving.value = false }
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
const copyFromProject = async () => {
  const source = workspace.projects.find((item) => String(item.id) === String(copySourceProjectId.value))
  if (!source) return
  try { copySourceItems.value = (await getWorkspaceCatalog({ lineId: source.lineId, professionId: source.professionId, projectId: source.id, category: props.category })).data?.data || [] }
  catch (error) { ElMessage.error(await getApiErrorMessage(error)) }
}
const copyCatalogItems = async () => {
  if (!copySourceItems.value.length) return ElMessage.warning('来源目录没有可复制的数据')
  copying.value = true
  let copied = 0
  try {
    for (const item of copySourceItems.value) {
      await saveWorkspaceCatalog(null, { scope: scopePayload(), category: props.category, code: item.code, name: item.name, description: item.description, sortOrder: item.sortOrder, isEnabled: item.isEnabled })
      copied += 1
    }
    copyDialogVisible.value = false
    ElMessage.success(`已复制 ${copied} 项到当前线路`)
    await load()
  } catch (error) { ElMessage.error(copied ? `已复制 ${copied} 项，其余项目因名称或编码冲突未复制：${await getApiErrorMessage(error)}` : await getApiErrorMessage(error)) } finally { copying.value = false }
}
onMounted(load)
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId, props.category], load)
</script>

<template>
  <div class="workspace-catalog" v-loading="loading">
    <div class="catalog-hero">
      <div><el-tag type="primary" effect="light" round>{{ isLineSharedCategory ? '线路共享目录' : '独立配置目录' }}</el-tag><h2>{{ categoryMeta.title }}</h2><p>{{ categoryMeta.description }}</p></div>
      <div class="catalog-stats"><div><strong>{{ items.length }}</strong><span>全部</span></div><div><strong>{{ enabledCount }}</strong><span>启用中</span></div><div><strong>{{ items.length - enabledCount }}</strong><span>已停用</span></div></div>
      <div v-if="canEdit" class="catalog-actions"><el-button v-if="['disciplines', 'stations'].includes(props.category)" plain @click="copyDialogVisible = true">复制其他线路{{ props.category === 'stations' ? '站点' : '/专业' }}</el-button><el-button type="primary" :icon="Plus" @click="openCreate">新增{{ categoryMeta.title }}</el-button></div>
    </div>
    <div class="catalog-toolbar"><span>当前范围：{{ workspace.selectedLine?.name }}<template v-if="!isLineSharedCategory"> / {{ workspace.selectedProfession?.name }} / {{ workspace.selectedProject?.name }}</template></span><el-button plain :icon="Refresh" :loading="loading" @click="load">刷新</el-button></div>
    <el-table :data="items" stripe class="catalog-table" empty-text="当前范围暂无配置">
      <el-table-column prop="sortOrder" label="排序" width="82" align="center" />
      <el-table-column label="编码" min-width="150"><template #default="{ row }">{{ row.code || '—' }}</template></el-table-column>
      <el-table-column prop="name" :label="categoryMeta.name" min-width="180" />
      <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
      <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column v-if="canEdit" label="操作" width="170" fixed="right" align="center"><template #default="{ row }"><div class="catalog-row-actions"><el-button text type="primary" :icon="EditPen" @click="openEdit(row)">编辑</el-button><el-switch :model-value="row.isEnabled" inline-prompt active-text="启用" inactive-text="停用" @change="(enabled) => toggleStatus(row, enabled)" /></div></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" :title="editingId ? `编辑${categoryMeta.title}` : `新增${categoryMeta.title}`" width="min(620px, calc(100vw - 32px))" destroy-on-close>
      <el-form label-position="top"><div class="catalog-form-grid"><el-form-item v-if="props.category === 'stations' && !editingId" class="catalog-form-wide" label="站点名称（每行一项，可一次新增多个）" required><el-input v-model="batchNames" type="textarea" :rows="6" :placeholder="`${categoryMeta.example}\n例如：站厅层\n站台层`" /></el-form-item><el-form-item v-else label="名称" required><el-input v-model="form.name" :placeholder="categoryMeta.example" /></el-form-item><el-form-item v-if="!(props.category === 'stations' && !editingId)" label="编码"><el-input v-model="form.code" placeholder="可选" /></el-form-item><el-form-item label="排序"><el-input-number v-model="form.sortOrder" :min="1" controls-position="right" /></el-form-item><el-form-item label="状态"><el-switch v-model="form.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item><el-form-item class="catalog-form-wide" label="说明"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item></div></el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="copyDialogVisible" :title="`复制${categoryMeta.title}`" width="min(620px, calc(100vw - 32px))"><p>复制会在当前线路建立独立目录，不会修改来源线路或专业。</p><el-select v-model="copySourceProjectId" filterable placeholder="选择来源线路、专业和项目" @change="copyFromProject"><el-option v-for="item in workspace.projects.filter((project) => project.isEnabled !== false && (String(project.lineId) !== String(workspace.selectedLineId) || String(project.professionId) !== String(workspace.selectedProfessionId)))" :key="item.id" :label="`${workspace.lines.find((line) => String(line.id) === String(item.lineId))?.name || ''} / ${workspace.professions.find((profession) => String(profession.id) === String(item.professionId))?.name || ''} / ${item.code}`" :value="item.id" /></el-select><el-table v-if="copySourceItems.length" :data="copySourceItems" stripe style="margin-top:14px"><el-table-column prop="name" :label="`将复制的${categoryMeta.title}`" /><el-table-column prop="code" label="编码" width="140" /></el-table><template #footer><el-button @click="copyDialogVisible = false">取消</el-button><el-button type="primary" :loading="copying" @click="copyCatalogItems">复制到当前线路</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.catalog-hero{display:flex;align-items:center;gap:24px;margin:8px 0 18px;padding:22px 24px;border:1px solid #dce8fb;border-radius:15px;background:linear-gradient(135deg,#f4f8ff,#fbfdff 58%,#f1f7ff);box-shadow:0 8px 24px #2c5ba012}.catalog-hero>div:first-child{flex:1}.catalog-hero h2{margin:10px 0 5px;color:#1f3454;font-size:22px}.catalog-hero p{margin:0;color:#71829a;font-size:13px}.catalog-stats{display:flex;gap:10px}.catalog-stats>div{min-width:76px;padding:9px 12px;border:1px solid #dfe8f5;border-radius:10px;background:#ffffffc9;text-align:center}.catalog-stats strong,.catalog-stats span{display:block}.catalog-stats strong{color:#31558d;font-size:20px}.catalog-stats span{margin-top:3px;color:#8190a5;font-size:12px}.catalog-toolbar{display:flex;justify-content:space-between;align-items:center;margin:0 2px 12px;color:#71829a;font-size:13px}.catalog-table{overflow:hidden;border:1px solid #e1e8f2;border-radius:13px;box-shadow:0 7px 22px #233b5f0d}.catalog-table :deep(th.el-table__cell){height:48px;color:#667892;background:#f7f9fc;font-size:13px;font-weight:700}.catalog-table :deep(td.el-table__cell){height:58px;color:#42536c;border-bottom-color:#edf1f6}.catalog-row-actions{display:flex;align-items:center;justify-content:center;gap:10px}.catalog-row-actions .el-button{margin:0}.catalog-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}.catalog-form-grid :deep(.el-input-number){width:100%}.catalog-form-wide{grid-column:1/-1}@media(max-width:720px){.catalog-hero{align-items:stretch;flex-direction:column;padding:18px}.catalog-stats{width:100%}.catalog-stats>div{flex:1}.catalog-toolbar{align-items:stretch;flex-direction:column;gap:8px}.catalog-form-grid{grid-template-columns:1fr}.catalog-form-wide{grid-column:auto}}
</style>
