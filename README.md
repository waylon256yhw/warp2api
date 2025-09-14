# warp2api

Warp AI ⇄ OpenAI API 兼容桥接。提供：

- 纯 Protobuf 编解码与 Warp API 代理（桥接层）
- OpenAI Chat Completions 兼容层（/v1/chat/completions 与 /v1/models）

## 快速开始

要求：Python 3.12+

### 1) 安装依赖

使用 uv（推荐）：

```bash
uv sync
```

或使用 pip：

```bash
pip install -e .
```

### 2) 启动服务

桥接层（Protobuf & Warp 代理）：

```bash
uv run warp-server --port 28888
```

OpenAI 兼容层：

```bash
uv run warp-openai --port 28889
```

（或直接使用 `python server.py` / `python openai_compat.py`）

### 3) 验证

- 模型列表：`GET http://127.0.0.1:28889/v1/models`
- 非流式对话：`POST http://127.0.0.1:28889/v1/chat/completions`
- 流式对话：同上请求体添加 `"stream": true`，以 SSE 读取

## 环境变量

在项目根目录创建 `.env`（可选）：

- `WARP_JWT`：Warp 访问 JWT
- `WARP_REFRESH_TOKEN`：刷新令牌（若提供可自动刷新）
- `WARP_SERVER_PORT` / `OPENAI_COMPAT_PORT`：服务端口
- `WARP_BRIDGE_URL`：兼容层访问桥接层的地址（默认 `http://127.0.0.1:28888`）

遇到配额/429 时，桥接层会尝试匿名额度申请并写回 `.env`。

## 主要命令

- `warp-server`：桥接层入口（见 `server.py`）
- `warp-openai`：OpenAI 兼容层入口（见 `openai_compat.py`）

## 代码结构

- `warp2protobuf/`：桥接层（路由、Protobuf 运行时、JWT、流处理）
- `protobuf2openai/`：OpenAI 兼容层（消息重排、工具调用映射、SSE 转换）
- `common/`：通用配置、日志、HTTP 工具、schema 处理
- `proto/`：`.proto` 与 `compiled_descriptors.pb`（优先使用预编译描述符）

## 许可

未设置许可证。如需开源请补充 LICENSE 文件。

