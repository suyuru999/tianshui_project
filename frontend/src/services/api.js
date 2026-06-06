/**
 * API服务层
 * 封装所有后端接口的调用方法
 */

import request from '../utils/http.js'
import { API_ENDPOINTS, buildApiUrl } from '../config/api.js'

// 用户认证服务
export const authService = {
  // 用户登录
  login(credentials) {
    return request.post(buildApiUrl(API_ENDPOINTS.AUTH.LOGIN), credentials)
  },
  
  // 用户注册
  register(userData) {
    return request.post(buildApiUrl(API_ENDPOINTS.AUTH.REGISTER), userData)
  },
  
  // 获取用户信息
  getProfile(config = {}) {
    return request.get(buildApiUrl(API_ENDPOINTS.AUTH.PROFILE), {}, config)
  },
  
  // 用户登出
  logout() {
    return request.post(buildApiUrl(API_ENDPOINTS.AUTH.LOGOUT))
  },
  
  // 刷新token
  refreshToken() {
    return request.post(buildApiUrl(API_ENDPOINTS.AUTH.REFRESH_TOKEN))
  }
}

// 遥感影像服务
export const remoteSensingService = {
  // 获取影像列表
  getList(params = {}) {
    return request.get(buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.LIST), params)
  },
  
  // 上传影像
  upload(file, metadata = {}) {
    const formData = new FormData()
    formData.append('file', file)  // 改为'file'而不是'file_path'
    
    // 添加其他元数据
    Object.keys(metadata).forEach(key => {
      formData.append(key, metadata[key])
    })
    
    // 确保路径以斜杠开头，避免相对路径问题
    const url = buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.UPLOAD);
    console.log('上传请求URL:', url);
    return request.upload(url, formData)
  },
  
  // 获取影像详情
  getDetail(id) {
    return request.get(buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.DETAIL(id)))
  },
  
  // 更新影像信息
  update(id, data) {
    return request.put(buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.UPDATE(id)), data)
  },
  
  // 删除影像
  delete(id) {
    return request.delete(buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.DELETE(id)))
  },
  
  // 计算生态指数
  calculateIndices(imageId, indices = ['ndvi', 'ndwi', 'ndbi']) {
    const url = buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.CALCULATE_INDICES(imageId));
    const data = { indices: indices };

    console.log('calculateIndices 调用详情:', {
      url: url,
      data: data,
      imageId: imageId,
      indices: indices
    });

    return request.post(url, data)
  },

  // 获取影像的生态指数结果
  getIndices(imageId) {
    const url = buildApiUrl(API_ENDPOINTS.REMOTE_SENSING.GET_INDICES(imageId));
    console.log('getIndices 调用详情:', {
      url: url,
      imageId: imageId
    });
    return request.get(url)
  }
}

// 生态指数服务
export const ecologicalIndicesService = {
  // 获取指数列表
  getList(params = {}) {
    return request.get(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.LIST), params)
  },
  
  // 创建指数计算任务
  create(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.CREATE), data)
  },
  
  // 获取指数详情
  getDetail(id) {
    return request.get(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.DETAIL(id)))
  },
  
  // 计算生态指数
  calculate(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.CALCULATE), data)
  },
  
  // 计算RSEI
  calculateRSEI(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.ECOLOGICAL_INDICES.RSEI_CALCULATE), data)
  }
}

// 处理任务服务
export const processingTaskService = {
  // 获取任务列表
  getList(params = {}) {
    return request.get(buildApiUrl(API_ENDPOINTS.PROCESSING_TASKS.LIST), params)
  },
  
  // 创建任务
  create(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.PROCESSING_TASKS.CREATE), data)
  },
  
  // 获取任务详情
  getDetail(id) {
    return request.get(buildApiUrl(API_ENDPOINTS.PROCESSING_TASKS.DETAIL(id)))
  },
  
  // 获取任务状态
  getStatus(id) {
    return request.get(buildApiUrl(API_ENDPOINTS.PROCESSING_TASKS.STATUS(id)))
  }
}

// 地理空间服务
export const spatialService = {
  // 获取WMS服务能力
  getWMSCapabilities() {
    return request.get(buildApiUrl(API_ENDPOINTS.SPATIAL.WMS_CAPABILITIES))
  },
  
  // WMS地图服务
  getWMSMap(params) {
    return request.get(buildApiUrl(API_ENDPOINTS.SPATIAL.WMS_MAP), params)
  },
  
  // 获取WFS服务能力
  getWFSCapabilities() {
    return request.get(buildApiUrl(API_ENDPOINTS.SPATIAL.WFS_CAPABILITIES))
  },
  
  // 获取空间图层列表
  getSpatialLayers() {
    return request.get(buildApiUrl(API_ENDPOINTS.SPATIAL.SPATIAL_LAYERS))
  },
  
  // 发布图层到GeoServer
  publishToGeoServer(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.SPATIAL.PUBLISH_TO_GEOSERVER), data)
  },
  
  // 获取GeoServer状态
  getGeoServerStatus() {
    return request.get(buildApiUrl(API_ENDPOINTS.SPATIAL.GEOSERVER_STATUS))
  }
}

// 民众意见反馈服务
export const feedbackService = {
  // 提交反馈
  create(data) {
    return request.post(buildApiUrl(API_ENDPOINTS.FEEDBACK.CREATE), data)
  },
  // 获取反馈列表（可选：管理员查看）
  getList(params = {}) {
    return request.get(buildApiUrl(API_ENDPOINTS.FEEDBACK.LIST), params)
  },
  // 获取反馈详情
  getDetail(id) {
    return request.get(buildApiUrl(API_ENDPOINTS.FEEDBACK.DETAIL(id)))
  }
}

// 气候监测服务
export const climateMonitoringService = {
  // 上传气候数据文件
  uploadClimateData(file, metadata = {}) {
    // 验证文件
    if (!file) {
      return Promise.reject(new Error('文件不能为空'))
    }
    
    if (!(file instanceof File)) {
      return Promise.reject(new Error('无效的文件对象'))
    }
    
    // 验证文件大小（50MB限制）
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      return Promise.reject(new Error('文件大小不能超过50MB'))
    }
    
    // 验证文件类型
    const allowedTypes = ['.csv', '.xlsx', '.xls']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    if (!allowedTypes.includes(fileExtension)) {
      return Promise.reject(new Error('只支持CSV和Excel格式文件'))
    }
    
    const formData = new FormData()
    formData.append('file', file)
    
    // 添加元数据
    Object.keys(metadata).forEach(key => {
      if (metadata[key] !== null && metadata[key] !== undefined) {
        formData.append(key, metadata[key])
      }
    })
    
    return request.upload(buildApiUrl(API_ENDPOINTS.CLIMATE_MONITORING.UPLOAD), formData)
  },
  
  // 开始气候数据分析
  analyzeClimateData(fileId, analysisType = 'comprehensive') {
    // 验证文件ID
    if (!fileId) {
      return Promise.reject(new Error('文件ID不能为空'))
    }
    
    if (typeof fileId !== 'string' && typeof fileId !== 'number') {
      return Promise.reject(new Error('文件ID格式无效'))
    }
    
    // 验证分析类型
    const validAnalysisTypes = ['comprehensive', 'temperature', 'precipitation', 'humidity', 'wind', 'wind_speed']
    if (!validAnalysisTypes.includes(analysisType)) {
      return Promise.reject(new Error(`无效的分析类型: ${analysisType}`))
    }
    const normalizedAnalysisType = analysisType === 'wind_speed' ? 'wind' : analysisType
    
    return request.post(buildApiUrl(API_ENDPOINTS.CLIMATE_MONITORING.ANALYZE), {
      file_id: fileId,
      analysis_type: normalizedAnalysisType
    })
  },
  
  // 获取分析结果
  getAnalysisResults(taskId) {
    // 验证任务ID
    if (!taskId) {
      return Promise.reject(new Error('任务ID不能为空'))
    }
    
    if (typeof taskId !== 'string' && typeof taskId !== 'number') {
      return Promise.reject(new Error('任务ID格式无效'))
    }
    
    return request.get(buildApiUrl(API_ENDPOINTS.CLIMATE_MONITORING.RESULTS(taskId)))
  },
  
  // 获取分析状态
  getAnalysisStatus(taskId) {
    // 验证任务ID
    if (!taskId) {
      return Promise.reject(new Error('任务ID不能为空'))
    }
    
    if (typeof taskId !== 'string' && typeof taskId !== 'number') {
      return Promise.reject(new Error('任务ID格式无效'))
    }
    
    return request.get(buildApiUrl(API_ENDPOINTS.CLIMATE_MONITORING.STATUS(taskId)))
  },
  
  // 下载分析报告
  downloadReport(taskId) {
    // 验证任务ID
    if (!taskId) {
      return Promise.reject(new Error('任务ID不能为空'))
    }
    
    if (typeof taskId !== 'string' && typeof taskId !== 'number') {
      return Promise.reject(new Error('任务ID格式无效'))
    }
    
    return request.download(buildApiUrl(API_ENDPOINTS.CLIMATE_MONITORING.DOWNLOAD_REPORT(taskId)))
  }
}

// 导出所有服务
export default {
  auth: authService,
  remoteSensing: remoteSensingService,
  ecologicalIndices: ecologicalIndicesService,
  processingTask: processingTaskService,
  spatial: spatialService,
  feedback: feedbackService,
  climateMonitoring: climateMonitoringService
}
