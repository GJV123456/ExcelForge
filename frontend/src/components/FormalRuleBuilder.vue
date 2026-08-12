<script setup>
import { createEmptyResult, createEmptyStep } from '../utils/formalRules'

const props = defineProps({
  modelValue: { type: Object, required: true },
  equipmentTypes: { type: Array, required: true }
})
const emit = defineEmits(['update:modelValue'])

const label = (equipmentType) => equipmentType || '未提供设备类型'
const replaceSteps = (equipmentType, steps) => emit('update:modelValue', { ...props.modelValue, [equipmentType]: steps })
const updateStep = (equipmentType, stepIndex, patch) => replaceSteps(
  equipmentType,
  props.modelValue[equipmentType].map((step, index) => index === stepIndex ? { ...step, ...patch } : step)
)
const addStep = (equipmentType) => replaceSteps(equipmentType, [...props.modelValue[equipmentType], createEmptyStep()])
const removeStep = (equipmentType, stepIndex) => replaceSteps(equipmentType, props.modelValue[equipmentType].filter((_, index) => index !== stepIndex))
const updateResult = (equipmentType, stepIndex, resultIndex, patch) => {
  const step = props.modelValue[equipmentType][stepIndex]
  updateStep(equipmentType, stepIndex, {
    results: step.results.map((result, index) => index === resultIndex ? { ...result, ...patch } : result)
  })
}
const addResult = (equipmentType, stepIndex) => {
  const step = props.modelValue[equipmentType][stepIndex]
  updateStep(equipmentType, stepIndex, { results: [...step.results, createEmptyResult()] })
}
const removeResult = (equipmentType, stepIndex, resultIndex) => {
  const step = props.modelValue[equipmentType][stepIndex]
  updateStep(equipmentType, stepIndex, { results: step.results.filter((_, index) => index !== resultIndex) })
}
</script>

<template>
  <el-alert class="formal-rule-tip" type="info" :closable="false" show-icon title="同一设备类型共用以下规则；所有内容均需至少一个步骤，每步均需至少一个结果。" />
  <div v-for="equipmentType in equipmentTypes" :key="equipmentType" class="formal-rule-type">
    <div class="formal-rule-heading">
      <b>设备类型：{{ label(equipmentType) }}</b>
      <el-button plain type="primary" @click="addStep(equipmentType)">添加操作步骤</el-button>
    </div>
    <el-empty v-if="!modelValue[equipmentType]?.length" :image-size="56" description="尚未添加操作步骤" />
    <div v-for="(step, stepIndex) in modelValue[equipmentType]" :key="step.id" class="formal-step">
      <div class="formal-step-fields">
        <el-input :model-value="step.description" :placeholder="`操作步骤 ${stepIndex + 1}`" @update:model-value="value => updateStep(equipmentType, stepIndex, { description: value })" />
        <el-select :model-value="step.ratioChange" placeholder="是否变比" @update:model-value="value => updateStep(equipmentType, stepIndex, { ratioChange: value })">
          <el-option label="否" value="否" />
          <el-option label="是" value="是" />
        </el-select>
        <el-button type="danger" plain @click="removeStep(equipmentType, stepIndex)">删除步骤</el-button>
      </div>
      <div v-for="(result, resultIndex) in step.results" :key="result.id" class="formal-result">
        <el-input :model-value="result.description" :placeholder="`结果输出 ${resultIndex + 1}`" @update:model-value="value => updateResult(equipmentType, stepIndex, resultIndex, { description: value })" />
        <el-input :model-value="result.responsibleDisciplines" placeholder="责任专业，多个请用逗号分隔" @update:model-value="value => updateResult(equipmentType, stepIndex, resultIndex, { responsibleDisciplines: value })" />
        <el-button type="danger" text @click="removeResult(equipmentType, stepIndex, resultIndex)">删除结果</el-button>
      </div>
      <el-button text type="primary" @click="addResult(equipmentType, stepIndex)">+ 添加结果输出</el-button>
    </div>
  </div>
</template>

<style scoped>
.formal-rule-tip { margin-bottom: 16px; }
.formal-rule-type { border: 1px solid #e1e8f3; border-radius: 10px; padding: 16px; margin-top: 14px; }
.formal-rule-heading, .formal-step-fields, .formal-result { display: flex; align-items: center; gap: 12px; }
.formal-rule-heading { justify-content: space-between; margin-bottom: 12px; }
.formal-step { background: #f8faff; border-radius: 8px; padding: 14px; margin-top: 10px; }
.formal-step-fields .el-input, .formal-result .el-input { flex: 1; }
.formal-step-fields .el-select { width: 130px; }
.formal-result { padding: 10px 0 0 18px; }
@media (max-width: 760px) {
  .formal-step-fields, .formal-result { align-items: stretch; flex-direction: column; }
  .formal-step-fields .el-select { width: 100%; }
}
</style>
