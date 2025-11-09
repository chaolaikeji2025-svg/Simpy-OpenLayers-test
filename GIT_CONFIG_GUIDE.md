# 📝 Git配置完整指南

## 🔧 基本配置（必需）

### 1. 配置用户名

```bash
git config --global user.name "您的名字"
```

**示例：**
```bash
git config --global user.name "Zhang San"
```

### 2. 配置邮箱

```bash
git config --global user.email "您的邮箱@example.com"
```

**示例：**
```bash
git config --global user.email "zhangsan@example.com"
```

## 🔐 凭证管理（保存密码）

### 方法1：使用凭证缓存（推荐）

**临时缓存（默认15分钟）：**
```bash
git config --global credential.helper cache
```

**设置缓存时长（如1小时 = 3600秒）：**
```bash
git config --global credential.helper 'cache --timeout=3600'
```

**永久保存凭证：**
```bash
git config --global credential.helper store
```

⚠️ **注意**：`store` 方式会将密码以明文形式保存在 `~/.git-credentials` 文件中，不够安全。

### 方法2：使用个人访问令牌（GitHub/GitLab推荐）

对于GitHub、GitLab等平台，推荐使用个人访问令牌（PAT）代替密码：

**GitHub生成令牌：**
1. 登录GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token
3. 设置权限（如repo、workflow等）
4. 复制生成的token

**使用令牌：**
- 在git push时，用户名输入你的GitHub用户名
- 密码输入生成的token（不是你的GitHub密码）

## 📋 快速配置命令

将以下命令复制并修改后执行：

```bash
# 配置用户名（修改为你的名字）
git config --global user.name "Your Name"

# 配置邮箱（修改为你的邮箱）
git config --global user.email "your.email@example.com"

# 配置凭证缓存（1小时）
git config --global credential.helper 'cache --timeout=3600'

# 或者永久保存（不太安全）
# git config --global credential.helper store

# 配置默认编辑器（可选）
git config --global core.editor vim

# 配置默认分支名（可选）
git config --global init.defaultBranch main

# 配置中文文件名显示（可选）
git config --global core.quotepath false

# 配置换行符处理（可选）
git config --global core.autocrlf input
```

## 🔍 查看当前配置

```bash
# 查看所有全局配置
git config --global --list

# 查看特定配置项
git config --global user.name
git config --global user.email

# 查看当前仓库配置（在仓库目录下）
git config --list
```

## 📂 配置文件位置

- **全局配置**：`~/.gitconfig` 或 `~/.config/git/config`
- **系统配置**：`/etc/gitconfig`
- **仓库配置**：`.git/config`（在仓库内）

## 🔑 常见Git平台认证方式

### GitHub

**方式1：个人访问令牌（推荐）**
```bash
# 使用HTTPS克隆
git clone https://github.com/username/repo.git

# 推送时输入：
# Username: 你的GitHub用户名
# Password: 你的个人访问令牌
```

**方式2：SSH密钥**
```bash
# 生成SSH密钥
ssh-keygen -t ed25519 -C "your.email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 复制公钥并添加到GitHub设置中
# 使用SSH克隆
git clone git@github.com:username/repo.git
```

### GitLab

类似GitHub，支持个人访问令牌和SSH密钥。

### 自建Git服务器

通常使用用户名和密码，或SSH密钥认证。

## 🛠️ 实用Git配置

```bash
# 设置命令别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.last 'log -1 HEAD'

# 配置颜色输出
git config --global color.ui auto

# 配置推送行为
git config --global push.default simple
```

## 🔄 修改已有配置

```bash
# 重新设置用户名
git config --global user.name "New Name"

# 删除某个配置
git config --global --unset credential.helper

# 编辑配置文件
git config --global --edit
```

## 📝 针对单个仓库配置

如果只想为当前仓库配置（不使用 `--global` 参数）：

```bash
cd /path/to/your/repo

# 配置仓库级用户名
git config user.name "Project Specific Name"

# 配置仓库级邮箱
git config user.email "project@example.com"
```

## 🔐 安全建议

1. ✅ **推荐使用SSH密钥**而不是HTTPS密码
2. ✅ **使用个人访问令牌**代替账号密码
3. ✅ **定期更新访问令牌**
4. ❌ **避免在脚本中硬编码密码**
5. ❌ **不要使用 `credential.helper store`** 除非在安全环境

## 📖 示例：完整配置流程

```bash
# 1. 配置基本信息
git config --global user.name "Zhang San"
git config --global user.email "zhangsan@company.com"

# 2. 配置凭证缓存（1天）
git config --global credential.helper 'cache --timeout=86400'

# 3. 配置中文支持
git config --global core.quotepath false

# 4. 配置默认分支
git config --global init.defaultBranch main

# 5. 查看配置
git config --global --list

# 6. 克隆仓库并输入凭证
git clone https://github.com/username/repo.git
# 输入用户名和令牌，会自动缓存

# 7. 后续操作不需要再输入凭证（缓存期内）
cd repo
git pull
git push
```

## ❓ 常见问题

### Q1: 忘记了Git密码怎么办？
A: Git不存储原始密码。如果是平台账号（如GitHub），去平台重置密码或重新生成访问令牌。

### Q2: 如何查看保存的凭证？
A: 如果使用 `credential.helper store`，查看：
```bash
cat ~/.git-credentials
```

### Q3: 如何删除保存的凭证？
A: 删除凭证文件：
```bash
rm ~/.git-credentials
```

### Q4: 多个Git账号如何管理？
A: 使用SSH密钥配置，编辑 `~/.ssh/config`：
```
Host github-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_work

Host github-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_personal
```

---

**创建时间**: 2025-11-09  
**适用于**: Git 2.x 所有版本

