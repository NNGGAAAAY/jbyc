<script setup>
import { ref } from 'vue'
import { Activity, BrainCircuit, LogIn, ShieldCheck, Stethoscope } from 'lucide-vue-next'
import { api, getErrorMessage } from '../api'

const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

const highlights = [
  { title: '术前风险分层', text: '围绕麻醉相关并发症进行二分类预测，帮助更早识别高风险患者。', icon: Stethoscope },
  { title: '模型驱动决策', text: '融合多种机器学习模型，对病例数据进行训练、评估与结果回溯。', icon: BrainCircuit },
  { title: '数据与权限可控', text: '支持账号登录、训练队列和结果追踪，适合教学、科研与院内演示。', icon: ShieldCheck },
]

async function login() {
  busy.value = true
  error.value = ''
  try {
    const { data } = await api.post('/auth/login', {
      username: username.value,
      password: password.value,
    })
    localStorage.setItem('访问令牌', data.token)
    localStorage.setItem('当前用户', JSON.stringify(data.user))
    location.href = '/'
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-container">
      <div class="login-left">
        <div class="login-left-content">
          <div class="login-logo">
            <Activity :size="28" />
            <span>Perioperative Intelligence</span>
          </div>
          <h1>麻醉与疾病预测平台</h1>
          <p class="login-subtitle">
            面向围术期风险评估、临床病例建模与并发症预测的智能工作台
          </p>
          
          <div class="login-features">
            <div v-for="item in highlights" :key="item.title" class="feature-item">
              <div class="feature-icon">
                <component :is="item.icon" :size="20" />
              </div>
              <div class="feature-text">
                <h3>{{ item.title }}</h3>
                <p>{{ item.text }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="login-right">
        <div class="login-form-container">
          <div class="login-form-header">
            <h2>欢迎登录</h2>
            <p>请输入您的账号和密码进入系统</p>
          </div>

          <form class="login-form" @submit.prevent="login">
            <div class="form-group">
              <label>用户名</label>
              <input v-model="username" autocomplete="username" placeholder="请输入用户名" required />
            </div>

            <div class="form-group">
              <label>密码</label>
              <input
                v-model="password"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                required
              />
            </div>

            <p v-if="error" class="feedback error" role="alert">{{ error }}</p>

            <button class="button primary large login-submit" :disabled="busy">
              <LogIn :size="18" />
              <span>{{ busy ? '正在登录…' : '登录系统' }}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  </main>
</template>
