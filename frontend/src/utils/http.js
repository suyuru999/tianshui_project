/**
 * HTTP请求工具
 * 基于axios封装，处理认证、错误、拦截器等
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { API_CONFIG } from '../config/api.js'

// 创建axios实例
const http = axios.create({
  // 使用API配置中的完整URL
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: API_CONFIG.HEADERS,
  withCredentials: true, // 支持跨域携带cookie
})

// 从 cookie 读取 csrftoken（适用于 Django）
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

// 请求拦截器
http.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    
    // 为非安全方法自动附带 CSRF Token（Django SessionAuthentication 需要）
    const method = (config.method || 'get').toLowerCase()
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      const csrfToken = getCookie('csrftoken')
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
      // 提示后端这是XHR请求（某些中间件会用到）
      config.headers['X-Requested-With'] = 'XMLHttpRequest'
    }

    // 添加请求时间戳
    config.headers['X-Request-Time'] = Date.now()
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  (response) => {
    // 直接返回响应数据
    return response.data
  },
  (error) => {
    // 错误处理
    const { response } = error
    
    if (response) {
      const { status, data } = response
      
      switch (status) {
        case 400:
          ElMessage.error(data.error || '请求参数错误')
          break
        case 401:
          ElMessage.error('未授权，请重新登录')
          // 清除token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data.error || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

// 通用请求方法
export const request = {
  // GET请求
  get(url, params = {}, config = {}) {
    return http.get(url, { params, ...config })
  },
  
  // POST请求
  post(url, data = {}, config = {}) {
    return http.post(url, data, config)
  },
  
  // PUT请求
  put(url, data = {}, config = {}) {
    return http.put(url, data, config)
  },
  
  // DELETE请求
  delete(url, config = {}) {
    return http.delete(url, config)
  },
  
  // 文件上传
  upload(url, formData, config = {}) {
    return http.post(url, formData, {
      // 不手动设置Content-Type，让浏览器自动设置boundary
      headers: {
        // 移除默认的Content-Type，让浏览器自动设置multipart/form-data
        'Content-Type': undefined,
      },
      ...config,
    })
  },
  
  // 文件下载
  download(url, params = {}, filename = 'download') {
    return http.get(url, {
      params,
      responseType: 'blob',
    }).then((data) => {
      const blob = new Blob([data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.URL.revokeObjectURL(url)
    })
  }
}

// 导出axios实例和请求方法
export { http }
export default request
