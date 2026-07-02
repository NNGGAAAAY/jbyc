import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('./views/LoginView.vue'), meta: { title: '用户登录', public: true } },
    { path: '/', component: () => import('./views/DashboardView.vue'), meta: { title: '实验概览' } },
    { path: '/datasets', component: () => import('./views/DatasetsView.vue'), meta: { title: '数据集' } },
    { path: '/datasets/:id', component: () => import('./views/DatasetDetailView.vue'), meta: { title: '数据分析' } },
    { path: '/training', component: () => import('./views/TrainingView.vue'), meta: { title: '训练中心' } },
    { path: '/inference', component: () => import('./views/InferenceView.vue'), meta: { title: '模型推理' } },
    { path: '/inference/:id', component: () => import('./views/InferenceDetailView.vue'), meta: { title: '推理结果详情' } },
    { path: '/model-versions', component: () => import('./views/ModelVersionsView.vue'), meta: { title: '模型版本管理' } },
    { path: '/runs', component: () => import('./views/RunsView.vue'), meta: { title: '实验记录' } },
    { path: '/tasks', component: () => import('./views/TasksView.vue'), meta: { title: '训练队列' } },
    { path: '/runs/:id', component: () => import('./views/RunDetailView.vue'), meta: { title: '结果详情' } },
  ],
})
router.beforeEach((to) => {
  if (!to.meta.public && !localStorage.getItem('访问令牌')) return '/login'
  if (to.path === '/login' && localStorage.getItem('访问令牌')) return '/'
})

createApp(App).use(router).mount('#app')
