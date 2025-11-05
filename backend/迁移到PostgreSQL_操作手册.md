# 迁移到 PostgreSQL - 3 步操作手册

## ⚡ 快速开始（20分钟完成）

### 📋 准备清单
- [ ] 已备份当前数据库（复制 `db.sqlite3`）
- [ ] PostgreSQL 已安装（见 `POSTGRESQL_安装指南.md`）
- [ ] Python 虚拟环境已激活

---

## 🚀 步骤 1：安装依赖（2分钟）

```bash
# 进入后端目录
cd backend

# 安装 PostgreSQL 驱动
pip install psycopg2-binary==2.9.9 python-dotenv==1.0.0

# 验证安装
python -c "import psycopg2; print('✓ PostgreSQL驱动安装成功')"
```

**如果遇到错误：**
- Windows: 直接使用 `psycopg2-binary` 即可
- Linux/Mac: 可能需要先安装 `libpq-dev` 或 `postgresql-devel`

---

## 🔧 步骤 2：配置数据库（3分钟）

### 方法 A：使用自动配置脚本（推荐）

```bash
# 运行迁移脚本，按提示输入配置
python migrate_to_postgresql.py
```

脚本会询问：
1. 数据库名称（默认: tianshuipy）
2. 数据库用户（默认: postgres）
3. 数据库密码（你安装 PostgreSQL 时设置的）
4. 数据库主机（默认: localhost）
5. 数据库端口（默认: 5432）

### 方法 B：手动创建配置文件

在 `backend` 目录创建 `.env` 文件：

```bash
# PostgreSQL 配置
DB_ENGINE=postgresql
DB_NAME=tianshuipy
DB_USER=postgres
DB_PASSWORD=你的密码
DB_HOST=localhost
DB_PORT=5432

# Django 配置
SECRET_KEY=django-insecure-@jmeepv1459j^#n1nfu@87jcfkcp_ia@jip2)m=k#h7n6@89lw
DEBUG=True

# GeoServer 配置
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_USERNAME=admin
GEOSERVER_PASSWORD=geoserver
GEOSERVER_WORKSPACE=tianshuipy
```

---

## 📦 步骤 3：创建数据库并迁移（5分钟）

### 3.1 创建数据库

**使用 pgAdmin（图形界面）：**
1. 打开 pgAdmin
2. 右键点击 "Databases" → "Create" → "Database"
3. 名称填写：`tianshuipy`
4. Encoding 选择：UTF8
5. 点击保存

**使用命令行：**

```bash
# Windows (PowerShell)
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE tianshuipy ENCODING 'UTF8';"

# 或者交互式
psql -U postgres
CREATE DATABASE tianshuipy ENCODING 'UTF8';
\q
```

### 3.2 启用 PostGIS 扩展（可选，用于高级空间功能）

```sql
-- 连接到数据库
\c tianshuipy

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS postgis;

-- 验证
SELECT PostGIS_Version();
```

### 3.3 运行数据库迁移

#### 自动迁移（推荐）

```bash
# 方式1: 使用迁移脚本（会自动导出SQLite数据）
python migrate_to_postgresql.py
```

#### 手动迁移

```bash
# 1. 创建表结构
python manage.py migrate --settings=tianshuipy.settings_postgresql

# 2. 创建超级用户（如果需要）
python manage.py createsuperuser --settings=tianshuipy.settings_postgresql

# 3. 如果需要从 SQLite 导入数据
python manage.py dumpdata --settings=tianshuipy.settings_dev --output=data.json
python manage.py loaddata data.json --settings=tianshuipy.settings_postgresql
```

---

## ✅ 步骤 4：验证和启动（5分钟）

### 4.1 验证数据库连接

```bash
# 测试连接
python manage.py dbshell --settings=tianshuipy.settings_postgresql

# 在 psql 中查看表
\dt

# 查看用户数据
SELECT * FROM users_user;

# 退出
\q
```

### 4.2 启动服务

```bash
# 使用 PostgreSQL 配置启动
python manage.py runserver --settings=tianshuipy.settings_postgresql

# 或者永久切换（修改 manage.py）
```

**永久切换方法：**

编辑 `manage.py` 文件，修改第 6 行：

```python
# 原来
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings_dev')

# 改为
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings_postgresql')
```

### 4.3 测试功能

访问：
- 后端管理: http://localhost:8000/admin/
- API 文档: http://localhost:8000/api/
- 前端页面: http://localhost:5173/

---

## 🔍 常见问题排查

### ❌ 问题 1: "django.db.utils.OperationalError: could not connect to server"

**原因：** PostgreSQL 服务未启动

**解决：**
```bash
# Windows
# 服务 → PostgreSQL → 启动

# 或使用命令
net start postgresql-x64-15
```

---

### ❌ 问题 2: "authentication failed for user"

**原因：** 密码错误或认证配置问题

**解决：**
1. 检查 `.env` 文件中的密码是否正确
2. 或修改 PostgreSQL 配置允许本地信任登录

编辑 `C:\Program Files\PostgreSQL\15\data\pg_hba.conf`:
```
# 找到这行
host    all             all             127.0.0.1/32            md5

# 临时改为（仅开发环境！）
host    all             all             127.0.0.1/32            trust
```

重启 PostgreSQL 服务。

---

### ❌ 问题 3: "relation does not exist"

**原因：** 表未创建

**解决：**
```bash
python manage.py migrate --settings=tianshuipy.settings_postgresql
```

---

### ❌ 问题 4: 中文乱码

**原因：** 数据库编码问题

**解决：** 重建数据库时指定编码
```sql
DROP DATABASE tianshuipy;
CREATE DATABASE tianshuipy 
    ENCODING 'UTF8' 
    LC_COLLATE = 'zh_CN.UTF-8' 
    LC_CTYPE = 'zh_CN.UTF-8';
```

---

## 📊 性能优化建议（可选）

### 1. 创建索引

```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_remote_sensing_date ON remote_sensing_images(acquisition_date);
CREATE INDEX idx_ecological_type ON ecological_indices(index_type);
CREATE INDEX idx_processing_status ON processing_tasks(status);
```

### 2. 连接池配置（已在 settings_postgresql.py 中配置）

```python
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 60,  # 连接复用 60 秒
    }
}
```

### 3. 查询优化

使用 Django Debug Toolbar 检查慢查询：
```bash
pip install django-debug-toolbar
```

---

## 🎉 迁移完成检查清单

- [ ] PostgreSQL 服务正常运行
- [ ] 数据库表结构创建成功（运行 `\dt` 看到所有表）
- [ ] 用户数据正常（可以登录管理后台）
- [ ] 文件上传功能正常
- [ ] API 接口正常响应
- [ ] 前端页面正常显示

---

## 🔄 回退到 SQLite（如果需要）

如果遇到问题想回退：

```bash
# 1. 修改 manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tianshuipy.settings_dev')

# 2. 启动服务
python manage.py runserver
```

你的 SQLite 数据库（`db.sqlite3`）完全没有改动，可以直接使用。

---

## 📞 需要帮助？

如果遇到问题，检查：
1. `logs/django.log` - Django 日志
2. PostgreSQL 日志：`C:\Program Files\PostgreSQL\15\data\log\`
3. 运行 `python manage.py check` 检查配置

---

## 🚀 下一步优化

迁移成功后，可以考虑：
1. ✅ 启用 PostGIS 进行空间查询
2. ✅ 配置 Redis 缓存
3. ✅ 设置定时备份
4. ✅ 配置监控和告警


