<script setup>
defineProps({ label: String, value: [String, Number], note: String, tone: { type: String, default: 'blue' } })
</script>
<template><article class="metric-card" :class="tone"><span>{{ label }}</span><strong>{{ value }}</strong><small>{{ note }}</small></article></template>
