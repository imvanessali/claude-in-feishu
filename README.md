# Claude in Feishu

把 Claude Code 装进飞书。手机发消息，Claude 在你的 Mac 上执行任务，结果直接发回飞书。

> **使用 Claude Code 订阅（Pro/Max Plan），不需要 API Key，不按 token 计费。**

## 能做什么

| 能力 | 说明 |
|---|---|
| **手机远程操控** | 飞书发消息 → 启动子代理执行任务 → 结果发回聊天 |
| **飞书文档** | 创建、搜索、读取、追加文档，管理云盘文件夹 |
| **飞书日历** | 创建日历事件、查看日程 |
| **截图验收** | Claude 截取本地应用/网页截图，发到飞书，手机上做产品验收 |
| **文件传输** | 本地图片、PDF 等文件直接发到飞书对话 |
| **跨会话可见** | 所有 Claude 会话跑在 tmux 里，互相可以查看进度 |
| **自动踩坑日志** | 每次会话结束自动总结：做了什么、踩了什么坑、关键决策 |

## 快速开始

### 前置条件

- macOS + [Claude Code](https://claude.com/claude-code)
- Node.js 20+、Python 3、tmux

### 安装与配置

```bash
git clone https://github.com/imvanessali/claude-in-feishu.git
cd claude-in-feishu
```

然后运行 setup wizard，会一步步引导你完成所有配置（飞书应用创建、权限、OAuth 授权、日志系统、tmux 等）：

```
/claude-in-feishu setup
```

### 使用

打开飞书，给机器人发消息就行了。Claude 会在你的 Mac 上执行任务，把结果发回聊天。

遇到问题？运行 `/claude-in-feishu doctor` 诊断。

## 架构

```
📱 飞书（手机）
    ↓ 发消息
🖥️ 本地 daemon (Node.js)
    ↓ 启动子代理
🤖 Claude Code subagent
    ↓ 执行任务
💻 Mac 本地 + 飞书 API
    ↓ 会话结束
📝 自动日志（Haiku 总结）
```

## Credits

Built on top of [claude-to-im](https://github.com/op7418/claude-to-im) by op7418.

## License

MIT
