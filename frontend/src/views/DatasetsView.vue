<script setup>
import { computed, onMounted, ref } from 'vue'
import { CalendarDays, Database, Eye, FileUp, FolderInput, HardDriveUpload, Pencil, Save, Trash2 } from 'lucide-vue-next'
import { api, getErrorMessage } from '../api'

const datasets = ref([])
const path = ref('E:\\Desktop\\Anesthesia_Dataset.csv')
const name = ref('Anesthesia Dataset')
const datasetType = ref('training')
const busy = ref(false)
const message = ref('')
const error = ref('')
const editingId = ref(null)
const editDraft = ref({ name: '', dataset_type: 'training' })

const datasetTypeOptions = [
  { value: 'training', label: '训练集' },
  { value: 'test', label: '测试集' },
  { value: 'validation', label: '验证集' },
  { value: 'inference', label: '推理集' },
]

const load = async () => {
  datasets.value = (await api.get('/datasets')).data
}

onMounted(load)

const totalRows = computed(() => datasets.value.reduce((sum, item) => sum + item.rows, 0))

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function formatSize(value) {
  if (!value && value !== 0) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

function datasetTypeLabel(value) {
  return datasetTypeOptions.find((item) => item.value === value)?.label || value || '未分类'
}

async function importPath() {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await api.post('/datasets/import-path', { path: path.value, name: name.value, dataset_type: datasetType.value })
    message.value = '数据集导入成功'
    await load()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}

async function upload(event) {
  const file = event.target.files[0]
  if (!file) return
  busy.value = true
  error.value = ''
  message.value = ''
  const form = new FormData()
  form.append('file', file)
  form.append('dataset_type', datasetType.value)
  try {
    await api.post('/datasets/upload', form)
    message.value = '文件上传成功'
    await load()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
    event.target.value = ''
  }
}

async function removeDataset(item) {
  const confirmed = window.confirm(`确认删除数据集“${item.name}”吗？`)
  if (!confirmed) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await api.delete(`/datasets/${item.id}`)
    message.value = '数据集已删除'
    await load()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}

function startEdit(item) {
  editingId.value = item.id
  editDraft.value = { name: item.name, dataset_type: item.dataset_type || 'training' }
}

async function saveEdit(item) {
  busy.value = true
  error.value = ''
  try {
    await api.patch(`/datasets/${item.id}`, editDraft.value)
    editingId.value = null
    message.value = '数据集信息已更新'
    await load()
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>导入数据集</h2>
          <p>支持服务器路径导入和浏览器上传，上传后自动进入可视化分析与训练管理</p>
        </div>
      </div>
      <div class="form-grid">
        <label>数据集名称<input v-model="name" /></label>
        <label>数据集类型<select v-model="datasetType"><option v-for="item in datasetTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
        <label class="wide">CSV 本地路径<input v-model="path" /></label>
      </div>
      <div class="form-actions">
        <button class="button primary" :disabled="busy" @click="importPath"><FolderInput :size="18" />{{ busy ? '处理中…' : '按路径导入' }}</button>
        <label class="button secondary file-button"><FileUp :size="18" />上传 CSV<input type="file" accept=".csv" @change="upload" /></label>
      </div>
      <p v-if="message" class="feedback success" aria-live="polite">{{ message }}</p>
      <p v-if="error" class="feedback error" role="alert">{{ error }}</p>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>数据集管理</h2>
          <p>共 {{ datasets.length }} 个数据集，累计 {{ totalRows }} 条记录</p>
        </div>
      </div>

      <div v-if="datasets.length" class="dataset-card-grid">
        <article v-for="item in datasets" :key="item.id" class="dataset-card">
          <div class="dataset-card-top">
            <div class="table-title">
              <Database :size="18" />
              <strong>{{ item.name }}</strong>
            </div>
            <span class="status-pill">{{ datasetTypeLabel(item.dataset_type) }}</span>
          </div>

          <div class="dataset-kpis">
            <div>
              <small>病例数</small>
              <strong>{{ item.rows }}</strong>
            </div>
            <div>
              <small>字段数</small>
              <strong>{{ item.columns.length }}</strong>
            </div>
          </div>

          <div class="dataset-meta">
            <span><CalendarDays :size="15" />{{ formatDate(item.created_at) }}</span>
            <span><HardDriveUpload :size="15" />{{ formatSize(item.file_size) }}</span>
          </div>

          <p class="row-subtitle">{{ item.original_filename || '未记录源文件名' }}</p>
          <p class="row-subtitle">来源：{{ item.source_type === 'browser_upload' ? '浏览器上传' : '路径导入' }}</p>

          <div v-if="editingId === item.id" class="dataset-edit-form">
            <label>名称<input v-model="editDraft.name" /></label>
            <label>类型<select v-model="editDraft.dataset_type"><option v-for="opt in datasetTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select></label>
          </div>

          <div class="chip-list">
            <span v-for="column in item.columns.slice(0, 6)" :key="column">{{ column }}</span>
            <span v-if="item.columns.length > 6">+{{ item.columns.length - 6 }}</span>
          </div>

          <div class="dataset-card-actions">
            <RouterLink class="action-icon-button" :to="`/datasets/${item.id}`" aria-label="查看分析" title="查看分析">
              <Eye :size="18" />
              <span>查看分析</span>
            </RouterLink>
            <button
              v-if="editingId !== item.id"
              class="action-icon-button"
              type="button"
              :disabled="busy"
              aria-label="编辑数据集"
              title="编辑"
              @click="startEdit(item)"
            >
              <Pencil :size="18" />
              <span>编辑</span>
            </button>
            <button
              v-else
              class="action-icon-button primary-action"
              type="button"
              :disabled="busy"
              aria-label="保存修改"
              title="保存"
              @click="saveEdit(item)"
            >
              <Save :size="18" />
              <span>保存</span>
            </button>
            <button
              class="action-icon-button danger-action"
              type="button"
              :disabled="busy"
              aria-label="删除数据集"
              title="删除"
              @click="removeDataset(item)"
            >
              <Trash2 :size="18" />
              <span>删除</span>
            </button>
          </div>
        </article>
      </div>
      <div v-else class="empty-state">尚未导入数据集</div>
    </section>
  </div>
</template>
