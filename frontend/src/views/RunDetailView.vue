<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Download } from 'lucide-vue-next'
import { api } from '../api'
import ChartCard from '../components/ChartCard.vue'; import MetricCard from '../components/MetricCard.vue'
import DetailPageHeader from '../components/DetailPageHeader.vue'
import { modelNames, statusNames } from '../modelNames'
const route=useRoute();const run=ref(null);const loading=ref(true);onMounted(async()=>{run.value=(await api.get(`/runs/${route.params.id}`)).data;loading.value=false})
const metrics=computed(()=>run.value?.test_metrics||{})
const rocOption=computed(()=>run.value&&({tooltip:{trigger:'axis'},legend:{data:['训练集','测试集'],bottom:0},grid:{left:52,right:20,top:24,bottom:55},xAxis:{type:'value',min:0,max:1,name:'假阳性率 FPR'},yAxis:{type:'value',min:0,max:1,name:'真阳性率 TPR'},series:[['训练集',run.value.train_roc],['测试集',run.value.test_roc]].map(([name,d],i)=>({name,type:'line',showSymbol:false,data:d.fpr.map((x,k)=>[x,d.tpr[k]]),lineStyle:{width:3,type:i?'solid':'dashed'},itemStyle:{color:i?'#d97706':'#1e40af'}})).concat([{name:'随机基线',type:'line',data:[[0,0],[1,1]],symbol:'none',lineStyle:{color:'#94a3b8',type:'dotted'}}])}))
const matrixOption=computed(()=>run.value&&({tooltip:{formatter:p=>`真实 ${p.data[1]} / 预测 ${p.data[0]}：${p.data[2]}`},grid:{left:70,right:60,top:25,bottom:55},xAxis:{type:'category',data:['预测 0','预测 1']},yAxis:{type:'category',data:['真实 0','真实 1']},visualMap:{min:0,max:Math.max(...run.value.test_confusion_matrix.flat()),calculable:false,orient:'horizontal',left:'center',bottom:0,inRange:{color:['#eff6ff','#1e40af']}},series:[{type:'heatmap',data:run.value.test_confusion_matrix.flatMap((row,y)=>row.map((v,x)=>[x,y,v])),label:{show:true,color:'#0f172a',fontSize:16,fontWeight:700}}]}))
const shapOption=computed(()=>{if(!run.value?.shap)return null;const rows=run.value.shap.feature_names.map((name,i)=>({name:name.replace(/^(numeric|categorical)__/,'').replace(/^.*?__/,'') ,value:run.value.shap.mean_abs_shap[i]})).sort((a,b)=>b.value-a.value).slice(0,12).reverse();return{tooltip:{trigger:'axis'},grid:{left:150,right:30,top:15,bottom:35},xAxis:{type:'value',name:'平均 |SHAP|'},yAxis:{type:'category',data:rows.map(x=>x.name)},series:[{type:'bar',data:rows.map(x=>x.value),itemStyle:{color:'#3b82f6',borderRadius:[0,5,5,0]},label:{show:true,position:'right',formatter:p=>Number(p.value).toFixed(3)}}]}})
function exportJson(){const blob=new Blob([JSON.stringify(run.value,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`run-${run.value.id}.json`;a.click();URL.revokeObjectURL(a.href)}
</script>
<template><div v-if="loading" class="skeleton-page"><div v-for="i in 6" :key="i" class="skeleton"></div></div><div v-else-if="run" class="page-stack">
  <DetailPageHeader
    fallback="/runs"
    back-label="返回实验记录"
    :title="`${modelNames[run.model_name]}实验`"
    :mono="run.id"
  >
    <template #meta>
      <span class="status-pill" :class="run.status">{{statusNames[run.status]}}</span>
      <span v-if="run.target_column"><strong>目标列:</strong> {{ run.target_column }}</span>
      <span v-if="run.test_size"><strong>测试集比例:</strong> {{ run.test_size }}</span>
      <span v-if="run.random_state"><strong>随机种子:</strong> {{ run.random_state }}</span>
    </template>
    <template #action>
      <button class="button secondary" @click="exportJson"><Download :size="17"/>导出原始数据</button>
    </template>
  </DetailPageHeader>
  <section class="metrics-grid five"><MetricCard label="准确率" :value="metrics.accuracy?.toFixed(3)" note="预测正确的比例"/><MetricCard label="精确率" :value="metrics.precision?.toFixed(3)" note="阳性预测可靠程度" tone="violet"/><MetricCard label="召回率" :value="metrics.recall?.toFixed(3)" note="阳性病例检出比例" tone="green"/><MetricCard label="F1分数" :value="metrics.f1?.toFixed(3)" note="精确率与召回率调和" tone="amber"/><MetricCard label="曲线下面积" :value="metrics.roc_auc?.toFixed(3)" note="概率排序能力" tone="navy"/></section>
  <section class="dashboard-grid"><ChartCard title="ROC 曲线" description="训练集与测试集概率判别表现" :option="rocOption"/><ChartCard title="测试集混淆矩阵" description="行是真实类别，列是预测类别" :option="matrixOption"/></section>
  <ChartCard title="SHAP 全局特征重要性" description="平均绝对 SHAP 值越高，对模型输出的总体影响越大" :option="shapOption" height="430px"/>
  <section class="panel"><div class="panel-heading"><div><h2>训练集 / 测试集指标对照</h2><p>识别过拟合和泛化差距</p></div></div><div class="table-wrap"><table><thead><tr><th>数据分区</th><th>准确率</th><th>精确率</th><th>召回率</th><th>F1分数</th><th>曲线下面积</th></tr></thead><tbody><tr v-for="key in ['train','test']" :key="key"><td><strong>{{key==='train'?'训练集':'测试集'}}</strong></td><td v-for="metric in ['accuracy','precision','recall','f1','roc_auc']" :key="metric" class="mono">{{run[`${key}_metrics`][metric].toFixed(3)}}</td></tr></tbody></table></div></section>
</div></template>
