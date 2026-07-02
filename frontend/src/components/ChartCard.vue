<script setup>
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, BoxplotChart, HeatmapChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
use([CanvasRenderer, BarChart, BoxplotChart, HeatmapChart, LineChart, GridComponent, LegendComponent, TooltipComponent, VisualMapComponent])
defineProps({ title: String, description: String, option: Object, height: { type: String, default: '320px' } })
</script>

<template>
  <section class="panel chart-card">
    <div class="panel-heading"><div><h2>{{ title }}</h2><p>{{ description }}</p></div><slot name="action" /></div>
    <VChart v-if="option" class="chart" :option="option" autoresize :style="{ height }" :aria-label="`${title}图表`" />
    <div v-else class="empty-state">暂无可绘制数据</div>
    <slot />
  </section>
</template>
