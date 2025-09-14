# 日志优化指南

## 优化概述

本次优化旨在减少项目启动和运行时的日志输出，只保留必要的关键操作日志，提高日志可读性。

## 主要优化内容

### 1. 日志格式简化
- **原格式**: `%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s`
- **新格式**: `%(asctime)s - %(levelname)s - %(message)s`
- 移除了函数名和行号信息，使日志更简洁

### 2. 日志级别调整
- **控制台输出**: 从 `INFO` 提升到 `WARNING`
  - 只显示警告、错误和关键操作
  - 减少常规信息输出
- **文件输出**: 保持 `INFO` 级别
  - 文件中仍然记录详细信息，便于调试

### 3. 关键操作日志保留

以下关键操作仍会在控制台显示：

#### JWT令牌管理
- 🔄 JWT令牌刷新
- ✅ JWT令牌刷新成功
- ⚠️ JWT令牌即将过期提醒
- 🔑 申请匿名访问令牌

#### API请求处理
- 📤 发送请求到Warp API
- ✅ 请求完成和响应信息
- 📤 处理API请求（包括模型信息）
- ✅ SSE流完成

#### 服务器状态
- 🚀 服务器启动
- 🌐 服务器监听端口
- 📍 API端点和文档界面地址
- ✅ JWT token有效性状态

### 4. DEBUG日志降级

以下日志从 `INFO` 降级为 `DEBUG`（不在控制台显示）：

- 详细的请求/响应数据
- SSE事件的详细内容
- WebSocket连接数变化
- 编码/解码的字节数统计
- 流式会话的详细信息
- HTTP请求重试信息

### 5. 移除的冗余日志

完全移除了以下冗余输出：
- SSE事件的逐个打印
- 数据包的hex dump
- 详细的事件数据内容
- 重复的分隔线和统计信息

## 使用说明

### 查看详细日志
如需查看详细日志，可以：
1. 查看日志文件：`logs/` 目录下的日志文件包含 INFO 级别的详细信息
2. 临时调整日志级别：修改 [`common/logging.py`](../common/logging.py:25) 中的 `console_level` 参数

### 恢复原始设置
如需恢复原始的详细日志输出：
```python
# common/logging.py
console_level: int = logging.INFO,  # 改回 INFO
```

## 优化效果

### 优化前
- 启动时输出大量详细信息
- 每个请求都有多行日志
- SSE事件逐个显示详情
- 控制台被大量日志占满

### 优化后
- 启动时只显示关键信息
- 请求只显示简要状态
- 只保留必要的操作日志
- 控制台清晰简洁

## 相关文件

优化涉及的主要文件：
- [`common/logging.py`](../common/logging.py) - 日志配置
- [`warp2protobuf/core/auth.py`](../warp2protobuf/core/auth.py) - JWT相关日志
- [`warp2protobuf/warp/api_client.py`](../warp2protobuf/warp/api_client.py) - API请求日志
- [`server.py`](../server.py) - 服务器启动日志
- [`warp2protobuf/api/protobuf_routes.py`](../warp2protobuf/api/protobuf_routes.py) - 路由处理日志
- [`protobuf2openai/`](../protobuf2openai/) - OpenAI兼容层日志