# 生态指数计算器测试说明

## 问题修复总结

我们已经修复了以下主要问题：

### 1. **数组形状检查错误**
- 修复了 `ValueError('not enough values to unpack (expected 3, got 0)')` 错误
- 在所有数组访问前添加了完整的属性检查
- 使用 `hasattr()` 和 `is not None` 进行双重验证

### 2. **日志记录兼容性问题**
- 修复了 `AttributeError: '_Code' object has no attribute 'co_positions'` 错误
- 在 `celery.py` 中添加了Python版本兼容性检查
- 为老版本Python提供了兼容的日志格式化器

### 3. **资源管理改进**
- 改进了 `close()` 方法，添加了异常处理
- 确保所有资源都能被正确清理

### 4. **模型字段不匹配错误** ⭐ **新修复**
- 修复了 `TypeError: ProcessingTask() got unexpected keyword arguments: 'celery_task_id'` 错误
- 在 `tasks.py` 中移除了不存在的 `celery_task_id` 字段
- 确保模型创建时只使用已定义的字段

### 5. **DateTime字段类型错误** ⭐ **最新修复**
- 修复了 `fromisoformat: argument must be str` 错误
- 将 `time.time()` 替换为 `timezone.now()`
- 确保时间字段使用正确的Django datetime对象

### 6. **文件保存格式错误** ⭐ **最新修复**
- 修复了 `JPEG driver doesn't support data type Float32` 错误
- 在 `save_result` 方法中明确指定 `driver='GTiff'`
- 确保Float32数据类型能够正确保存为GeoTIFF格式

## 如何运行测试

### 方法1：测试生态指数计算器（推荐）

```bash
# 进入Django项目目录
cd tianshuipy/tianshuipy

# 运行测试脚本
python test_simple.py
```

### 方法2：测试任务修复

```bash
# 进入Django项目目录
cd tianshuipy/tianshuipy

# 运行任务修复测试
python test_tasks_fix.py
```

### 方法3：测试DateTime字段修复

```bash
# 进入Django项目目录
cd tianshuipy/tianshuipy

# 运行DateTime字段修复测试
python test_datetime_fix.py
```

### 方法4：测试文件保存修复

```bash
# 进入Django项目目录
cd tianshuipy/tianshuipy

# 运行文件保存修复测试
python test_save_result_fix.py
```

### 方法5：使用原始测试脚本

```bash
# 在项目根目录运行
cd tianshuipy
python test_fix.py
```

## 测试内容

### 生态指数计算器测试
测试脚本会验证以下功能：

1. **NDVI计算** - 归一化植被指数
2. **NDWI计算** - 归一化水体指数  
3. **NDBI计算** - 归一化建筑指数
4. **统计信息计算** - 基本统计量和分类统计
5. **资源管理** - 确保资源正确清理

### 任务修复测试
测试脚本会验证以下功能：

1. **模型字段检查** - 确认没有不存在的字段
2. **ProcessingTask创建** - 测试任务记录创建功能
3. **任务状态更新** - 测试任务状态管理
4. **函数导入检查** - 确认任务函数可正常导入

### DateTime字段修复测试
测试脚本会验证以下功能：

1. **timezone模块导入** - 确认Django timezone模块可用
2. **模型字段类型** - 检查时间字段的定义
3. **时间字段赋值** - 测试开始时间和完成时间的设置
4. **任务状态更新** - 验证完整的时间字段更新流程

### 文件保存修复测试
测试脚本会验证以下功能：

1. **GeoTIFF格式保存** - 确认Float32数据能正确保存
2. **不同数据类型** - 测试各种数据类型的保存兼容性
3. **元数据处理** - 验证元数据配置的正确性
4. **文件完整性** - 检查保存文件的完整性和可读性

## 预期输出

### 生态指数计算器测试输出

如果一切正常，您应该看到类似这样的输出：

```
==================================================
生态指数计算器测试
==================================================
✅ Django设置成功
✅ 导入生态指数计算器成功

开始测试基本功能...
测试数据形状: (3, 50, 50)

🔍 测试NDVI计算...
✅ NDVI计算成功
   形状: (50, 50)
   值范围: [-0.9999, 0.9999]

📊 测试统计信息计算...
✅ 统计信息计算成功
   最小值: -0.9999
   最大值: 0.9999
   平均值: 0.0000
   标准差: 0.5774

🌊 测试NDWI计算...
✅ NDWI计算成功，形状: (50, 50)

🏗️ 测试NDBI计算...
✅ NDBI计算成功，形状: (50, 50)

🎉 所有测试完成！
🧹 资源清理完成
```

### 任务修复测试输出

```
============================================================
Tasks.py 修复验证测试
============================================================
✅ Django设置成功
✅ 导入模块成功

🔍 测试模型定义...
检查ProcessingTask模型字段...
ProcessingTask字段: ['id', 'remote_sensing_image', 'task_type', 'status', 'progress', 'current_step', 'error_message', 'created_by', 'created_at', 'started_at', 'completed_at']
✅ 没有celery_task_id字段，符合预期

🔍 测试ProcessingTask创建功能...
找到 X 个遥感影像
使用测试影像: 微信图片_2025-08-22_105402_376.jpg (ID: a6ebc4bf-773c-4074-a06a-2ca6e75dda8c)

📝 测试创建ProcessingTask...
✅ ProcessingTask创建成功，ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

🔄 测试更新任务状态...
✅ 任务状态更新成功: 处理中

🧹 清理测试数据...
✅ 测试数据清理完成

🔍 测试任务函数基本功能...
检查calculate_ecological_indices函数...
✅ 函数存在: calculate_ecological_indices
检查calculate_rsei_only函数...
✅ 函数存在: calculate_rsei_only

检查函数属性...
calculate_ecological_indices.__name__: calculate_ecological_indices
calculate_rsei_only.__name__: calculate_rsei_only

============================================================
测试完成！
============================================================
```

### DateTime字段修复测试输出

```
============================================================
DateTime字段修复验证测试
============================================================
✅ Django设置成功
✅ 导入模块成功

🔍 测试timezone模块导入...
✅ timezone模块导入成功
   当前时间: 2025-08-26 10:30:00+08:00
   时间类型: <class 'django.utils.timezone.datetime'>
   是否为时区感知: True

🔍 测试模型字段定义...
检查ProcessingTask模型字段...
ProcessingTask字段: ['id', 'remote_sensing_image', 'task_type', 'status', 'progress', 'current_step', 'error_message', 'created_by', 'created_at', 'started_at', 'completed_at']
✅ created_at: DateTimeField - 创建时间
✅ started_at: DateTimeField - 开始时间
✅ completed_at: DateTimeField - 完成时间

🔍 测试datetime字段赋值...
找到 X 个遥感影像
使用测试影像: 微信图片_2025-08-22_105402_376.jpg (ID: a6ebc4bf-773c-4074-a06a-2ca6e75dda8c)

📝 测试创建ProcessingTask...
✅ ProcessingTask创建成功，ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

🕐 测试设置开始时间...
✅ 开始时间设置成功: 2025-08-26 10:30:00+08:00

✅ 测试设置完成时间...
✅ 完成时间设置成功: 2025-08-26 10:30:00+08:00

🔄 测试更新任务状态...
✅ 任务状态更新成功: 已完成

📊 最终任务信息:
   任务ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   任务类型: test_datetime_task
   状态: 已完成
   进度: 100%
   当前步骤: 测试完成
   创建时间: 2025-08-26 10:30:00+08:00
   开始时间: 2025-08-26 10:30:00+08:00
   完成时间: 2025-08-26 10:30:00+08:00

🧹 清理测试数据...
✅ 测试数据清理完成

============================================================
测试完成！
============================================================
```

### 文件保存修复测试输出

```
============================================================
Save Result 修复验证测试
============================================================
✅ Django设置成功
✅ 导入模块成功

🔍 测试save_result方法修复...

💾 测试保存结果...
✅ 结果保存成功: test_save_result.tif
   文件大小: 12345 字节
   读取成功，驱动: GTiff
   数据类型: float32
   形状: (100, 100)
   波段数: 1
🧹 测试文件已清理: test_save_result.tif

🔍 测试不同数据类型...

📊 测试 float32 类型...
   ✅ float32 保存成功
     文件大小: 6789 字节
     文件已清理

📊 测试 float64 类型...
   ✅ float64 保存成功
     文件大小: 13579 字节
     文件已清理

📊 测试 int16 类型...
   ✅ int16 保存成功
     文件大小: 3456 字节
     文件已清理

📊 测试 uint8 类型...
   ✅ uint8 保存成功
     文件大小: 2345 字节
     文件已清理

🔍 测试元数据处理...

📋 测试元数据配置 1: TEST
   ✅ 保存成功
     文件大小: 5678 字节
     文件已清理

📋 测试元数据配置 2: PNG
   ✅ 保存成功
     文件大小: 4567 字节
     文件已清理

============================================================
测试完成！
============================================================
```

## 故障排除

### 如果遇到Django设置错误：

1. 确保在正确的目录中运行脚本
2. 检查Django项目结构是否正确
3. 确保所有依赖包已安装

### 如果遇到模块导入错误：

1. 检查Python路径设置
2. 确保在正确的conda环境中运行
3. 验证所有依赖包版本兼容性

### 如果遇到模型字段错误：

1. 确保数据库迁移是最新的
2. 检查模型定义是否与数据库表结构一致
3. 验证代码中使用的字段名是否正确

### 如果遇到时间字段错误：

1. 确保使用 `django.utils.timezone.now()` 而不是 `time.time()`
2. 检查时间字段的类型定义
3. 验证时区设置是否正确

### 如果遇到文件保存错误：

1. 确保使用 `driver='GTiff'` 而不是默认的JPEG格式
2. 检查数据类型是否与格式兼容
3. 验证输出路径和权限设置

## 修复的问题详情

### ProcessingTask字段不匹配问题

**错误信息：**
```
TypeError: ProcessingTask() got unexpected keyword arguments: 'celery_task_id'
```

**原因：**
在 `tasks.py` 中尝试创建 `ProcessingTask` 时，传递了不存在的字段 `celery_task_id`。

**修复：**
- 从 `calculate_ecological_indices` 函数中移除 `celery_task_id=self.request.id`
- 从 `calculate_rsei_only` 函数中移除 `celery_task_id=self.request.id`
- 确保只使用模型中已定义的字段

**修复位置：**
- `tianshuipy/tianshuipy/environment/tasks.py` 第61行和第384行

### DateTime字段类型错误问题

**错误信息：**
```
fromisoformat: argument must be str
```

**原因：**
在 `tasks.py` 中使用 `time.time()` 返回浮点数时间戳，而 Django 的 `DateTimeField` 需要 `datetime` 对象。

**修复：**
- 将 `task.completed_at = time.time()` 替换为 `task.completed_at = timezone.now()`
- 在函数开头添加 `from django.utils import timezone`
- 确保所有时间字段都使用正确的 Django datetime 对象

**修复位置：**
- `tianshuipy/tianshuipy/environment/tasks.py` 第61行和第384行
- 影响字段：`completed_at`

### 文件保存格式错误问题

**错误信息：**
```
JPEG driver doesn't support data type Float32
```

**原因：**
在 `ecological_indices.py` 的 `save_result` 方法中，`rasterio.open()` 没有明确指定 driver，默认可能使用 JPEG 格式，但 JPEG 不支持 Float32 数据类型。

**修复：**
- 在 `save_result` 方法中添加 `output_meta['driver'] = 'GTiff'`
- 明确指定使用 GeoTIFF 格式，支持 Float32 数据类型
- 确保生态指数计算结果能够正确保存

**修复位置：**
- `tianshuipy/tianshuipy/environment/ecological_indices.py` 第 901 行
- 影响方法：`save_result`

## 下一步

测试成功后，您可以：

1. **启动Django服务器** 测试API接口
2. **启动Celery worker** 测试异步任务
3. **上传真实的遥感影像** 进行实际计算
4. **监控任务执行** 确保不再出现字段错误、时间类型错误和文件保存错误

## 联系支持

如果仍然遇到问题，请提供：
- 完整的错误信息
- 运行环境信息（Python版本、操作系统等）
- 当前工作目录
- 使用的测试脚本名称
