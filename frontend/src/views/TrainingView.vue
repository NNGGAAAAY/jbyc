<script setup>
import { onMounted, ref, watch } from 'vue'
import { CheckCircle2, PlayCircle } from 'lucide-vue-next'
import { api, getErrorMessage } from '../api'
import { modelNames } from '../modelNames'

const datasets=ref([]); const models=ref([]); const busy=ref(false); const error=ref(''); const result=ref(null)
const form=ref({dataset_id:'',model_name:'xgb',target_column:'Outcome',test_size:0.2,random_state:42})

const paramSchemas = {
  xgb: [
    { key: 'n_estimators', label: '树的数量', type: 'number', default: 150 },
    { key: 'max_depth', label: '最大深度', type: 'number', default: 4 },
    { key: 'learning_rate', label: '学习率', type: 'number', step: '0.01', default: 0.05 }
  ],
  rf: [
    { key: 'n_estimators', label: '树的数量', type: 'number', default: 200 },
    { key: 'max_depth', label: '最大深度 (留空不限制)', type: 'number', default: '' }
  ],
  svm: [
    { key: 'C', label: '正则化参数 C', type: 'number', step: '0.1', default: 1.0 },
    { key: 'kernel', label: '核函数', type: 'select', options: ['rbf', 'linear', 'poly', 'sigmoid'], default: 'rbf' }
  ],
  catboost: [
    { key: 'iterations', label: '迭代次数', type: 'number', default: 150 },
    { key: 'depth', label: '树深度', type: 'number', default: 5 },
    { key: 'learning_rate', label: '学习率', type: 'number', step: '0.01', default: 0.05 }
  ],
  dt: [
    { key: 'max_depth', label: '最大深度', type: 'number', default: 5 },
    { key: 'min_samples_split', label: '最小分裂样本数', type: 'number', default: 2 }
  ],
  knn: [
    { key: 'n_neighbors', label: '邻居数 (K)', type: 'number', default: 5 },
    { key: 'weights', label: '权重', type: 'select', options: ['uniform', 'distance'], default: 'uniform' }
  ],
  ann: [
    { key: 'epochs', label: '训练轮数', type: 'number', default: 100 },
    { key: 'learning_rate', label: '学习率', type: 'number', step: '0.001', default: 0.001 }
  ],
  rnn: [
    { key: 'epochs', label: '训练轮数', type: 'number', default: 100 },
    { key: 'learning_rate', label: '学习率', type: 'number', step: '0.001', default: 0.001 },
    { key: 'hidden_size', label: '隐藏层维度', type: 'number', default: 32 }
  ]
}

const currentParams = ref({})

watch(() => form.value.model_name, (newModel) => {
  const schema = paramSchemas[newModel] || []
  currentParams.value = {}
  schema.forEach(p => {
    if(p.default !== '' && p.default !== null) {
      currentParams.value[p.key] = p.default
    }
  })
}, { immediate: true })

onMounted(async()=>{ const [d,m]=await Promise.all([api.get('/datasets'),api.get('/models')]); datasets.value=d.data; models.value=m.data.models; if(datasets.value[0])form.value.dataset_id=datasets.value[0].id })

async function submit() {
  busy.value = true;
  error.value = '';
  result.value = null;
  try {
    const cleanParams = {}
    for (const key in currentParams.value) {
      const val = currentParams.value[key]
      if (val !== '' && val !== null) {
        const num = Number(val)
        cleanParams[key] = isNaN(num) ? val : num
      }
    }
    const body = {
      ...form.value,
      dataset_id: Number(form.value.dataset_id),
      test_size: Number(form.value.test_size),
      random_state: Number(form.value.random_state),
      parameters: cleanParams,
      priority: 0
    };
    result.value = (await api.post('/train', body)).data
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>
<template><div class="page-stack"><section class="panel training-layout"><div><span class="badge">实验配置</span><h2>训练一个二分类模型</h2><p class="section-copy">系统自动完成分层划分、特征预处理、模型持久化、评价计算与 SHAP 解释。训练期间请保持页面打开。</p>
  <form @submit.prevent="submit" class="form-stack"><label>数据集<select v-model="form.dataset_id" required><option disabled value="">请选择</option><option v-for="d in datasets" :key="d.id" :value="d.id">{{d.name}}（{{d.rows}} 行）</option></select></label>
  <fieldset><legend>模型算法</legend><div class="model-grid"><label v-for="model in models" :key="model" class="model-option" :class="{selected:form.model_name===model}"><input v-model="form.model_name" type="radio" :value="model"/><strong>{{modelNames[model]}}</strong><span>{{ {xgb:'集成提升算法',rf:'树模型集成',svm:'最大间隔分类',catboost:'类别特征提升',dt:'可解释树模型',ann:'全连接神经网络',rnn:'序列神经网络',knn:'近邻投票算法'}[model] }}</span></label></div></fieldset>
  <div class="form-grid">
    <label>目标列<input v-model="form.target_column"/></label>
    <label>测试集比例<input v-model="form.test_size" type="number" min="0.1" max="0.5" step="0.05"/></label>
    <label>随机种子<input v-model="form.random_state" type="number"/></label>
  </div>
  
  <fieldset v-if="paramSchemas[form.model_name] && paramSchemas[form.model_name].length > 0">
    <legend>超参数设置</legend>
    <div class="form-grid">
      <label v-for="p in paramSchemas[form.model_name]" :key="p.key">
        {{ p.label }}
        <select v-if="p.type === 'select'" v-model="currentParams[p.key]">
          <option v-for="opt in p.options" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <input v-else v-model="currentParams[p.key]" type="number" :step="p.step || '1'" :placeholder="p.default === '' ? '留空使用默认值' : ''"/>
      </label>
    </div>
  </fieldset>

  <button class="button primary large" :disabled="busy||!form.dataset_id"><PlayCircle :size="19"/>{{busy?'正在提交任务…':'加入训练队列'}}</button><p v-if="error" class="feedback error" role="alert">{{error}}</p></form></div>
  <aside class="training-note"><h3>异步任务将保存</h3><ul><li><CheckCircle2/>训练集与测试集评价指标</li><li><CheckCircle2/>两组混淆矩阵</li><li><CheckCircle2/>ROC 曲线原始坐标</li><li><CheckCircle2/>SHAP 特征贡献数据</li><li><CheckCircle2/>分阶段训练日志</li></ul><div v-if="result" class="result-callout"><strong>任务提交成功</strong><span>已进入后台训练队列</span><RouterLink to="/tasks">查看队列与日志</RouterLink></div></aside>
  </section></div></template>
