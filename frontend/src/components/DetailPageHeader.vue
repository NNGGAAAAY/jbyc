<script setup>
import BackLink from './BackLink.vue'

defineProps({
  fallback: { type: String, default: '/' },
  backLabel: { type: String, default: '返回上一页' },
  badge: { type: String, default: '' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  mono: { type: String, default: '' },
})
</script>

<template>
  <section class="detail-page-header">
    <BackLink :fallback="fallback" :label="backLabel" />
    <section class="detail-header">
      <div>
        <span v-if="badge" class="badge">{{ badge }}</span>
        <h2>{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
        <p v-if="mono" class="mono">{{ mono }}</p>
      </div>
      <div v-if="$slots.meta" class="detail-meta">
        <slot name="meta" />
      </div>
      <div v-if="$slots.action" class="detail-header-action">
        <slot name="action" />
      </div>
    </section>
  </section>
</template>
