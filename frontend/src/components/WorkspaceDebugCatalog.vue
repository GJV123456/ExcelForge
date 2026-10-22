<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Delete, EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createWorkspaceDebugItemsBatch, deleteWorkspaceDebugItem, getWorkspaceDebugItems, saveWorkspaceDebugItem } from '../api/workspace'
import { useWorkspaceStore } from '../store/workspace'
import { useUserStore } from '../store/user'
import { getApiErrorMessage } from '../utils/httpError'

const workspace = useWorkspaceStore()
const user = useUserStore()
const tableRef = ref(null)
const subitems = ref([])
const divisionsByParent = ref({})
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const copyVisible = ref(false)
const copyLoading = ref(false)
const copySaving = ref(false)
const copySourceProjectId = ref(null)
const copySourceSubitems = ref([])
const copyDivisionsByParent = ref({})
const selectedCopySubitemIds = ref([])
const selectedCopyDivisionIds = ref([])
const editingId = ref('')
const expandedSubitemId = ref(null)
const kind = ref('debug_subitems')
const parentId = ref(null)
const batchNames = ref('')
const form = reactive({ name: '', description: '', sortOrder: 1, isEnabled: true })
const canEdit = computed(() => user.userInfo.role === 'super_admin' || (String(user.userInfo.lineId) === String(workspace.selectedLineId) && (user.userInfo.role === 'line_admin' || String(user.userInfo.professionId) === String(workspace.selectedProfessionId))))
const scope = computed(() => ({ lineId: workspace.selectedLineId, professionId: workspace.selectedProfessionId, projectId: workspace.selectedProjectId }))
const rows = computed(() => subitems.value.map((item) => ({ ...item, children: divisionsByParent.value[item.id] || [] })))
const copySourceProjects = computed(() => workspace.projects.filter((item) => String(item.lineId) !== String(workspace.selectedLineId)))
const copySourceRows = computed(() => copySourceSubitems.value.map((item) => ({ ...item, children: copyDivisionsByParent.value[item.id] || [] })))
const copyAllSelected = computed(() => copySourceSubitems.value.length > 0 && copySourceSubitems.value.every((item) => selectedCopySubitemIds.value.includes(item.id)))
let requestId = 0

const onExpandChange = (row, expanded) => {
  if (row.category !== 'debug_subitems') return
  if (expanded === true) expandedSubitemId.value = row.id
  else if (expandedSubitemId.value === row.id) expandedSubitemId.value = null
  if (expanded !== true) return
  for (const item of rows.value) {
    if (item.id !== row.id) tableRef.value?.toggleRowExpansion(item, false)
  }
}

const toggleSubitem = (row) => {
  if (row.category !== 'debug_subitems' || !row.children?.length) return
  tableRef.value?.toggleRowExpansion(row, expandedSubitemId.value !== row.id)
}

const openCopy = () => {
  copySourceProjectId.value = null
  copySourceSubitems.value = []
  copyDivisionsByParent.value = {}
  selectedCopySubitemIds.value = []
  selectedCopyDivisionIds.value = []
  copyVisible.value = true
}

const loadCopySource = async () => {
  copySourceSubitems.value = []
  copyDivisionsByParent.value = {}
  selectedCopySubitemIds.value = []
  selectedCopyDivisionIds.value = []
  if (!copySourceProjectId.value) return
  copyLoading.value = true
  try {
    const source = workspace.projects.find((item) => String(item.id) === String(copySourceProjectId.value))
    const sourceScope = { lineId: source.lineId, professionId: source.professionId, projectId: source.id }
    const parents = (await getWorkspaceDebugItems({ ...sourceScope, category: 'debug_subitems' })).data?.data || []
    const childLists = await Promise.all(parents.map(async (item) => [
      item.id,
      (await getWorkspaceDebugItems({ ...sourceScope, category: 'debug_divisions', parentId: item.id })).data?.data || [],
    ]))
    copySourceSubitems.value = parents
    copyDivisionsByParent.value = Object.fromEntries(childLists)
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { copyLoading.value = false }
}

const toggleCopySubitem = (item, checked) => {
  const subitems = new Set(selectedCopySubitemIds.value)
  const divisions = new Set(selectedCopyDivisionIds.value)
  checked ? subitems.add(item.id) : subitems.delete(item.id)
  ;(copyDivisionsByParent.value[item.id] || []).forEach((division) => checked ? divisions.add(division.id) : divisions.delete(division.id))
  selectedCopySubitemIds.value = [...subitems]
  selectedCopyDivisionIds.value = [...divisions]
}

const toggleCopyDivision = (division, checked) => {
  const divisions = new Set(selectedCopyDivisionIds.value)
  const subitems = new Set(selectedCopySubitemIds.value)
  checked ? divisions.add(division.id) : divisions.delete(division.id)
  const parent = copySourceSubitems.value.find((item) => (copyDivisionsByParent.value[item.id] || []).some((child) => child.id === division.id))
  if (checked && parent) subitems.add(parent.id)
  selectedCopyDivisionIds.value = [...divisions]
  selectedCopySubitemIds.value = [...subitems]
}

const selectAllCopyHierarchy = (checked) => {
  selectedCopySubitemIds.value = checked ? copySourceSubitems.value.map((item) => item.id) : []
  selectedCopyDivisionIds.value = checked
    ? copySourceSubitems.value.flatMap((item) => (copyDivisionsByParent.value[item.id] || []).map((division) => division.id))
    : []
}

const copyHierarchy = async () => {
  if (!selectedCopySubitemIds.value.length) return ElMessage.warning('请选择要复制的调试子项')
  const source = workspace.projects.find((item) => String(item.id) === String(copySourceProjectId.value))
  if (!source) return
  copySaving.value = true
  let copiedSubitems = 0
  let copiedDivisions = 0
  try {
    const targetScope = scope.value
    const targetSubitems = (await getWorkspaceDebugItems({ ...targetScope, category: 'debug_subitems', includeDisabled: true })).data?.data || []
    const targetByName = new Map(targetSubitems.map((item) => [item.name.toLocaleLowerCase(), item]))
    for (const sourceSubitem of copySourceSubitems.value.filter((item) => selectedCopySubitemIds.value.includes(item.id))) {
      let targetSubitem = targetByName.get(sourceSubitem.name.toLocaleLowerCase())
      if (!targetSubitem) {
        targetSubitem = (await createWorkspaceDebugItemsBatch({ scope: targetScope, category: 'debug_subitems', names: [sourceSubitem.name], description: sourceSubitem.description || '' })).data?.data?.[0]
        targetByName.set(sourceSubitem.name.toLocaleLowerCase(), targetSubitem)
        copiedSubitems += 1
      }
      const selectedDivisions = (copyDivisionsByParent.value[sourceSubitem.id] || []).filter((item) => selectedCopyDivisionIds.value.includes(item.id))
      const targetDivisions = (await getWorkspaceDebugItems({ ...targetScope, category: 'debug_divisions', parentId: targetSubitem.id, includeDisabled: true })).data?.data || []
      const divisionNames = new Set(targetDivisions.map((item) => item.name.toLocaleLowerCase()))
      const names = selectedDivisions.filter((item) => !divisionNames.has(item.name.toLocaleLowerCase())).map((item) => item.name)
      if (names.length) {
        const response = await createWorkspaceDebugItemsBatch({ scope: targetScope, category: 'debug_divisions', parentId: targetSubitem.id, names })
        copiedDivisions += response.data?.data?.length || 0
      }
    }
    copyVisible.value = false
    await load()
    ElMessage.success(`已复制 ${copiedSubitems} 个调试子项、${copiedDivisions} 个调试分项`)
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { copySaving.value = false }
}

const load = async () => {
  const currentRequestId = ++requestId
  if (!workspace.isSelected) {
    subitems.value = []
    divisionsByParent.value = {}
    loading.value = false
    return
  }
  loading.value = true
  try {
    const base = scope.value
    const parents = (await getWorkspaceDebugItems({ ...base, category: 'debug_subitems', includeDisabled: canEdit.value })).data?.data || []
    if (currentRequestId !== requestId) return
    const childLists = await Promise.all(parents.map(async (item) => {
      const response = await getWorkspaceDebugItems({ ...base, category: 'debug_divisions', parentId: item.id, includeDisabled: canEdit.value })
      return [item.id, response.data?.data || []]
    }))
    if (currentRequestId !== requestId) return
    subitems.value = parents
    divisionsByParent.value = Object.fromEntries(childLists)
  } catch (error) {
    if (currentRequestId === requestId) ElMessage.error(await getApiErrorMessage(error))
  } finally {
    if (currentRequestId === requestId) loading.value = false
  }
}

const reset = (category, row = null, parent = null) => {
  kind.value = category
  editingId.value = row?.id || ''
  parentId.value = category === 'debug_divisions' ? (parent?.id || row?.parentId || null) : null
  Object.assign(form, row
    ? { name: row.name, description: row.description || '', sortOrder: row.sortOrder, isEnabled: row.isEnabled }
    : { name: '', description: '', sortOrder: 1, isEnabled: true })
  batchNames.value = ''
  visible.value = true
}

const save = async () => {
  if (kind.value === 'debug_divisions' && !parentId.value) return ElMessage.warning('请从所属调试子项下新增分项')
  const names = editingId.value ? [form.name.trim()] : batchNames.value.split(/\r?\n/).map((name) => name.trim()).filter(Boolean)
  if (!names.length) return ElMessage.warning('请输入至少一个名称')
  if (!editingId.value && new Set(names.map((name) => name.toLocaleLowerCase())).size !== names.length) {
    return ElMessage.warning('输入内容中有重复名称，请修改后再保存')
  }
  saving.value = true
  try {
    const payload = {
      scope: scope.value,
      category: kind.value,
      parentId: parentId.value,
      name: names[0],
      description: form.description.trim(),
      sortOrder: form.sortOrder,
      isEnabled: form.isEnabled,
    }
    const response = editingId.value
      ? await saveWorkspaceDebugItem(editingId.value, payload)
      : await createWorkspaceDebugItemsBatch({
          scope: scope.value,
          category: kind.value,
          parentId: parentId.value,
          names,
          description: form.description.trim(),
          sortOrder: form.sortOrder,
        })
    const savedItems = editingId.value ? [response.data?.data] : response.data?.data || []
    const targetList = kind.value === 'debug_subitems' ? subitems : null
    if (targetList) {
      if (editingId.value) targetList.value = targetList.value.map((item) => item.id === editingId.value ? savedItems[0] : item)
      else targetList.value = [...targetList.value, ...savedItems]
    } else {
      const current = [...(divisionsByParent.value[parentId.value] || [])]
      if (editingId.value) {
        divisionsByParent.value[parentId.value] = current.map((item) => item.id === editingId.value ? savedItems[0] : item)
      } else {
        divisionsByParent.value[parentId.value] = [...current, ...savedItems]
      }
    }
    visible.value = false
    ElMessage.success(editingId.value ? '已保存修改' : `已新增 ${savedItems.length} 条${kind.value === 'debug_subitems' ? '调试子项' : '调试分项'}`)
  } catch (error) { ElMessage.error(await getApiErrorMessage(error)) } finally { saving.value = false }
}

const remove = async (row) => {
  try {
    await ElMessageBox.confirm(
      row.category === 'debug_subitems'
        ? '删除该调试子项会同时删除其下所有分项。若有关联配置，将无法删除。'
        : '确认删除这个调试分项？若有关联配置，将无法删除。',
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteWorkspaceDebugItem(row.id, { ...scope.value, category: row.category })
    if (row.category === 'debug_subitems') {
      subitems.value = subitems.value.filter((item) => item.id !== row.id)
      const next = { ...divisionsByParent.value }
      delete next[row.id]
      divisionsByParent.value = next
    } else {
      divisionsByParent.value[row.parentId] = (divisionsByParent.value[row.parentId] || []).filter((item) => item.id !== row.id)
    }
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(await getApiErrorMessage(error))
  }
}

onMounted(load)
watch(() => [workspace.selectedLineId, workspace.selectedProfessionId, workspace.selectedProjectId], load)
</script>

<template>
  <div class="debug-catalog">
    <div class="debug-catalog-heading">
      <div>
        <h2>调试子项与分项</h2>
        <p>分项直接归属在对应调试子项下维护。</p>
      </div>
      <div class="debug-catalog-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
      <el-button v-if="canEdit" @click="openCopy">复制其他线路子项/分项</el-button>
      <el-button v-if="canEdit" type="primary" :icon="Plus" @click="reset('debug_subitems')">新增调试子项</el-button>
      </div>
    </div>
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="rows"
      row-key="id"
      :expand-row-keys="expandedSubitemId ? [expandedSubitemId] : []"
      :tree-props="{ children: 'children' }"
      @expand-change="onExpandChange"
      stripe
      class="debug-hierarchy-table"
      empty-text="当前项目还没有调试子项"
    >
      <el-table-column prop="name" label="名称" min-width="300">
        <template #default="{ row }">
          <span :class="row.category === 'debug_divisions' ? 'division-name' : 'subitem-name'" @click="toggleSubitem(row)">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="层级" width="130">
        <template #default="{ row }">{{ row.category === 'debug_subitems' ? '调试子项' : '调试分项' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }"><el-tag :type="row.isEnabled ? 'success' : 'info'" effect="light">{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column v-if="canEdit" label="操作" width="300" fixed="right" align="center">
        <template #default="{ row }">
          <div class="debug-row-actions">
            <el-button v-if="row.category === 'debug_subitems'" text type="primary" :icon="Plus" @click="reset('debug_divisions', null, row)">新增分项</el-button>
            <span v-else class="action-placeholder" aria-hidden="true" />
            <el-button text type="primary" :icon="EditPen" @click="reset(row.category, row)">编辑</el-button>
            <el-button text type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="editingId ? '编辑' : (kind === 'debug_subitems' ? '新增调试子项' : '新增调试分项')" width="min(560px, calc(100vw - 28px))">
      <el-form label-position="top">
        <el-form-item v-if="kind === 'debug_divisions'" label="所属调试子项"><el-input :model-value="subitems.find((item) => item.id === parentId)?.name || ''" disabled /></el-form-item>
        <el-form-item v-if="editingId" label="名称" required><el-input v-model="form.name" maxlength="200" /></el-form-item>
        <el-form-item v-else label="名称（每行一项，可一次新增多项）" required><el-input v-model="batchNames" type="textarea" :rows="5" maxlength="10000" placeholder="例如：&#10;烟感和温感&#10;手报和消火栓&#10;吸气式主机" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" :rows="2" maxlength="2000" /></el-form-item>
        <el-form-item v-if="editingId" label="排序"><el-input-number v-model="form.sortOrder" :min="1" controls-position="right" /></el-form-item>
        <el-form-item v-if="editingId" label="状态"><el-switch v-model="form.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">{{ editingId ? '保存修改' : '保存' }}</el-button></template>
    </el-dialog>
    <el-dialog v-model="copyVisible" title="复制其他线路调试子项与分项" width="min(780px, calc(100vw - 28px))" destroy-on-close>
      <p class="copy-dialog-tip">先复制调试层级，再到联调表单配置复制对应规则。已存在的同名层级会自动跳过。</p>
      <el-select v-model="copySourceProjectId" filterable clearable placeholder="选择其他线路的联调项目" @change="loadCopySource"><el-option v-for="item in copySourceProjects" :key="item.id" :label="`${workspace.lines.find((line) => String(line.id) === String(item.lineId))?.name || ''} / ${workspace.professions.find((profession) => String(profession.id) === String(item.professionId))?.name || ''} / ${item.code}`" :value="item.id" /></el-select>
      <div v-loading="copyLoading" class="copy-hierarchy-panel">
        <div v-if="copySourceRows.length" class="copy-hierarchy-toolbar"><el-checkbox :model-value="copyAllSelected" @change="selectAllCopyHierarchy">全选全部层级</el-checkbox><span>已选 {{ selectedCopySubitemIds.length }} 个子项、{{ selectedCopyDivisionIds.length }} 个分项</span></div>
        <el-table v-if="copySourceRows.length" :data="copySourceRows" row-key="id" :tree-props="{ children: 'children' }" stripe>
          <el-table-column label="调试子项 / 调试分项" min-width="360"><template #default="{ row }"><el-checkbox v-if="row.category === 'debug_subitems'" :model-value="selectedCopySubitemIds.includes(row.id)" @change="(checked) => toggleCopySubitem(row, checked)">{{ row.name }}</el-checkbox><el-checkbox v-else :model-value="selectedCopyDivisionIds.includes(row.id)" @change="(checked) => toggleCopyDivision(row, checked)">{{ row.name }}</el-checkbox></template></el-table-column>
          <el-table-column prop="code" label="固定编码" width="180" />
        </el-table>
        <el-empty v-else-if="!copyLoading" description="请选择来源项目" />
      </div>
      <template #footer><el-button @click="copyVisible = false">取消</el-button><el-button type="primary" :loading="copySaving" :disabled="!selectedCopySubitemIds.length" @click="copyHierarchy">复制到当前项目</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.debug-catalog { display: grid; gap: 14px; }
.debug-catalog-heading, .debug-catalog-actions, .debug-row-actions { display: flex; align-items: center; }
.debug-catalog-heading { justify-content: space-between; gap: 16px; }
.debug-catalog-heading h2 { margin: 0; color: #263750; font-size: 18px; }
.debug-catalog-heading p { margin: 5px 0 0; color: #8390a3; font-size: 13px; }
.debug-catalog-actions { gap: 8px; }
.debug-hierarchy-table { border: 1px solid #e1e8f2; border-radius: 10px; }
.debug-hierarchy-table :deep(th.el-table__cell) { height: 46px; color: #667892; background: #f7f9fc; }
.debug-hierarchy-table :deep(td.el-table__cell) { height: 52px; }
.subitem-name { color: #263750; font-weight: 650; }
.subitem-name { cursor: pointer; }
.subitem-name:hover { color: #327cf6; }
.division-name { color: #596b83; }
.debug-row-actions { justify-content: flex-start; gap: 4px; white-space: nowrap; overflow: visible; }
.debug-row-actions .el-button { margin: 0; }
.action-placeholder { display: inline-block; width: 78px; }
.debug-hierarchy-table :deep(.el-table__fixed-right) { height: 100% !important; }
.copy-dialog-tip { margin:0 0 14px;color:#71829a;font-size:13px;line-height:1.6; }
.copy-hierarchy-panel { min-height:180px;margin-top:14px; }
.copy-hierarchy-toolbar { display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;padding:9px 12px;border:1px solid #e1e8f2;border-radius:8px;background:#f8faff;color:#71829a;font-size:13px; }
.copy-hierarchy-panel :deep(.el-table) { border:1px solid #e1e8f2;border-radius:9px;overflow:hidden; }
@media (max-width: 680px) {
  .debug-catalog-heading { align-items: flex-start; flex-direction: column; }
  .debug-catalog-actions { width: 100%; justify-content: flex-end; }
}
</style>
