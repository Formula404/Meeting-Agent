# 压力测试方案

## 快速开始

### 1. 安装 k6

```bash
# Windows (Chocolatey)
choco install k6

# Windows (winget)
winget install k6

# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo apt install k6

# 或下载二进制: https://k6.io/docs/get-started/installation/
```

验证安装：

```bash
k6 version
```

### 2. 准备测试文件

在 `load-test/` 目录下放置：

| 文件 | 说明 |
|------|------|
| `sample.docx` | 测试用 Word 文档 (~100KB) |
| `sample.mp3` | 测试用音频文件 (30秒~1分钟) |

### 3. 启动服务

```bash
# 容器部署
docker start meeting-agent

# 查看日志（另一个终端）
docker logs -f meeting-agent

# 观察资源（第三个终端）
docker stats
```

### 4. 确认服务正常运行

```bash
curl http://127.0.0.1:8011/api/auth/me
```

### ⚠️ Windows 特别注意：避免 USERNAME 变量冲突

Windows 系统自带 `USERNAME` 环境变量（值为你的 Windows 登录名），脚本中 **不能用** `__ENV.USERNAME` 作为变量名，否则 k6 会取到 "Formula" 之类的值而非预期的 "admin"。

所有脚本统一改用 `K6_USER` / `K6_PASS`：

```powershell
# 正确（使用自定义变量名）
k6 run -e K6_USER=myuser -e K6_PASS=mypass round1-login.js

# 错误（Windows 上会被冲突覆盖）
k6 run -e USERNAME=admin round1-login.js    # ← 会读取系统 USERNAME
```

---

## 5 轮测试（按顺序执行）

### 第 1 轮：仅登录压测

**目的**：确认登录接口本身是否正常，建立基线。

```bash
k6 run load-test/round1-login.js
```

**判断标准**：

| 指标 | 正常 | 注意 | 异常 |
|------|------|------|------|
| P95 | <500ms | 500ms~2s | >2s |
| 失败率 | <1% | 1%~5% | >5% |

**如果登录慢**：检查数据库认证、密码校验逻辑、服务器资源。

---

### 第 2 轮：仅普通页面接口

**目的**：确认列表查询、用户信息等轻量接口是否稳定。

```bash
k6 run load-test/round2-normal.js
```

**判断标准**：

| 指标 | 正常 | 注意 | 异常 |
|------|------|------|------|
| P95 | <1s | 1s~2s | >2s |
| 失败率 | <1% | 1%~5% | >5% |

---

### 第 3 轮：仅文档上传提取

**目的**：判断 LLM 提取任务的并发瓶颈。

**逐步增加并发**：

```bash
# 1 人 → 基线
k6 run -e VUS=1 -e DURATION=3m load-test/round3-extract.js

# 2 人 → 看是否线性变慢
k6 run -e VUS=2 -e DURATION=5m load-test/round3-extract.js

# 4 人 → 看 workers/线程池是否排队
k6 run -e VUS=4 -e DURATION=5m load-test/round3-extract.js

# 8 人 → 复现故障
k6 run -e VUS=8 -e DURATION=5m load-test/round3-extract.js
```

**记录指标**：平均耗时、P95、失败率、CPU、内存、DB 连接数

---

### 第 4 轮：仅音频转写（谨慎）

**目的**：判断 ASR 上传/轮询是否拖死后端。

```bash
# 1 个转写用户
k6 run load-test/round4-transcribe.js

# 2 个转写用户
k6 run -e VUS=2 load-test/round4-transcribe.js

# ⚠️ 4 个 → 谨慎，可能触发外部 ASR 限流
k6 run -e VUS=4 load-test/round4-transcribe.js
```

**注意**：音频文件大会触发外部 ASR 费用，建议用短音频（30秒）。

---

### 第 5 轮：真实 8 人混合场景（最重要）

**目的**：复现"页面卡死、不能登录"的真实故障。

```bash
k6 run load-test/round5-mixed.js
```

**模拟场景**：6 个普通用户 + 1 个文档上传 + 1 个音频转写。

**判断重点不是重任务多快，而是**：

- 重任务运行期间，普通用户还能不能登录、翻页、查看结果？
- 普通请求 P95 是否从 <1s 变成 >10s？

---

## 通过单一脚本运行所有场景

```bash
# 登录压测
k6 run -e SCENARIO=login -e VUS=8 load-test/test.js

# 普通页面
k6 run -e SCENARIO=normal -e VUS=8 load-test/test.js

# 文档提取
k6 run -e SCENARIO=extract -e VUS=2 load-test/test.js

# 音频转写
k6 run -e SCENARIO=transcribe -e VUS=1 load-test/test.js

# 混合场景
k6 run -e SCENARIO=mixed load-test/test.js
```

---

## 压测期间同步观察

### 终端 1：容器日志（查看 PERF/STAGE 日志）

```bash
docker logs -f meeting-agent | findstr "PERF\|STAGE"
```

预期输出示例：

```
14:30:01 [perf] INFO PERF method=POST path=/api/auth/login cost=0.123s
14:30:05 [perf] INFO PERF method=GET path=/api/results cost=0.231s
14:30:10 [perf] INFO PERF method=POST path=/api/extract cost=28.532s
14:30:10 [perf] INFO STAGE save_file cost=0.214s
14:30:10 [perf] INFO STAGE llm_extract cost=18.325s
14:30:10 [perf] INFO STAGE db_write cost=0.118s
14:31:00 [perf] INFO PERF method=POST path=/api/transcribe cost=132.482s
14:31:00 [perf] INFO STAGE save_audio cost=0.512s
14:31:00 [perf] INFO STAGE tflink_upload cost=5.832s
14:31:00 [perf] INFO STAGE asr_create_task cost=0.341s
14:31:00 [perf] INFO STAGE asr_polling task_id=12345 cost=72.441s
14:31:00 [perf] INFO STAGE llm_generate cost=18.325s
14:31:00 [perf] INFO STAGE db_write cost=0.095s
```

**关键判断**：如果 transcribe 运行期间，login 从 0.1s 变成 10s、30s、timeout → 长任务阻塞事件循环。

### 终端 2：Docker 资源监控

```bash
docker stats
```

重点看：

| 现象 | 判断 |
|------|------|
| CPU 20%，但请求超时 | 阻塞/外部 API 等待/连接池问题 |
| CPU 100%，请求变慢 | 计算密集或 worker 不够 |
| 内存持续上涨 | 文件/缓存泄漏 |
| BLOCK I/O 很高 | 磁盘 I/O 瓶颈 |

### 终端 3：PostgreSQL 连接监控

```bash
docker exec -it meeting-agent-db psql -U meeting_user -d meeting_db
```

```sql
-- 查看连接状态分布
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- 查看具体连接详情
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - query_start AS duration,
       left(query, 120) AS query
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY duration DESC;
```

**重点观察**：

| 现象 | 说明 |
|------|------|
| active 多，duration 长 | SQL 本身慢，或长事务 |
| idle in transaction 多 | 事务未提交/回滚 |
| 连接数接近 10 | 连接池耗尽 |

---

## 结果解读

### k6 输出示例

```
http_req_duration...: avg=1.23s min=20ms med=200ms p(90)=3.5s p(95)=8.9s
http_req_failed.....: 12.00%
checks...............: 88.00%
```

### 关键指标

| 指标 | 说明 | 目标 |
|------|------|------|
| `http_req_failed` | 请求失败率 | <1% 好，1%~5% 有风险，>5% 不可接受 |
| `p(95)` | 95% 请求在此时间内完成 | 登录/列表 <1s，提取 <60s |
| 普通请求是否被拖慢 | 单独测 vs 混合测对比 | 混合时不应显著变慢 |
| 服务器资源 | CPU/内存/DB 连接 | CPU 不高但卡 = 阻塞问题 |

### 故障诊断对照表

| 现象 | 可能原因 |
|------|----------|
| 1 人快，2 人明显变慢 | 外部 LLM/ASR 限流或单进程阻塞 |
| 1 人上传时登录也慢 | 事件循环阻塞或 worker 被占 |
| 4 人上传后 DB 连接满 | 连接持有时间过长 |
| CPU 不高但请求卡 | I/O 等待、外部 API 等待、阻塞 |
| CPU 高且内存高 | worker/并发需控制 |
