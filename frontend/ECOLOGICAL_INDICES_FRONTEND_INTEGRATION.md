# 前端生态环境指数API集成说明

## 概述

本文档说明了如何在前端生态环境评估页面中集成新的生态环境指数计算API。

## 已集成的功能

### 1. **生态环境结构指数**
- ✅ 破碎度指数 (`fragmentation_index`)
- ✅ 内聚力指数 (`cohesion_index`)
- ✅ 多样性指数 (`shannon_diversity`)
- ✅ 脆弱度指数 (`fragility_index`)

### 2. **生态环境胁迫指数**
- ✅ 土壤侵蚀指数 (`soil_erosion_index`)
- ✅ 未利用地面积比例 (`unused_land_proportion`)
- ✅ 耕地建设用地面积比例 (`cultivated_construction_proportion`)
- ✅ 土地退化指数 (`land_degradation_index`)

## API端点配置

### 新增的API端点

```javascript
// 在 frontend/src/config/api.js 中新增
ECOLOGICAL_INDICES: {
  // ... 现有端点
  STRUCTURE_INDICES: '/environment/ecological-structure-indices/',
  STRESS_INDICES: '/environment/ecological-stress-indices/',
}
```

### API调用方式

#### 1. **批量计算所有指数**
```javascript
// 点击"开始分析"按钮时调用
const startAnalysis = async () => {
  const formData = new FormData()
  formData.append('landuse_file', file)
  
  // 计算生态环境结构指数
  const structureResponse = await http.post(
    API_ENDPOINTS.ECOLOGICAL_INDICES.STRUCTURE_INDICES, 
    formData
  )
  
  // 计算生态环境胁迫指数
  const stressResponse = await http.post(
    API_ENDPOINTS.ECOLOGICAL_INDICES.STRESS_INDICES, 
    formData
  )
  
  // 合并结果
  Object.assign(indexResults, structureResponse.summary, stressResponse.summary)
}
```

#### 2. **单独计算特定指数**
```javascript
// 点击单个指数按钮时调用
const calculateIndex = async (indexKey) => {
  const formData = new FormData()
  formData.append('landuse_file', file)
  
  // 根据指数类型选择API端点
  const apiEndpoint = structureIndices.find(i => i.key === indexKey) 
    ? API_ENDPOINTS.ECOLOGICAL_INDICES.STRUCTURE_INDICES
    : API_ENDPOINTS.ECOLOGICAL_INDICES.STRESS_INDICES
  
  const response = await http.post(apiEndpoint, formData)
  
  // 更新结果
  if (response.summary && response.summary[index.apiKey]) {
    indexResults[index.apiKey] = response.summary[index.apiKey]
    index.calculated = true
  }
}
```

## 数据结构

### 指数定义结构
```javascript
const structureIndices = reactive([
  { 
    key: 'fragmentation',           // 前端使用的键名
    name: '破碎度指数',             // 显示名称
    calculated: false,              // 是否已计算
    loading: false,                 // 是否正在计算
    apiKey: 'fragmentation_index'  // API返回结果中的键名
  }
])
```

### API返回结果结构
```javascript
// 生态环境结构指数API返回
{
  "message": "生态环境结构指数计算完成",
  "results": { ... },
  "summary": {
    "fragmentation_index": 0.1234,
    "cohesion_index": 85.67,
    "shannon_diversity": 1.2345,
    "fragility_index": 0.4567
  }
}

// 生态环境胁迫指数API返回
{
  "message": "生态环境胁迫指数计算完成",
  "results": { ... },
  "summary": {
    "soil_erosion_index": 0.3456,
    "unused_land_proportion": 15.67,
    "cultivated_construction_proportion": 45.23,
    "land_degradation_index": 0.5678
  }
}
```

## 用户界面功能

### 1. **文件上传**
- 支持 GeoTIFF (.tif, .tiff) 和 Shapefile (.shp, .dbf, .shx, .prj) 格式
- 文件验证和错误提示
- 上传状态显示

### 2. **指数计算**
- **批量计算**: 点击"开始分析"按钮计算所有指数
- **单独计算**: 点击单个指数按钮计算特定指数
- 计算状态显示（加载中、已完成、失败）
- 实时进度反馈

### 3. **结果展示**
- **数值显示**: 每个指数的计算结果和单位
- **状态评估**: 根据数值范围显示"良好"、"一般"、"较差"
- **图表可视化**: 
  - 雷达图：显示所有指数的相对关系
  - 柱状图：对比不同指数的数值
- **下载功能**: 将计算结果导出为JSON文件

### 4. **响应式设计**
- 支持桌面端和移动端
- 自适应布局
- 触摸友好的交互

## 使用方法

### 1. **上传数据文件**
1. 点击"上传影像数据"按钮
2. 选择土地利用数据文件（.tif 或 .shp 格式）
3. 确认文件格式正确

### 2. **计算生态环境指数**
- **方式一**: 点击"开始分析"按钮，一次性计算所有指数
- **方式二**: 点击单个指数按钮，单独计算特定指数

### 3. **查看结果**
- 在右侧面板查看计算结果
- 查看雷达图和柱状图
- 下载结果文件

## 错误处理

### 1. **文件格式错误**
- 只支持指定的地理数据格式
- 显示友好的错误提示

### 2. **API调用失败**
- 网络错误处理
- 服务器错误处理
- 用户友好的错误消息

### 3. **数据验证**
- 检查API返回结果格式
- 验证必要字段是否存在

## 技术特点

### 1. **性能优化**
- 异步API调用
- 防抖和节流处理
- 图表懒加载

### 2. **用户体验**
- 实时状态反馈
- 加载动画
- 错误提示和恢复

### 3. **代码质量**
- 模块化设计
- 错误边界处理
- 类型安全

## 注意事项

### 1. **文件大小限制**
- 建议上传文件大小不超过100MB
- 大文件可能需要较长处理时间

### 2. **数据格式要求**
- 土地利用数据必须包含正确的分类信息
- 坐标系统应该与系统要求一致

### 3. **网络要求**
- 需要稳定的网络连接
- API调用可能需要几秒到几分钟不等

## 扩展功能

### 1. **历史记录**
- 保存计算历史
- 结果对比功能

### 2. **批量处理**
- 支持多个文件同时处理
- 批量结果导出

### 3. **高级分析**
- 时间序列分析
- 空间统计分析
- 趋势预测

## 总结

前端生态环境指数API集成已经完成，提供了完整的用户界面和功能。用户可以：

1. 上传土地利用数据文件
2. 计算多种生态环境指数
3. 查看计算结果和可视化图表
4. 下载分析结果

系统具有良好的用户体验、错误处理和响应式设计，可以满足不同用户的需求。
