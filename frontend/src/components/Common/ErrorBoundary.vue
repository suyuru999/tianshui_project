<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">
        <i class="el-icon-warning"></i>
      </div>
      <h3 class="error-title">{{ errorTitle }}</h3>
      <p class="error-message">{{ errorMessage }}</p>
      <div class="error-actions">
        <el-button type="primary" @click="retry">
          <i class="el-icon-refresh"></i>
          重试
        </el-button>
        <el-button @click="goBack">
          <i class="el-icon-back"></i>
          返回
        </el-button>
        <el-button @click="reportError">
          <i class="el-icon-message"></i>
          报告错误
        </el-button>
      </div>
      <div v-if="showDetails" class="error-details">
        <details>
          <summary>错误详情</summary>
          <pre class="error-stack">{{ errorStack }}</pre>
        </details>
      </div>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup>
import { ref, onErrorCaptured, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessageStore } from '@/store/message'

const props = defineProps({
  // 是否显示错误详情
  showDetails: {
    type: Boolean,
    default: false
  },
  // 自定义错误标题
  customTitle: {
    type: String,
    default: ''
  },
  // 自定义错误消息
  customMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['error', 'retry'])

const router = useRouter()
const messageStore = useMessageStore()

// 错误状态
const hasError = ref(false)
const error = ref(null)
const errorInfo = ref(null)

// 错误信息
const errorTitle = ref('页面出现错误')
const errorMessage = ref('抱歉，页面加载时出现了问题。请尝试刷新页面或联系技术支持。')
const errorStack = ref('')

// 捕获错误
onErrorCaptured((err, instance, info) => {
  console.error('ErrorBoundary caught an error:', err, instance, info)
  
  error.value = err
  errorInfo.value = info
  hasError.value = true
  
  // 设置错误信息
  if (props.customTitle) {
    errorTitle.value = props.customTitle
  }
  if (props.customMessage) {
    errorMessage.value = props.customMessage
  }
  
  // 生成错误堆栈
  if (err && err.stack) {
    errorStack.value = err.stack
  }
  
  // 发送错误事件
  emit('error', { error: err, info, instance })
  
  // 显示错误通知
  messageStore.error('页面出现错误，请查看错误详情')
  
  // 记录错误日志（可以发送到错误监控服务）
  logError(err, info, instance)
  
  return false // 阻止错误继续传播
})

// 重试
function retry() {
  hasError.value = false
  error.value = null
  errorInfo.value = null
  
  emit('retry')
  
  // 刷新当前页面
  window.location.reload()
}

// 返回上一页
function goBack() {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

// 报告错误
function reportError() {
  // 构建错误报告
  const errorReport = {
    timestamp: new Date().toISOString(),
    url: window.location.href,
    userAgent: navigator.userAgent,
    error: {
      name: error.value?.name,
      message: error.value?.message,
      stack: error.value?.stack
    },
    info: errorInfo.value,
    component: errorInfo.value?.componentName || 'Unknown'
  }
  
  // 这里可以发送错误报告到后端或错误监控服务
  console.log('Error Report:', errorReport)
  
  // 显示成功消息
  messageStore.success('错误报告已发送，感谢您的反馈！')
  
  // 可以打开错误报告表单
  // openErrorReportForm(errorReport)
}

// 记录错误日志
function logError(err, info, instance) {
  const errorLog = {
    timestamp: new Date().toISOString(),
    url: window.location.href,
    error: {
      name: err?.name,
      message: err?.message,
      stack: err?.stack
    },
    info,
    component: instance?.$options?.name || 'Unknown',
    userAgent: navigator.userAgent
  }
  
  // 发送到错误监控服务
  // sendErrorToMonitoring(errorLog)
  
  // 或者保存到本地存储
  try {
    const errorLogs = JSON.parse(localStorage.getItem('errorLogs') || '[]')
    errorLogs.push(errorLog)
    
    // 只保留最近100条错误记录
    if (errorLogs.length > 100) {
      errorLogs.splice(0, errorLogs.length - 100)
    }
    
    localStorage.setItem('errorLogs', JSON.stringify(errorLogs))
  } catch (e) {
    console.error('Failed to save error log:', e)
  }
}

// 组件挂载时检查是否有未处理的错误
onMounted(() => {
  // 监听全局错误
  window.addEventListener('error', (event) => {
    if (!hasError.value) {
      onErrorCaptured(event.error, null, { type: 'global', event })
    }
  })
  
  // 监听未处理的Promise拒绝
  window.addEventListener('unhandledrejection', (event) => {
    if (!hasError.value) {
      onErrorCaptured(new Error(event.reason), null, { type: 'unhandledrejection', event })
    }
  })
})
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 40px 20px;
  background: #fafafa;
}

.error-content {
  text-align: center;
  max-width: 500px;
  padding: 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 64px;
  color: #f56c6c;
  margin-bottom: 24px;
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
}

.error-message {
  font-size: 16px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 32px 0;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.error-details {
  margin-top: 24px;
  text-align: left;
}

.error-details summary {
  cursor: pointer;
  color: #409eff;
  font-weight: 500;
  margin-bottom: 12px;
}

.error-stack {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 6px;
  font-size: 12px;
  color: #606266;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .error-boundary {
    padding: 20px 10px;
  }
  
  .error-content {
    padding: 24px 16px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .error-actions .el-button {
    width: 100%;
    max-width: 200px;
  }
}
</style>
