# EduAgent 前端镜像
# Next.js 16 standalone 输出 + pnpm，多阶段构建
# 构建（在项目根目录执行）：docker compose -f docker-compose.prod.yml build frontend
# 注意：NEXT_PUBLIC_API_URL 在构建时固化进前端包，更换域名需重新构建

FROM node:20-alpine AS base
# 国内镜像加速：corepack 下载 pnpm、pnpm 安装依赖都走 npmmirror
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
RUN corepack enable && corepack prepare pnpm@10 --activate \
    && pnpm config set registry https://registry.npmmirror.com

# ---------- 依赖安装 ----------
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# ---------- 构建 ----------
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# 浏览器访问后端的地址，经 Nginx 同源反代
ARG NEXT_PUBLIC_API_URL=https://xwz0219.top
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ---------- 运行 ----------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
