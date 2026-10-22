import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'
import { useExcelStore } from '../store/excel'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('../views/Layout.vue'),
      redirect: '/workspace',
      children: [
        { path: 'workspace', component: () => import('../views/Workspace.vue') },
        { path: 'config', component: () => import('../views/Config.vue') },
        { path: 'admin', component: () => import('../views/Admin.vue') }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach((to) => {
  const user = useUserStore()
  const excel = useExcelStore()
  if (!to.meta.public && !user.token) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.path === '/login' && user.token) return '/'
})
export default router
