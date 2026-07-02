<script setup>
import { useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'

const props = defineProps({
  label: { type: String, default: '返回上一页' },
  fallback: { type: String, default: '/' },
})

const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push(props.fallback)
}
</script>

<template>
  <button class="back-link" type="button" @click="goBack">
    <ArrowLeft :size="16" />
    <span>{{ label }}</span>
  </button>
</template>
