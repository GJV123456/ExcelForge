<script setup>
import { ref } from 'vue'

const activeTab = ref('stations')
const tabs = [
  { name: 'stations', label: '站点信息', title: '站点信息配置开发中', description: '后续可在这里维护站点名称、排序、启用状态等基础数据。' },
  { name: 'steps', label: '操作步骤', title: '操作步骤配置开发中', description: '后续可在这里维护不同设备类型对应的测试操作步骤。' },
  { name: 'results', label: '输出结果', title: '输出结果配置开发中', description: '后续可在这里维护后端生成文件需要匹配的输出结果模板。' }
]
</script>

<template>
  <div class="config-page">
    <div class="page-title">
      <div>
        <h1>基础配置</h1>
        <p>统一维护站点信息、操作步骤和输出结果。</p>
      </div>
    </div>

    <el-card class="section-card config-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane v-for="item in tabs" :key="item.name" :label="item.label" :name="item.name">
          <div class="config-placeholder">
            <h2>{{ item.title }}</h2>
            <p>{{ item.description }}</p>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>
