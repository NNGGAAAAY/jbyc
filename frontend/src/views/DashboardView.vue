<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, Database, FlaskConical, Layers3, Trophy } from 'lucide-vue-next'
import { api } from '../api'
import MetricCard from '../components/MetricCard.vue'
import ChartCard from '../components/ChartCard.vue'

const datasets = ref([]); const runs = ref([]); const loading = ref(true)
onMounted(async () => { try { [datasets.value, runs.value] = (await Promise.all([api.get('/datasets'), api.get('/runs')])).map(x => x.data) } finally { loading.value = false } })
const completed = computed(() => runs.value.filter(x => x.status === 'completed'))
const best = computed(() => completed.value.reduce((a, b) => (b.test_metrics?.roc_auc || 0) > (a?.test_metrics?.roc_auc || 0) ? b : a, null))
const comparison = computed(() => ({
  tooltip: { trigger: 'axis' }, grid: { left: 44, right: 20, top: 28, bottom: 44 },
  xAxis: { type: 'category', data: completed.value.slice(0, 8).map(x => x.model_name.toUpperCase()), axisLabel: { color: '#475569' } },
  yAxis: { type: 'value', min: 0, max: 1, name: '分数' },
  series: [{ name: '测试集 AUC', type: 'bar', data: completed.value.slice(0, 8).map(x => x.test_metrics?.roc_auc || 0), itemStyle: { color: '#1e40af', borderRadius: [5,5,0,0] }, label: { show: true, position: 'top', formatter: ({value}) => Number(value).toFixed(3) } }]
}))
</script>

<template>
  <div v-if="loading" class="skeleton-page" aria-label="正在加载"><div v-for="i in 6" :key="i" class="skeleton"></div></div>
  <div v-else class="page-stack">
    <section class="hero-panel"><div><span class="badge">术前并发症二分类</span><h2>从数据导入到模型解释，一条链路完成</h2><p>集中管理八类算法、训练与测试评价、ROC 曲线、混淆矩阵和 SHAP 特征贡献。</p></div><RouterLink class="button primary" to="/training">开始一次训练<ArrowRight :size="17" /></RouterLink></section>
    <section class="metrics-grid">
      <MetricCard label="数据集" :value="datasets.length" note="已登记的 CSV 数据" /><MetricCard label="实验总数" :value="runs.length" note="包含训练中与失败任务" tone="violet" />
      <MetricCard label="已完成" :value="completed.length" note="结果可视化可用" tone="green" /><MetricCard label="最佳测试 AUC" :value="best ? best.test_metrics.roc_auc.toFixed(3) : '—'" :note="best ? best.model_name.toUpperCase() : '等待训练结果'" tone="amber" />
    </section>
    <section class="dashboard-grid">
      <ChartCard title="模型表现速览" description="按最近实验比较测试集 ROC-AUC" :option="comparison" />
      <section class="panel workflow"><div class="panel-heading"><div><h2>工作流</h2><p>推荐按顺序完成实验</p></div></div>
        <div class="workflow-step"><Database /><div><strong>1. 导入数据集</strong><span>检查列名与病例数量</span></div></div>
        <div class="workflow-step"><Layers3 /><div><strong>2. 配置模型</strong><span>选择算法与超参数</span></div></div>
        <div class="workflow-step"><FlaskConical /><div><strong>3. 查看实验</strong><span>比较训练集与测试集</span></div></div>
        <div class="workflow-step"><Trophy /><div><strong>4. 解释结果</strong><span>阅读 ROC、矩阵与 SHAP</span></div></div>
      </section>
    </section>
  </div>
</template>
