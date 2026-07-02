<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowUpRight, RefreshCw } from 'lucide-vue-next'
import { api } from '../api'
import { modelNames, statusNames } from '../modelNames'
const runs=ref([]),filter=ref('all')
const load=async()=>runs.value=(await api.get('/runs')).data
onMounted(load)
const shown=computed(()=>filter.value==='all'?runs.value:runs.value.filter(x=>x.status===filter.value))
const pct=v=>v==null?'—':(v*100).toFixed(1)+'%'
</script>
<template><div class="page-stack"><section class="panel"><div class="panel-heading"><div><h2>实验记录</h2><p>比较模型状态与测试集表现</p></div><button class="button ghost" @click="load"><RefreshCw :size="17"/>刷新</button></div><div class="filter-row" role="group" aria-label="状态筛选"><button v-for="item in [['all','全部'],['completed','已完成'],['training','训练中'],['failed','失败']]" :key="item[0]" :class="{active:filter===item[0]}" @click="filter=item[0]">{{item[1]}}</button></div><div v-if="shown.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>模型</th>
              <th>版本</th>
              <th>目标列</th>
              <th>测试集</th>
              <th>随机种子</th>
              <th>状态</th>
              <th>准确率</th>
              <th>F1分数</th>
              <th>曲线下面积</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in shown" :key="run.id">
              <td class="mono" style="font-size:12px;color:var(--muted-text)">{{run.id.slice(0,8)}}…</td>
              <td><strong>{{modelNames[run.model_name]}}</strong></td>
              <td class="mono">v{{ run.version_no || 1 }}</td>
              <td>{{ run.target_column || 'Outcome' }}</td>
              <td>{{ run.test_size || '0.2' }}</td>
              <td>{{ run.random_state || '42' }}</td>
              <td><span class="status-pill" :class="run.status">{{statusNames[run.status]}}</span></td>
              <td>{{pct(run.test_metrics?.accuracy)}}</td>
              <td>{{pct(run.test_metrics?.f1)}}</td>
              <td class="mono">{{run.test_metrics?.roc_auc?.toFixed(3)||'—'}}</td>
              <td>
                <RouterLink class="icon-link" :to="`/runs/${run.id}`" aria-label="查看结果"><ArrowUpRight/></RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div><div v-else class="empty-state">该筛选条件下暂无实验</div></section></div></template>
