<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Activity, BrainCircuit, Database, FlaskConical, GitBranch, LayoutDashboard, ListOrdered, LogOut, Menu, PlayCircle, X } from 'lucide-vue-next'
import { api } from '../api'

const route = useRoute()
const open = ref(false)
const navigation = [
  { to: '/', label: '实验概览', icon: LayoutDashboard },
  { to: '/datasets', label: '数据集', icon: Database },
  { to: '/training', label: '训练中心', icon: PlayCircle },
  { to: '/inference', label: '模型推理', icon: BrainCircuit },
  { to: '/model-versions', label: '模型版本', icon: GitBranch },
  { to: '/tasks', label: '训练队列', icon: ListOrdered },
  { to: '/runs', label: '实验记录', icon: FlaskConical },
]
const user = JSON.parse(localStorage.getItem('当前用户') || '{}')
async function logout(){ try{await api.post('/auth/logout')}finally{localStorage.clear();location.href='/login'} }
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <div class="app-shell">
    <aside class="sidebar" :class="{ open }" aria-label="主导航">
      <div class="brand"><span class="brand-mark"><Activity :size="22" /></span><div><strong>麻醉风险平台</strong><small>机器学习分析系统</small></div></div>
      <button class="icon-button sidebar-close" aria-label="关闭菜单" @click="open = false"><X /></button>
      <nav>
        <RouterLink v-for="item in navigation" :key="item.to" :to="item.to" @click="open = false">
          <component :is="item.icon" :size="19" /><span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="service-state"><span class="status-dot"></span><div><strong>{{user.display_name||'当前用户'}}</strong><small>训练服务运行中</small></div><button class="logout-button" aria-label="退出登录" @click="logout"><LogOut :size="17"/></button></div>
    </aside>
    <div v-if="open" class="scrim" @click="open = false"></div>
    <section class="workspace">
      <header class="topbar">
        <button class="icon-button menu-button" aria-label="打开菜单" @click="open = true"><Menu /></button>
        <div><span class="eyebrow">临床机器学习工作台</span><h1>{{ route.meta.title }}</h1></div>
        <RouterLink class="button primary compact" to="/training"><PlayCircle :size="17" />新建训练</RouterLink>
      </header>
      <main id="main-content" tabindex="-1"><slot /></main>
    </section>
  </div>
</template>
