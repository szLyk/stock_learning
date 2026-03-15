# XXL-JOB 执行器开机自启配置

## 当前状态

✅ 执行器已启动
- PID: 23395
- 日志：`/home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log`

---

## 方案一：Systemd 服务（推荐，适用于 Linux 系统）

### 1. 复制服务文件

```bash
sudo cp /home/fan/.openclaw/workspace/stock_learning/xxljob/stock-xxljob-executor.service /etc/systemd/system/
```

### 2. 启用并启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-xxljob-executor
sudo systemctl start stock-xxljob-executor
```

### 3. 验证

```bash
# 查看状态
sudo systemctl status stock-xxljob-executor

# 查看日志
sudo journalctl -u stock-xxljob-executor -f
```

### 4. 管理命令

```bash
# 启动
sudo systemctl start stock-xxljob-executor

# 停止
sudo systemctl stop stock-xxljob-executor

# 重启
sudo systemctl restart stock-xxljob-executor

# 禁用开机自启
sudo systemctl disable stock-xxljob-executor
```

---

## 方案二：Crontab（适用于无 systemd 的系统）

### 1. 编辑 crontab

```bash
crontab -e
```

### 2. 添加开机自启任务

```bash
# XXL-JOB 执行器开机自启
@reboot /home/fan/.openclaw/workspace/stock_learning/xxljob/start.sh >> /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/cron.log 2>&1
```

### 3. 验证

```bash
# 查看 crontab
crontab -l

# 重启后查看日志
cat /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/cron.log
```

---

## 方案三：Docker 容器自启

如果在 Docker 容器中运行，使用以下方式：

### 1. Docker Compose

```yaml
version: '3.8'

services:
  xxljob-executor:
    build: .
    container_name: stock-xxljob-executor
    restart: always  # 容器重启时自动启动
    environment:
      - XXL_JOB_ADMIN_ADDRESS=http://xxl-job-admin:8080/xxl-job-admin
      - DB_HOST=mysql
      - DB_USER=open_claw
      - DB_PASSWORD=xK7#pL9!mN2$vQ5@
    volumes:
      - ./logs:/home/fan/.openclaw/workspace/stock_learning/logs
    networks:
      - stock-network
```

### 2. Docker 启动命令

```bash
docker run -d \
  --name stock-xxljob-executor \
  --restart always \
  -e XXL_JOB_ADMIN_ADDRESS=http://localhost:8080/xxl-job-admin \
  -e DB_HOST=192.168.1.109 \
  -v /home/fan/.openclaw/workspace/stock_learning/logs:/home/fan/.openclaw/workspace/stock_learning/logs \
  stock-xxljob-executor:latest
```

---

## 方案四：Supervisor（进程管理）

### 1. 安装 Supervisor

```bash
# Ubuntu/Debian
sudo apt-get install supervisor

# CentOS/RHEL
sudo yum install supervisor
```

### 2. 创建配置文件

```bash
sudo vim /etc/supervisor/conf.d/stock-xxljob.conf
```

内容：
```ini
[program:stock-xxljob]
command=/usr/bin/python3 /home/fan/.openclaw/workspace/stock_learning/xxljob/executor_server.py
directory=/home/fan/.openclaw/workspace/stock_learning/xxljob
autostart=true
autorestart=true
stderr_logfile=/home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.err.log
stdout_logfile=/home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.out.log
user=root
environment=PYTHONPATH="/home/fan/.openclaw/workspace/stock_learning"
```

### 3. 启动

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start stock-xxljob
```

### 4. 管理

```bash
# 查看状态
sudo supervisorctl status stock-xxljob

# 重启
sudo supervisorctl restart stock-xxljob

# 停止
sudo supervisorctl stop stock-xxljob
```

---

## 方案五：Dockerfile 自启

创建 Dockerfile：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY xxljob/requirements.txt .
RUN pip3 install -r requirements.txt

# 复制代码
COPY xxljob/ ./xxljob/
COPY src/ ./src/
COPY logs/ ./logs/

# 设置环境变量
ENV PYTHONPATH=/app
ENV XXL_JOB_ADMIN_ADDRESS=http://localhost:8080/xxl-job-admin

# 启动脚本
CMD ["python3", "/app/xxljob/executor_server.py"]
```

构建和运行：

```bash
docker build -t stock-xxljob-executor .
docker run -d --restart always stock-xxljob-executor
```

---

## 手动启动脚本

如果以上方案都不适用，可以手动启动：

### 启动

```bash
cd /home/fan/.openclaw/workspace/stock_learning/xxljob
./start.sh
```

### 停止

```bash
./stop.sh
```

### 重启

```bash
./restart.sh
```

### 查看状态

```bash
# 查看进程
ps aux | grep executor_server.py

# 查看日志
tail -f /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

---

## 验证自启是否成功

### 1. 重启系统

```bash
sudo reboot
```

### 2. 检查进程

```bash
ps aux | grep executor_server.py
```

### 3. 查看日志

```bash
tail -100 /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

### 4. 测试连接

```bash
curl http://localhost:9999/health
```

---

## 故障排查

### 问题 1：服务未启动

**检查日志：**
```bash
tail -100 /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

**手动启动测试：**
```bash
cd /home/fan/.openclaw/workspace/stock_learning/xxljob
python3 executor_server.py
```

### 问题 2：端口被占用

**查看端口占用：**
```bash
netstat -tlnp | grep 9999
```

**解决方案：**
修改 `config.py` 中的 `executor_port` 配置

### 问题 3：数据库连接失败

**检查数据库：**
```bash
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw stock -e "SELECT 1"
```

**检查配置：**
```bash
cat /home/fan/.openclaw/workspace/stock_learning/xxljob/config.py
```

---

## 推荐方案

| 环境 | 推荐方案 |
|------|----------|
| Linux 服务器（systemd） | 方案一：Systemd 服务 |
| Linux 服务器（无 systemd） | 方案二：Crontab 或 方案四：Supervisor |
| Docker 容器 | 方案三：Docker Compose（restart: always） |
| 开发环境 | 方案五：手动启动脚本 |

---

## 当前环境说明

当前运行在 Docker 容器中，建议使用以下方式：

1. **容器重启策略**：设置 Docker 容器 `--restart always`
2. **进程守护**：使用 `start.sh` 脚本启动（已执行）
3. **外部管理**：在宿主机上配置 systemd 服务管理容器

**当前状态：**
```
✅ 执行器已启动 (PID: 23395)
📄 日志文件：/home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

**下次重启后需要手动执行：**
```bash
cd /home/fan/.openclaw/workspace/stock_learning/xxljob
./start.sh
```
