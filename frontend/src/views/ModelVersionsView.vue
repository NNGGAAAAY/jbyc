<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowUpRight, BrainCircuit, RefreshCw } from 'lucide-vue-next'
import DetailPageHeader from '../components/DetailPageHeader.vue'
import { api } from '../api'
import { modelNames, statusNames } from '../modelNames'

const groups = ref([])
const busy = ref(false)
const filterModel = ref('all')
const filterStatus = ref('all')

async function load() {
  busy.value = true
  try {
    groups.value = (await api.get('/model-versions')).data
  } finally {
    busy.value = false
  }
}

onMounted(load)

const modelOptions = computed(() => groups.value.map((item) => item.model_name))

const filteredGroups = computed(() => {
  return groups.value
    .filter((group) => filterModel.value === 'all' || group.model_name === filterModel.value)
    .map((group) => ({
      ...group,
      versions: group.versions.filter((version) => filterStatus.value === 'all' || version.status === filterStatus.value),
    }))
    .filter((group) => group.versions.length)
})

const summary = computed(() => {
  const versions = groups.value.flatMap((group) => group.versions)
  const completed = versions.filter((item) => item.status === 'completed').length
  const bestAuc = versions.reduce((best, item) => {
    const auc = item.test_metrics?.roc_auc
    return auc == null ? best : Math.max(best, auc)
  }, 0)
  return {
    models: groups.value.length,
    versions: versions.length,
    completed,
    bestAuc,
  }
})

function pct(value) {
  return value == null ? '—' : `${(value * 100).toFixed(1)}%`
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="page-stack">
    <DetailPageHeader
      fallback="/runs"
      back-label="返回实验记录"
      badge="版本资产"
      title="模型版本管理"
      subtitle="按模型聚合查看历史版本、最佳指标与可用状态，方便训练复盘和推理选型"
    >
      <template #action>
        <button class="button secondary" :disabled="busy" @click="load">
          <RefreshCw :size="17" />刷新版本
        </button>
      </template>
    </DetailPageHeader>

    <section class="metrics-grid four">
      <article class="metric-card">
        <span class="metric-label">模型类别</span>
        <strong>{{ summary.models }}</strong>
        <p>当前已沉淀的模型族</p>
      </article>
      <article class="metric-card tone-violet">
        <span class="metric-label">版本总数</span>
        <strong>{{ summary.versions }}</strong>
        <p>训练运行生成的可追溯版本</p>
      </article>
      <article class="metric-card tone-green">
        <span class="metric-label">已完成版本</span>
        <strong>{{ summary.completed }}</strong>
        <p>可直接用于推理</p>
      </article>
      <article class="metric-card tone-navy">
        <span class="metric-label">最佳 AUC</span>
        <strong>{{ summary.bestAuc ? summary.bestAuc.toFixed(3) : '—' }}</strong>
        <p>跨模型历史最佳测试表现</p>
      </article>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>版本筛选</h2>
          <p>支持按模型与训练状态快速定位特定版本</p>
        </div>
      </div>
      <div class="form-grid compact-grid">
        <label>
          模型类别
          <select v-model="filterModel">
            <option value="all">全部模型</option>
            <option v-for="item in modelOptions" :key="item" :value="item">{{ modelNames[item] || item }}</option>
          </select>
        </label>
        <label>
          训练状态
          <select v-model="filterStatus">
            <option value="all">全部状态</option>
            <option value="completed">已完成</option>
            <option value="training">训练中</option>
            <option value="failed">失败</option>
          </select>
        </label>
      </div>
    </section>

    <section v-if="filteredGroups.length" class="page-stack">
      <article v-for="group in filteredGroups" :key="group.model_name" class="panel version-panel">
        <div class="version-panel-head">
          <div>
            <div class="table-title">
              <BrainCircuit :size="18" />
              <strong>{{ modelNames[group.model_name] || group.model_name }}</strong>
            </div>
            <p class="row-subtitle">
              共 {{ group.total_versions }} 个版本，已完成 {{ group.completed_versions }} 个，最新版本 v{{ group.latest_version_no }}
            </p>
          </div>
          <div class="version-group-summary">
            <span>最佳 AUC {{ group.best_auc != null ? group.best_auc.toFixed(3) : '—' }}</span>
          </div>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>版本</th>
                <th>训练集</th>
                <th>目标列</th>
                <th>测试集比例</th>
                <th>随机种子</th>
                <th>状态</th>
                <th>准确率</th>
                <th>F1</th>
                <th>AUC</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="version in group.versions" :key="version.id">
                <td class="mono">v{{ version.version_no || 1 }}</td>
                <td>{{ version.dataset_name || `#${version.dataset_id}` }}</td>
                <td>{{ version.target_column || 'Outcome' }}</td>
                <td>{{ version.test_size ?? '—' }}</td>
                <td>{{ version.random_state ?? '—' }}</td>
                <td><span class="status-pill" :class="version.status">{{ statusNames[version.status] || version.status }}</span></td>
                <td>{{ pct(version.test_metrics?.accuracy) }}</td>
                <td>{{ pct(version.test_metrics?.f1) }}</td>
                <td class="mono">{{ version.test_metrics?.roc_auc?.toFixed(3) || '—' }}</td>
                <td>{{ formatDate(version.created_at) }}</td>
                <td>
                  <RouterLink class="icon-link" :to="`/runs/${version.id}`" aria-label="查看版本详情">
                    <ArrowUpRight />
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <section v-else class="panel empty-state">
      当前筛选条件下暂无模型版本
    </section>
  </div>
</template>
