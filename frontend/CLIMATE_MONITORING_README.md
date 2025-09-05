# 气候环境监测统计界面

## 功能概述

气候环境监测统计界面是一个用于上传、分析和可视化气候数据的Web应用程序。用户可以上传CSV或Excel格式的气候监测数据，系统将自动生成统计图表和数据分析报告。

## 主要功能

### 1. 文件上传
- 支持CSV和Excel格式文件
- 文件类型验证
- 上传进度显示
- 文件状态管理

### 2. 数据分析
- 自动数据解析
- 统计分析计算
- 多维度数据展示
- 实时分析状态监控

### 3. 数据可视化
- 温度趋势折线图
- 降水量柱状图
- 湿度变化面积图
- 风速雷达图

### 4. 统计报告
- 数据统计摘要表格
- 平均值、最大值、最小值、标准差
- 可下载的分析报告

## 使用方法

### 1. 访问界面
在浏览器中访问 `/climate-monitoring` 路由即可进入气候监测界面。

### 2. 上传数据文件
1. 点击"上传气候数据"按钮
2. 选择CSV或Excel格式的气候数据文件
3. 文件格式要求：
   - 必须包含以下列：日期、温度(°C)、降水量(mm)、湿度(%)、风速(m/s)
   - 日期格式：YYYY-MM-DD
   - 数值列应为数字格式

### 3. 开始分析
1. 确认文件已选择
2. 点击"开始分析"按钮
3. 等待分析完成（通常需要几秒钟）

### 4. 查看结果
分析完成后，界面将显示：
- 四个不同类型的图表
- 数据统计摘要表格
- 可下载的详细报告

## 示例数据

项目包含一个示例数据文件 `sample_climate_data.csv`，位于 `public` 目录下。您可以使用此文件测试界面功能。

## 技术特性

### 前端技术
- Vue 3 Composition API
- 响应式设计
- Canvas图表绘制
- 实时进度指示器

### 后端集成
- RESTful API接口
- 文件上传处理
- 异步任务管理
- 错误处理机制

### 演示模式
当后端服务不可用时，界面会自动切换到演示模式，使用模拟数据展示功能。

## 文件结构

```
frontend/src/views/ClimateMonitoring.vue  # 主界面组件
frontend/src/services/api.js              # API服务层
frontend/src/config/api.js                # API配置
frontend/public/sample_climate_data.csv   # 示例数据文件
```

## 自定义配置

### API端点配置
在 `src/config/api.js` 中配置后端API端点：

```javascript
CLIMATE_MONITORING: {
  UPLOAD: '/environment/climate-monitoring/upload/',
  ANALYZE: '/environment/climate-monitoring/analyze/',
  RESULTS: (taskId) => `/environment/climate-monitoring/results/${taskId}/`,
  STATUS: (taskId) => `/environment/climate-monitoring/status/${taskId}/`,
  DOWNLOAD_REPORT: (taskId) => `/environment/climate-monitoring/report/${taskId}/download/`
}
```

### 图表样式自定义
在 `ClimateMonitoring.vue` 的样式部分可以自定义图表颜色和样式。

## 错误处理

界面包含完善的错误处理机制：
- 文件格式验证
- 网络请求错误处理
- 分析失败提示
- 用户友好的错误消息

## 浏览器兼容性

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 开发说明

### 本地开发
1. 确保前端开发服务器运行
2. 访问 `http://localhost:3000/climate-monitoring`
3. 使用示例数据文件进行测试

### 生产部署
1. 配置正确的API端点
2. 确保后端服务正常运行
3. 构建并部署前端应用

## 未来扩展

- 支持更多数据格式
- 添加更多图表类型
- 实现数据导出功能
- 添加数据对比分析
- 支持多文件批量上传
