<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowDown, ArrowUp, Delete, EditPen, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createDiscipline,
  createEquipmentType,
  createTestContent,
  deleteDiscipline,
  deleteEquipmentSubtype,
  deleteEquipmentType,
  deleteTestContent,
  getDisciplines,
  getStations,
  getEquipmentSubtypes,
  getEquipmentTypes,
  getEquipmentHierarchy,
  getTestContents,
  updateEquipmentSubtypeStatuses,
  updateDiscipline,
  createStation,
  updateStation,
  deleteStation,
  updateEquipmentType,
  updateTestContent
} from '../api/catalog'
import { getApiErrorMessage } from '../utils/httpError'
import {
  buildTestContentPayload,
  createOperationStep,
  createResultOutput,
  createRuleDraft,
  getBuiltinStatuses,
  validateRuleDraft,
  inferRuleStatus,
  selectorMatches
} from '../utils/catalogRule'

// 页面级状态：规则、责任专业分别加载，避免把接口数据直接改坏。
const activeTab = ref('rules')
const pageLoading = ref(false)
const rulesLoading = ref(false)
const savingRule = ref(false)
const equipmentTypes = ref([])
const disciplines = ref([])
const stations = ref([])
const stationKeyword = ref('')
const rules = ref([])
const selectedEquipmentCode = ref('')
const selectedSubtypeName = ref('')
const selectedStatus = ref('')
const loadedEquipmentCode = ref('')
const selectedRuleId = ref(null)
const editorMode = ref('empty')
const draft = ref(null)
const baseline = ref('')
const undoAction = ref(null)
// 部分历史目录响应可能没有回传子类型。保存成功后先在本次页面会话中
// 保留提交的子类型，避免重新加载时暂时丢失筛选结果。
const ruleSelectorOverrides = reactive(new Map())

const saveRuleSelectorOverride = (rule, selector) => {
  if (rule?.id != null) ruleSelectorOverrides.set(`id:${rule.id}`, selector)
  if (rule?.code) ruleSelectorOverrides.set(`code:${rule.code}`, selector)
}

const getRuleSelectorOverride = (rule) => (
  ruleSelectorOverrides.get(`id:${rule?.id}`)
  || ruleSelectorOverrides.get(`code:${rule?.code}`)
)

const deleteRuleSelectorOverride = (rule) => {
  if (rule?.id != null) ruleSelectorOverrides.delete(`id:${rule.id}`)
  if (rule?.code) ruleSelectorOverrides.delete(`code:${rule.code}`)
}
// key 是步骤下标，值为 true 表示该步骤的输出结果已展开。
const expandedStepResults = reactive({})

const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuRule = ref(null)

const closeContextMenu = () => { contextMenuVisible.value = false }

const showContextMenu = (event, rule) => {
  event.preventDefault()
  contextMenuRule.value = rule
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  contextMenuVisible.value = true
}

const contextEditRule = async (rule) => {
  closeContextMenu()
  await selectRule(rule)
  await enterEdit()
}

const contextDeleteRule = async (rule) => {
  closeContextMenu()
  await selectRule(rule)
  await removeRule()
}

const disciplineDialogVisible = ref(false)
const disciplineSaving = ref(false)
const disciplineMode = ref('create')
const disciplineForm = reactive({ id: null, code: '', name: '', description: '', sortOrder: 1, isEnabled: true })
const equipmentDialogVisible = ref(false)
const equipmentSaving = ref(false)
const equipmentMode = ref('create')
const equipmentForm = reactive({ id: null, code: '', name: '', description: '', sortOrder: 1, isEnabled: true, subtypes: [] })
const equipmentTableRef = ref()
const statusDialogVisible = ref(false)
const statusSaving = ref(false)
const statusParent = ref(null)
const statusSubtype = ref(null)
const statusDraft = ref([])
const stationDialogVisible = ref(false)
const stationSaving = ref(false)
const stationMode = ref('create')
const stationForm = reactive({ id: null, code: '', name: '', description: '', sortOrder: 1, isEnabled: true })
const filteredStations = computed(() => {
  const keyword = stationKeyword.value.trim().toLocaleLowerCase()
  if (!keyword) return stations.value
  return stations.value.filter((station) => (
    [station.name, station.code, station.description]
      .some((value) => String(value || '').toLocaleLowerCase().includes(keyword))
  ))
})

const createEquipmentSubtypeDraft = () => ({
  id: null,
  name: '',
  sortOrder: 1,
  isEnabled: true,
  statuses: []
})

const addEquipmentSubtype = () => equipmentForm.subtypes.push({
  ...createEquipmentSubtypeDraft(),
  sortOrder: equipmentForm.subtypes.length + 1
})

const removeEquipmentSubtype = (index) => equipmentForm.subtypes.splice(index, 1)

const addEquipmentSubtypeStatus = (subtype) => subtype.statuses.push('')

const removeEquipmentSubtypeStatus = (subtype, index) => subtype.statuses.splice(index, 1)

const removeSavedEquipmentSubtype = async (parent, subtype) => {
  try {
    await ElMessageBox.confirm(
      `确认删除子类型“${subtype.name}”？其状态/动作也会一并删除，已被规则使用时无法删除。`,
      '删除设备子类型？',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteEquipmentSubtype(subtype.id)
    await refreshEquipmentDirectory(parent.code)
    ElMessage.success('设备子类型已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    await showError(error)
  }
}

// 顶部目录只选择父设备类型，规则编辑器再选择该父类型下的子类型。
const equipmentOptions = computed(() => equipmentTypes.value.map((parent) => ({
  key: `type:${parent.id}`,
  parent,
  subtype: null,
  label: parent.name,
  queryCode: parent.code
})))
const selectedEquipmentOption = computed(() => equipmentOptions.value.find((item) => item.key === selectedEquipmentCode.value))
const selectedEquipment = computed(() => selectedEquipmentOption.value?.parent)
const selectedSubtypes = computed(() => selectedEquipment.value?.subtypes || [])
const selectedSubtype = computed(() => selectedSubtypes.value.find((item) => item.name === selectedSubtypeName.value))
const availableStatuses = computed(() => selectedSubtype.value?.statuses?.length
  ? selectedSubtype.value.statuses
  : ((selectedEquipment.value?.statuses?.length
    ? selectedEquipment.value.statuses
    : getBuiltinStatuses(selectedEquipment.value?.name, selectedSubtypeName.value))))
const draftAvailableStatuses = computed(() => {
  const subtype = selectedSubtypes.value.find((item) => item.name === draft.value?.equipmentSubtype)
  return statusesForSubtype(selectedEquipment.value?.name, draft.value?.equipmentSubtype, subtype)
})
const trimParentPrefix = (value, parentName) => {
  const text = String(value || '').trim()
  if (!text || !parentName) return text
  const prefix = String(parentName).trim()
  return text.startsWith(`${prefix}/`) || text.startsWith(`${prefix} /`)
    ? text.slice(text.indexOf('/') + 1).trim()
    : text
}

const statusesForSubtype = (parentName, subtypeName, subtype) => {
  const configured = subtype?.statuses?.length ? subtype.statuses : []
  if (configured.length) return configured
  const variants = [subtypeName, String(subtypeName || '').replace(/等$/, ''), String(subtypeName || '').replace(/测试$/, '房功能测试')]
  for (const variant of variants) {
    const values = getBuiltinStatuses(parentName, variant)
    if (values.length) return values
  }
  return []
}

// 左侧规则菜单只显示最有辨识度的一层：有状态/动作就显示状态，
// 没有状态时显示子类型，避免出现“控制模块/主机手自动、人工确认”这类重复前缀。
const displayRuleTitle = (rule) => {
  const parentName = rule.equipmentType?.name || selectedEquipment.value?.name || ''
  const explicitSubtype = rule.equipmentSubtype ?? rule.equipment_subtype ?? rule.subtype?.name ?? ''
  const explicitStatus = rule.equipmentStatus ?? rule.equipment_status ?? rule.status ?? ''
  const searchable = compactCatalogText(`${rule.content || ''}${rule.code || ''}`)
  const subtypeItems = selectedEquipment.value?.subtypes || []
  const subtypeCandidates = subtypeItems
    .map((item) => item.name)
    .filter(Boolean)
    .sort((left, right) => right.length - left.length)
  const inferredSubtype = subtypeCandidates.find((name) => searchable.includes(compactCatalogText(name))) || ''
  const statusCandidates = []
  const appendStatuses = (parent, subtype) => {
    const values = statusesForSubtype(parent, subtype?.name || '', subtype)
    values.forEach((value) => { if (value) statusCandidates.push(value) })
  }
  if (explicitSubtype) {
    appendStatuses(parentName, subtypeItems.find((item) => item.name === explicitSubtype) || { name: explicitSubtype })
  } else if (inferredSubtype) {
    appendStatuses(parentName, subtypeItems.find((item) => item.name === inferredSubtype) || { name: inferredSubtype })
  } else {
    const parentStatuses = selectedEquipment.value?.statuses || getBuiltinStatuses(parentName)
    parentStatuses.forEach((value) => {
      if (value) statusCandidates.push(value)
    })
  }
  const inferredStatus = [...new Set(statusCandidates)]
    .sort((left, right) => right.length - left.length)
    .find((status) => searchable.includes(compactCatalogText(status))) || ''
  const status = trimParentPrefix(explicitStatus || inferredStatus, parentName)
  if (status && status !== parentName) return status
  const subtype = trimParentPrefix(explicitSubtype || inferredSubtype, parentName)
  if (subtype && subtype !== parentName) return subtype
  return trimParentPrefix(rule.content || parentName || '未命名规则', parentName) || '未命名规则'
}
const enabledDisciplineCount = computed(() => disciplines.value.filter((item) => item.isEnabled).length)
const automationDisciplineId = computed(() => disciplines.value.find((item) => item.name === '自动化' || item.code?.toUpperCase() === 'AUTOMATION')?.id)
const editorTitle = computed(() => editorMode.value === 'create' ? '新增测试内容规则' : draft.value?.content || '规则详情')
const stepMatchBasis = computed(() => {
  if (!draft.value) return ''
  const parts = []
  const typeName = draft.value.equipmentType?.name || selectedEquipment.value?.name
  if (typeName) parts.push(`设备类型：${typeName}`)
  if (draft.value.equipmentSubtype) parts.push(`子类型：${draft.value.equipmentSubtype}`)
  if (draft.value.equipmentStatus) parts.push(`状态/动作：${draft.value.equipmentStatus}`)
  if (draft.value.content) parts.push(`测试内容关键词：${draft.value.content}`)
  return parts.join('；') || '暂无匹配条件'
})
const isEditing = computed(() => editorMode.value === 'edit' || editorMode.value === 'create')
// 将当前草稿和进入页面时的快照比较，用于切换规则前提示“未保存”。
const isDirty = computed(() => {
  if (!draft.value || editorMode.value === 'empty') return false
  return JSON.stringify(buildTestContentPayload(draft.value)) !== baseline.value
})

const saveBaseline = () => {
  baseline.value = draft.value ? JSON.stringify(buildTestContentPayload(draft.value)) : ''
}

const resetExpandedResults = () => {
  Object.keys(expandedStepResults).forEach((key) => delete expandedStepResults[key])
}

const expandAllStepResults = (steps = []) => {
  steps.forEach((_, index) => { expandedStepResults[index] = true })
}

const toggleStepResults = (stepIndex) => {
  expandedStepResults[stepIndex] = !expandedStepResults[stepIndex]
}

const isStepResultsExpanded = (stepIndex) => Boolean(expandedStepResults[stepIndex])

const compactCatalogText = (value) => String(value || '').replace(/[\s\n\r（）()、，,:：/_-]/g, '').toLowerCase()

// 旧数据里部分“子类型”仍以独立顶层设备类型保存，例如“防火阀（电动）”。
// 这里把新目录选项映射到这些历史名称，保证迁移后仍能查到原规则。
const subtypeAliases = (subtype) => {
  const name = subtype?.name || ''
  if (name.includes('电动防火阀')) return ['防火阀', '电动']
  if (name.includes('手动防火阀')) return ['防火阀', '手动']
  if (name.includes('气灭')) return ['气灭']
  if (name.includes('区间')) return ['区间']
  if (name.includes('站内')) return ['站内']
  return [name]
}

const ruleBelongsToEquipmentOption = (rule, option) => {
  if (!option?.parent) return false
  const ruleType = rule.equipmentType || {}
  const ruleEquipmentTypeId = rule.equipmentTypeId ?? rule.equipment_type_id
  const ruleSubtype = rule.equipmentSubtype ?? rule.equipment_subtype ?? rule.subtype?.name ?? ''
  const ruleStatus = rule.equipmentStatus ?? rule.equipment_status ?? rule.status ?? inferRuleStatus(rule)
  const sameParent = ruleType.id === option.parent.id
    || ruleType.code === option.parent.code
    || ruleEquipmentTypeId === option.parent.id
    || String(ruleEquipmentTypeId) === String(option.parent.id)
  if (sameParent) {
    if (!option.subtype) return true
    if (ruleSubtype) return selectorMatches(ruleSubtype, option.subtype.name)
    // 兼容旧数据：后端尚未回传 selector 时，用规则标题/编码中的关键词
    // 判断它属于哪个子类型，避免电动、手动规则全部混在一起。
    const searchable = compactCatalogText(`${rule.content || ''}${rule.code || ''}`)
    return subtypeAliases(option.subtype).every((alias) => searchable.includes(compactCatalogText(alias)))
  }
  if (!option.subtype) {
  const searchable = compactCatalogText(`${ruleType.name || ''}${rule.content || ''}${rule.code || ''}`)
    return compactCatalogText(option.parent.name) === searchable
      || searchable.includes(compactCatalogText(option.parent.name))
  }
  const searchable = compactCatalogText(`${ruleType.name || ''}${rule.content || ''}${ruleSubtype}${ruleStatus}`)
  return subtypeAliases(option.subtype).every((alias) => searchable.includes(compactCatalogText(alias)))
}

// 列表只展示后端实际返回的规则记录。
const prepareRulesForDisplay = (matchedRules) => matchedRules.map((rule) => ({ ...rule, displayContent: rule.content }))

const showError = async (error) => ElMessage.error(await getApiErrorMessage(error))

const setUndoAction = (label, undo) => {
  undoAction.value = { label, undo }
}

const undoLastAction = async () => {
  const action = undoAction.value
  if (!action) return
  try {
    await action.undo()
    undoAction.value = null
    await refreshEquipmentDirectory()
    ElMessage.success('已撤销上一步操作')
  } catch (error) {
    await showError(error)
  }
}

const responseList = (response) => {
  const body = response?.data
  if (Array.isArray(body)) return body
  if (Array.isArray(body?.data)) return body.data
  return []
}

// 设备目录唯一来源是设备类型 -> 子类型层级。
const loadEquipmentTypes = async () => {
  const [hierarchyResponse, typesResponse] = await Promise.all([
    getEquipmentHierarchy({ includeDisabled: false }),
    getEquipmentTypes({ includeDisabled: false })
  ])
  const hierarchy = responseList(hierarchyResponse).map((item) => ({
    ...item,
    subtypes: item.subtypes || []
  }))
  const visibleIds = new Set(hierarchy.map((item) => item.id))
  const missingTypes = responseList(typesResponse).filter((item) => !visibleIds.has(item.id))
  const recovered = await Promise.all(missingTypes.map(async (item) => {
    try {
      const response = await getEquipmentSubtypes(item.id, { includeDisabled: false })
      const subtypes = responseList(response)
      return subtypes.length ? { ...item, subtypes, statuses: [] } : null
    } catch {
      return null
    }
  }))
  return [...hierarchy, ...recovered.filter(Boolean)].sort((left, right) => (
    (left.sortOrder || 0) - (right.sortOrder || 0) || left.id - right.id
  ))
}

const refreshEquipmentDirectory = async (preferredCode = selectedEquipmentOption.value?.queryCode) => {
  equipmentTypes.value = await loadEquipmentTypes()
  const nextOption = equipmentOptions.value.find((item) => item.queryCode === preferredCode) || equipmentOptions.value[0]
  selectedEquipmentCode.value = nextOption?.key || ''
  selectedSubtypeName.value = ''
  selectedStatus.value = ''
  loadedEquipmentCode.value = selectedEquipmentCode.value
  if (nextOption) await loadRules(nextOption.queryCode)
  else clearEditor()
}

const loadDisciplines = async () => {
  try {
    const response = await getDisciplines({ includeDisabled: true })
    disciplines.value = responseList(response)
  } catch {
    disciplines.value = []
  }
}

const loadStations = async () => {
  try {
    const response = await getStations({ includeDisabled: true })
    stations.value = responseList(response).sort((left, right) => (
      (left.sortOrder || 0) - (right.sortOrder || 0) || left.id - right.id
    ))
  } catch (error) {
    stations.value = []
    await showError(error)
  }
}

const openStationDialog = (station = null) => {
  stationMode.value = station ? 'edit' : 'create'
  Object.assign(stationForm, station
    ? {
        id: station.id,
        code: station.code,
        name: station.name,
        description: station.description || '',
        sortOrder: station.sortOrder,
        isEnabled: station.isEnabled
      }
    : {
        id: null,
        code: '',
        name: '',
        description: '',
        sortOrder: Math.max(0, ...stations.value.map((item) => item.sortOrder || 0)) + 1,
        isEnabled: true
      })
  stationDialogVisible.value = true
}

const saveStation = async () => {
  if (!stationForm.name.trim()) return ElMessage.warning('请输入站点名称')
  if (!Number.isInteger(stationForm.sortOrder) || stationForm.sortOrder < 1) {
    return ElMessage.warning('排序必须是大于 0 的整数')
  }
  stationSaving.value = true
  try {
    const payload = {
      name: stationForm.name.trim(),
      description: stationForm.description.trim(),
      sortOrder: stationForm.sortOrder,
      isEnabled: stationForm.isEnabled
    }
    if (stationMode.value === 'create') await createStation(payload)
    else await updateStation(stationForm.id, payload)
    stationDialogVisible.value = false
    await loadStations()
    ElMessage.success(stationMode.value === 'create' ? '站点已新增' : '站点已更新')
  } catch (error) {
    await showError(error)
  } finally {
    stationSaving.value = false
  }
}

const removeStation = async (station) => {
  try {
    await ElMessageBox.confirm(
      `确认删除站点“${station.name}”？删除后无法恢复。`,
      '删除站点？',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteStation(station.id)
    await loadStations()
    ElMessage.success('站点已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    await showError(error)
  }
}

// 查看规则时把后端对象复制成独立草稿，避免直接修改 rules 列表。
const openRule = (rule) => {
  const nextDraft = createRuleDraft(rule, selectedEquipment.value)
  draft.value = nextDraft
  selectedRuleId.value = rule.uiKey || rule.id
  editorMode.value = 'view'
  resetExpandedResults()
  expandAllStepResults(nextDraft.operationSteps)
  saveBaseline()
}

const clearEditor = () => {
  draft.value = null
  selectedRuleId.value = null
  editorMode.value = 'empty'
  baseline.value = ''
}

// 按父设备类型查询规则，并默认选中第一条规则。
const loadRules = async (equipmentCode, preferredRuleId = null) => {
  if (!equipmentCode) {
    rules.value = []
    clearEditor()
    return
  }
  rulesLoading.value = true
  try {
    // 查询完整规则后在前端按“父类型/子类型”筛选。
    // 这样可以兼容历史上把子类型另存为顶层设备类型的规则。
    // Configuration needs the complete rule tree so a disabled step/result
    // can be re-enabled after a refresh. Generation still queries the catalog
    // with includeDisabled=false and therefore keeps using enabled nodes only.
    const response = await getTestContents({ includeDisabled: true })
    const allRules = responseList(response).map((rule) => {
      const override = getRuleSelectorOverride(rule)
      return override ? { ...rule, ...override } : rule
    })
    const option = selectedEquipmentOption.value || equipmentOptions.value.find((item) => item.queryCode === equipmentCode)
    rules.value = prepareRulesForDisplay(allRules.filter((rule) => {
      if (rule.isEnabled === false) return false
      if (!ruleBelongsToEquipmentOption(rule, option)) return false
      const ruleSubtype = rule.equipmentSubtype ?? rule.equipment_subtype ?? rule.subtype?.name ?? ''
      const ruleStatus = rule.equipmentStatus ?? rule.equipment_status ?? rule.status ?? inferRuleStatus(rule)
      if (selectedSubtypeName.value && !selectorMatches(ruleSubtype, selectedSubtypeName.value)) return false
      if (selectedStatus.value && !selectorMatches(ruleStatus, selectedStatus.value)) return false
      return true
    }))
    const preferred = rules.value.find((item) => item.id === preferredRuleId || item.uiKey === preferredRuleId)
    if (preferred) openRule(preferred)
    else if (rules.value.length) openRule(rules.value[0])
    else clearEditor()
  } catch (error) {
    rules.value = []
    clearEditor()
    await showError(error)
  } finally {
    rulesLoading.value = false
  }
}

const confirmDiscard = async () => {
  if (!isDirty.value) return true
  try {
    await ElMessageBox.confirm('当前规则有未保存的修改，继续后这些修改会丢失。', '放弃未保存修改？', {
      confirmButtonText: '放弃修改',
      cancelButtonText: '继续编辑',
      type: 'warning'
    })
    return true
  } catch {
    return false
  }
}

const changeEquipment = async (code) => {
  if (!(await confirmDiscard())) {
    selectedEquipmentCode.value = loadedEquipmentCode.value
    return
  }
  selectedSubtypeName.value = ''
  selectedStatus.value = ''
  loadedEquipmentCode.value = code
  await loadRules(selectedEquipmentOption.value?.queryCode || code)
}

const changeSubtype = async () => {
  if (!(await confirmDiscard())) {
    selectedSubtypeName.value = draft.value?.equipmentSubtype || ''
    selectedStatus.value = draft.value?.equipmentStatus || ''
    return
  }
  selectedStatus.value = ''
  await loadRules(selectedEquipmentOption.value?.queryCode || selectedEquipmentCode.value)
}

const changeStatus = async () => {
  if (!(await confirmDiscard())) {
    selectedStatus.value = draft.value?.equipmentStatus || ''
    return
  }
  await loadRules(selectedEquipmentOption.value?.queryCode || selectedEquipmentCode.value)
}

const selectRule = async (rule) => {
  if ((rule.uiKey || rule.id) === selectedRuleId.value && ['view', 'edit'].includes(editorMode.value)) return
  if (!(await confirmDiscard())) return
  openRule(rule)
}

// 查看态和编辑态共用同一个草稿，只有点击此按钮才允许出现输入控件。
const enterEdit = () => {
  if (!draft.value) return
  editorMode.value = 'edit'
}

const refreshRules = async () => {
  if (!(await confirmDiscard())) return
  await loadRules(selectedEquipmentOption.value?.queryCode || selectedEquipmentCode.value, selectedRuleId.value)
}

const addRule = async () => {
  const selectedOption = selectedEquipmentOption.value
  if (!selectedOption?.parent) return ElMessage.warning('请先选择设备类型')
  if (!(await confirmDiscard())) return
  // 先固定当前选项，再写入草稿。子类型规则必须使用父类型 ID + 子类型名称保存，
  // 不能只依赖页面标题，否则请求体里的 equipmentSubtype 会变成空字符串。
  const nextDraft = createRuleDraft(null, selectedOption.parent)
  nextDraft.equipmentTypeId = selectedOption.parent.id
  nextDraft.code = ''
  nextDraft.content = selectedOption.parent.name
  nextDraft.equipmentSubtype = selectedSubtypeName.value
  nextDraft.equipmentStatus = selectedStatus.value
  nextDraft.sortOrder = Math.max(0, ...rules.value.map((item) => item.sortOrder || 0)) + 1
  if (automationDisciplineId.value) {
    nextDraft.operationSteps.forEach((step) => step.results.forEach((result) => {
      result.responsibleDisciplineIds = [automationDisciplineId.value]
    }))
  }
  draft.value = nextDraft
  selectedRuleId.value = null
  editorMode.value = 'create'
  resetExpandedResults()
  expandAllStepResults(nextDraft.operationSteps)
  saveBaseline()
}

const cancelEdit = async () => {
  if (!(await confirmDiscard())) return
  if (editorMode.value === 'edit' || editorMode.value === 'view') {
    const source = rules.value.find((item) => item.id === selectedRuleId.value)
    if (source) openRule(source)
    else clearEditor()
  } else if (rules.value.length) openRule(rules.value[0])
  else clearEditor()
}

// 规则保存是聚合保存：一次请求提交规则基本信息和完整步骤树。
const saveRule = async () => {
  if (!draft.value || savingRule.value) return
  const validationMessage = validateRuleDraft(draft.value)
  if (validationMessage) return ElMessage.warning(validationMessage)

  savingRule.value = true
  try {
    const isCreate = editorMode.value === 'create'
    const payload = buildTestContentPayload(draft.value, { incrementRevision: !isCreate })
    const response = isCreate
      ? await createTestContent(payload)
      : await updateTestContent(draft.value.id, payload)
    const saved = response.data?.data
    if (!saved) throw Object.assign(new Error('empty catalog response'), { publicMessage: '保存成功，但后端未返回最新规则数据' })

    const selector = { equipmentSubtype: payload.equipmentSubtype, equipmentStatus: payload.equipmentStatus }
    // 后端当前版本响应中可能仍返回空 selector；用本次提交值覆盖，
    // 保证保存后仍能按子类型筛选当前规则。
    saveRuleSelectorOverride({ id: saved.id || draft.value.id, code: saved.code || payload.code }, selector)
    // 保存后重新读取接口数据，避免把当前规则和新返回的原始规则拼在一起造成重复。
    await loadRules(selectedEquipmentOption.value?.queryCode || selectedEquipmentCode.value, saved.id)
    ElMessage.success('规则已保存')
  } catch (error) {
    await showError(error)
  } finally {
    savingRule.value = false
  }
}

const removeRule = async () => {
  if (!draft.value) return
  if (editorMode.value === 'create') {
    await cancelEdit()
    return
  }
  try {
    await ElMessageBox.confirm(`删除后将同时删除“${draft.value.content}”的全部步骤和结果，且无法恢复。`, '删除整条规则？', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error'
    })
    await deleteTestContent(draft.value.id)
    deleteRuleSelectorOverride(draft.value)
    ElMessage.success('规则已删除')
    await loadRules(selectedEquipmentOption.value?.queryCode || selectedEquipmentCode.value)
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    await showError(error)
  }
}

// 新增/删除步骤和结果只操作本地草稿，点击“保存完整规则”时才发请求。
const addStep = () => {
  const step = createOperationStep()
  step.sortOrder = draft.value.operationSteps.length + 1
  if (editorMode.value === 'create' && automationDisciplineId.value) {
    step.results.forEach((result) => {
      result.responsibleDisciplineIds = [automationDisciplineId.value]
    })
  }
  draft.value.operationSteps.push(step)
  // 新增步骤时与打开规则保持一致，输出结果直接展开可编辑。
  expandedStepResults[draft.value.operationSteps.length - 1] = true
}

const removeStep = (stepIndex) => {
  if (draft.value.operationSteps.length === 1) return ElMessage.warning('至少需要保留一个操作步骤')
  draft.value.operationSteps.splice(stepIndex, 1)
}

const addResult = (step) => {
  const result = createResultOutput()
  result.sortOrder = step.results.length + 1
  if (editorMode.value === 'create' && automationDisciplineId.value) {
    result.responsibleDisciplineIds = [automationDisciplineId.value]
  }
  step.results.push(result)
}

const removeResult = (step, resultIndex) => {
  if (step.results.length === 1) return ElMessage.warning('每个操作步骤至少需要保留一个输出结果')
  step.results.splice(resultIndex, 1)
}

const setResultDiscipline = (result, disciplineId) => {
  result.responsibleDisciplineIds = disciplineId == null ? [] : [disciplineId]
}

// 页面按钮移动数组元素；保存时 buildTestContentPayload 会按新顺序重排编号。
const moveItem = (items, index, offset) => {
  const target = index + offset
  if (target < 0 || target >= items.length) return
  const [item] = items.splice(index, 1)
  items.splice(target, 0, item)
}

// discipline 为空表示新增，否则表示把已有记录填入编辑弹窗。
const openDisciplineDialog = (discipline = null) => {
  disciplineMode.value = discipline ? 'edit' : 'create'
  Object.assign(disciplineForm, discipline
    ? {
        id: discipline.id,
        code: discipline.code,
        name: discipline.name,
        description: discipline.description || '',
        sortOrder: discipline.sortOrder,
        isEnabled: discipline.isEnabled
      }
    : {
        id: null,
        code: '',
        name: '',
        description: '',
        sortOrder: Math.max(0, ...disciplines.value.map((item) => item.sortOrder || 0)) + 1,
        isEnabled: true
      })
  disciplineDialogVisible.value = true
}

const saveDiscipline = async () => {
  if (!disciplineForm.name.trim()) return ElMessage.warning('请输入专业名称')
  if (!Number.isInteger(disciplineForm.sortOrder) || disciplineForm.sortOrder < 1) return ElMessage.warning('排序必须是大于 0 的整数')
  disciplineSaving.value = true
  const payload = {
    name: disciplineForm.name.trim(),
    description: disciplineForm.description.trim(),
    sortOrder: disciplineForm.sortOrder,
    isEnabled: disciplineForm.isEnabled
  }
  try {
    if (disciplineMode.value === 'create') await createDiscipline(payload)
    else await updateDiscipline(disciplineForm.id, payload)
    await loadDisciplines()
    disciplineDialogVisible.value = false
    ElMessage.success(disciplineMode.value === 'create' ? '责任专业已新增' : '责任专业已更新')
  } catch (error) {
    await showError(error)
  } finally {
    disciplineSaving.value = false
  }
}

const removeDiscipline = async (discipline) => {
  try {
    await ElMessageBox.confirm(`确认删除责任专业“${discipline.name}”？已被规则引用的专业无法直接删除。`, '删除责任专业？', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteDiscipline(discipline.id)
    await loadDisciplines()
    ElMessage.success('责任专业已删除')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    await showError(error)
  }
}

const openEquipmentDialog = (equipment = null) => {
  equipmentMode.value = equipment ? 'edit' : 'create'
  const subtypes = equipment
    ? (equipment.subtypes || []).map((subtype) => ({
        id: subtype.id,
        name: subtype.name,
        sortOrder: subtype.sortOrder,
        isEnabled: subtype.isEnabled,
        statuses: [...(subtype.statuses || [])]
      }))
    : []
  Object.assign(equipmentForm, equipment
    ? {
        id: equipment.id,
        code: equipment.code,
        name: equipment.name,
        description: equipment.description || '',
        sortOrder: equipment.sortOrder,
        isEnabled: equipment.isEnabled,
        subtypes
      }
    : {
        id: null,
        code: '',
        name: '',
        description: '',
        sortOrder: Math.max(0, ...equipmentTypes.value.map((item) => item.sortOrder || 0)) + 1,
        isEnabled: true,
        subtypes: []
      })
  equipmentDialogVisible.value = true
}

const saveEquipment = async () => {
  if (!equipmentForm.name.trim()) return ElMessage.warning('请输入设备类型名称')
  if (!Number.isInteger(equipmentForm.sortOrder) || equipmentForm.sortOrder < 1) return ElMessage.warning('排序必须是大于 0 的整数')
  const names = equipmentForm.subtypes.map((subtype) => subtype.name.trim().toLocaleLowerCase())
  if (new Set(names).size !== names.length) return ElMessage.warning('子类型名称不能重复')
  for (const subtype of equipmentForm.subtypes) {
    if (!subtype.name.trim()) return ElMessage.warning('子类型名称不能为空')
    const statuses = subtype.statuses.map((status) => status.trim())
    if (statuses.some((status) => !status)) return ElMessage.warning('状态/动作名称不能为空')
    if (new Set(statuses.map((status) => status.toLocaleLowerCase())).size !== statuses.length) {
      return ElMessage.warning('同一子类型下的状态/动作不能重复')
    }
  }
  const payload = {
    name: equipmentForm.name.trim(),
    description: equipmentForm.description.trim(),
    sortOrder: equipmentForm.sortOrder,
    isEnabled: equipmentForm.isEnabled,
    subtypes: equipmentForm.subtypes.map((subtype, index) => ({
      ...(subtype.id ? { id: subtype.id } : {}),
      name: subtype.name.trim(),
      sortOrder: index + 1,
      isEnabled: subtype.isEnabled,
      statuses: subtype.statuses.map((status) => status.trim())
    }))
  }
  equipmentSaving.value = true
  try {
    const wasCreate = equipmentMode.value === 'create'
    const oldValue = wasCreate
      ? null
      : {
          ...equipmentForm,
          subtypes: equipmentForm.subtypes.map((subtype) => ({
            ...subtype,
            statuses: [...subtype.statuses]
          }))
        }
    const response = wasCreate ? await createEquipmentType(payload) : await updateEquipmentType(equipmentForm.id, payload)
    const saved = response.data?.data || payload
    if (!wasCreate || !payload.subtypes.length) {
      setUndoAction(wasCreate ? `撤销新增“${saved.name}”` : `撤销修改“${saved.name}”`, async () => {
        if (wasCreate) await deleteEquipmentType(saved.id)
        else await updateEquipmentType(oldValue.id, {
          name: oldValue.name,
          description: oldValue.description || '',
          sortOrder: oldValue.sortOrder,
          isEnabled: oldValue.isEnabled,
          subtypes: oldValue.subtypes.map((subtype, index) => ({
            id: subtype.id,
            name: subtype.name,
            sortOrder: index + 1,
            isEnabled: subtype.isEnabled,
            statuses: [...subtype.statuses]
          }))
        })
      })
    } else {
      undoAction.value = null
    }
    equipmentDialogVisible.value = false
    await refreshEquipmentDirectory(saved.code || equipmentForm.code || selectedEquipmentCode.value)
    ElMessage.success(wasCreate ? '设备类型已新增' : '设备类型已更新')
  } catch (error) {
    await showError(error)
  } finally {
    equipmentSaving.value = false
  }
}

const removeEquipment = async (equipment) => {
  try {
    await ElMessageBox.confirm(`确认删除设备类型“${equipment.name}”？如果存在规则或子类型，后端会拒绝删除。`, '删除设备类型？', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteEquipmentType(equipment.id)
    setUndoAction(`撤销删除“${equipment.name}”`, async () => {
      await createEquipmentType({
        code: equipment.code,
        name: equipment.name,
        description: equipment.description || '',
        sortOrder: equipment.sortOrder,
        isEnabled: equipment.isEnabled
      })
    })
    await refreshEquipmentDirectory()
    ElMessage.success('设备类型已删除，可在顶部撤销')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    await showError(error)
  }
}

const toggleEquipmentRow = (row) => {
  if (!row.subtypes?.length) return
  equipmentTableRef.value?.toggleRowExpansion(row)
}

const openStatusDialog = (parent, subtype) => {
  statusParent.value = parent
  statusSubtype.value = subtype
  statusDraft.value = [...(subtype.statuses || [])]
  statusDialogVisible.value = true
}

const addStatus = () => statusDraft.value.push('')

const removeStatus = (index) => statusDraft.value.splice(index, 1)

const saveStatuses = async () => {
  const statuses = statusDraft.value.map((item) => String(item || '').trim())
  if (statuses.some((item) => !item)) return ElMessage.warning('状态/动作名称不能为空')
  if (new Set(statuses.map((item) => item.toLocaleLowerCase())).size !== statuses.length) {
    return ElMessage.warning('状态/动作名称不能重复')
  }
  statusSaving.value = true
  try {
    await updateEquipmentSubtypeStatuses(statusSubtype.value.id, { statuses })
    const parentCode = statusParent.value.code
    statusDialogVisible.value = false
    await refreshEquipmentDirectory(parentCode)
    ElMessage.success('状态/动作已更新')
  } catch (error) {
    await showError(error)
  } finally {
    statusSaving.value = false
  }
}

onMounted(async () => {
  pageLoading.value = true
  try {
    const [equipmentResult] = await Promise.allSettled([
      loadEquipmentTypes(),
      loadDisciplines(),
      loadStations()
    ])
    if (equipmentResult.status === 'rejected') throw equipmentResult.reason
    equipmentTypes.value = equipmentResult.value
    if (equipmentTypes.value.length) {
      const firstOption = equipmentOptions.value[0]
      selectedEquipmentCode.value = firstOption?.key || ''
      selectedSubtypeName.value = ''
      selectedStatus.value = ''
      loadedEquipmentCode.value = selectedEquipmentCode.value
      if (firstOption) await loadRules(firstOption.queryCode)
    }
  } catch (error) {
    await showError(error)
  } finally {
    pageLoading.value = false
  }
})
</script>

<template>
  <div v-loading="pageLoading" class="config-page">
    <div class="page-title config-title">
      <div>
        <h1>基础配置</h1>
        <p>维护设备测试规则及输出结果的责任专业。</p>
      </div>
      <div class="config-title-actions">
        <el-tag v-if="equipmentTypes.length" effect="plain" round>{{ equipmentTypes.length }} 类设备</el-tag>
        <el-button type="primary" plain :icon="EditPen" @click="activeTab = 'equipment-types'">
          管理设备类型
        </el-button>
      </div>
    </div>

    <el-card class="section-card config-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane name="equipment-types" label="设备类型">
          <div class="discipline-hero equipment-type-hero">
            <div class="discipline-hero-copy">
              <el-tag type="primary" effect="light" round>目录基础资料</el-tag>
              <h2>设备类型</h2>
              <p>维护设备类型名称、编码、排序和启用状态。点击表格右侧“编辑”即可修改；删除前请先处理该类型下的规则与子类型。</p>
            </div>
            <div class="discipline-stats">
              <div class="discipline-stat"><strong>{{ equipmentTypes.length }}</strong><span>设备类型</span></div>
              <div class="discipline-stat stat-success"><strong>{{ equipmentTypes.filter((item) => item.isEnabled).length }}</strong><span>启用中</span></div>
              <div class="discipline-stat stat-muted"><strong>{{ equipmentTypes.filter((item) => !item.isEnabled).length }}</strong><span>已停用</span></div>
            </div>
            <el-button class="discipline-add-button" type="primary" :icon="Plus" @click="openEquipmentDialog()">新增设备类型</el-button>
          </div>
          <el-alert v-if="undoAction" class="undo-alert" type="warning" show-icon :closable="false">
            <template #title><span>{{ undoAction.label }}</span><el-button text type="primary" @click="undoLastAction">立即撤销</el-button></template>
          </el-alert>
          <el-table ref="equipmentTableRef" :data="equipmentTypes" row-key="id" stripe class="discipline-table" @row-click="toggleEquipmentRow">
            <el-table-column type="expand" width="48">
              <template #default="{ row }">
                <div class="hierarchy-panel" @click.stop>
                  <div v-if="row.subtypes?.length" class="subtype-grid">
                    <article v-for="subtype in row.subtypes" :key="subtype.id" class="subtype-card">
                      <div class="subtype-heading"><div><strong>{{ subtype.name }}</strong><code>{{ subtype.code }}</code></div><div class="subtype-heading-actions"><el-tag v-if="!subtype.isEnabled" type="info" effect="plain">停用</el-tag><el-button text type="danger" :icon="Delete" title="删除子类型" @click="removeSavedEquipmentSubtype(row, subtype)">删除</el-button></div></div>
                      <div class="status-heading"><span>状态 / 动作</span><el-button text type="primary" :icon="EditPen" @click="openStatusDialog(row, subtype)">编辑</el-button></div>
                      <div v-if="subtype.statuses?.length" class="status-list"><el-tag v-for="status in subtype.statuses" :key="status" effect="plain">{{ status }}</el-tag></div>
                      <div v-else class="empty-status">暂无状态 / 动作</div>
                    </article>
                  </div>
                  <div v-else class="empty-status">该设备类型暂无子类型</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="sortOrder" label="排序" width="80" align="center" />
            <el-table-column label="设备类型编码" min-width="190"><template #default="{ row }"><code class="discipline-code">{{ row.code }}</code></template></el-table-column>
            <el-table-column label="设备类型名称" min-width="160"><template #default="{ row }"><strong class="discipline-name">{{ row.name }}</strong></template></el-table-column>
            <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
            <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag class="status-tag" :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right" align="center">
              <template #default="{ row }"><div class="table-actions" @click.stop><el-button text type="primary" :icon="EditPen" @click="openEquipmentDialog(row)">编辑</el-button><el-button text type="danger" :icon="Delete" @click="removeEquipment(row)">删除</el-button></div></template>
            </el-table-column>
            <template #empty><el-empty :image-size="72" description="暂无设备类型" /></template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="rules" label="测试规则">
          <div class="rules-toolbar">
            <div class="equipment-picker">
              <span>设备类型</span>
              <el-select v-model="selectedEquipmentCode" filterable placeholder="请选择设备类型" @change="changeEquipment">
                <el-option v-for="item in equipmentOptions" :key="item.key" :label="item.label" :value="item.key">
                  <span>{{ item.label }}</span>
                  <span class="option-code">{{ item.subtype ? `${item.parent.name} / ${item.subtype.name}` : item.parent.code }}</span>
                </el-option>
              </el-select>
              <el-select v-if="selectedSubtypes.length" v-model="selectedSubtypeName" clearable filterable placeholder="请选择子类型" @change="changeSubtype">
                <el-option v-for="subtype in selectedSubtypes" :key="subtype.id" :label="subtype.name" :value="subtype.name" />
              </el-select>
              <el-select v-if="availableStatuses.length" v-model="selectedStatus" clearable filterable placeholder="请选择状态/动作" @change="changeStatus">
                <el-option v-for="status in availableStatuses" :key="status" :label="status" :value="status" />
              </el-select>
            </div>
            <div class="toolbar-actions">
              <el-button plain :icon="EditPen" @click="activeTab = 'equipment-types'">管理设备类型</el-button>
              <el-button :icon="Refresh" :loading="rulesLoading" @click="refreshRules">刷新</el-button>
              <el-button type="primary" :icon="Plus" :disabled="!selectedEquipmentCode" @click="addRule">新增规则</el-button>
            </div>
          </div>

          <div class="rule-workbench">
            <aside class="rule-sidebar">
              <div class="sidebar-heading"><div><strong>{{ selectedStatus || selectedSubtypeName || selectedEquipment?.name || '测试规则' }}</strong><span>{{ rules.length }} 条</span></div></div>
              <div v-loading="rulesLoading" class="rule-menu">
                <button v-for="rule in rules" :key="rule.uiKey || rule.id" type="button" class="rule-menu-item" :class="{ active: ['view', 'edit'].includes(editorMode) && selectedRuleId === (rule.uiKey || rule.id) }" @click="selectRule(rule)" @contextmenu="showContextMenu($event, rule)">
                  <span class="rule-menu-title">{{ displayRuleTitle(rule) }}</span>
                  <span class="rule-menu-meta"><code>{{ rule.code }}</code><span>{{ rule.operationSteps?.length || 0 }} 个步骤</span></span>
                </button>
                <el-empty v-if="!rulesLoading && !rules.length" :image-size="72" description="该设备类型暂无规则" />
              </div>
            </aside>

            <ul v-if="contextMenuVisible" class="rule-context-menu" :style="{ top: contextMenuY + 'px', left: contextMenuX + 'px' }" @click.stop>
              <li class="rule-context-item" @click="contextEditRule(contextMenuRule)"><el-icon><EditPen /></el-icon><span>编辑规则</span></li>
              <li class="rule-context-item rule-context-item-danger" @click="contextDeleteRule(contextMenuRule)"><el-icon><Delete /></el-icon><span>删除规则</span></li>
            </ul>
            <div v-if="contextMenuVisible" class="rule-context-mask" @click="closeContextMenu" @contextmenu.prevent="closeContextMenu"></div>
            <main class="rule-editor">
              <el-empty v-if="!draft" :image-size="96" description="选择一条规则，或新建规则开始配置">
                <el-button type="primary" :icon="Plus" :disabled="!selectedEquipmentCode" @click="addRule">新增规则</el-button>
              </el-empty>

              <template v-else>
                <div class="editor-heading">
                  <div>
                    <div class="editor-title-line"><h2>{{ editorTitle }}</h2><el-tag v-if="isDirty" type="warning" effect="plain">未保存</el-tag><el-tag v-else-if="editorMode === 'view'" type="success" effect="plain">只读查看</el-tag></div>
                    <p v-if="editorMode === 'view'">规则编码：<code>{{ draft.code }}</code> · 当前版本 v{{ draft.revision }}</p>
                    <p v-else-if="editorMode === 'edit'">规则编码：<code>{{ draft.code }}</code> · 保存后自动更新为 v{{ draft.revision + 1 }}</p>
                    <p v-else>规则编码将在保存后由系统自动生成。</p>
                  </div>
                  <div class="heading-actions">
                    <el-button v-if="editorMode === 'view'" type="primary" :icon="EditPen" @click="enterEdit">编辑规则</el-button>
                    <el-button v-if="editorMode !== 'view'" type="danger" plain :icon="Delete" @click="removeRule">{{ editorMode === 'create' ? '放弃新增' : '删除规则' }}</el-button>
                  </div>
                </div>

                <div v-if="!isEditing" class="readonly-summary">
                  <div class="summary-grid">
                    <div class="summary-item"><span>设备类型</span><strong>{{ selectedEquipment?.name || '—' }}</strong></div>
                    <div class="summary-item"><span>设备子类型</span><strong>{{ draft.equipmentSubtype || '—' }}</strong></div>
                    <div class="summary-item"><span>状态/动作</span><strong>{{ draft.equipmentStatus || '—' }}</strong></div>
                    <div class="summary-item summary-wide"><span>规则说明</span><strong>{{ draft.description || '暂无说明' }}</strong></div>
                  </div>
                  <div class="tree-heading"><div><h3>操作步骤与输出结果</h3><p>以下为当前规则的完整配置。</p></div></div>
                  <div class="steps-list">
                    <section v-for="(step, stepIndex) in draft.operationSteps" :key="stepIndex" class="step-card readonly-step-card">
                      <div class="step-heading step-heading-clickable" @click="toggleStepResults(stepIndex)"><span class="step-number">步骤 {{ stepIndex + 1 }} <span class="step-match-basis">（{{ stepMatchBasis }}）</span></span><div class="step-heading-summary"><el-tag size="small" effect="plain">是否变比：{{ step.ratioChange }}</el-tag><span class="result-count">{{ step.results.length }} 个输出结果</span><el-icon class="expand-icon" :class="{ expanded: isStepResultsExpanded(stepIndex) }"><ArrowDown /></el-icon></div></div>
                      <div class="readonly-step-description">{{ step.description }}</div>
                      <div v-if="isStepResultsExpanded(stepIndex)" class="results-list">
                        <article v-for="(result, resultIndex) in step.results" :key="resultIndex" class="result-row readonly-result-row">
                          <div class="result-index">{{ resultIndex + 1 }}</div>
                          <div class="readonly-result-description">{{ result.description }}</div>
                          <div class="discipline-tags"><el-tag v-if="result.responsibleDisciplineIds[0]" size="small" effect="plain">{{ disciplines.find((item) => item.id === result.responsibleDisciplineIds[0])?.name || `专业 #${result.responsibleDisciplineIds[0]}` }}</el-tag></div>
                        </article>
                      </div>
                    </section>
                  </div>
                </div>

                <template v-else>
                <el-form label-position="top" class="rule-form">
                  <div class="rule-base-grid">
                    <el-form-item label="规则编码"><div class="readonly-field"><code>{{ draft.code || '保存后由系统自动生成' }}</code><span>编码不可手动填写</span></div></el-form-item>
                    <el-form-item label="设备类型"><div class="readonly-field"><strong>{{ selectedEquipment?.name || '—' }}</strong><span>由上方目录选择决定</span></div></el-form-item>
                    <el-form-item label="设备子类型">
                       <el-select v-model="draft.equipmentSubtype" clearable filterable placeholder="请选择子类型" @change="draft.equipmentStatus = ''">
                         <el-option v-for="subtype in selectedSubtypes" :key="subtype.id" :label="subtype.name" :value="subtype.name" />
                       </el-select>
                     </el-form-item>
                     <el-form-item v-if="draftAvailableStatuses.length" label="状态/动作">
                       <el-select v-model="draft.equipmentStatus" clearable filterable placeholder="请选择状态/动作">
                         <el-option v-for="status in draftAvailableStatuses" :key="status" :label="status" :value="status" />
                       </el-select>
                     </el-form-item>
                    <el-form-item class="description-field" label="说明"><el-input v-model="draft.description" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="可选的规则说明" /></el-form-item>
                  </div>
                </el-form>

                <div class="tree-heading">
                  <div><h3>操作步骤与输出结果</h3><p>保存时会提交完整规则树，顺序由当前排列自动编号。</p></div>
                  <el-button type="primary" plain :icon="Plus" @click="addStep">新增步骤</el-button>
                </div>

                <div class="steps-list">
                  <section v-for="(step, stepIndex) in draft.operationSteps" :key="stepIndex" class="step-card">
                    <div class="step-heading step-heading-clickable" @click="toggleStepResults(stepIndex)">
                      <span class="step-number">步骤 {{ stepIndex + 1 }} <span class="step-match-basis">（{{ stepMatchBasis }}）</span> <span class="result-count">{{ step.results.length }} 个输出结果</span><el-icon class="expand-icon" :class="{ expanded: isStepResultsExpanded(stepIndex) }"><ArrowDown /></el-icon></span>
                      <div class="item-actions" @click.stop>
                        <el-button text :icon="ArrowUp" :disabled="stepIndex === 0" title="上移步骤" @click="moveItem(draft.operationSteps, stepIndex, -1)" />
                        <el-button text :icon="ArrowDown" :disabled="stepIndex === draft.operationSteps.length - 1" title="下移步骤" @click="moveItem(draft.operationSteps, stepIndex, 1)" />
                        <el-button text type="danger" :icon="Delete" title="删除步骤" @click="removeStep(stepIndex)" />
                      </div>
                    </div>

                    <div class="step-fields">
                      <el-input v-model="step.description" maxlength="500" show-word-limit placeholder="输入现场操作或测试动作" />
                      <div class="step-options"><span>是否变比</span><el-radio-group v-model="step.ratioChange" size="small"><el-radio-button value="否">否</el-radio-button><el-radio-button value="是">是</el-radio-button></el-radio-group><el-switch v-model="step.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></div>
                    </div>

                    <div v-if="isStepResultsExpanded(stepIndex)" class="results-list">
                      <article v-for="(result, resultIndex) in step.results" :key="resultIndex" class="result-row">
                        <div class="result-index">{{ resultIndex + 1 }}</div>
                        <div class="result-fields">
                          <el-input v-model="result.description" maxlength="500" show-word-limit placeholder="输入预期输出结果" />
                          <el-select :model-value="result.responsibleDisciplineIds[0] ?? null" filterable clearable placeholder="选择责任专业（仅一项）" @update:model-value="setResultDiscipline(result, $event)">
                            <el-option v-for="discipline in disciplines" :key="discipline.id" :label="`${discipline.name}${discipline.isEnabled ? '' : '（已停用）'}`" :value="discipline.id" :disabled="!discipline.isEnabled && result.responsibleDisciplineIds[0] !== discipline.id" />
                          </el-select>
                        </div>
                        <div class="result-actions">
                          <el-switch v-model="result.isEnabled" size="small" inline-prompt active-text="启" inactive-text="停" />
                          <el-button text :icon="ArrowUp" :disabled="resultIndex === 0" title="上移结果" @click="moveItem(step.results, resultIndex, -1)" />
                          <el-button text :icon="ArrowDown" :disabled="resultIndex === step.results.length - 1" title="下移结果" @click="moveItem(step.results, resultIndex, 1)" />
                          <el-button text type="danger" :icon="Delete" title="删除结果" @click="removeResult(step, resultIndex)" />
                        </div>
                      </article>
                    </div>
                    <el-button class="add-result-button" text type="primary" :icon="Plus" @click="addResult(step)">新增输出结果</el-button>
                  </section>
                </div>

                <div class="editor-footer">
                  <span>{{ draft.operationSteps.length }} 个步骤，{{ draft.operationSteps.reduce((count, step) => count + step.results.length, 0) }} 个输出结果</span>
                  <div><el-button @click="cancelEdit">取消修改</el-button><el-button class="rule-save-button" type="primary" size="large" :loading="savingRule" @click="saveRule">保存完整规则</el-button></div>
                </div>
                </template>
              </template>
            </main>
          </div>
        </el-tab-pane>

        <el-tab-pane name="disciplines">
          <template #label>责任专业</template>
          <div class="discipline-hero">
            <div class="discipline-hero-copy">
              <el-tag type="primary" effect="light" round>规则责任配置</el-tag>
              <h2>责任专业</h2>
              <p>配置输出结果的责任归属。规则保存时使用专业 ID，已有规则引用的专业建议停用，不要直接删除。</p>
            </div>
            <div class="discipline-stats">
              <div class="discipline-stat"><strong>{{ disciplines.length }}</strong><span>全部专业</span></div>
              <div class="discipline-stat stat-success"><strong>{{ enabledDisciplineCount }}</strong><span>启用中</span></div>
              <div class="discipline-stat stat-muted"><strong>{{ disciplines.length - enabledDisciplineCount }}</strong><span>已停用</span></div>
            </div>
            <el-button class="discipline-add-button" type="primary" :icon="Plus" @click="openDisciplineDialog()">新增责任专业</el-button>
          </div>
          <el-table :data="disciplines" stripe class="discipline-table">
            <el-table-column prop="sortOrder" label="排序" width="80" align="center" />
            <el-table-column label="专业编码" min-width="170">
              <template #default="{ row }"><code class="discipline-code">{{ row.code }}</code></template>
            </el-table-column>
            <el-table-column label="专业名称" min-width="140">
              <template #default="{ row }"><strong class="discipline-name">{{ row.name }}</strong></template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
            <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag class="status-tag" :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right" align="center"><template #default="{ row }"><div class="table-actions" @click.stop><el-button text type="primary" :icon="EditPen" @click="openDisciplineDialog(row)">编辑</el-button><el-button text type="danger" :icon="Delete" @click="removeDiscipline(row)">删除</el-button></div></template></el-table-column>
            <template #empty><el-empty :image-size="72" description="暂无责任专业" /></template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="stations" label="站点信息">
          <div class="discipline-hero station-hero">
            <div class="discipline-hero-copy">
              <el-tag type="primary" effect="light" round>地点基础资料</el-tag>
              <h2>站点信息</h2>
              <p>维护正式文件生成时可选择的站点名称、排序和启用状态。</p>
            </div>
            <div class="discipline-stats">
              <div class="discipline-stat"><strong>{{ stations.length }}</strong><span>全部站点</span></div>
              <div class="discipline-stat stat-success"><strong>{{ stations.filter((item) => item.isEnabled).length }}</strong><span>启用中</span></div>
              <div class="discipline-stat stat-muted"><strong>{{ stations.filter((item) => !item.isEnabled).length }}</strong><span>已停用</span></div>
            </div>
            <el-button class="discipline-add-button" type="primary" :icon="Plus" @click="openStationDialog()">新增站点</el-button>
          </div>
          <div class="station-toolbar">
            <el-input v-model="stationKeyword" clearable placeholder="搜索站点名称、编码或说明" />
            <el-button plain :icon="Refresh" :loading="pageLoading" @click="loadStations">刷新</el-button>
          </div>
          <el-table :data="filteredStations" stripe class="discipline-table">
            <el-table-column prop="sortOrder" label="排序" width="80" align="center" />
            <el-table-column label="站点编码" min-width="180"><template #default="{ row }"><code class="discipline-code">{{ row.code }}</code></template></el-table-column>
            <el-table-column label="站点名称" min-width="180"><template #default="{ row }"><strong class="discipline-name">{{ row.name }}</strong></template></el-table-column>
            <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
            <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag class="status-tag" :type="row.isEnabled ? 'success' : 'info'" effect="light" round>{{ row.isEnabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right" align="center"><template #default="{ row }"><div class="table-actions"><el-button text type="primary" :icon="EditPen" @click="openStationDialog(row)">编辑</el-button><el-button text type="danger" :icon="Delete" @click="removeStation(row)">删除</el-button></div></template></el-table-column>
            <template #empty><el-empty :image-size="72" description="暂无站点信息" /></template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="equipmentDialogVisible" :title="equipmentMode === 'create' ? '新增设备类型' : '编辑设备类型'" width="min(780px, calc(100vw - 32px))" destroy-on-close>
      <el-form label-position="top">
        <div class="discipline-form-grid">
          <el-form-item label="设备类型编码"><div class="readonly-field"><code>{{ equipmentForm.code || '保存后由系统自动生成' }}</code><span>编码不可手动填写</span></div></el-form-item>
          <el-form-item label="设备类型名称" required><el-input v-model="equipmentForm.name" maxlength="100" placeholder="例如 烟感" /></el-form-item>
          <el-form-item label="排序" required><el-input-number v-model="equipmentForm.sortOrder" :min="1" :step="1" controls-position="right" /></el-form-item>
          <el-form-item label="启用状态"><el-switch v-model="equipmentForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="discipline-description" label="说明"><el-input v-model="equipmentForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        </div>
        <div class="hierarchy-form-section">
          <div class="hierarchy-form-heading"><div><strong>子类型与状态/动作</strong><span>{{ equipmentMode === 'create' ? '保存后自动生成所有编码。' : '可编辑名称、启用状态和状态/动作；删除已被规则使用的项目会被拦截。' }}</span></div><el-button type="primary" plain :icon="Plus" @click="addEquipmentSubtype">新增子类型</el-button></div>
          <div v-if="equipmentForm.subtypes.length" class="new-subtype-list">
            <article v-for="(subtype, subtypeIndex) in equipmentForm.subtypes" :key="subtypeIndex" class="new-subtype-card">
              <div class="new-subtype-heading"><span>子类型 {{ subtypeIndex + 1 }}<code v-if="subtype.code">{{ subtype.code }}</code></span><el-button text type="danger" :icon="Delete" @click="removeEquipmentSubtype(subtypeIndex)">删除</el-button></div>
              <div class="new-subtype-fields"><el-input v-model="subtype.name" maxlength="100" placeholder="请输入子类型名称" /><el-switch v-model="subtype.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></div>
              <div class="new-status-heading"><span>状态/动作（可选）</span><el-button text type="primary" :icon="Plus" @click="addEquipmentSubtypeStatus(subtype)">新增</el-button></div>
              <div v-if="subtype.statuses.length" class="new-status-list"><div v-for="(status, statusIndex) in subtype.statuses" :key="statusIndex" class="new-status-row"><span>{{ statusIndex + 1 }}</span><el-input v-model="subtype.statuses[statusIndex]" maxlength="100" placeholder="请输入状态/动作" /><el-button text type="danger" :icon="Delete" @click="removeEquipmentSubtypeStatus(subtype, statusIndex)" /></div></div>
              <span v-else class="new-status-empty">暂无状态/动作，可按需添加</span>
            </article>
          </div>
          <el-empty v-else :image-size="64" description="暂未添加子类型" />
        </div>
      </el-form>
      <template #footer><el-button @click="equipmentDialogVisible = false">取消</el-button><el-button type="primary" :loading="equipmentSaving" @click="saveEquipment">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="statusDialogVisible" :title="`${statusParent?.name || ''} / ${statusSubtype?.name || ''} · 状态/动作`" width="min(620px, calc(100vw - 32px))" destroy-on-close>
      <div class="status-editor-tip">调整后会立即用于新增规则。已被现有规则使用的状态/动作不允许直接删除，避免影响正式生成。</div>
      <div class="status-editor-list">
        <div v-for="(status, index) in statusDraft" :key="index" class="status-editor-row">
          <span>{{ index + 1 }}</span><el-input v-model="statusDraft[index]" maxlength="100" placeholder="请输入状态/动作" /><el-button text type="danger" :icon="Delete" @click="removeStatus(index)">删除</el-button>
        </div>
        <el-button class="status-add-button" type="primary" plain :icon="Plus" @click="addStatus">新增状态/动作</el-button>
        <el-empty v-if="!statusDraft.length" :image-size="64" description="暂无状态/动作" />
      </div>
      <template #footer><el-button @click="statusDialogVisible = false">取消</el-button><el-button type="primary" :loading="statusSaving" @click="saveStatuses">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="disciplineDialogVisible" :title="disciplineMode === 'create' ? '新增责任专业' : '编辑责任专业'" width="min(520px, calc(100vw - 32px))" destroy-on-close>
      <el-form label-position="top">
        <div class="discipline-form-grid">
          <el-form-item label="专业编码"><div class="readonly-field"><code>{{ disciplineForm.code || '保存后由系统自动生成' }}</code><span>编码不可手动填写</span></div></el-form-item>
          <el-form-item label="专业名称" required><el-input v-model="disciplineForm.name" maxlength="100" placeholder="例如 自动化" /></el-form-item>
          <el-form-item label="排序" required><el-input-number v-model="disciplineForm.sortOrder" :min="1" :step="1" controls-position="right" /></el-form-item>
          <el-form-item label="启用状态"><el-switch v-model="disciplineForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="discipline-description" label="说明"><el-input v-model="disciplineForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="disciplineDialogVisible = false">取消</el-button><el-button type="primary" :loading="disciplineSaving" @click="saveDiscipline">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="stationDialogVisible" :title="stationMode === 'create' ? '新增站点' : '编辑站点'" width="min(520px, calc(100vw - 32px))" destroy-on-close>
      <el-form label-position="top">
        <div class="discipline-form-grid">
          <el-form-item label="站点编码"><div class="readonly-field"><code>{{ stationForm.code || '保存后由系统自动生成' }}</code><span>编码不可手动填写</span></div></el-form-item>
          <el-form-item label="站点名称" required><el-input v-model="stationForm.name" maxlength="100" placeholder="例如 嘉庚体育馆站" /></el-form-item>
          <el-form-item label="排序" required><el-input-number v-model="stationForm.sortOrder" :min="1" :step="1" controls-position="right" /></el-form-item>
          <el-form-item label="启用状态"><el-switch v-model="stationForm.isEnabled" inline-prompt active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="discipline-description" label="说明"><el-input v-model="stationForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="可选的站点说明" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="stationDialogVisible = false">取消</el-button><el-button type="primary" :loading="stationSaving" @click="saveStation">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.config-title { align-items: flex-end; }
.config-title-actions { display: flex; align-items: center; gap: 12px; }
.config-card :deep(.el-card__body) { padding-top: 10px; }
.rules-toolbar, .discipline-toolbar, .editor-heading, .tree-heading, .editor-footer { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.rules-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; padding: 10px 2px 20px; }
.equipment-picker { display: grid; grid-template-columns: auto repeat(3, minmax(120px, 1fr)); flex: 1 1 auto; min-width: 0; align-items: center; gap: 12px; color: #44546a; font-weight: 650; }
.equipment-picker > span { flex: 0 0 auto; }
.equipment-picker .el-select { width: 100%; min-width: 0; max-width: none; }
.option-code { float: right; margin-left: 28px; color: #94a3b8; font-size: 12px; }
.toolbar-actions { display: flex; flex: 0 0 auto; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 10px; margin-left: auto; }
@media (max-width: 720px) {
  .config-title { align-items: flex-start; gap: 14px; }
  .config-title-actions { width: 100%; justify-content: space-between; }
  .config-title-actions .el-button { flex: 1; }
}
.rule-workbench { display: grid; grid-template-columns: 250px minmax(0, 1fr); min-height: 560px; border: 1px solid #e4eaf2; border-radius: 12px; overflow: hidden; background: #fff; }
.rule-sidebar { background: #f8faff; border-right: 1px solid #e4eaf2; }
.sidebar-heading { min-height: 64px; padding: 15px 16px; border-bottom: 1px solid #e8edf5; }
.sidebar-heading div { display: flex; align-items: center; justify-content: space-between; }
.sidebar-heading span { color: #8491a5; font-size: 13px; }
.rule-context-menu { position: fixed; z-index: 9999; min-width: 140px; margin: 0; padding: 5px 0; list-style: none; border: 1px solid #dbe7fa; border-radius: 8px; background: #fff; box-shadow: 0 8px 24px rgba(35, 59, 95, .18); user-select: none; }
.rule-context-item { display: flex; align-items: center; gap: 8px; padding: 8px 14px; color: #2e4364; font-size: 13px; cursor: pointer; transition: .15s; }
.rule-context-item:hover { background: #eef4ff; color: #1f3454; }
.rule-context-item .el-icon { font-size: 14px; color: #4f6f9f; }
.rule-context-item-danger { color: #c45656; }
.rule-context-item-danger .el-icon { color: #c45656; }
.rule-context-item-danger:hover { background: #fdf2f2; color: #b24040; }
.rule-context-item-danger:hover .el-icon { color: #b24040; }
.rule-context-mask { position: fixed; inset: 0; z-index: 9998; }
.rule-menu { min-height: 450px; padding: 10px; }
.rule-menu-item { width: 100%; margin: 0 0 8px; padding: 12px; text-align: left; border: 1px solid transparent; border-radius: 9px; background: transparent; color: inherit; cursor: pointer; transition: .18s ease; }
.rule-menu-item:hover { background: #eef4ff; }
.rule-menu-item.active { border-color: #a9c5ff; background: #eaf2ff; box-shadow: 0 3px 12px rgba(40, 100, 232, .08); }
.rule-menu-title, .rule-menu-meta { display: block; }
.rule-menu-title { margin-bottom: 7px; color: #22334e; font-weight: 700; line-height: 1.4; }
.rule-menu-meta { color: #7b8798; font-size: 12px; }
.rule-menu-meta code { display: block; overflow: hidden; margin-bottom: 4px; color: #53709f; text-overflow: ellipsis; }
.rule-editor { min-width: 0; padding: 24px; }
.editor-heading { align-items: flex-start; padding-bottom: 20px; border-bottom: 1px solid #edf0f5; }
.editor-title-line { display: flex; align-items: center; gap: 10px; }
.heading-actions { display: flex; align-items: center; gap: 10px; }
.readonly-summary { padding-top: 22px; }
.summary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.summary-item { min-height: 72px; padding: 14px 16px; border: 1px solid #e4eaf2; border-radius: 10px; background: linear-gradient(135deg, #f8fbff, #fff); }
.summary-item span { display: block; margin-bottom: 7px; color: #8390a4; font-size: 12px; }
.summary-item strong { color: #253858; font-size: 15px; line-height: 1.5; }
.summary-wide { grid-column: 1 / -1; }
.readonly-step-card { background: #fff; }
.readonly-step-description { padding: 18px 16px 12px; color: #2c3e5d; font-size: 15px; line-height: 1.7; }
.readonly-result-row { grid-template-columns: 28px minmax(0, 1fr) auto; }
.readonly-result-description { color: #3a4b66; line-height: 1.6; }
.discipline-tags { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 5px; }
.readonly-summary .tree-heading { margin-top: 22px; }
.readonly-summary .results-list { padding-bottom: 14px; }
.readonly-field { display: flex; align-items: center; justify-content: space-between; min-height: 32px; padding: 8px 12px; border: 1px solid #dfe6f0; border-radius: 7px; background: #f8fafc; }
.readonly-field code { color: #43659a; }
.readonly-field span { color: #9aa6b7; font-size: 12px; }
.editor-heading h2, .discipline-toolbar h2, .tree-heading h3 { margin: 0; color: #243653; }
.editor-heading h2, .discipline-toolbar h2 { font-size: 20px; }
.editor-heading p, .tree-heading p, .discipline-toolbar p { margin: 6px 0 0; color: #8290a4; font-size: 13px; }
.rule-form { padding-top: 20px; }
.rule-base-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.rule-base-grid :deep(.el-input-number) { width: 100%; }
.description-field { grid-column: 1 / -1; }
.tree-heading { align-items: flex-end; margin: 4px 0 14px; }
.tree-heading h3 { font-size: 17px; }
.steps-list { display: flex; flex-direction: column; gap: 10px; }
.step-card { overflow: hidden; border: 1px solid #dfe7f3; border-radius: 12px; background: #fbfcff; box-shadow: 0 3px 12px rgba(35, 59, 95, .04); }
.step-heading { display: flex; align-items: center; justify-content: space-between; min-height: 44px; padding: 6px 10px 6px 14px; background: #f5f8fd; border-bottom: 1px solid #e7edf5; }
.step-heading-clickable { cursor: pointer; transition: background .18s ease; }
.step-heading-clickable:hover { background: #e8f0fc; }
.step-number { color: #31558d; font-weight: 750; }
.step-match-basis { color: #73829a; font-size: 12px; font-weight: 500; }
.step-heading-summary { display: flex; align-items: center; gap: 10px; }
.result-count { color: #8290a4; font-size: 12px; font-weight: 500; }
.expand-icon { color: #6b83aa; transition: transform .2s ease; }
.expand-icon.expanded { transform: rotate(180deg); }
.item-actions, .result-actions { display: flex; align-items: center; }
.item-actions .el-button + .el-button, .result-actions .el-button + .el-button { margin-left: 2px; }
.step-fields { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: center; padding: 10px 14px; }
.step-options { display: flex; align-items: center; justify-content: flex-end; gap: 10px; color: #64748b; font-size: 13px; }
.results-list { display: flex; flex-direction: column; gap: 8px; padding: 0 14px 2px; }
.result-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 8px 10px; border: 1px solid #e6ebf3; border-radius: 9px; background: #fff; }
.result-index { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 50%; background: #eaf2ff; color: #3766af; font-size: 12px; font-weight: 750; }
.result-fields { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(180px, .75fr); gap: 10px; }
.add-result-button { margin: 6px 14px 10px; }
.editor-footer { position: fixed; right: max(20px, calc((100vw - 1120px) / 2)); bottom: 20px; z-index: 30; display: flex; align-items: center; gap: 16px; margin: 0; padding: 12px 14px 12px 18px; border: 1px solid #dbe7fa; border-radius: 14px; background: rgba(255, 255, 255, .96); box-shadow: 0 12px 30px rgba(35, 59, 95, .18); backdrop-filter: blur(10px); }
.editor-footer > span { color: #758399; font-size: 13px; }
.editor-footer > div { display: flex; align-items: center; gap: 8px; }
.editor-footer .rule-save-button { min-width: 150px; height: 44px; border: 0; border-radius: 12px; background: linear-gradient(135deg, #2864e8, #4f86ff); box-shadow: 0 10px 24px rgba(40, 100, 232, .24); font-weight: 700; }
.editor-footer .rule-save-button:hover, .editor-footer .rule-save-button:focus { background: linear-gradient(135deg, #1f57d6, #3f78f7); box-shadow: 0 12px 28px rgba(40, 100, 232, .3); transform: translateY(-1px); }
.discipline-hero { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 24px; margin: 8px 0 20px; padding: 24px 26px; overflow: hidden; border: 1px solid #dce8fb; border-radius: 16px; background: linear-gradient(135deg, #f4f8ff 0%, #fbfdff 52%, #f1f7ff 100%); box-shadow: 0 8px 24px rgba(44, 91, 160, .07); }
.discipline-hero::after { content: ''; position: absolute; width: 220px; height: 220px; right: 28%; top: -150px; border-radius: 50%; background: rgba(92, 145, 250, .12); pointer-events: none; }
.discipline-hero-copy { position: relative; z-index: 1; max-width: 560px; }
.discipline-hero-copy h2 { margin: 12px 0 6px; color: #1f3454; font-size: 23px; letter-spacing: .2px; }
.discipline-hero-copy p { margin: 0; color: #71829a; font-size: 13px; line-height: 1.7; }
.discipline-stats { position: relative; z-index: 1; display: flex; align-items: stretch; gap: 10px; margin-left: auto; }
.discipline-stat { min-width: 82px; padding: 10px 13px; text-align: center; border: 1px solid #dfe8f5; border-radius: 10px; background: rgba(255, 255, 255, .8); }
.discipline-stat strong, .discipline-stat span { display: block; }
.discipline-stat strong { color: #31558d; font-size: 21px; line-height: 1.2; }
.discipline-stat span { margin-top: 4px; color: #8190a5; font-size: 12px; }
.discipline-stat.stat-success strong { color: #2f9568; }
.discipline-stat.stat-muted strong { color: #8c99aa; }
.discipline-add-button { position: relative; z-index: 1; align-self: flex-start; flex: 0 0 auto; margin-top: 2px; height: 40px; padding: 0 17px; border-radius: 10px; box-shadow: 0 7px 16px rgba(40, 100, 232, .18); }
.discipline-table { width: 100%; overflow: hidden; border: 1px solid #e1e8f2; border-radius: 13px; box-shadow: 0 7px 22px rgba(35, 59, 95, .05); }
.station-toolbar { display: flex; align-items: center; gap: 10px; margin: 0 0 14px; }
.station-toolbar .el-input { max-width: 360px; }
.undo-alert { margin: 0 0 14px; }
.undo-alert :deep(.el-alert__title) { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px; }
.discipline-table :deep(.el-table__inner-wrapper::before) { display: none; }
.discipline-table :deep(th.el-table__cell) { height: 48px; color: #667892; background: #f7f9fc; font-size: 13px; font-weight: 700; }
.discipline-table :deep(td.el-table__cell) { height: 58px; color: #42536c; border-bottom-color: #edf1f6; }
.discipline-table :deep(.el-table__row:hover > td.el-table__cell) { background: #f5f9ff; }
.discipline-table :deep(.el-table__expand-icon) { color: #5b7fbd; font-size: 16px; }
.hierarchy-panel { padding: 16px 20px 18px 52px; background: linear-gradient(180deg, #f8fbff, #f4f8fd); border-top: 1px solid #e7edf5; }
.subtype-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.subtype-card { min-width: 0; padding: 14px; border: 1px solid #dce7f5; border-radius: 11px; background: #fff; box-shadow: 0 3px 10px rgba(35, 59, 95, .04); }
.subtype-heading, .status-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.subtype-heading-actions { display: flex; align-items: center; gap: 8px; }
.subtype-heading > div { min-width: 0; }
.subtype-heading strong { display: block; overflow: hidden; color: #2e4364; text-overflow: ellipsis; white-space: nowrap; }
.subtype-heading code { display: block; margin-top: 4px; overflow: hidden; color: #8a9ab0; font-size: 11px; text-overflow: ellipsis; }
.status-heading { margin-top: 13px; padding-top: 11px; border-top: 1px solid #edf1f6; color: #7b8ba1; font-size: 12px; font-weight: 650; }
.status-heading .el-button { padding: 3px 0; }
.status-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.status-list :deep(.el-tag) { max-width: 100%; }
.empty-status { padding: 12px 0 2px; color: #a0acbc; font-size: 12px; }
.status-editor-tip { margin-bottom: 16px; padding: 10px 12px; border: 1px solid #dce9fb; border-radius: 8px; background: #f5f9ff; color: #6d809c; font-size: 13px; line-height: 1.6; }
.status-editor-list { display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow: auto; }
.status-editor-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.status-editor-row > span { color: #8190a5; font-size: 13px; text-align: center; }
.status-editor-row .el-button { padding: 4px 0; }
.status-add-button { align-self: flex-start; margin-top: 4px; }
.table-actions { display: flex; align-items: center; justify-content: center; gap: 12px; white-space: nowrap; }
.table-actions .el-button { margin-left: 0 !important; padding: 4px 0; }
.discipline-code { display: inline-flex; max-width: 100%; overflow: hidden; padding: 5px 8px; border: 1px solid #dbe7fa; border-radius: 6px; background: #f2f7ff; color: #4f6f9f; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.discipline-name { color: #2e4364; }
.status-tag { min-width: 48px; justify-content: center; }
.discipline-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
.discipline-form-grid :deep(.el-input-number) { width: 100%; }
.discipline-description { grid-column: 1 / -1; }
.hierarchy-form-section { margin-top: 4px; padding-top: 18px; border-top: 1px solid #edf1f7; }
.hierarchy-form-heading, .new-subtype-heading, .new-status-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hierarchy-form-heading strong { display: block; color: #2e4364; }
.hierarchy-form-heading span { display: block; margin-top: 4px; color: #8a98aa; font-size: 12px; }
.new-subtype-list { display: grid; gap: 12px; max-height: 390px; margin-top: 14px; overflow: auto; }
.new-subtype-card { padding: 14px; border: 1px solid #e2eaf5; border-radius: 10px; background: #fbfdff; }
.new-subtype-heading { color: #47658d; font-size: 13px; }
.new-subtype-heading > span { display: flex; align-items: center; gap: 8px; min-width: 0; }
.new-subtype-heading code { color: #9aa8ba; font-size: 11px; font-weight: 400; }
.new-subtype-fields { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.new-subtype-fields .el-input { flex: 1; }
.new-status-heading { margin-top: 14px; color: #687991; font-size: 12px; }
.new-status-list { display: grid; gap: 8px; margin-top: 8px; }
.new-status-row { display: grid; grid-template-columns: 24px minmax(0, 1fr) 32px; align-items: center; gap: 8px; }
.new-status-row > span { color: #94a3b8; font-size: 12px; text-align: center; }
.new-status-row .el-button { padding: 4px 0; }
.new-status-empty { display: block; margin-top: 8px; color: #a0acbc; font-size: 12px; }

@media (max-width: 960px) {
  .rules-toolbar { grid-template-columns: 1fr; }
  .toolbar-actions { justify-content: flex-start; margin-left: 0; }
  .rule-workbench { grid-template-columns: 210px minmax(0, 1fr); }
  .step-fields, .result-fields { grid-template-columns: 1fr; }
  .step-options { justify-content: flex-start; }
  .result-row { grid-template-columns: 28px minmax(0, 1fr); }
  .result-actions { grid-column: 2; justify-content: flex-end; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .subtype-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 700px) {
  .rules-toolbar, .discipline-toolbar, .editor-heading, .tree-heading, .editor-footer { align-items: stretch; flex-direction: column; }
  .discipline-hero { align-items: stretch; flex-direction: column; padding: 20px; }
  .discipline-stats { width: 100%; margin-left: 0; }
  .discipline-stat { flex: 1; }
  .discipline-add-button { width: 100%; margin-top: 0; }
  .equipment-picker { grid-template-columns: 1fr; align-items: stretch; }
  .equipment-picker .el-select, .toolbar-actions .el-button { width: 100%; }
  .station-toolbar { align-items: stretch; flex-direction: column; }
  .station-toolbar .el-input { max-width: none; }
  .rule-workbench { display: block; }
  .rule-sidebar { border-right: 0; border-bottom: 1px solid #e4eaf2; }
  .rule-menu { min-height: 0; max-height: 260px; overflow: auto; }
  .rule-editor { padding: 16px; }
  .rule-base-grid, .discipline-form-grid { grid-template-columns: 1fr; }
  .hierarchy-form-heading, .new-subtype-fields { align-items: stretch; flex-direction: column; }
  .hierarchy-form-heading .el-button { width: 100%; }
  .description-field, .discipline-description { grid-column: auto; }
  .result-row { grid-template-columns: 1fr; }
  .result-index { display: none; }
  .result-actions { grid-column: auto; }
  .summary-grid { grid-template-columns: 1fr; }
  .summary-wide { grid-column: auto; }
  .hierarchy-panel { padding: 14px; }
  .subtype-grid { grid-template-columns: 1fr; }
  .heading-actions { width: 100%; }
  .heading-actions .el-button { flex: 1; }
  .editor-footer { right: 16px; bottom: 14px; left: 16px; justify-content: space-between; padding: 10px; }
  .editor-footer > span { display: none; }
  .editor-footer > div { width: 100%; }
  .editor-footer > div .el-button { flex: 1; }
  .editor-footer .rule-save-button { min-width: 0; }
}
</style>

