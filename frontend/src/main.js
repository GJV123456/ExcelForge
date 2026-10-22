import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import router from './router'
import ExclusiveSelect from './components/ExclusiveSelect.vue'

const app = createApp(App)
app.use(createPinia()).use(router).use(ElementPlus)
app.component('el-select', ExclusiveSelect)
app.mount('#app')
