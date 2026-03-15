# XXL-JOB 调度中心部署指南

## 快速部署（Docker 方式 - 推荐）

### 1. 启动 XXL-JOB Admin（调度中心）

```bash
docker run -d \
  --name xxl-job-admin \
  -p 8080:8080 \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://192.168.1.109:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai \
  -e SPRING_DATASOURCE_USERNAME=open_claw \
  -e SPRING_DATASOURCE_PASSWORD=xK7#pL9!mN2$vQ5@ \
  -e SERVER_PORT=8080 \
  xuxueli/xxl-job-admin:2.4.0
```

### 2. 访问网页端

打开浏览器访问：
```
http://localhost:8080/xxl-job-admin
```

**默认账号密码：**
- 用户名：`admin`
- 密码：`123456`

---

## 方案二：手动部署（Java）

### 1. 下载 XXL-JOB

```bash
# 下载
wget https://github.com/xuxueli/xxl-job/releases/download/2.4.0/xxl-job-2.4.0.zip

# 解压
unzip xxl-job-2.4.0.zip
cd xxl-job-2.4.0
```

### 2. 初始化数据库

```bash
# 连接 MySQL
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw stock

# 创建数据库
CREATE DATABASE IF NOT EXISTS xxl_job DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

# 导入表结构
use xxl_job;
source /path/to/xxl-job-2.4.0/doc/db/tables_xxl_job.sql;
```

### 3. 修改配置

编辑 `xxl-job-admin/conf/application.properties`：

```properties
### web 端口
server.port=8080

### 数据库配置
spring.datasource.url=jdbc:mysql://192.168.1.109:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai
spring.datasource.username=open_claw
spring.datasource.password=xK7#pL9!mN2$vQ5@
```

### 4. 启动

```bash
cd xxl-job-2.4.0/xxl-job-admin
./bin/start.sh
```

### 5. 访问

```
http://localhost:8080/xxl-job-admin
```

---

## 方案三：Docker Compose（完整环境）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  xxl-job-admin:
    image: xuxueli/xxl-job-admin:2.4.0
    container_name: xxl-job-admin
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=open_claw
      - SPRING_DATASOURCE_PASSWORD=xK7#pL9!mN2$vQ5@
      - SERVER_PORT=8080
    depends_on:
      - mysql
    networks:
      - stock-network

  mysql:
    image: mysql:8.0
    container_name: stock-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=root123
      - MYSQL_DATABASE=xxl_job
      - MYSQL_USER=open_claw
      - MYSQL_PASSWORD=xK7#pL9!mN2$vQ5@
    ports:
      - "3306:3306"
    volumes:
      - ./mysql-data:/var/lib/mysql
      - ./xxl-job-2.4.0/doc/db/tables_xxl_job.sql:/docker-entrypoint-initdb.d/tables_xxl_job.sql
    networks:
      - stock-network

  xxl-job-executor:
    build: .
    container_name: stock-xxljob-executor
    restart: always
    environment:
      - XXL_JOB_ADMIN_ADDRESS=http://xxl-job-admin:8080/xxl-job-admin
      - DB_HOST=mysql
      - DB_USER=open_claw
      - DB_PASSWORD=xK7#pL9!mN2$vQ5@
    depends_on:
      - xxl-job-admin
    networks:
      - stock-network

networks:
  stock-network:
    driver: bridge
```

启动：

```bash
docker-compose up -d
```

访问：
```
http://localhost:8080/xxl-job-admin
```

---

## 数据库初始化脚本

如果数据库中没有 `xxl_job` 库和表，执行以下 SQL：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS xxl_job DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE xxl_job;

-- 创建 XXL-JOB 表（简化版，完整表结构见官方 SQL）
CREATE TABLE IF NOT EXISTS `xxl_job_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `job_group` int(11) NOT NULL COMMENT '执行器主键 ID',
  `job_desc` varchar(255) NOT NULL,
  `add_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `author` varchar(64) DEFAULT NULL COMMENT '作者',
  `alarm_email` varchar(255) DEFAULT NULL COMMENT '报警邮件',
  `schedule_type` varchar(50) NOT NULL DEFAULT 'NONE' COMMENT '调度类型',
  `schedule_conf` varchar(128) DEFAULT NULL COMMENT '调度配置，值取决于调度类型',
  `misfire_strategy` varchar(50) NOT NULL DEFAULT 'DO_NOTHING' COMMENT '调度过期策略',
  `executor_route_strategy` varchar(50) DEFAULT NULL COMMENT '执行器路由策略',
  `executor_handler` varchar(255) DEFAULT NULL COMMENT '执行器任务 handler',
  `executor_param` varchar(512) DEFAULT NULL COMMENT '执行器任务参数',
  `executor_block_strategy` varchar(50) DEFAULT NULL COMMENT '阻塞处理策略',
  `executor_timeout` int(11) NOT NULL DEFAULT '0' COMMENT '任务执行超时时间，单位秒',
  `executor_fail_retry_count` int(11) NOT NULL DEFAULT '0' COMMENT '失败重试次数',
  `glue_type` varchar(50) NOT NULL COMMENT 'GLUE 类型',
  `glue_source` mediumtext COMMENT 'GLUE 源代码',
  `glue_remark` varchar(128) DEFAULT NULL COMMENT 'GLUE 备注',
  `glue_updatetime` datetime DEFAULT NULL COMMENT 'GLUE 更新时间',
  `child_jobid` varchar(255) DEFAULT NULL COMMENT '子任务 ID，多个逗号分隔',
  `trigger_status` int(11) NOT NULL DEFAULT '0' COMMENT '调度状态：0-停止，1-运行',
  `trigger_last_time` bigint(13) NOT NULL DEFAULT '0' COMMENT '上次调度时间',
  `trigger_next_time` bigint(13) NOT NULL DEFAULT '0' COMMENT '下次调度时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务信息';

CREATE TABLE IF NOT EXISTS `xxl_job_registry` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `registry_group` varchar(50) NOT NULL,
  `registry_key` varchar(255) NOT NULL,
  `registry_value` varchar(255) NOT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `i_g_k_v` (`registry_group`,`registry_key`,`registry_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行器注册表';
```

---

## 配置执行器

登录 XXL-JOB 管理后台后：

### 1. 创建执行器

进入 **执行器管理** → **新增执行器**

| 配置项 | 值 |
|--------|-----|
| AppName | `stock-data-executor` |
| 名称 | 股票数据采集执行器 |
| 排序 | 1 |
| 执行器类型 | 自动注册 |
| 地址列表 | （自动注册，留空） |

保存后，执行器会自动注册（需要执行器已启动）。

### 2. 创建任务

进入 **任务管理** → **新增任务**

示例：日线采集任务

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

## 任务配置清单（24 个任务）

### 第 1 层：基础行情（18:00-19:00）

| JobHandler | CRON | 运行参数 | 说明 |
|------------|------|----------|------|
| `run_daily_collection` | `0 0 18 * * ?` | `date_type=d` | 日线 |
| `run_daily_collection` | `0 30 18 * * ?` | `date_type=w` | 周线 |
| `run_daily_collection` | `0 0 19 * * ?` | `date_type=m` | 月线 |
| `run_min_collection` | `0 */30 9-15 * * ?` | - | 分钟线（交易日） |

### 第 2 层：财务数据（20:00-21:00）

| JobHandler | CRON | 运行参数 | 说明 |
|------------|------|----------|------|
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=profit` | 利润表 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=balance` | 资产负债表 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=cashflow` | 现金流量表 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=growth` | 成长能力 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=operation` | 运营能力 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=dupont` | 杜邦分析 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=forecast` | 业绩预告 |
| `run_financial_collection` | `0 0 20 * * ?` | `data_type=dividend` | 分红送配 |

### 第 3 层：东方财富（21:00-22:00）

| JobHandler | CRON | 运行参数 | 说明 |
|------------|------|----------|------|
| `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=moneyflow` | 资金流向 |
| `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=north` | 北向资金 |
| `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=shareholder` | 股东人数 |
| `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=concept` | 概念板块 |
| `run_eastmoney_collection` | `0 0 21 * * ?` | `data_type=analyst` | 分析师评级 |

### 第 4 层：指标计算（22:00-23:00）

| JobHandler | CRON | 运行参数 | 说明 |
|------------|------|----------|------|
| `run_indicator_calculation` | `0 0 22 * * ?` | `indicator_type=all` | 所有指标 |

### 第 5 层：多因子（23:00-24:00）

| JobHandler | CRON | 运行参数 | 说明 |
|------------|------|----------|------|
| `run_multi_factor` | `0 0 23 * * ?` | - | 多因子打分 |

---

## 故障排查

### 问题 1：无法访问网页

**检查 Docker 容器：**
```bash
docker ps | grep xxl-job-admin
```

**查看日志：**
```bash
docker logs xxl-job-admin
```

**检查端口：**
```bash
netstat -tlnp | grep 8080
```

### 问题 2：数据库连接失败

**测试连接：**
```bash
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw xxl_job -e "SELECT 1"
```

### 问题 3：执行器未注册

**检查执行器日志：**
```bash
tail -f /home/fan/.openclaw/workspace/stock_learning/logs/xxljob/executor.log
```

**查看注册表：**
```bash
MYSQL_PWD='xK7#pL9!mN2$vQ5@' mysql -h 192.168.1.109 -P 3306 -u open_claw xxl_job -e "SELECT * FROM xxl_job_registry"
```

---

## 快速启动命令（Docker）

```bash
# 1. 启动 XXL-JOB Admin
docker run -d \
  --name xxl-job-admin \
  -p 8080:8080 \
  -e SPRING_DATASOURCE_URL=jdbc:mysql://192.168.1.109:3306/xxl_job?Unicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai \
  -e SPRING_DATASOURCE_USERNAME=open_claw \
  -e SPRING_DATASOURCE_PASSWORD=xK7#pL9!mN2$vQ5@ \
  -e SERVER_PORT=8080 \
  xuxueli/xxl-job-admin:2.4.0

# 2. 等待启动完成（约 30 秒）
sleep 30

# 3. 访问网页
echo "访问：http://localhost:8080/xxl-job-admin"
echo "账号：admin / 123456"
```

---

## 官方资源

- GitHub：https://github.com/xuxueli/xxl-job
- 官方文档：https://www.xuxueli.com/xxl-job/
- Docker Hub：https://hub.docker.com/r/xuxueli/xxl-job-admin
