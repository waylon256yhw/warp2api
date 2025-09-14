# Warp2Protobuf 桥接服务器架构文档

## 概述
warp2protobuf 是一个用于将 Warp AI API 的 protobuf 协议桥接为更通用接口的服务器实现。它提供了完整的 protobuf 编解码、JWT 认证管理、流式处理和 WebSocket 支持。

## 目录结构
```
warp2protobuf/
├── api/                 # API路由模块
├── config/             # 配置管理
├── core/               # 核心功能模块
└── warp/               # Warp API客户端
```

## 模块详细说明

### 1. API模块 (`api/`)

#### `protobuf_routes.py` - Protobuf编解码API路由
这是服务器的主要路由文件，提供了完整的RESTful API和WebSocket接口。

**主要类和组件：**
- `EncodeRequest`: Pydantic模型，用于接收编码请求
- `DecodeRequest`: Pydantic模型，用于接收解码请求
- `StreamDecodeRequest`: 用于流式解码请求
- `ConnectionManager`: WebSocket连接管理器

**核心API端点：**

1. **`POST /api/encode`** - JSON转Protobuf编码
   - 接收JSON数据，转换为protobuf字节
   - 自动处理server_message_data字段编码
   - 支持MCP工具的input_schema验证和清理

2. **`POST /api/decode`** - Protobuf转JSON解码
   - 将Base64编码的protobuf数据解码为JSON
   - 自动解析server_message_data字段

3. **`POST /api/stream-decode`** - 流式数据解码
   - 处理多个protobuf数据块
   - 支持完整消息拼接

4. **`GET /api/schemas`** - 获取Protobuf模式信息
   - 返回所有可用的protobuf消息类型
   - 包含字段定义和结构信息

5. **认证相关端点：**
   - `GET /api/auth/status` - 检查JWT状态
   - `POST /api/auth/refresh` - 刷新JWT token
   - `GET /api/auth/user_id` - 获取用户ID

6. **Warp API交互端点：**
   - `POST /api/warp/send` - 发送请求到Warp API（返回文本）
   - `POST /api/warp/send_stream` - 发送请求并解析SSE事件
   - `POST /api/warp/send_stream_sse` - SSE流式转发

7. **WebSocket端点：**
   - `WS /ws` - 实时数据包监控

**重要实现细节：**
- 使用FastAPI框架构建
- 支持CORS跨域请求
- WebSocket用于实时数据包监控
- 自动处理429配额错误并尝试申请匿名token

### 2. 配置模块 (`config/`)

#### `models.py` - 模型配置管理
管理Warp AI支持的所有模型配置。

**主要函数：**
- `get_model_config(model_name)`: 获取模型配置
  - 返回base、planning、coding三个层级的模型设置
  - 支持的模型包括：claude-4系列、gpt-5、gpt-4系列、o3/o4-mini、gemini-2.5-pro等

- `get_warp_models()`: 获取完整模型列表
  - 分为三个类别：agent_mode、planning、coding
  - 每个模型包含视觉支持、使用倍数等元数据

- `get_all_unique_models()`: 获取去重后的模型列表
  - 生成OpenAI兼容的模型格式
  - 用于API的/models端点

#### `settings.py` - 环境配置
桥接到统一的配置模块，导出所有必要的配置项：
- API URLs (WARP_URL, REFRESH_URL)
- 客户端headers配置 (CLIENT_VERSION, OS_CATEGORY等)
- Protobuf字段名配置
- JWT刷新配置

### 3. 核心模块 (`core/`)

#### `auth.py` - JWT认证管理
处理Warp API的JWT token管理和刷新。

**主要功能：**
- `decode_jwt_payload(token)`: 解码JWT获取过期时间
- `is_token_expired(token, buffer_minutes)`: 检查token是否过期
- `refresh_jwt_token()`: 使用refresh token刷新JWT
- `get_valid_jwt()`: 获取有效的JWT（自动刷新）
- `acquire_anonymous_access_token()`: 申请匿名访问token（配额刷新）

**重要实现细节：**
- 支持环境变量WARP_REFRESH_TOKEN动态配置
- 自动处理token过期和刷新
- 匿名token申请流程（用于配额耗尽时）

**匿名JWT刷新详细流程：**

1. **触发时机**
   - 当Warp API返回HTTP 429错误（配额耗尽）时触发
   - 错误消息包含 "No remaining quota" 或 "No AI requests remaining"
   - 只在第一次尝试失败时申请（每个请求最多尝试两次）

2. **申请流程**
   ```python
   async def acquire_anonymous_access_token() -> str:
   ```
   - **Step 1**: 调用 `_create_anonymous_user()` 创建匿名用户
     - 发送GraphQL请求到 `https://app.warp.dev/graphql/v2`
     - 请求类型：`NATIVE_CLIENT_ANONYMOUS_USER_FEATURE_GATED`
     - 过期设置：`NO_EXPIRATION`
     - 获取 `idToken`
   
   - **Step 2**: 调用 `_exchange_id_token_for_refresh_token(id_token)`
     - 使用Google Identity Toolkit API
     - 将 `idToken` 交换为 `refreshToken`
     - API端点：`https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken`
   
   - **Step 3**: 获取最终的access_token
     - 使用新的 `refreshToken` 调用Warp代理端点
     - 获取可用的 `access_token`

3. **持久化处理**
   ```python
   # 保存refresh_token到.env文件
   update_env_refresh_token(refresh_token)
   
   # 保存access_token到.env文件
   update_env_file(access)
   ```
   - **写入.env文件**：是的，会自动写回
   - 使用 `python-dotenv` 的 `set_key()` 函数
   - 更新两个环境变量：
     - `WARP_REFRESH_TOKEN`: 新的刷新令牌（供将来使用）
     - `WARP_JWT`: 新的访问令牌（立即使用）

4. **使用新token重试**
   - 申请成功后，将新的JWT赋值给当前请求
   - 使用新token重新发送原始请求
   - 如果申请失败，返回错误不再重试

5. **日志记录**
   - 申请开始：`"🔑 申请匿名访问令牌..."`
   - .env更新：`"Updated .env file with new JWT token"`
   - 失败警告：`"匿名token申请失败，无法重试"`

#### `logging.py` - 日志系统
统一的日志管理系统。

**主要功能：**
- `setup_logging()`: 初始化日志系统
- `backup_existing_log()`: 备份现有日志文件
- `set_log_file(log_file_name)`: 动态切换日志文件

**特点：**
- 使用RotatingFileHandler防止日志文件过大
- 自动备份旧日志
- 支持动态日志文件切换

#### `protobuf.py` - Protobuf运行时
核心的protobuf编译和消息处理模块。

**主要功能：**
- `ensure_proto_runtime()`: 确保protobuf运行时已初始化
- `msg_cls(full_name)`: 获取消息类
- `build_request_bytes(user_text, model)`: 构建请求字节
- `get_request_schema()`: 自动检测请求消息格式

**重要实现细节：**
- 动态编译.proto文件
- 自动检测请求消息的text字段路径
- 支持多种请求格式的兼容性

#### `protobuf_utils.py` - Protobuf工具函数
提供protobuf和JSON之间的转换工具。

**主要函数：**
- `protobuf_to_dict(protobuf_bytes, message_type)`: Protobuf转字典
- `dict_to_protobuf_bytes(data_dict, message_type)`: 字典转Protobuf
- `_populate_protobuf_from_dict()`: 递归填充protobuf消息

**特殊处理：**
- google.protobuf.Struct类型的特殊处理
- google.protobuf.Value类型的动态填充
- Map字段和Repeated字段的处理
- 枚举类型支持字符串名称或数字

#### `schema_sanitizer.py` - MCP工具模式清理器
验证和清理MCP工具的input_schema。

**主要功能：**
- `sanitize_mcp_input_schema_in_packet()`: 清理请求包中的schema
- 移除空值（空字符串、空列表、空字典）
- 确保每个属性有非空的type和description
- 特殊处理headers字段

#### `server_message_data.py` - 服务器消息数据编解码
处理特殊的server_message_data字段。

**数据格式：**
- Base64URL编码的proto3消息
- 包含UUID（字段1）和Timestamp（字段3）
- 支持三种类型：UUID_ONLY、TIMESTAMP_ONLY、UUID_AND_TIMESTAMP

**主要函数：**
- `decode_server_message_data(b64url)`: 解码Base64URL数据
- `encode_server_message_data(uuid, seconds, nanos)`: 编码为Base64URL
- 使用varint编码实现protobuf wire format

#### `session.py` - 全局会话管理
管理固定的conversation_id和任务上下文。

**主要类：**
- `SessionMessage`: 会话消息数据类
- `SessionState`: 会话状态
- `GlobalSessionManager`: 全局会话管理器

**固定的conversation_id：**
```python
FIXED_CONVERSATION_ID = "5b48d359-0715-479e-a158-0a00f2dfea36"
```

#### `stream_processor.py` - 流式数据处理器
处理流式protobuf数据包。

**主要类：**
- `StreamProcessor`: 流式处理器主类
- `StreamSession`: 单个流式会话
- `StreamPacketAnalyzer`: 数据包分析工具

**功能特点：**
- 支持实时解析和WebSocket推送
- 数据块模式分析
- 流式内容增量提取

### 4. Warp客户端模块 (`warp/`)

#### `api_client.py` - Warp API客户端
处理与Warp API的实际通信，包含特殊的HTTP/2和TLS配置。

**主要函数：**
- `send_protobuf_to_warp_api()`: 发送protobuf并获取响应
  - 处理SSE事件流
  - 自动重试机制（429错误时申请匿名token）
  - 解析多种事件类型

- `send_protobuf_to_warp_api_parsed()`: 解析模式的API调用
  - 返回完整的解析事件列表
  - 保留原始事件数据结构

**HTTP/2 和 TLS 特殊处理：**

1. **HTTP/2 协议支持**
   ```python
   async with httpx.AsyncClient(http2=True, timeout=httpx.Timeout(60.0), verify=verify_opt, trust_env=True) as client:
   ```
   - 明确启用 `http2=True` 以支持HTTP/2协议
   - 设置60秒超时时间
   - 启用 `trust_env=True` 以使用系统代理设置

2. **TLS 验证配置**
   ```python
   verify_opt = True
   insecure_env = os.getenv("WARP_INSECURE_TLS", "").lower()
   if insecure_env in ("1", "true", "yes"):
       verify_opt = False
       logger.warning("TLS verification disabled via WARP_INSECURE_TLS")
   ```
   - 默认启用TLS证书验证（`verify_opt = True`）
   - 支持通过环境变量 `WARP_INSECURE_TLS` 禁用TLS验证（开发环境）
   - 当设置为 "1"、"true" 或 "yes" 时禁用证书验证

3. **请求头配置**
   ```python
   headers = {
       "accept": "text/event-stream",
       "content-type": "application/x-protobuf",
       "x-warp-client-version": "v0.2025.08.06.08.12.stable_02",
       "x-warp-os-category": "Windows",
       "x-warp-os-name": "Windows",
       "x-warp-os-version": "11 (26100)",
       "authorization": f"Bearer {jwt}",
       "content-length": str(len(protobuf_bytes)),
   }
   ```
   - 使用 `text/event-stream` 接收SSE流
   - 内容类型为 `application/x-protobuf`
   - 包含客户端版本和操作系统信息

**SSE事件类型处理：**
- INITIALIZATION - 会话初始化
- CLIENT_ACTIONS - 客户端动作（包含多种子类型）
- FINISHED - 请求完成
- 支持的动作类型：CREATE_TASK、APPEND_CONTENT、ADD_MESSAGE、TOOL_CALL、TOOL_RESPONSE

#### `response.py` - 响应解析器
解析Warp API的protobuf响应。

**主要函数：**
- `extract_openai_content_from_response()`: 提取OpenAI兼容内容
  - 解析agent_output中的文本
  - 提取工具调用信息
  - 处理多种消息类型

- `extract_openai_sse_deltas_from_response()`: 生成SSE增量
  - 将响应转换为OpenAI流式格式
  - 支持内容增量和工具调用

## 关键技术实现

### 1. Protobuf动态编译
- 运行时编译.proto文件生成Python类
- 使用descriptor_pool管理消息定义
- 自动检测请求消息格式

### 2. JWT认证流程
```
1. 检查环境变量中的JWT
2. 验证token是否过期
3. 使用refresh_token刷新（如需要）
4. 429错误时申请匿名token
```

### 3. 流式处理架构
- 支持分块接收和解析
- WebSocket实时推送
- 完整消息拼接和验证

### 4. 错误处理机制
- 自动重试（配额耗尽时）
- 详细的错误日志
- 用户友好的错误响应

## 部署和使用

### 环境变量配置
- `WARP_JWT`: JWT认证token
- `WARP_REFRESH_TOKEN`: 刷新token
- `WARP_INSECURE_TLS`: 禁用TLS验证（开发环境）
- `WARP_URL`: Warp API端点URL

### 启动服务器
```bash
python -m warp2protobuf.api.protobuf_routes
```

### API使用示例

1. **编码JSON为Protobuf：**
```json
POST /api/encode
{
  "json_data": {
    "input": {"user_inputs": [{"inputs": [{"user_query": {"query": "Hello"}}]}]}
  },
  "message_type": "warp.multi_agent.v1.Request"
}
```

2. **发送到Warp API：**
```json
POST /api/warp/send
{
  "input": {"user_inputs": [{"inputs": [{"user_query": {"query": "What is 2+2?"}}]}]}
}
```

### HTTP客户端配置详情

#### 与Warp API交互的HTTP客户端配置

所有三个Warp API端点（`/api/warp/send`、`/api/warp/send_stream`、`/api/warp/send_stream_sse`）都使用相同的HTTP客户端配置：

1. **HTTP/2 协议**
   - 所有请求均启用HTTP/2协议（`http2=True`）
   - 这对于处理SSE（Server-Sent Events）流式响应至关重要
   - HTTP/2的多路复用特性提高了流式数据传输效率

2. **TLS/SSL 处理**
   - **生产环境**：默认启用完整的TLS证书验证
   - **开发环境**：可通过环境变量 `WARP_INSECURE_TLS` 禁用证书验证
   - 支持的禁用值："1"、"true"、"yes"（不区分大小写）
   - 禁用时会记录警告日志

3. **超时配置**
   - Warp API请求：60秒超时（`httpx.Timeout(60.0)`）
   - JWT刷新请求：30秒超时
   - 匿名token申请：30秒超时

4. **代理支持**
   - 通过 `trust_env=True` 启用系统代理设置
   - 自动读取 HTTP_PROXY、HTTPS_PROXY 等环境变量

5. **其他HTTP客户端（非Warp API）**
   - JWT刷新和匿名token申请使用标准HTTP/1.1
   - 这些请求不需要HTTP/2特性
   - 超时时间较短（30秒）

#### SSE流式处理端点特殊配置

`/api/warp/send_stream_sse` 端点作为SSE代理时的额外配置：

```python
return StreamingResponse(
    _agen(), 
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
)
```
- 设置正确的SSE媒体类型
- 禁用缓存确保实时性
- 保持连接活跃以支持流式传输

## 安全性考虑

1. JWT token自动管理和刷新
2. 支持TLS验证（生产环境）
3. CORS配置支持
4. 敏感信息不记录在日志中

## 性能优化

1. 连接池复用（httpx.AsyncClient）
2. 流式处理减少内存占用
3. WebSocket用于实时通信
4. 异步处理提高并发性能

## 总结

warp2protobuf提供了一个完整的桥接解决方案，将Warp AI的protobuf协议转换为更通用的接口。通过模块化设计、完善的错误处理和流式处理支持，它能够可靠地处理各种AI请求场景。
