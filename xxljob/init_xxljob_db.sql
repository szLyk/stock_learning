-- =====================================================
-- XXL-JOB 数据库初始化脚本
-- 执行：连接到 MySQL 后运行此脚本
-- =====================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS xxl_job DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE xxl_job;

-- =====================================================
-- 表结构（完整版）
-- =====================================================

-- 1. 任务信息表
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

-- 2. 任务日志表
CREATE TABLE IF NOT EXISTS `xxl_job_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `job_group` int(11) NOT NULL COMMENT '执行器主键 ID',
  `job_id` int(11) NOT NULL COMMENT '任务，主键 ID',
  `executor_address` varchar(255) DEFAULT NULL COMMENT '执行器地址，本次执行的地址',
  `executor_handler` varchar(255) DEFAULT NULL COMMENT '执行器任务 handler',
  `executor_param` varchar(512) DEFAULT NULL COMMENT '执行器任务参数',
  `executor_sharding_param` varchar(20) DEFAULT NULL COMMENT '执行器任务分片参数，格式：0/2',
  `executor_fail_retry_count` int(11) NOT NULL DEFAULT '0' COMMENT '失败重试次数',
  `trigger_time` datetime DEFAULT NULL COMMENT '调度-时间',
  `trigger_code` int(11) NOT NULL COMMENT '调度-结果',
  `trigger_msg` varchar(2048) DEFAULT NULL COMMENT '调度 - 日志',
  `handle_time` datetime DEFAULT NULL COMMENT '执行 - 时间',
  `handle_code` int(11) NOT NULL COMMENT '执行 - 状态',
  `handle_msg` varchar(2048) DEFAULT NULL COMMENT '执行 - 日志',
  `alarm_status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '告警状态：0-默认、1-无需告警、2-需要告警、3-已告警、4-已取消',
  PRIMARY KEY (`id`),
  KEY `I_trigger_time` (`trigger_time`),
  KEY `I_handle_code` (`handle_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务日志';

-- 3. 任务日志详情表
CREATE TABLE IF NOT EXISTS `xxl_job_log_detail` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `log_id` bigint(20) NOT NULL,
  `executor_param` varchar(512) DEFAULT NULL COMMENT '执行器任务参数',
  `result_msg` varchar(2048) DEFAULT NULL COMMENT '执行结果',
  PRIMARY KEY (`id`),
  KEY `I_log_id` (`log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务日志详情';

-- 4. 执行器注册表
CREATE TABLE IF NOT EXISTS `xxl_job_registry` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `registry_group` varchar(50) NOT NULL,
  `registry_key` varchar(255) NOT NULL,
  `registry_value` varchar(255) NOT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `i_g_k_v` (`registry_group`,`registry_key`,`registry_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行器注册表';

-- 5. 执行器表
CREATE TABLE IF NOT EXISTS `xxl_job_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_name` varchar(64) NOT NULL COMMENT '执行器 AppName',
  `title` varchar(12) NOT NULL COMMENT '执行器名称',
  `address_type` tinyint(4) NOT NULL DEFAULT '0' COMMENT '执行器地址类型：0=自动注册、1=手动录入',
  `address_list` varchar(512) DEFAULT NULL COMMENT '执行器地址列表，非自动注册有效',
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='执行器表';

-- 6. 用户表
CREATE TABLE IF NOT EXISTS `xxl_job_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL COMMENT '账号',
  `password` varchar(50) NOT NULL COMMENT '密码',
  `role` tinyint(4) NOT NULL COMMENT '角色：0=普通用户、1=管理员',
  `permission` varchar(255) DEFAULT NULL COMMENT '权限：执行器、任务、日志等',
  PRIMARY KEY (`id`),
  UNIQUE KEY `i_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 7. 任务锁表
CREATE TABLE IF NOT EXISTS `xxl_job_lock` (
  `lock_name` varchar(50) NOT NULL COMMENT '锁名称',
  PRIMARY KEY (`lock_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务锁';

-- =====================================================
-- 初始化数据
-- =====================================================

-- 插入默认管理员账号（密码：123456）
INSERT INTO xxl_job_user (username, password, role, permission) 
VALUES ('admin', 'e10adc3949ba59abbe56e057f20f883e', 1, NULL)
ON DUPLICATE KEY UPDATE username=username;

-- 插入执行器组
INSERT INTO xxl_job_group (app_name, title, address_type, address_list, update_time) 
VALUES ('stock-data-executor', '股票数据采集执行器', 0, NULL, NOW())
ON DUPLICATE KEY UPDATE app_name=app_name;

-- 插入任务锁
INSERT INTO xxl_job_lock (lock_name) VALUES ('schedule_lock')
ON DUPLICATE KEY UPDATE lock_name=lock_name;

-- =====================================================
-- 验证
-- =====================================================

SELECT '数据库初始化完成！' as status;
SELECT '默认账号：admin / 123456' as login_info;
SELECT * FROM xxl_job_user;
SELECT * FROM xxl_job_group;
