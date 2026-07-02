<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Download } from 'lucide-vue-next'
import { api } from '../api'
import DetailPageHeader from '../components/DetailPageHeader.vue'
import { modelNames } from '../modelNames'
import MetricCard from '../components/MetricCard.vue'

const route = useRoute()
const detail = ref(null)
const loading = ref(true)

onMounted(async () => {
  detail.value = (await api.get(`/inference/runs/${route.params.id}`)).data
  loading.value = false
})

const metrics = computed(() => detail.value?.summary || {})

async function download() {
  const response = await api.get(`/inference/runs/${route.params.id}/download`, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = `${detail.value.output_name}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(blobUrl)
}
</script>

<template>
  <div v-if="loading" class="skeleton-page"><div v-for="i in 6" :key="i" class="skeleton"></div></div>
  <div v-else-if="detail" class="page-stack">
    <DetailPageHeader
      fallback="/inference"
      back-label="返回推理中心"
      badge="推理结果"
      :title="detail.output_name"
      :mono="detail.id"
    >
      <template #meta>
        <span><strong>模型:</strong> {{ modelNames[detail.model_name] || detail.model_name }}</span>
        <span><strong>版本:</strong> v{{ detail.version_no }}</span>
        <span><strong>阈值:</strong> {{ detail.threshold }}</span>
      </template>
      <template #action>
        <button class="button secondary" @click="download"><Download :size="17" />下载 CSV</button>
      </template>
    </DetailPageHeader>

    <section class="metrics-grid five">
      <MetricCard label="样本数" :value="metrics.rows" note="本次推理处理的记录数" />
      <MetricCard label="阳性预测" :value="metrics.positive_predictions" note="预测为高风险/阳性的数量" tone="amber" />
      <MetricCard label="阴性预测" :value="metrics.negative_predictions" note="预测为低风险/阴性的数量" tone="green" />
      <MetricCard label="阳性率" :value="metrics.positive_rate != null ? `${(metrics.positive_rate * 100).toFixed(1)}%` : '-'" note="预测标签中的阳性比例" tone="violet" />
      <MetricCard label="平均概率" :value="metrics.mean_probability?.toFixed ? metrics.mean_probability.toFixed(3) : metrics.mean_probability" note="样本平均预测概率" tone="navy" />
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>结果预览</h2>
          <p>展示前 20 行预测结果，完整数据请下载 CSV</p>
        </div>
      </div>
      <div class="table-wrap preview-table">
        <table>
          <thead>
            <tr>
              <th v-for="column in Object.keys(detail.preview?.[0] || {})" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in detail.preview || []" :key="index">
              <td v-for="(value, key) in row" :key="key">{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
