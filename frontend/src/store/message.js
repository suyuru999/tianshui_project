/**
 * 全局消息提示管理
 * 用于统一管理各种提示消息、通知等
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'

export const useMessageStore = defineStore('message', () => {
  // 消息队列
  const messageQueue = ref([])
  const notificationQueue = ref([])
  
  // 消息配置
  const defaultConfig = {
    duration: 3000,
    showClose: true,
    position: 'top-right'
  }
  
  // 成功消息
  function success(message, title = '成功', config = {}) {
    const finalConfig = { ...defaultConfig, ...config }
    
    // 显示Element Plus消息
    ElMessage.success({
      message,
      duration: finalConfig.duration,
      showClose: finalConfig.showClose
    })
    
    // 添加到队列
    messageQueue.value.push({
      type: 'success',
      message,
      title,
      timestamp: Date.now(),
      config: finalConfig
    })
    
    // 限制队列长度
    if (messageQueue.value.length > 100) {
      messageQueue.value.shift()
    }
  }
  
  // 错误消息
  function error(message, title = '错误', config = {}) {
    const finalConfig = { ...defaultConfig, ...config }
    
    // 显示Element Plus消息
    ElMessage.error({
      message,
      duration: finalConfig.duration,
      showClose: finalConfig.showClose
    })
    
    // 添加到队列
    messageQueue.value.push({
      type: 'error',
      message,
      title,
      timestamp: Date.now(),
      config: finalConfig
    })
  }
  
  // 警告消息
  function warning(message, title = '警告', config = {}) {
    const finalConfig = { ...defaultConfig, ...config }
    
    ElMessage.warning({
      message,
      duration: finalConfig.duration,
      showClose: finalConfig.showClose
    })
    
    messageQueue.value.push({
      type: 'warning',
      message,
      title,
      timestamp: Date.now(),
      config: finalConfig
    })
  }
  
  // 信息消息
  function info(message, title = '信息', config = {}) {
    const finalConfig = { ...defaultConfig, ...config }
    
    ElMessage.info({
      message,
      duration: finalConfig.duration,
      showClose: finalConfig.showClose
    })
    
    messageQueue.value.push({
      type: 'info',
      message,
      title,
      timestamp: Date.now(),
      config: finalConfig
    })
  }
  
  // 通知消息
  function notify(message, title = '通知', type = 'info', config = {}) {
    const finalConfig = { ...defaultConfig, ...config }
    
    ElNotification({
      title,
      message,
      type,
      duration: finalConfig.duration,
      position: finalConfig.position
    })
    
    notificationQueue.value.push({
      type,
      message,
      title,
      timestamp: Date.now(),
      config: finalConfig
    })
    
    // 限制通知队列长度
    if (notificationQueue.value.length > 50) {
      notificationQueue.value.shift()
    }
  }
  
  // 确认对话框
  function confirm(message, title = '确认', config = {}) {
    return new Promise((resolve) => {
      ElMessageBox.confirm(message, title, {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        ...config
      }).then(() => {
        resolve(true)
      }).catch(() => {
        resolve(false)
      })
    })
  }
  
  // 清空消息队列
  function clearMessages() {
    messageQueue.value = []
  }
  
  // 清空通知队列
  function clearNotifications() {
    notificationQueue.value = []
  }
  
  // 获取消息统计
  function getMessageStats() {
    const stats = {
      total: messageQueue.value.length,
      success: messageQueue.value.filter(m => m.type === 'success').length,
      error: messageQueue.value.filter(m => m.type === 'error').length,
      warning: messageQueue.value.filter(m => m.type === 'warning').length,
      info: messageQueue.value.filter(m => m.type === 'info').length
    }
    return stats
  }
  
  return {
    // 状态
    messageQueue,
    notificationQueue,
    
    // 方法
    success,
    error,
    warning,
    info,
    notify,
    confirm,
    clearMessages,
    clearNotifications,
    getMessageStats
  }
})
