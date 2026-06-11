# JWT 认证系统设计

**日期**：2026-04-18
**范围**：用户注册/登录 + JWT 认证 + API 端点保护 + 前端适配
**目标**：为 EduAgent 添加最小可用的用户认证，替代硬编码 DEFAULT_USER_ID，所有 API 端点受保护

---

## 1. 背景与动机

当前所有 API 端点无认证，学生画像绑定硬编码 `user_id=1`。赛题要求多用户个性化学习，需要区分不同学生。

## 2. 用户模型

新增 `users` 表：

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

文件：`backend/app/models/user.py`

`student_profiles` 表的 `user_id` 外键关联到 `users.id`（现有数据需要迁移脚本处理）。

## 3. 认证流程

### 3.1 注册

`POST /api/auth/register`

请求体：
```json
{"username": "student1", "password": "xxx", "display_name": "张三"}
```

响应：
```json
{"access_token": "eyJ...", "token_type": "bearer", "user_id": 1}
```

- 用户名唯一性校验
- 密码用 bcrypt 哈希存储（passlib）
- 注册成功直接返回 JWT

### 3.2 登录

`POST /api/auth/login`

请求体：
```json
{"username": "student1", "password": "xxx"}
```

响应：同注册。

### 3.3 JWT 配置

- 算法：HS256
- 有效期：1440 分钟（24 小时，CLAUDE.md 指定）
- Payload：`{"sub": "<user_id>", "exp": <timestamp>}`
- Secret：从环境变量 `JWT_SECRET_KEY` 读取

### 3.4 认证依赖

`get_current_user` 依赖函数：
- 从 `Authorization: Bearer <token>` 提取 token
- 解码验证 JWT
- 查询用户，返回 User 对象
- 失败返回 401

文件：`backend/app/core/auth.py`

## 4. API 端点保护

### 4.1 公开端点（无需认证）

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /health`

### 4.2 受保护端点

所有 chat、profile、wiki 端点加 `user: User = Depends(get_current_user)`：

- chat 端点：`ChatSession` 绑定 `user_id`，查询时过滤当前用户
- profile 端点：画像绑定当前用户 `user.id`，替代 `DEFAULT_USER_ID`
- wiki 搜索：公开（不需要认证），write-back 需认证

### 4.3 数据隔离

- `chat_sessions` 表新增 `user_id` 列
- 查询 session/message/resource 时过滤 `user_id`
- `student_profiles` 的 `user_id` 改为关联 `users.id`

## 5. 前端适配

### 5.1 Token 管理

文件：`frontend/src/lib/auth.ts`

- `saveToken(token)` — 存入 localStorage
- `getToken()` — 读取 token
- `removeToken()` — 清除（登出）
- `isAuthenticated()` — 检查 token 是否存在且未过期

### 5.2 请求拦截

`api.ts` 和 `sse.ts` 所有请求添加 header：
```typescript
headers: { "Authorization": `Bearer ${getToken()}` }
```

### 5.3 登录/注册页面

文件：`frontend/src/app/login/page.tsx`

- 表单：用户名 + 密码 + 显示名称（注册时）
- 登录/注册切换
- 成功后跳转到 `/chat/new`
- 遵循 DESIGN.md 暖色调设计规范

### 5.4 路由保护

`frontend/src/app/(main)/layout.tsx` 中检查认证状态，未登录重定向到 `/login`。

## 6. 依赖变更

新增到 `pyproject.toml`：
```toml
"pyjwt>=2.9.0",
"passlib[bcrypt]>=1.7.4",
```

## 7. 数据库迁移

通过 Alembic 生成迁移：
1. 创建 `users` 表
2. `chat_sessions` 新增 `user_id` 列（nullable，兼容旧数据）
3. `student_profiles` 的 `user_id` 添加外键约束（需处理现有 user_id=1 的数据）

## 8. 配置变更

`core/config.py` 新增：
```python
jwt_secret_key: str = "dev-secret-change-in-production"
jwt_algorithm: str = "HS256"
jwt_expire_minutes: int = 1440
```

## 9. 不在本次范围

- OAuth / 第三方登录
- 角色权限（管理员/学生）
- Token 刷新机制
- 密码重置
- 邮箱验证

## 10. 测试策略

- 单元测试：密码哈希、JWT 生成/验证、get_current_user
- API 测试：注册、登录、受保护端点 401、正常访问
- 前端：手动验证登录流程
