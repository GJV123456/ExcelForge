<script setup>
import { computed, ref } from 'vue'
import draggable from 'vuedraggable'
import { Delete, Plus } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  availableFields: { type: Array, default: () => ['设备编码', '设备类型', '设备中文', '信号描述', '附加编号'] }
})
const emit = defineEmits(['update:modelValue'])
const customText = ref('')
const rules = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const addField = (value) => { if (!rules.value.some((item) => item.type === 'field' && item.value === value)) rules.value = [...rules.value, { type: 'field', value }] }
const addText = () => { if (customText.value.trim()) { rules.value = [...rules.value, { type: 'text', value: customText.value.trim() }]; customText.value = '' } }
const remove = (index) => rules.value = rules.value.filter((_, i) => i !== index)
const fieldOptions = computed(() => props.availableFields)
</script>

<template>
  <div class="rule-builder">
    <p class="muted">点击字段加入规则，再拖动标签调整生成顺序。</p>
    <div class="field-actions"><el-button v-for="field in fieldOptions" :key="field" @click="addField(field)">+ {{ field }}</el-button></div>
    <div class="text-actions"><el-input v-model="customText" placeholder="输入自定义文字，例如：报警测试" @keyup.enter="addText" /><el-button type="primary" :icon="Plus" @click="addText">添加文字</el-button></div>
    <draggable v-model="rules" item-key="value" class="rule-list" ghost-class="dragging">
      <template #item="{ element, index }"><div class="rule-item"><el-tag :type="element.type === 'field' ? 'primary' : 'success'">{{ element.type === 'field' ? '字段：' : '文字：' }}{{ element.value }}</el-tag><el-button text type="danger" :icon="Delete" @click="remove(index)" /></div></template>
    </draggable>
    <el-empty v-if="!rules.length" :image-size="70" description="请添加生成规则" />
  </div>
</template>
