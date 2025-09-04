# GDAL安装指南

## 概述
GDAL (Geospatial Data Abstraction Library) 是一个用于栅格和矢量地理空间数据转换的库。本项目使用GDAL进行土地利用分析和生态环境指数计算。

## Windows安装方法

### 方法1：使用conda（推荐）
```bash
# 创建新的conda环境
conda create -n tianshui python=3.9
conda activate tianshui

# 安装GDAL
conda install -c conda-forge gdal

# 安装其他依赖
pip install -r requirements_dev.txt
```

### 方法2：使用pip安装预编译包
```bash
# 安装GDAL
pip install GDAL==3.6.2

# 安装PyProj
pip install PyProj==3.6.1
```

### 方法3：从OSGeo4W安装
1. 访问 https://trac.osgeo.org/osgeo4w/
2. 下载OSGeo4W安装程序
3. 选择"Advanced Install"
4. 选择GDAL包进行安装

## 验证安装
```python
# 在Python中测试
from osgeo import gdal
print(gdal.__version__)
```

## 常见问题

### 问题1：ImportError: No module named 'osgeo'
**解决方案：**
- 确保使用正确的Python环境
- 重新安装GDAL包

### 问题2：DLL加载失败
**解决方案：**
- 安装Visual C++ Redistributable
- 使用conda安装而不是pip

### 问题3：版本兼容性
**解决方案：**
- 使用Python 3.9-3.11
- 确保GDAL版本与Python版本兼容

## 替代方案
如果GDAL安装困难，可以考虑：
1. 使用Docker容器
2. 使用云服务
3. 使用其他地理空间库（如rasterio）

## 联系支持
如果遇到安装问题，请联系项目维护者。
