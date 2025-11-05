# PostgreSQL + PostGIS 安装指南（Windows）

## 方法一：使用官方安装包（推荐新手）

### 1. 下载 PostgreSQL
- 访问：https://www.postgresql.org/download/windows/
- 下载最新版本（推荐 PostgreSQL 15 或 16）
- 运行安装程序

### 2. 安装过程
- **端口**：保持默认 5432
- **密码**：设置 postgres 用户密码（**请记住！**）
- **区域**：选择 Chinese, China

### 3. 安装 PostGIS
- 在安装 PostgreSQL 时，勾选 **Stack Builder**
- 安装完成后会自动启动 Stack Builder
- 选择：Spatial Extensions → PostGIS
- 点击安装

## 方法二：使用 Docker（推荐开发者）

```bash
# 一键启动 PostgreSQL + PostGIS
docker run -d \
  --name tianshuipy-postgres \
  -e POSTGRES_DB=tianshuipy \
  -e POSTGRES_USER=tianshuipy \
  -e POSTGRES_PASSWORD=your_password_here \
  -p 5432:5432 \
  postgis/postgis:15-3.3

# 验证安装
docker ps
docker exec -it tianshuipy-postgres psql -U tianshuipy -d tianshuipy -c "SELECT version();"
```

## 创建数据库

```sql
-- 使用 pgAdmin 或命令行执行

-- 1. 创建数据库
CREATE DATABASE tianshuipy
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'zh_CN.UTF-8'
    LC_CTYPE = 'zh_CN.UTF-8'
    TEMPLATE = template0;

-- 2. 连接到数据库
\c tianshuipy

-- 3. 启用 PostGIS 扩展
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 4. 验证安装
SELECT PostGIS_Version();
```

## 验证安装成功

```bash
# 方式1：使用 psql
psql -U postgres -d tianshuipy -c "SELECT PostGIS_Version();"

# 方式2：使用 Python
python -c "import psycopg2; print('PostgreSQL 驱动安装成功!')"
```

## 常见问题

### Q: 忘记 postgres 密码怎么办？
A: 修改 `C:\Program Files\PostgreSQL\15\data\pg_hba.conf`
   将 `md5` 改为 `trust`，重启服务，然后修改密码

### Q: PostGIS 安装失败？
A: 重新运行 Stack Builder，或者手动下载安装包

### Q: 端口 5432 被占用？
A: 在安装时选择其他端口（如 5433），并修改配置文件

