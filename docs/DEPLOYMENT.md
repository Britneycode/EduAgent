# EduAgent 云服务器部署手册

目标环境：阿里云 ECS（华东 1 杭州，Ubuntu 24.04，公网 IP `47.97.255.65`），域名 `xwz0219.top`（已完成 ICP 备案）。

## 架构总览

```
浏览器
  │  https://xwz0219.top
  ▼
Nginx 容器（80/443，唯一对外端口）
  ├── /api/*  →  backend 容器（FastAPI，uvicorn，127.0.0.1:8000）
  └── /*      →  frontend 容器（Next.js standalone，:3000）

数据持久化：Docker 卷 backend_data → 容器内 /data
  ├── /data/eduagent.db      SQLite 数据库
  ├── /data/chroma_data/     Chroma 向量库
  └── /data/storage/assets/  生成的 PPT/音频等资产

证书：certbot 容器自动续期 Let's Encrypt 免费证书
```

仓库中与本部署相关的文件：

| 文件 | 作用 |
| --- | --- |
| `backend/Dockerfile` | 后端镜像（Python 3.12 + uv + CPU 版 PyTorch + 预置 BGE 模型） |
| `frontend/Dockerfile` | 前端镜像（Next.js standalone 多阶段构建） |
| `docker-compose.prod.yml` | 生产编排：backend + frontend + nginx + certbot |
| `deploy/nginx/app.http.conf` | 初始 HTTP 配置（用于首次签发证书） |
| `deploy/nginx/app.https.conf` | 正式 HTTPS 配置 |
| `frontend/next.config.ts` | 已加 `output: "standalone"`（本地开发不受影响） |

> 本地开发流程完全不变，以上文件只在服务器上使用。

---

## 一、DNS 解析

在域名控制台（阿里云 DNS）添加记录：

| 记录类型 | 主机记录 | 记录值 |
| --- | --- | --- |
| A | @ | 47.97.255.65 |
| A | www（可选） | 47.97.255.65 |

验证（本地电脑执行）：`ping xwz0219.top` 能解析到 `47.97.255.65` 即可继续。

## 二、安全组放行端口

阿里云控制台 → ECS 实例 → 安全组 → 入方向规则，确认放行：

- `22`（SSH，应已存在）
- `80`（HTTP，证书签发 + 跳转 HTTPS）
- `443`（HTTPS）

**不需要**对外开放 3000 / 8000，它们只在 Docker 内部网络通信。

## 三、服务器初始化（装 Docker）

SSH 登录服务器后执行：

```bash
# 安装 Docker（阿里云镜像源）
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
systemctl enable --now docker

# 配置 Docker Hub 镜像加速（国内服务器必须，否则拉不动镜像）
# 加速器地址在「阿里云控制台 → 容器镜像服务 → 镜像工具 → 镜像加速器」获取
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://<你的加速器ID>.mirror.aliyuncs.com"]
}
EOF
systemctl restart docker

docker --version
docker compose version   # 应为 v2.x
```

内存提示：构建阶段 PyTorch 依赖较大，若服务器内存小于 4GB，建议先加 2GB swap：

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 四、上传代码

方式任选其一，目标目录 `/opt/eduagent`。

**方式 A：Git（推荐，便于后续更新）**

```bash
# 本地（Windows PowerShell）：推送到私有仓库（Gitee 国内速度快）
cd D:\a-program\EduAgent
git add -A && git commit -m "添加 Docker 部署配置"
git remote add gitee git@gitee.com:<你的账号>/eduagent.git   # 首次
git push gitee main

# 服务器：
git clone git@gitee.com:<你的账号>/eduagent.git /opt/eduagent
```

**方式 B：scp 直传（本地 PowerShell 执行）**

```powershell
scp -r D:\a-program\EduAgent root@47.97.255.65:/opt/eduagent
```

> `backend/.env` 已被 `.gitignore` 排除，无论哪种方式都需要单独处理（下一步）。

## 五、服务器上配置环境变量

### 1. 后端密钥配置 `/opt/eduagent/backend/.env`

把本地 `backend/.env` 传上去再修改，或直接在服务器新建：

```powershell
# 本地 PowerShell（方式 A 的用户也要执行此步）
scp D:\a-program\EduAgent\backend\.env root@47.97.255.65:/opt/eduagent/backend/.env
```

然后 `vim /opt/eduagent/backend/.env`，确认以下关键项：

```ini
# 必须：生成一个随机密钥（服务器上执行 openssl rand -hex 32 生成）
JWT_SECRET_KEY=<64位随机十六进制字符串>
# 必须：演示/生产严禁模拟模式
LLM_DEV_MODE=false
# 确认 LLM 密钥齐全（按你实际使用的厂商）
DEEPSEEK_API_KEY=...
DASHSCOPE_API_KEY=...
TAVILY_API_KEY=...
```

> `DATABASE_URL`、`APP_ENV`、`BACKEND_CORS_ORIGINS` 等路径类配置**不用改**，`docker-compose.prod.yml` 会自动覆盖为容器内路径。

### 2. 根目录 `/opt/eduagent/.env`

```bash
cd /opt/eduagent
echo 'NGINX_MODE=http' > .env    # 首次签发证书用 http 模式，签好后改成 https
```

## 六、构建并启动

```bash
cd /opt/eduagent
alias dc='docker compose -f docker-compose.prod.yml'   # 下文简写，可写入 ~/.bashrc

# 1. 构建并启动后端、前端（首次构建约 10~20 分钟，主要是 PyTorch 依赖较大）
dc up -d --build backend frontend

# 2. 观察后端日志：看到知识库导入完成、Uvicorn running 即就绪
dc logs -f backend

# 3. 确认后端健康
dc ps        # backend 应显示 (healthy)
curl http://127.0.0.1:8000/health
```

> 前端构建参数 `NEXT_PUBLIC_API_URL=https://xwz0219.top` 已写死在 compose 中，浏览器端所有 API 请求都走 Nginx 同源反代。

## 七、签发 HTTPS 证书

```bash
# 1. 启动 Nginx（当前为 http 模式）
dc up -d nginx

# 2. 通过 webroot 方式签发证书（--email 换成你的邮箱）
dc run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d xwz0219.top \
  --email you@example.com --agree-tos --no-eff-email
# 若解析了 www 子域名，追加：-d www.xwz0219.top
# 看到 "Congratulations" 即签发成功

# 3. 切换为 HTTPS 配置并重启
sed -i 's/NGINX_MODE=http/NGINX_MODE=https/' .env
dc up -d

# 4. 启动 certbot 自动续期服务
dc up -d certbot
```

## 八、验证清单

- [ ] `https://xwz0219.top` 能打开首页，浏览器显示安全锁
- [ ] `http://xwz0219.top` 自动跳转 HTTPS
- [ ] `https://xwz0219.top/health` 返回 `{"status":"ok",...}`（确认 `llm_warning` 为 null）
- [ ] 注册/登录正常
- [ ] 发起对话有**流式输出**（逐字出现而非长时间等待后一次性返回）
- [ ] 生成资源（文档/题目/PPT）成功，且刷新后资源中心仍可见（验证数据卷持久化）

## 九、日常运维

```bash
# 更新代码后重新部署
cd /opt/eduagent && git pull
dc up -d --build            # 只重建有变更的镜像

# 查看日志
dc logs -f backend
dc logs -f frontend
dc logs -f nginx

# 备份数据（SQLite + 向量库 + 资产）
docker run --rm -v eduagent_backend_data:/data -v /opt/backup:/backup \
  alpine tar czf /backup/eduagent-$(date +%F).tar.gz -C /data .

# 查看磁盘占用（镜像较大，定期清理）
docker system df
docker system prune -f      # 清理悬空镜像
```

## 十、常见问题

**1. `docker compose build` 拉取镜像超时**
说明没配 Docker Hub 加速器，回到第三节配置 `daemon.json`。

**2. 后端日志卡在 "正在加载 Embedding 模型" 或报网络错误**
镜像构建时已预下载模型；若预下载失败，运行时会通过 `HF_ENDPOINT=https://hf-mirror.com` 重试。仍失败可手动执行：
`dc exec backend python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"`

**3. Nginx 报 502**
后端首次启动要导入知识库（1~3 分钟），`dc ps` 看 backend 是否 `(healthy)`，未就绪时稍等即可。其他情况用 `dc logs backend` 排查。

**4. 对话接口长时间无响应或流式中断**
Nginx 配置已针对 SSE 关闭缓冲并设置 1 小时超时；若自行修改过 Nginx 配置，确认 `proxy_buffering off` 未删除。

**5. 浏览器报 CORS 错误**
确认 compose 中 `BACKEND_CORS_ORIGINS` 包含你实际访问的域名（含协议头），改后 `dc up -d backend` 生效。

**6. 访问 `https://www.xwz0219.top` 证书报错**
证书只签了主域名。重新执行签发命令并追加 `-d www.xwz0219.top`，同时在两个 Nginx 配置的 `server_name` 后加上 `www.xwz0219.top`。

**7. 数据会丢吗？**
不会。SQLite / Chroma / 生成资产都在 Docker 卷 `eduagent_backend_data` 中，`dc down`、重建镜像都不影响。只有执行 `dc down -v` 或手动删卷才会丢数据。

**8. 后端健康检查一直 unhealthy**
常见原因是 `JWT_SECRET_KEY` 未配置（`APP_ENV=production` 时缺失会拒绝启动），`dc logs backend` 可看到具体报错。
