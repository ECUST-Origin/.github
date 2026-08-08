<div align="center">

![](https://github.com/ECUST-Origin/.github/raw/main/assets/dashboard.png)

<sub>由 GitHub Action 驱动  ·  自动更新  ·  每周刷新 PNG</sub>

</div>

---

## 迁移指南

### 一、个人仓库迁移到 ECUST-Origin 组织

适用于：把原本在自己账号下的项目以个人/原作者身份迁入组织，保留完整的 git 历史、issue、PR、release、wiki、star、watcher。

#### 1. 前提条件

| 条件 | 说明 |
| --- | --- |
| 你是仓库 owner | 个人账号下拥有该仓库的管理权限 |
| 你是组织成员 | 至少是 `ECUST-Origin` 的 `Member`（创建仓库需要 `Owner`） |
| 组织已存在仓库 | 如果同名仓库已经在组织中存在，需要先处理冲突（见 §4） |
| 本地工作区干净 | `git status` 无未提交修改，或已 stash |

#### 2. 标准流程（推荐）

```bash
# 1. 在 GitHub 网页上操作：把仓库从个人账号转让到组织
#    Settings -> Danger Zone -> Transfer ownership
#    New owner: ECUST-Origin
#    确认后会重定向，原 URL 永久 301 跳转到新地址

# 2. 替换本地 remote（旧的 remote 会失效）
git remote set-url origin https://github.com/ECUST-Origin/<repo>.git

# 3. 拉取新仓库的元数据并验证
git fetch --all --prune
git log --oneline -5          # 确认历史完整
git remote -v                 # 确认 origin 已更新

# 4. 推送可能的本地分支
git push --all
git push --tags
```

转让后 GitHub 会自动：
- 把所有 issue、PR、release、tag、wiki 一起迁过去
- 给所有 star / watch 的人发邮件通知
- 在原 URL 设置 301 重定向（**保留外链和 SEO**）
- 在所有 issue / PR 评论里把头像链接改成组织头像

#### 3. 特殊场景处理

**3.1 同名仓库冲突**

如果 `ECUST-Origin/<repo>` 已经存在，Transfer 按钮会报错。两种处理方式：

- 让组织 Owner 先重命名已有仓库
- 或者把个人仓库在本地 `git remote rename` 后再转让（无效——URL 是 GitHub 端决定的）

**3.2 包含 GitHub Actions / Secrets**

- 转让后，仓库的 **Secrets 不会迁移**，需要在组织里重新配置
- 组织的 Secrets 设置路径：`Organization -> Settings -> Secrets and variables -> Actions`
- 如果用了 PAT，转让后 PAT 的 owner 仍然是个人账号，建议重新生成组织专属的 PAT

**3.3 GitHub Pages 站点**

- 转让后 Pages 站点可能短暂不可用（5-30 分钟 DNS 刷新）
- 自定义域名需要在 `Settings -> Pages -> Custom domain` 重新验证
- 如果原 Pages 是用 `username.github.io/<repo>` 这种 user-page 路径，需要改成 `org-name.github.io/<repo>`

**3.4 LFS / 大文件**

- Git LFS 存储属于账号级，转让后 LFS 数据仍归个人账号，但 LFS 指针文件会随仓库一起迁移
- 建议在转让前确认个人账号有足够 LFS 配额（免费 1GB），否则后续 push 会失败
- 转让完成后用 `git lfs fetch --all` 验证一遍

**3.5 受保护的分支 / 规则**

- 转让后仓库继承**组织级别**的规则集（如果组织配置了）
- 个人级别的 ruleset 不会带过去
- 转让前在 `Settings -> Rules -> Rulesets` 截图备份配置

**3.6 GitHub Apps / Webhooks**

- 安装在仓库上的 GitHub Apps 不会自动转移
- 转让后需要组织 Owner 重新安装这些 App
- Webhook 会随仓库迁移，但 secret 会被重置，需要在接收端更新

**3.7 已经 fork 过的人**

- 已 fork 的仓库会变成 "fork 指向新地址"，但 fork 关系本身可能丢失
- 建议提前通知所有 contributor 重新 fork
- 或者在 issue 里发通知：`This repo has been moved to https://github.com/ECUST-Origin/<repo>`

**3.8 协作者 / 写入权限**

- 转让后，**所有协作者会被清空**（因为他们对你的个人仓库有权限，但默认对组织没权限）
- 需要在转让后重新邀请他们成为组织成员 / 仓库 collaborator
- 提示：让协作者先加入组织（`https://github.com/orgs/ECUST-Origin/people`）再转让

**3.9 私有仓库 + 付费功能**

- 转让私有仓库到组织，**会消耗组织的私有仓库额度**
- 如果组织在免费 plan 上没有空余私有仓库槽位，会失败
- 建议在转让前让组织 Owner 在 `Settings -> Billing` 确认额度

#### 4. 转让失败的常见原因

| 错误提示 | 原因 | 解决办法 |
| --- | --- | --- |
| `Repository transfer failed: A repository with this name already exists` | 同名冲突 | 重命名或删除已有仓库 |
| `You do not have permission to transfer this repository` | 你不是 owner | 联系当前 owner 转让给你 |
| `Organization has reached its member limit` | 组织成员上限 | 升级 plan 或移除不活跃成员 |
| `Two-factor authentication required` | 你没开 2FA | 在 `Settings -> Password and authentication` 开启 |

#### 5. 验证清单

完成转让后，**逐项检查**：

- [ ] `git remote -v` 指向新地址
- [ ] `git push` 成功（如果不是只读）
- [ ] GitHub 网页能打开新仓库
- [ ] 所有 issue / PR 都在
- [ ] 所有 release / tag 都在
- [ ] star 数一致
- [ ] Actions 可以手动触发一次（如果之前有）
- [ ] Pages 站点能访问（如果之前有）
- [ ] Webhook 收到测试事件（如果之前有）
- [ ] 在原 URL 访问会 301 跳到新 URL

---

### 二、已有组织迁移为组织的子部门仓库

适用于：你已经在用其他组织（个人组织、临时组织、RoboMaster 其他战队组织），现在要把整个组织（或部分子团队）整合到 `ECUST-Origin` 旗下。

#### 1. 整体方案对比

| 方案 | 难度 | 适用场景 | 是否保留历史 |
| --- | --- | --- | --- |
| **A. 整组织转让** | 低 | 旧组织里所有仓库都要迁过来 | ✅ 完整保留 |
| **B. 仓库逐个转让** | 中 | 只迁部分仓库 | ✅ 完整保留 |
| **C. 镜像 + 重建** | 高 | 旧组织不想被改动 | ⚠️ 仅 git 历史 |
| **D. 导出 archive 后导入** | 高 | 需要脱机 / 备份 | ❌ 只保留代码 |

**下面只讲 A 和 B 两种最常用方案。**

#### 2. 方案 A：把整个旧组织转让到 ECUST-Origin

**注意**：GitHub **不允许直接把一个组织转让给另一个组织**。只能把组织里**每个仓库逐个**转让到新组织，然后让成员重新加入新组织。

```bash
# 步骤 1：在旧组织里，列出所有仓库
gh repo list <old-org> --limit 1000 > old-repos.txt

# 步骤 2：批量转让（用 GitHub API）
# 在 https://github.com/settings/tokens 生成一个有 repo: 所有权限的 PAT
# 然后用脚本批量调用（参考 §3 的脚本）
```

转让完成后：
- 旧组织的成员、teams、settings 全部丢失
- 需要在新组织里重新创建 teams 并分配权限
- Secrets、Apps 全部要重新配置

#### 3. 方案 B：仓库逐个转让（推荐）

**3.1 批量转让脚本**

在 `https://github.com/settings/tokens` 生成 PAT（勾选 `repo` 全部 + `admin:org` + `delete_repo`），然后：

```bash
#!/usr/bin/env bash
# transfer_repos.sh — 把 OLD_ORG 下所有仓库批量转让到 NEW_ORG
set -euo pipefail

OLD_ORG="your-old-org"
NEW_ORG="ECUST-Origin"
TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

for repo in $(gh repo list "$OLD_ORG" --limit 1000 --json name -q '.[].name'); do
  echo "==> Transferring $OLD_ORG/$repo -> $NEW_ORG"
  curl -X POST \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$OLD_ORG/$repo/transfer" \
    -d "{\"new_owner\":\"$NEW_ORG\",\"new_name\":\"$repo\"}"
  sleep 2  # 防止 rate limit
done
```

**3.2 Teams 重建**

组织转让不会带 teams，需要在新组织里手动重建：

```bash
# 列出旧组织的 teams
gh api "/orgs/$OLD_ORG/teams" --jq '.[].name'

# 在新组织里批量创建
for team in Mechanical Vision Algorithm Embedded Web PM; do
  gh api -X POST "/orgs/$NEW_ORG/teams" \
    -f name="$team" \
    -f description="Migrated from $OLD_ORG" \
    -f privacy=closed
done
```

**3.3 成员重新邀请**

```bash
# 导出旧组织成员
gh api "/orgs/$OLD_ORG/members" --jq '.[].login' > members.txt

# 批量邀请
while read user; do
  gh api -X PUT "/orgs/$NEW_ORG/memberships/$user" \
    -f role=member
done < members.txt
```

#### 4. 子部门仓库的特殊命名建议

为了让组织结构清晰，建议按以下规则命名子部门仓库：

```
ECUST-Origin/
├── .github                      # 组织主页 + 集中配置
├── docs                         # 公共文档
├── website                      # 官网 / Pages
├── team-handbook                # 队员手册
├── recruitment                  # 招新资料
├── mech-<robot-name>            # 机械组
├── electrical-<robot-name>      # 电气组
├── algorithm-<robot-name>       # 算法组
├── vision-<robot-name>          # 视觉组
├── embedded-<robot-name>        # 嵌入式组
└── web-<topic>                  # 前端 / 后端
```

**命名约定**：
- 全部小写、用 `-` 分隔单词
- 不带年份（避免每年改名）
- 私有仓库以 `-internal` 结尾
- 实验性仓库以 `-prototype` 结尾
- 已弃用仓库 transfer 到 `ECUST-Origin-archive` 组织而不是直接删

#### 5. 标签（Labels）规范

为了让所有子部门仓库的 issue / PR 分类统一，建议使用以下标签体系：

**5.1 类型标签（必须）**

| 标签 | 颜色 | 用途 |
| --- | --- | --- |
| `bug` | `#d73a4a` | 确认的 bug |
| `feature` | `#a2eeef` | 新功能 |
| `enhancement` | `#84b6eb` | 对已有功能的改进 |
| `docs` | `#0075ca` | 仅文档修改 |
| `test` | `#bfd4f2` | 仅测试修改 |
| `chore` | `#fef2c0` | 工具 / 构建 / CI 修改 |
| `refactor` | `#fbca04` | 重构（不增加功能也不修 bug） |
| `perf` | `#f97316` | 性能优化 |

**5.2 优先级标签（建议）**

| 标签 | 颜色 | 用途 |
| --- | --- | --- |
| `P0` | `#b60205` | 阻塞，必须立即处理 |
| `P1` | `#d93f0b` | 重要，48 小时内 |
| `P2` | `#fbca04` | 普通，本周内 |
| `P3` | `#0e8a16` | 不急，方便时处理 |

**5.3 状态标签（建议）**

| 标签 | 颜色 | 用途 |
| --- | --- | --- |
| `in-progress` | `#ededed` | 正在做 |
| `blocked` | `#b60205` | 被阻塞 |
| `needs-review` | `#0e8a16` | 等 review |
| `needs-info` | `#d4c5f9` | 缺信息 |
| `wontfix` | `#ffffff` | 不修 |

**5.4 子部门标签（强烈建议）**

| 标签 | 颜色 | 用途 |
| --- | --- | --- |
| `mech` | `#5319e7` | 机械组相关 |
| `electrical` | `#1d76db` | 电气组相关 |
| `algorithm` | `#006b75` | 算法组相关 |
| `vision` | `#e99695` | 视觉组相关 |
| `embedded` | `#bfd4f2` | 嵌入式组相关 |
| `web` | `#7057ff` | 前端 / 后端 |

**5.5 一键导入标签**

把下面 JSON 保存为 `labels.json`，然后执行：

```bash
# 用 gh CLI 一键同步
gh label sync --file labels.json --repo ECUST-Origin/<repo>

# 或者用 API
gh api -X POST "/repos/ECUST-Origin/<repo>/labels" --input labels.json
```

```json
[
  {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
  {"name": "feature", "color": "a2eeef", "description": "New feature"},
  {"name": "enhancement", "color": "84b6eb", "description": "Improvement to existing feature"},
  {"name": "docs", "color": "0075ca", "description": "Documentation only"},
  {"name": "test", "color": "bfd4f2", "description": "Tests only"},
  {"name": "chore", "color": "fef2c0", "description": "Tooling / build / CI"},
  {"name": "refactor", "color": "fbca04", "description": "Code refactor"},
  {"name": "perf", "color": "f97316", "description": "Performance"},
  {"name": "P0", "color": "b60205", "description": "Critical, fix immediately"},
  {"name": "P1", "color": "d93f0b", "description": "Important, within 48h"},
  {"name": "P2", "color": "fbca04", "description": "Normal, this week"},
  {"name": "P3", "color": "0e8a16", "description": "Low priority"},
  {"name": "in-progress", "color": "ededed", "description": "Work in progress"},
  {"name": "blocked", "color": "b60205", "description": "Blocked by something"},
  {"name": "needs-review", "color": "0e8a16", "description": "Waiting for review"},
  {"name": "needs-info", "color": "d4c5f9", "description": "More information needed"},
  {"name": "wontfix", "color": "ffffff", "description": "Will not be fixed"},
  {"name": "mech", "color": "5319e7", "description": "Mechanical subteam"},
  {"name": "electrical", "color": "1d76db", "description": "Electrical subteam"},
  {"name": "algorithm", "color": "006b75", "description": "Algorithm subteam"},
  {"name": "vision", "color": "e99695", "description": "Vision subteam"},
  {"name": "embedded", "color": "bfd4f2", "description": "Embedded subteam"},
  {"name": "web", "color": "7057ff", "description": "Web / frontend / backend"}
]
```

#### 6. 仓库分类（按可见性 + 用途）

| 类别 | 命名后缀 | 默认权限 | 用途 |
| --- | --- | --- | --- |
| `team-core` | 无 | 私有 | 比赛代码、核心算法 |
| `team-internal` | `-internal` | 私有 | 内部工具、训练数据 |
| `team-public` | 无 | 公开 | 文档、官网、招新 |
| `experiment` | `-prototype` | 私有 | 试错项目，3 个月不动转 archive |
| `archive` | 无（放到 `ECUST-Origin-archive`） | 公开 | 退役机器人代码 |

#### 7. 整体迁移 checklist

- [ ] 盘点旧组织所有仓库（`gh repo list`）
- [ ] 分类：核心 / 内部 / 公开 / 实验 / 归档
- [ ] 通知所有成员即将迁移（提前一周）
- [ ] 生成 PAT 用于批量 API 调用
- [ ] 备份数据库 / LFS / 重要二进制（`git bundle` 或 clone --bare）
- [ ] 按 §3.3 脚本批量转让仓库
- [ ] 同步标签（§5.5）
- [ ] 重建 teams（§3.2）
- [ ] 重新邀请成员（§3.3）
- [ ] 重新配置 Secrets / Apps / Webhooks
- [ ] 在 README 里标注 "Migrated from `<old-org>`"
- [ ] 旧组织设置 301 跳转说明（把旧仓库 archive 并在 README 写新地址）
- [ ] 旧组织 Owner 离职 / 转让给团队，避免再次成为孤岛
- [ ] 监控一周：看新组织有没有遗漏的引用、外链

#### 8. 出问题怎么办

| 问题 | 原因 | 解决 |
| --- | --- | --- |
| 转让按钮变灰 | 你不是组织 Owner | 联系组织 Owner 转让 |
| 转让后 git push 失败 | 本地 remote 仍是旧 URL | `git remote set-url origin ...` |
| 转让后 Actions 跑不起来 | Secrets 没迁 | 在新组织 Secrets 里重新配置 |
| 转让后 PR 提不上去 | 协作者权限没了 | 把协作者加入新组织 |
| 转让后 LFS 报错 | 配额 / 文件指针 | `git lfs fetch --all && git lfs push --all` |
| 转让后 404 | DNS 还在刷新 | 等 30 分钟再访问 |

---

<sub>最后更新：2026-08-07 · 由 ECUST-Origin 维护 · 欢迎 PR 补充更多场景</sub>
