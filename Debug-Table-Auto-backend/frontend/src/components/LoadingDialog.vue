<script setup>
import { Loading } from '@element-plus/icons-vue'
defineProps({ visible: Boolean })
</script>
<template><el-dialog v-loading="visible" :model-value="visible" width="360px" :show-close="false" :close-on-click-modal="false" :close-on-press-escape="false" align-center><div class="loading-content"><el-icon class="is-loading" :size="32"><Loading /></el-icon><h3>正在处理中...</h3><p>正在生成最终导入文件，请稍候</p></div></el-dialog></template>
