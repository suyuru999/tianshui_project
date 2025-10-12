/**
 * API配置文件
 * 定义所有后端接口的URL和配置
 */

// API基础配置
export const API_CONFIG = {
  // 基础URL
  // 使用localhost绕过DNS重定向问题
  BASE_URL: 'http://localhost:8000/api',
  
  // 版本
  VERSION: 'v1',
  
  // 超时时间（增加到2分钟）
  TIMEOUT: 120000,
  
  // 请求头
  HEADERS: {
    'Content-Type': 'application/json',
  }
}

// API端点配置
export const API_ENDPOINTS = {
  // 用户认证
  AUTH: {
    LOGIN: '/users/login/',
    LOGOUT: '/users/logout/',
    REGISTER: '/users/register/',
    PROFILE: '/users/profile/',
    REFRESH_TOKEN: '/users/token/refresh/',
  },
  
  // 遥感影像管理
  REMOTE_SENSING: {
    LIST: '/environment/remote-sensing-images/',
    UPLOAD: '/environment/remote-sensing-images/',
    DETAIL: (id) => `/environment/remote-sensing-images/${id}/`,
    DELETE: (id) => `/environment/remote-sensing-images/${id}/`,
    UPDATE: (id) => `/environment/remote-sensing-images/${id}/`,
    CALCULATE_INDICES: (id) => `/environment/remote-sensing-images/${id}/calculate_indices/`,
    GET_INDICES: (id) => `/environment/remote-sensing-images/${id}/indices/`,
  },
  
  // 生态指数计算
  ECOLOGICAL_INDICES: {
    LIST: '/environment/ecological-indices/',
    CREATE: '/environment/ecological-indices/',
    DETAIL: (id) => `/environment/ecological-indices/${id}/`,
    CALCULATE: '/environment/ecological-indices/calculate/',
    RSEI_CALCULATE: '/environment/rsei-results/calculate/',
    // 新增：生态环境结构指数计算
    STRUCTURE_INDICES: '/environment/ecological-structure-indices/',
    // 新增：生态环境胁迫指数计算
    STRESS_INDICES: '/environment/ecological-stress-indices/',
  },
  
  // 处理任务
  PROCESSING_TASKS: {
    LIST: '/environment/processing-tasks/',
    CREATE: '/environment/processing-tasks/',
    DETAIL: (id) => `/environment/processing-tasks/${id}/`,
    STATUS: (id) => `/environment/processing-tasks/${id}/status/`,
  },
  
  // 地理空间服务
  SPATIAL: {
    WMS_CAPABILITIES: '/environment/spatial/wms/capabilities/',
    WMS_MAP: '/environment/spatial/wms/map/',
    WFS_CAPABILITIES: '/environment/spatial/wfs/capabilities/',
    SPATIAL_LAYERS: '/environment/spatial/layers/',
    PUBLISH_TO_GEOSERVER: '/environment/spatial/publish/',
    GEOSERVER_STATUS: '/environment/spatial/geoserver/status/',
  },

  // 民众意见反馈
  FEEDBACK: {
    CREATE: '/environment/feedback/',
    LIST: '/environment/feedback/',
    DETAIL: (id) => `/environment/feedback/${id}/`
  },
  
  // 气候监测统计
  CLIMATE_MONITORING: {
    UPLOAD: '/environment/climate-monitoring/upload/',
    ANALYZE: '/environment/climate-monitoring/analyze/',
    RESULTS: (taskId) => `/environment/climate-monitoring/results/${taskId}/`,
    STATUS: (taskId) => `/environment/processing-tasks/${taskId}/status/`,
    DOWNLOAD_REPORT: (taskId) => `/environment/climate-monitoring/report/${taskId}/download/`
  }
}

// 构建完整的API URL
export function buildApiUrl(endpoint) {
  return `${API_CONFIG.BASE_URL}/${API_CONFIG.VERSION}${endpoint}`
}

// 获取所有API URL
export function getAllApiUrls() {
  const urls = {}
  
  // 遍历所有端点，构建完整URL
  Object.keys(API_ENDPOINTS).forEach(category => {
    urls[category] = {}
    Object.keys(API_ENDPOINTS[category]).forEach(key => {
      const endpoint = API_ENDPOINTS[category][key]
      if (typeof endpoint === 'function') {
        urls[category][key] = endpoint
      } else {
        urls[category][key] = buildApiUrl(endpoint)
      }
    })
  })
  
  return urls
}

export default {
  API_CONFIG,
  API_ENDPOINTS,
  buildApiUrl,
  getAllApiUrls
} 