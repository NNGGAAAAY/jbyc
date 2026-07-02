<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import ChartCard from '../components/ChartCard.vue'
import DetailPageHeader from '../components/DetailPageHeader.vue'
import MetricCard from '../components/MetricCard.vue'

const route = useRoute()
const analysis = ref(null)
const selectedCategory = ref('')
const selectedNumeric = ref('')

onMounted(async () => {
  analysis.value = (await api.get(`/datasets/${route.params.id}/analysis`)).data
  selectedCategory.value = Object.keys(analysis.value.distributions)[0] || ''
  selectedNumeric.value = Object.keys(analysis.value.numeric_histograms)[0] || ''
})

const missingOption = computed(() => analysis.value && ({
  tooltip: { trigger: 'axis' },
  grid: { left: 120, right: 25, top: 15, bottom: 35 },
  xAxis: { type: 'value', name: '缺失数量' },
  yAxis: { type: 'category', data: analysis.value.column_types.map((x) => x.column).reverse() },
  series: [{ type: 'bar', data: analysis.value.column_types.map((x) => x.missing).reverse(), itemStyle: { color: '#d97706' }, label: { show: true, position: 'right' } }],
}))

const distributionOption = computed(() => {
  if (!analysis.value || !selectedCategory.value) return null
  const rows = analysis.value.distributions[selectedCategory.value] || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 120, right: 25, top: 15, bottom: 40 },
    xAxis: { type: 'value', name: '病例数' },
    yAxis: { type: 'category', data: rows.map((x) => x.label).reverse() },
    series: [{ type: 'bar', data: rows.map((x) => x.value).reverse(), itemStyle: { color: '#1e40af', borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right' } }],
  }
})

const histogramOption = computed(() => {
  if (!analysis.value || !selectedNumeric.value) return null
  const rows = analysis.value.numeric_histograms[selectedNumeric.value] || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 25, top: 20, bottom: 45 },
    xAxis: { type: 'category', data: rows.map((x) => `${x.left.toFixed(1)}-${x.right.toFixed(1)}`), axisLabel: { rotate: 28 } },
    yAxis: { type: 'value', name: '频数' },
    series: [{ type: 'bar', data: rows.map((x) => x.count), itemStyle: { color: '#2563eb', borderRadius: [6, 6, 0, 0] } }],
  }
})

const violinOption = computed(() => {
  if (!analysis.value || !selectedNumeric.value) return null
  const rows = analysis.value.numeric_histograms[selectedNumeric.value] || []
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const label = params[0]?.axisValue || ''
        const count = Math.max(...params.map((item) => Math.abs(item.value)))
        return `${label}<br/>样本数: ${count}`
      },
    },
    grid: { left: 48, right: 25, top: 20, bottom: 45 },
    xAxis: { type: 'category', data: rows.map((x) => `${x.left.toFixed(1)}-${x.right.toFixed(1)}`), axisLabel: { rotate: 28 } },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (value) => Math.abs(value) },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [
      { type: 'bar', stack: 'violin', data: rows.map((x) => -x.count), itemStyle: { color: 'rgba(37,99,235,0.35)', borderRadius: [6, 6, 0, 0] } },
      { type: 'bar', stack: 'violin', data: rows.map((x) => x.count), itemStyle: { color: 'rgba(14,165,233,0.55)', borderRadius: [6, 6, 0, 0] } },
    ],
  }
})

const boxplotOption = computed(() => {
  if (!analysis.value || !selectedNumeric.value || !analysis.value.numeric_boxplots[selectedNumeric.value]) return null
  return {
    tooltip: { trigger: 'item' },
    grid: { left: 70, right: 25, top: 25, bottom: 40 },
    xAxis: { type: 'category', data: [selectedNumeric.value] },
    yAxis: { type: 'value', scale: true, name: '数值范围' },
    series: [{ type: 'boxplot', data: [analysis.value.numeric_boxplots[selectedNumeric.value]], itemStyle: { color: '#dbeafe', borderColor: '#1d4ed8' } }],
  }
})

const correlationOption = computed(() => {
  if (!analysis.value || !analysis.value.correlation.columns.length) return null
  return {
    tooltip: {
      formatter: (params) => {
        const x = analysis.value.correlation.columns[params.data[0]]
        const y = analysis.value.correlation.columns[params.data[1]]
        return `${y} / ${x}: ${Number(params.data[2]).toFixed(3)}`
      },
    },
    grid: { left: 110, right: 40, top: 20, bottom: 100 },
    xAxis: { type: 'category', data: analysis.value.correlation.columns, axisLabel: { rotate: 35 } },
    yAxis: { type: 'category', data: analysis.value.correlation.columns },
    visualMap: { min: -1, max: 1, calculable: false, orient: 'horizontal', left: 'center', bottom: 18, inRange: { color: ['#1e3a8a', '#eff6ff', '#b91c1c'] } },
    series: [{ type: 'heatmap', data: analysis.value.correlation.matrix, label: { show: true, formatter: (params) => Number(params.data[2]).toFixed(2), color: '#0f172a' } }],
  }
})

const rowMissingOption = computed(() => analysis.value && ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 25, top: 20, bottom: 40 },
  xAxis: { type: 'category', data: analysis.value.row_missing_histogram.map((item) => `${item.missing}`), name: '单行缺失字段数' },
  yAxis: { type: 'value', name: '记录数' },
  series: [{ type: 'line', smooth: true, areaStyle: { color: 'rgba(249,115,22,0.18)' }, lineStyle: { color: '#ea580c', width: 3 }, data: analysis.value.row_missing_histogram.map((item) => item.count) }],
}))

const correlationPairsOption = computed(() => analysis.value && ({
  tooltip: { trigger: 'axis' },
  grid: { left: 170, right: 25, top: 15, bottom: 35 },
  xAxis: { type: 'value', min: -1, max: 1, name: '相关系数' },
  yAxis: { type: 'category', data: analysis.value.correlation_pairs.map((item) => item.pair).reverse() },
  series: [{
    type: 'bar',
    data: analysis.value.correlation_pairs.map((item) => Number(item.value.toFixed(3))).reverse(),
    itemStyle: {
      color: (params) => (params.value >= 0 ? '#2563eb' : '#dc2626'),
      borderRadius: [0, 6, 6, 0],
    },
    label: { show: true, position: 'right' },
  }],
}))

const outlierRateOption = computed(() => analysis.value && ({
  tooltip: { trigger: 'axis' },
  grid: { left: 110, right: 25, top: 15, bottom: 35 },
  xAxis: { type: 'value', name: '离群率%' },
  yAxis: { type: 'category', data: analysis.value.numeric_outlier_rates.map((item) => item.column).reverse() },
  series: [{
    type: 'bar',
    data: analysis.value.numeric_outlier_rates.map((item) => Number((item.rate * 100).toFixed(2))).reverse(),
    itemStyle: { color: '#7c3aed' },
    label: { show: true, position: 'right', formatter: (params) => `${params.value}%` },
  }],
}))
</script>

<template>
  <div v-if="analysis" class="page-stack">
    <DetailPageHeader
      fallback="/datasets"
      back-label="返回数据集列表"
      badge="数据质量报告"
      :title="analysis.name"
      subtitle="导入后自动生成的探索性数据分析与特征体检"
    >
      <template #meta>
        <span><strong>类型:</strong> {{ { training: '训练集', test: '测试集', validation: '验证集', inference: '推理集' }[analysis.dataset_type] || analysis.dataset_type || '-' }}</span>
        <span><strong>来源:</strong> {{ analysis.source_type === 'browser_upload' ? '浏览器上传' : '路径导入' }}</span>
        <span><strong>原文件:</strong> {{ analysis.original_filename || '-' }}</span>
        <span><strong>导入时间:</strong> {{ analysis.created_at ? new Date(analysis.created_at).toLocaleString('zh-CN', { hour12: false }) : '-' }}</span>
      </template>
    </DetailPageHeader>

    <section class="metrics-grid five">
      <MetricCard label="病例数量" :value="analysis.rows" note="数据记录总数" />
      <MetricCard label="字段数量" :value="analysis.columns" note="原始特征数量" tone="violet" />
      <MetricCard label="缺失单元格" :value="analysis.missing_total" note="建议训练前关注" tone="amber" />
      <MetricCard label="重复病例" :value="analysis.duplicate_rows" note="完全重复的记录" tone="green" />
      <MetricCard label="数值字段" :value="analysis.numeric_summary.length" note="可做相关性和分布分析" tone="navy" />
    </section>

    <section class="dashboard-grid">
      <ChartCard title="字段缺失情况" description="逐字段统计缺失值数量" :option="missingOption" />
      <ChartCard title="分类变量分布" description="选择字段查看类别频数" :option="distributionOption">
        <template #action>
          <select v-model="selectedCategory" class="chart-select">
            <option v-for="(_, name) in analysis.distributions" :key="name" :value="name">{{ name }}</option>
          </select>
        </template>
      </ChartCard>
    </section>

    <section class="dashboard-grid">
      <ChartCard title="数值字段频数分布" description="快速观察偏态、离散程度和集中区间" :option="histogramOption">
        <template #action>
          <select v-model="selectedNumeric" class="chart-select">
            <option v-for="(_, name) in analysis.numeric_histograms" :key="name" :value="name">{{ name }}</option>
          </select>
        </template>
      </ChartCard>
      <ChartCard title="箱线图" description="查看离群点范围、四分位数与中位数" :option="boxplotOption" />
    </section>

    <section class="dashboard-grid">
      <ChartCard title="小提琴近似图" description="用镜像分布查看密度形态，帮助识别长尾与多峰趋势" :option="violinOption" />
      <ChartCard title="行缺失分布" description="观察单条记录的缺失字段数量，识别整体数据完整性" :option="rowMissingOption" />
    </section>

    <ChartCard title="Pearson 相关系数热力图" description="数值特征之间的线性相关性，便于发现共线性和耦合关系" :option="correlationOption" height="440px" />

    <section class="dashboard-grid">
      <ChartCard title="字段唯一值概览" description="帮助快速识别高基数字段和低信息量字段" :option="{ tooltip:{trigger:'axis'}, grid:{left:110,right:25,top:15,bottom:35}, xAxis:{type:'value',name:'唯一值数量'}, yAxis:{type:'category',data:analysis.column_types.map(x=>x.column).reverse()}, series:[{type:'bar',data:analysis.column_types.map(x=>x.unique).reverse(), itemStyle:{color:'#7c3aed'}, label:{show:true,position:'right'}}] }" />
      <ChartCard title="缺失率排行" description="按字段缺失率排序，帮助优先治理高风险字段" :option="{ tooltip:{trigger:'axis'}, grid:{left:110,right:25,top:15,bottom:35}, xAxis:{type:'value',name:'缺失率%'}, yAxis:{type:'category',data:analysis.column_types.map(x=>x.column).reverse()}, series:[{type:'bar',data:analysis.column_types.map(x=>analysis.rows?Number(((x.missing/analysis.rows)*100).toFixed(2)):0).reverse(), itemStyle:{color:'#ea580c'}, label:{show:true,position:'right', formatter:(p)=>`${p.value}%`}}] }" />
    </section>

    <section class="dashboard-grid">
      <ChartCard title="强相关特征对" description="快速锁定相关性最高的字段组合，便于特征筛选和共线性判断" :option="correlationPairsOption" />
      <ChartCard title="离群率排行" description="使用 IQR 规则衡量异常值比例，发现需要进一步清洗的字段" :option="outlierRateOption" />
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>数值字段统计</h2>
          <p>均值、中位数、标准差与取值范围</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>字段</th><th>均值</th><th>中位数</th><th>标准差</th><th>最小值</th><th>最大值</th></tr></thead>
          <tbody>
            <tr v-for="row in analysis.numeric_summary" :key="row.column">
              <td><strong>{{ row.column }}</strong></td>
              <td>{{ row.mean.toFixed(2) }}</td>
              <td>{{ row.median.toFixed(2) }}</td>
              <td>{{ row.std.toFixed(2) }}</td>
              <td>{{ row.min.toFixed(2) }}</td>
              <td>{{ row.max.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-heading">
        <div>
          <h2>字段字典</h2>
          <p>自动识别字段类型、缺失值和唯一值数量</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>字段名</th><th>类型</th><th>缺失</th><th>唯一值</th></tr></thead>
          <tbody>
            <tr v-for="row in analysis.column_types" :key="row.column">
              <td>{{ row.column }}</td>
              <td>{{ row.type }}</td>
              <td>{{ row.missing }}</td>
              <td>{{ row.unique }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
