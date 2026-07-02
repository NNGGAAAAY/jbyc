<script setup>
import { computed, onMounted, ref } from 'vue'
import { BrainCircuit, PlayCircle, Search } from 'lucide-vue-next'
import { api, getErrorMessage } from '../api'
import { modelNames } from '../modelNames'

const models = ref([])
const datasets = ref([])
const inferenceRuns = ref([])
const busy = ref(false)
const error = ref('')
const result = ref(null)
const form = ref({ training_run_id: '', dataset_id: '', threshold: 0.5, output_name: '' })
const historyFilter = ref({ model_name: 'all', version_no: 'all', dataset_id: 'all', keyword: '' })

const selectedModel = computed(() => models.value.find((item) => item.id === form.value.training_run_id))

const historyModelOptions = computed(() => Array.from(new Set(inferenceRuns.value.map((item) => item.model_name).filter(Boolean))))

const historyVersionOptions = computed(() => {
  return Array.from(new Set(
    inferenceRuns.value
      .filter((item) => historyFilter.value.model_name === 'all' || item.model_name === historyFilter.value.model_name)
      .map((item) => item.version_no)
      .filter((item) => item != null),
  )).sort((a, b) => Number(b) - Number(a))
})

const filteredInferenceRuns = computed(() => {
  const keyword = historyFilter.value.keyword.trim().toLowerCase()
  return inferenceRuns.value.filter((item) => {
    if (historyFilter.value.model_name !== 'all' && item.model_name !== historyFilter.value.model_name) return false
    if (historyFilter.value.version_no !== 'all' && Number(item.version_no) !== Number(historyFilter.value.version_no)) return false
    if (historyFilter.value.dataset_id !== 'all' && Number(item.dataset_id) !== Number(historyFilter.value.dataset_id)) return false
    if (!keyword) return true
    const haystack = [
      item.output_name,
      item.dataset_name,
      modelNames[item.model_name],
      item.model_name,
      item.target_column,
    ].join(' ').toLowerCase()
    return haystack.includes(keyword)
  })
})

async function load() {
  const [modelRes, datasetRes, runRes] = await Promise.all([
    api.get('/inference/models'),
    api.get('/datasets'),
    api.get('/inference/runs'),
  ])
  models.value = modelRes.data
  datasets.value = datasetRes.data
  inferenceRuns.value = runRes.data
  if (!form.value.training_run_id && models.value[0]) form.value.training_run_id = models.value[0].id
  if (!form.value.dataset_id && datasets.value[0]) form.value.dataset_id = datasets.value[0].id
}

onMounted(load)

async function submit() {
  busy.value = true
  error.value = ''
  result.value = null
  try {
    result.value = (await api.post('/inference/run', {
      training_run_id: form.value.training_run_id,
      dataset_id: Number(form.value.dataset_id),
      threshold: Number(form.value.threshold),
      output_name: form.value.output_name || undefined,
    })).data
    await load()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function datasetTypeLabel(value) {
  return {
    training: '训练集',
    test: '测试集',
    validation: '验证集',
    inference: '推理集',
  }[value] || value || '未分类'
}
</script>

<template>
  <div class="page-stack">
    <section class="panel training-layout inference-layout">
      <div>
        <span class="badge">模型服务化</span>
        <h2>推理中心</h2>
        <p class="section-copy">选择已训练完成的模型版本，对任意已上传数据集执行批量推理，并保存预测结果历史。</p>

        <form class="form-stack" @submit.prevent="submit">
          <div class="form-grid">
            <label class="wide">
              模型版本
              <select v-model="form.training_run_id" required>
                <option disabled value="">请选择模型版本</option>
                <option v-for="item in models" :key="item.id" :value="item.id">
                  {{ modelNames[item.model_name] }} / v{{ item.version_no }} / AUC {{ item.test_metrics?.roc_auc?.toFixed(3) ?? '-' }}
                </option>
              </select>
            </label>
            <label>
              推理数据集
              <select v-model="form.dataset_id" required>
                <option disabled value="">请选择数据集</option>
                <option v-for="item in datasets" :key="item.id" :value="item.id">{{ item.name }}（{{ item.rows }} 行）</option>
              </select>
            </label>
            <label>
              判定阈值
              <input v-model="form.threshold" type="number" min="0.1" max="0.9" step="0.05" />
            </label>
            <label class="wide">
              输出结果名称
              <input v-model="form.output_name" placeholder="留空则自动生成" />
            </label>
          </div>

          <div v-if="selectedModel" class="result-callout">
            <strong><BrainCircuit :size="16" /> 当前版本信息</strong>
            <span>模型：{{ modelNames[selectedModel.model_name] }} / 版本：v{{ selectedModel.version_no }}</span>
            <span>训练目标列：{{ selectedModel.target_column || 'Outcome' }}</span>
            <span>测试集 AUC：{{ selectedModel.test_metrics?.roc_auc?.toFixed(3) ?? '-' }}</span>
          </div>

          <button class="button primary large" :disabled="busy || !form.training_run_id || !form.dataset_id">
            <PlayCircle :size="18" />{{ busy ? '正在执行推理…' : '开始推理' }}
          </button>
          <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
        </form>
      </div>

      <aside class="training-note">
        <h3>推理结果会保存</h3>
        <ul>
          <li><BrainCircuit />模型版本号与训练来源</li>
          <li><BrainCircuit />预测概率与分类标签</li>
          <li><BrainCircuit />阳性预测数、阳性率、平均概率</li>
          <li><BrainCircuit />每次推理的历史记录</li>
        </ul>
        <div v-if="result" class="result-callout">
          <strong>推理完成</strong>
          <span>结果名称：{{ result.output_name }}</span>
          <span>阳性预测：{{ result.summary.positive_predictions }} / {{ result.summary.rows }}</span>
          <span>平均概率：{{ result.summary.mean_probability.toFixed(3) }}</span>
        </div>
      </aside>
    </section>

    <section v-if="result" class="panel">
      <div class="panel-heading">
        <div>
          <h2>推理结果预览</h2>
          <p>展示前 20 行预测结果，完整结果已在后端保存</p>
        </div>
      </div>
      <div class="table-wrap preview-table">
        <table>
          <thead>
            <tr>
              <th v-for="column in Object.keys(result.preview[0] || {})" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in result.preview" :key="index">
              <td v-for="(value, key) in row" :key="key">{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>推理历史</h2>
          <p>保存每次推理的模型版本、输入数据集和摘要统计，支持多维筛选</p>
        </div>
      </div>

      <div class="form-grid compact-grid inference-filter-grid">
        <label>
          模型类别
          <select v-model="historyFilter.model_name">
            <option value="all">全部模型</option>
            <option v-for="item in historyModelOptions" :key="item" :value="item">{{ modelNames[item] || item }}</option>
          </select>
        </label>
        <label>
          版本号
          <select v-model="historyFilter.version_no">
            <option value="all">全部版本</option>
            <option v-for="item in historyVersionOptions" :key="item" :value="item">v{{ item }}</option>
          </select>
        </label>
        <label>
          数据集
          <select v-model="historyFilter.dataset_id">
            <option value="all">全部数据集</option>
            <option v-for="item in datasets" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </label>
        <label class="wide">
          关键字检索
          <div class="inline-search">
            <Search :size="16" />
            <input v-model="historyFilter.keyword" placeholder="搜索结果名称、模型、数据集或目标列" />
          </div>
        </label>
      </div>

      <div v-if="filteredInferenceRuns.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>结果名称</th>
              <th>模型版本</th>
              <th>数据集</th>
              <th>阈值</th>
              <th>样本数</th>
              <th>阳性率</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredInferenceRuns" :key="item.id">
              <td><strong>{{ item.output_name }}</strong></td>
              <td>
                <strong>{{ modelNames[item.model_name] || item.model_name || '未知模型' }}</strong>
                <div class="row-subtitle mono">v{{ item.version_no || '-' }} / {{ item.training_run_id.slice(0, 8) }}…</div>
              </td>
              <td>
                <strong>{{ item.dataset_name || `#${item.dataset_id}` }}</strong>
                <div class="row-subtitle">{{ datasetTypeLabel(item.dataset_type) }}</div>
              </td>
              <td>{{ item.threshold }}</td>
              <td>{{ item.row_count }}</td>
              <td>{{ ((item.summary?.positive_rate || 0) * 100).toFixed(1) }}%</td>
              <td>{{ formatDate(item.created_at) }}</td>
              <td><RouterLink class="button ghost compact" :to="`/inference/${item.id}`">查看详情</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">当前筛选条件下暂无推理记录</div>
    </section>
  </div>
</template>
