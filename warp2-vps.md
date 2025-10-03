前置：进入文件夹，设置好 .env

安装 uv:

  - curl -LsSf https://astral.sh/uv/install.sh | sh
  - export PATH="$HOME/.local/bin:$PATH"

安装依赖（在仓库根目录）:

  - uv sync --no-dev

直连端口开放（若不走 Nginx）:

  - sudo ufw allow 28888/tcp
  - sudo ufw allow 28889/tcp

---

默认 uv 路径假设为` /root/.local/bin/uv`；若不同，用 `command -v uv` 查到的路径替换。

**创建服务文件（桥接层）**

```
sudo tee /etc/systemd/system/warp2api-bridge.service > /dev/null <<'EOF'
[Unit]
Description=Warp2API Bridge (Protobuf & Warp proxy)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/warp2api
EnvironmentFile=/root/warp2api/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/root/.local/bin/uv run python /root/warp2api/server.py --port 28888
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
```

**创建服务文件（OpenAI 兼容层，依赖桥接层）**

```
sudo tee /etc/systemd/system/warp2api-openai.service > /dev/null <<'EOF'
[Unit]
Description=Warp2API OpenAI Compatibility Server
After=network-online.target warp2api-bridge.service
Requires=warp2api-bridge.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/warp2api
EnvironmentFile=/root/warp2api/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=/root/.local/bin/uv run python /root/warp2api/openai_compat.py --port 28889
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
```

**加载并启用**

```
sudo systemctl daemon-reload
sudo systemctl enable --now warp2api-bridge.service
sudo systemctl enable --now warp2api-openai.service
```

**查看状态**

```
systemctl status warp2api-bridge --no-pager
systemctl status warp2api-openai --no-pager
```

**实时日志**

```
journalctl -u warp2api-bridge -f
journalctl -u warp2api-openai -f
```

**更新服务（滚动升级）**

```
sudo systemctl stop warp2api-openai warp2api-bridge
cd /root/warp2api
sudo -u root git pull origin main
/root/.local/bin/uv sync --no-dev
sudo systemctl start warp2api-bridge warp2api-openai
```

若在更新前修改过 `.env`，可执行 `cp .env .env.backup` 备份，更新后再还原差异。

**验证接口**

```
curl http://127.0.0.1:28888/v1/models
curl http://127.0.0.1:28889/v1/models
```
