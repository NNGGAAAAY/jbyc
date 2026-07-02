<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ListOrdered, RefreshCw, Terminal } from 'lucide-vue-next'
import { api } from '../api';import { modelNames,statusNames } from '../modelNames'
const tasks=ref([]),selected=ref(null),logs=ref([]);let timer
async function load(){tasks.value=(await api.get('/tasks')).data;if(selected.value){selected.value=tasks.value.find(x=>x.id===selected.value.id)||selected.value;logs.value=(await api.get(`/tasks/${selected.value.id}/logs`)).data}}
async function select(task){selected.value=task;logs.value=(await api.get(`/tasks/${task.id}/logs`)).data}
async function priority(task,value){await api.patch(`/tasks/${task.id}/priority`,{priority:Number(value)});await load()}
onMounted(()=>{load();timer=setInterval(load,2000)});onBeforeUnmount(()=>clearInterval(timer))
const time=v=>v?new Date(v).toLocaleString('zh-CN'):'—'
</script>
<template><div class="page-stack"><section class="panel"><div class="panel-heading"><div><h2>异步训练队列</h2><p>优先级数值越高越先执行，同优先级按入队时间排序</p></div><button class="button ghost" @click="load"><RefreshCw :size="17"/>刷新</button></div><div class="table-wrap"><table><thead><tr><th>队列</th><th>模型</th><th>状态</th><th>优先级</th><th>创建时间</th><th>操作</th></tr></thead><tbody><tr v-for="task in tasks" :key="task.id"><td class="mono">{{task.queue_position?`第 ${task.queue_position} 位`:'—'}}</td><td>{{modelNames[task.model_name]}}</td><td><span class="status-pill" :class="task.status">{{statusNames[task.status]}}</span></td><td><select v-if="task.status==='queued'" :value="task.priority" class="priority-select" @change="priority(task,$event.target.value)"><option v-for="n in [0,1,2,3,4,5]" :key="n" :value="n">{{n}}</option></select><span v-else>{{task.priority}}</span></td><td>{{time(task.created_at)}}</td><td><button class="button ghost" @click="select(task)"><Terminal :size="16"/>查看日志</button></td></tr></tbody></table></div></section>
<section v-if="selected" class="panel"><div class="panel-heading"><div><h2>训练日志</h2><p>{{modelNames[selected.model_name]}} · 每 2 秒自动刷新</p></div></div><div class="log-console" aria-live="polite"><div v-for="log in logs" :key="log.id" :class="log.level"><time>{{new Date(log.created_at).toLocaleTimeString('zh-CN')}}</time><span>{{log.message}}</span></div><div v-if="!logs.length">暂无日志</div></div><RouterLink v-if="selected.run_id" class="button primary" :to="`/runs/${selected.run_id}`">查看训练结果</RouterLink></section></div></template>
