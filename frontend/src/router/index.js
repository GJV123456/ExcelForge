import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
    { path: '/', component: () => import('../views/Layout.vue'), children: [{ path: '', component: () => import('../views/Workspace.vue') }] },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach((to) => {
  const user = useUserStore()
  if (!to.meta.public && !user.token) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.path === '/login' && user.token) return '/'
})
export default router
