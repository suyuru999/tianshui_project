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
  getProfile() {
    return request.get(buildApiUrl(API_ENDPOINTS.AUTH.PROFILE))
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

// 导出所有服务
export default {
  auth: authService,
  remoteSensing: remoteSensingService,
  ecologicalIndices: ecologicalIndicesService,
  processingTask: processingTaskService,
  spatial: spatialService
}
