# Claude Code 编排协作技能

## 角色分工

| 角色 | 职责 |
|-----|------|
| **用户** | 提出需求、确认方案 |
| **Xiao Luo（老大）** | 需求分析、架构设计、任务拆解、监督进度、测试验收 |
| **Claude Code（小弟）** | 具体编程实现 |

## 工作流程

```
用户 → Xiao Luo → Claude Code → Xiao Luo → 用户
  需求   分析/拆解    编码实现    验收    反馈
```

## Xiao Luo 职责

1. 📋 **需求梳理** - 和用户确认需求细节
2. 🏗️ **架构设计** - 设计技术方案和模块划分
3. 📦 **任务拆解** - 将大任务分解为可执行的小任务
4. 👀 **监督执行** - 调用 Claude Code 完成编码
5. ✅ **验收测试** - 代码审查和功能测试
6. 📊 **进度汇报** - 向用户汇报完成情况

## Claude Code 职责

1. 💻 编写代码
2. 🔧 实现功能
3. 🐛 修复问题

## 调用方式

使用 `sessions_spawn` 调用 Claude Code：

```python
# 示例：让 Claude Code 完成编程任务
sessions_spawn(
    runtime="acp",
    agentId="claude-code",  # Claude Code 的 agentId
    task="具体编程任务描述",
    cwd="工作目录"
)
```

## 配置文件

Claude Code 配置位置：`~/.claude/settings.json`

```json
{
  "model": "glm-5",
  "env": {
    "ANTHROPIC_BASE_URL": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "your-token"
  }
}
```

## 使用场景

- 编写新功能代码
- 重构现有代码
- 修复 Bug
- 编写测试用例
- 生成文档

## 注意事项

1. 任务要具体明确，避免模糊需求
2. 复杂任务要先拆解再分配
3. 验收时要检查代码质量和功能完整性
4. 重要修改需要用户确认后再执行

---

**创建时间**：2026-04-03
**创建人**：Xiao Luo