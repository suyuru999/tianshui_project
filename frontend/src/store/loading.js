/**
 * 全局加载状态管理
 * 用于管理整个应用的加载状态、进度条等
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  // 全局加载状态
  const globalLoading = ref(false)
  const loadingText = ref('加载中...')
  
  // 页面级加载状态
  const pageLoading = ref(false)
  const pageLoadingText = ref('页面加载中...')
  
  // 操作级加载状态
  const operationLoading = ref(false)
  const operationLoadingText = ref('操作中...')
  
  // 进度条状态
  const progress = ref(0)
  const showProgress = ref(false)
  
  // 计算属性
  const isLoading = computed(() => globalLoading.value || pageLoading.value || operationLoading.value)
  
  // 全局加载控制
  function setGlobalLoading(loading, text = '加载中...') {
    globalLoading.value = loading
    loadingText.value = text
  }
  
  // 页面加载控制
  function setPageLoading(loading, text = '页面加载中...') {
    pageLoading.value = loading
    pageLoadingText.value = text
  }
  
  // 操作加载控制
  function setOperationLoading(loading, text = '操作中...') {
    operationLoading.value = loading
    operationLoadingText.value = text
  }
  
  // 进度条控制
  function setProgress(value, show = true) {
    progress.value = Math.max(0, Math.min(100, value))
    showProgress.value = show
  }
  
  // 重置所有状态
  function resetAll() {
    globalLoading.value = false
    pageLoading.value = false
    operationLoading.value = false
    progress.value = 0
    showProgress.value = false
  }
  
  // 异步操作包装器
  async function withLoading(asyncFn, loadingType = 'operation', text = '') {
    const loadingText = text || (loadingType === 'global' ? '加载中...' : 
                                 loadingType === 'page' ? '页面加载中...' : '操作中...')
    
    try {
      if (loadingType === 'global') {
        setGlobalLoading(true, loadingText)
      } else if (loadingType === 'page') {
        setPageLoading(true, loadingText)
      } else {
        setOperationLoading(true, loadingText)
      }
      
      const result = await asyncFn()
      return result
    } finally {
      if (loadingType === 'global') {
        setGlobalLoading(false)
      } else if (loadingType === 'page') {
        setPageLoading(false)
      } else {
        setOperationLoading(false)
      }
    }
  }
  
  return {
    // 状态
    globalLoading,
    loadingText,
    pageLoading,
    pageLoadingText,
    operationLoading,
    operationLoadingText,
    progress,
    showProgress,
    isLoading,
    
    // 方法
    setGlobalLoading,
    setPageLoading,
    setOperationLoading,
    setProgress,
    resetAll,
    withLoading
  }
})
