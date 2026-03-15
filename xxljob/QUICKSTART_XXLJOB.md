# XXL-JOB 网页端快速部署指南

## 🌐 网页端地址

**XXL-JOB 调度中心是一个独立的 Java Web 应用，需要单独部署。**

部署后访问地址：
```
http://<你的服务器 IP>:8080/xxl-job-admin
```

**默认账号密码：**
- 用户名：`admin`
- 密码：`123456`

---

## 🚀 快速部署（3 步）

### 步骤 1：下载 XXL-JOB

```bash
# 下载
wget https://github.com/xuxueli/xxl-job/releases/download/2.4.0/xxl-job-2.4.0.zip

# 或手动下载后上传到服务器
# https://github.com/xuxueli/xxl-job/releases/download/2.4.0/xxl-job-2.4.0.zip
```

### 步骤 2：初始化数据库

**需要 root 权限或能创建数据库的用户：**

```bash
# 使用 root 用户连接
mysql -h 192.168.1.109 -P 3306 -u root -p

# 执行初始化脚本
source /home/fan/.openclaw/workspace/stock_learning/xxljob/init_xxljob_db.sql
```

**或者手动执行 SQL：**

```sql
-- 1. 创建数据库
CREATE DATABASE xxl_job DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- 2. 授权给 open_claw 用户
GRANT ALL PRIVILEGES ON xxl_job.* TO 'open_claw'@'%';
FLUSH PRIVILEGES;

-- 3. 导入表结构
USE xxl_job;
source /path/to/xxl-job-2.4.0/doc/db/tables_xxl_job.sql;
```

### 步骤 3：启动 XXL-JOB Admin

```bash
# 进入目录
cd xxl-job-2.4.0/xxl-job-admin

# 修改配置（如果需要）
vim conf/application.properties

# 启动
./bin/start.sh

# 或者直接用 Java 启动
java -jar xxl-job-admin-2.4.0.jar
```

---

## 📝 配置说明

### 修改数据库配置

编辑 `xxl-job-admin/conf/application.properties`：

```properties
### web 端口
server.port=8080

### 数据库配置
spring.datasource.url=jdbc:mysql://192.168.1.109:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai
spring.datasource.username=open_claw
spring.datasource.password=xK7#pL9!mN2$vQ5@
```

---

## 🔧 Docker 部署（推荐）

**如果你有 Docker 环境：**

```bash
docker run -d \
  --name xxl-job-admin \
  -p 8080:8080 \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://192.168.1.109:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai \
  -e SPRING_DATASOURCE_USERNAME=open_claw \
  -e SPRING_DATASOURCE_PASSWORD='xK7#pL9!mN2$vQ5@' \
  -e SERVER_PORT=8080 \
  xuxueli/xxl-job-admin:2.4.0
```

**等待 30 秒启动完成，然后访问：**
```
http://localhost:8080/xxl-job-admin
```

---

## 📊 配置执行器和任务

### 1. 登录管理后台

访问：`http://<你的服务器 IP>:8080/xxl-job-admin`

账号：`admin` / `123456`

### 2. 创建执行器

进入 **执行器管理** → **新增执行器**

| 配置项 | 值 |
|--------|-----|
| AppName | `stock-data-executor` |
| 名称 | 股票数据采集执行器 |
| 执行器类型 | 自动注册 |

保存后，等待执行器自动注册（执行器启动后会自动注册）。

### 3. 创建任务

进入 **任务管理** → **新增任务**

**示例：日线采集任务**

| 配置项 | 值 |
|--------|-----|
| 执行器 | 股票数据采集执行器 |
| JobHandler | `run_daily_collection` |
| 运行模式 | BEAN |
| 触发类型 | CRON |
| CRON | `0 0 18 * * ?` |
| 运行参数 | `date_type=d` |
| 阻塞处理策略 | 单机串行 |
| 超时时间 | 3600 |
| 失败重试次数 | 3 |

---

## ✅ 验证部署

### 1. 检查 Admin 是否启动

```bash
# 查看进程
ps aux | grep xxl-job-admin

# 查看端口
netstat -tlnp | grep 8080

# 查看日志
tail -f xxl-job-2.4.0/xxl-job-admin/logs/app.log
```

### 2. 检查执行器是否注册

登录 XXL-JOB 管理后台：
- 进入 **执行器管理**
- 查看 "股票数据采集执行器" 是否有注册地址

### 3. 测试任务

- 在任务列表中找到刚创建的任务
- 点击 **执行一次** 按钮
- 查看执行日志

---

## 🐛 常见问题

### 问题 1：无法访问网页

**检查服务是否启动：**
```bash
ps aux | grep xxl-job-admin
```

**检查端口：**
```bash
netstat -tlnp | grep 8080
```

**检查防火墙：**
```bash
# 开放 8080 端口
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### 问题 2：数据库连接失败

**测试连接：**
```bash
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw xxl_job -e "SELECT 1"
```

**检查数据库权限：**
```sql
SHOW GRANTS FOR 'open_claw'@'%';
```

### 问题 3：执行器未注册

**检查执行器日志：**
```bash
tail -f /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

**查看注册表：**
```sql
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw xxl_job -e "SELECT * FROM xxl_job_registry"
```

---

## 📦 文件清单

| 文件 | 说明 |
|------|------|
| `init_xxljob_db.sql` | XXL-JOB 数据库初始化脚本 |
| `DEPLOY_XXLJOB_ADMIN.md` | 详细部署文档 |
| `QUICKSTART_XXLJOB.md` | 快速入门指南（本文件） |

---

## 🔗 官方资源

- **GitHub**：https://github.com/xuxueli/xxl-job
- **官方文档**：https://www.xuxueli.com/xxl-job/
- **Docker 镜像**：https://hub.docker.com/r/xuxueli/xxl-job-admin
- **下载页面**：https://github.com/xuxueli/xxl-job/releases

---

## 📞 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| XXL-JOB Admin | ❌ 未部署 | 需要手动部署 |
| 执行器 | ✅ 运行中 | PID: 23395 |
| 数据库 | ✅ 已连接 | 192.168.1.109:3306 |

**下一步：** 按照上面的步骤部署 XXL-JOB Admin，然后访问网页端配置任务。
