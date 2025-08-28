# 波段索引越界错误修复和调试改进

## 问题分析

根据错误日志分析：
```
[ERROR] 计算NDVI失败: index 4 is out of bounds for axis 0 with size 4
File "...ecological_indices.py", line 161, in calculate_ndvi ... nir_band = self.bands[4] # B5
```

**问题描述：**
- 您的图像有4个波段（索引0-3）
- 代码试图访问 `self.bands[4]`（第5个波段）
- 这导致了 `IndexError: index 4 is out of bounds for axis 0 with size 4`

**根本原因：**
代码中存在硬编码的波段索引，没有根据实际可用的波段数进行动态调整。

## 已完成的修复

### 1. NDVI计算修复 (`calculate_ndvi`)

**修复前的问题：**
```python
elif available_bands >= 4:  # 错误！4波段图像会进入这个分支
    # Landsat-8: B5 (近红外), B4 (红波段)
    nir_band = self.bands[4]  # B5 - 错误！需要至少5个波段
    red_band = self.bands[3]   # B4
```

**修复后的逻辑：**
```python
elif available_bands >= 5:  # 修复：只有5+波段才进入
    # Landsat-8: B5 (近红外), B4 (红波段)
    nir_band = self.bands[4]  # B5
    red_band = self.bands[3]   # B4
elif available_bands == 4:  # 新增：专门处理4波段数据
    # 4波段数据，使用B4 (近红外) 和 B3 (红波段)
    nir_band = self.bands[3]  # B4 (近红外)
    red_band = self.bands[2]   # B3 (红波段)
```

### 2. NDWI计算修复 (`calculate_ndwi`)

**修复前的问题：**
```python
elif available_bands >= 4:  # 错误！4波段图像会进入这个分支
    # Landsat-8: B3 (绿波段), B5 (近红外)
    green_band = self.bands[2]  # B3
    nir_band = self.bands[4]    # B5 - 错误！需要至少5个波段
```

**修复后的逻辑：**
```python
elif available_bands >= 5:  # 修复：只有5+波段才进入
    # Landsat-8: B3 (绿波段), B5 (近红外)
    green_band = self.bands[2]  # B3
    nir_band = self.bands[4]    # B5
elif available_bands == 4:  # 新增：专门处理4波段数据
    # 4波段数据，使用B2 (绿波段) 和 B4 (近红外)
    green_band = self.bands[1]  # B2 (绿波段)
    nir_band = self.bands[3]    # B4 (近红外)
```

### 3. NDSI计算修复 (`calculate_ndsi`)

**修复前的问题：**
```python
else:
    # 多光谱影像：使用绿波段(1)和中红外波段(4)
    if not self._check_band_availability(5):
        logger.warning("需要至少5个波段来计算标准NDSI")
        return None
    
    green_band = self.bands[1].astype(float)  # 绿波段
    swir_band = self.bands[4].astype(float)  # 中红外波段 - 可能越界
```

**修复后的逻辑：**
```python
else:
    # 多光谱影像：根据可用波段数选择合适的波段
    available_bands = self.bands.shape[0]
    if available_bands >= 5:
        # 使用绿波段(1)和中红外波段(4)
        green_band = self.bands[1].astype(float)  # 绿波段
        swir_band = self.bands[4].astype(float)  # 中红外波段
    elif available_bands == 4:
        # 4波段数据：使用绿波段(1)和红波段(2)作为替代
        green_band = self.bands[1].astype(float)  # 绿波段
        swir_band = self.bands[2].astype(float)  # 红波段作为替代
    else:
        logger.warning(f"波段数不足，无法计算NDSI，当前波段数: {available_bands}")
        return None
```

## 新增的调试功能

为了帮助诊断问题，我们添加了详细的调试日志：

### 1. 波段信息调试
```python
logger.info(f"可用波段数: {available_bands}")
logger.info(f"波段数组形状: {self.bands.shape}")
logger.info(f"波段数组类型: {type(self.bands)}")
```

### 2. 分支执行调试
```python
logger.info(f"进入 >= 8 分支，available_bands = {available_bands}")
logger.info(f"进入 >= 5 分支，available_bands = {available_bands}")
logger.info(f"进入 == 4 分支，available_bands = {available_bands}")
logger.info(f"进入 == 3 分支，available_bands = {available_bands}")
```

## 修复后的波段分配策略

### 4波段数据
- **NDVI**: B3 (近红外) + B2 (红波段)
- **NDWI**: B1 (绿波段) + B3 (近红外)
- **NDSI**: B1 (绿波段) + B2 (红波段)

### 5+波段数据
- **NDVI**: B4 (近红外) + B3 (红波段) - Landsat-8标准
- **NDWI**: B2 (绿波段) + B4 (近红外) - Landsat-8标准
- **NDSI**: B1 (绿波段) + B4 (中红外) - 标准计算

### 8+波段数据
- **NDVI**: B7 (近红外) + B3 (红波段) - Sentinel-2标准
- **NDWI**: B2 (绿波段) + B7 (近红外) - Sentinel-2标准

## 测试验证

创建了两个测试脚本：
1. **`test_band_fix.py`**: 基本功能测试
2. **`test_band_fix_comprehensive.py`**: 全面测试，包括边界情况

## 下一步建议

1. **重新运行生态指数计算任务**，查看详细的调试日志
2. **检查日志输出**，确认：
   - 实际检测到的波段数
   - 代码进入的分支
   - 波段数组的形状和类型
3. **如果问题仍然存在**，根据调试日志进一步分析

## 注意事项

1. **NDBI计算**: 仍然需要至少6个波段，因为需要访问索引5
2. **RSEI相关计算**: 需要至少6个波段，使用Tasseled Cap变换
3. **波段编号**: 代码中的波段编号是基于0的索引，与遥感数据标准的1-based编号不同

## 预期结果

修复后，您的4波段遥感图像应该能够：
- 成功计算NDVI（使用B3和B2波段）
- 成功计算NDWI（使用B1和B3波段）
- 成功计算NDSI（使用B1和B2波段）
- 不再出现索引越界错误
