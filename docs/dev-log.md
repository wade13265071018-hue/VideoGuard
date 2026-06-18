# VideoGuard 项目开发日志

> 用途：记录每日项目进展、验证结果、问题处理和下一步计划，可作为课程实训日报、周报和最终报告素材。

## 2026-06-08

### 今日目标

- 根据课程设计要求，搭建 VideoGuard 短视频内容审核管理系统的项目基础结构。
- 完成三端服务的最小可运行版本。
- 完成 AI 分析服务 MVP。
- 完成后端视频上传、视频查询和 MySQL 入库的第一版。
- 配置 GitHub 仓库，方便与队友协作开发。
- 打通 SpringBoot 调用 FastAPI 的 AI 分析链路。
- 完成前端真实接口接入，让上传、列表、详情、AI 分析流程可交互验证。

### 完成工作

1. 项目初始化
   - 在 `D:\zaproject\Real_Projects\VideoGuard` 创建正式项目目录。
   - 建立 monorepo 结构：
     - `backend-springboot`
     - `ai-service-fastapi`
     - `frontend-vue`
     - `docs`
     - `sql`
     - `samples`
   - 编写 `README.md`，记录项目介绍、技术栈、目录结构、启动方式和文档索引。
   - 编写 `.gitignore`，忽略 `uploads`、模型文件、依赖目录、构建产物和日志。
   - 编写 `AGENTS.md`，记录协作规则和模块边界。

2. Git 与 GitHub 协作配置
   - 初始化本地 Git 仓库。
   - 创建 `main` 和 `dev` 分支。
   - 配置 GitHub 远程仓库：`git@github.com:wade13265071018-hue/VideoGuard.git`。
   - 生成并配置 GitHub SSH key。
   - 成功推送 `main` 和 `dev` 分支。

3. 三端最小服务
   - SpringBoot 后端：
     - 新增 `/api/health`
     - 本地运行端口：`8080`
   - FastAPI AI 服务：
     - 新增 `/ai/health`
     - 本地运行端口：`8000`
   - Vue 前端：
     - 创建 Vue 3 + Vite + Element Plus 骨架。
     - 创建基础页面和路由：
       - `/dashboard`
       - `/upload`
       - `/videos`
       - `/review`
       - `/login`
     - 本地运行端口：`5173`

4. 数据库设计与初始化
   - 编写 `sql/schema.sql`，创建 7 张核心表：
     - `user`
     - `video`
     - `video_frame`
     - `sensitive_word`
     - `sensitive_hit`
     - `ai_review_result`
     - `review_log`
   - 编写 `sql/seed.sql`，插入测试用户和敏感词。
   - 确认本地 MySQL 配置：
     - 用户名：`root`
     - 密码：`1234`
   - 创建数据库 `video_guard`。
   - 成功导入表结构和测试数据。

5. FastAPI AI 分析 MVP
   - 实现 `/ai/metadata`：提取视频时长、分辨率、fps、文件大小。
   - 实现 `/ai/extract-frames`：按固定间隔抽取关键帧。
   - 实现 `/ai/text-detect`：标题、描述、ASR 文本敏感词检测。
   - 实现 `/ai/image-detect`：图像风险识别 MVP，支持规则模拟。
   - 实现 `/ai/analyze`：组合元数据、抽帧、文本检测、图像检测和风险评分。
   - 风险等级规则：
     - `PASS`：风险分 `< 30`
     - `SUSPICIOUS`：`30 <= 风险分 < 70`
     - `VIOLATION`：风险分 `>= 70`

6. SpringBoot 视频基础接口
   - 接入 Spring Data JPA 和 MySQL。
   - 新增 `Video` 实体和 `VideoRepository`。
   - 实现 `POST /api/videos/upload`：
     - 支持 `mp4`、`mov`、`avi`
     - 保存文件到项目级 `uploads/videos`
     - 使用 UUID 文件名避免重名
     - 写入 `video` 表
   - 实现 `GET /api/videos`：
     - 支持按 `status` 和 `aiRiskLevel` 筛选
   - 实现 `GET /api/videos/{id}`：
     - 返回视频详情
     - 返回 AI 结果、关键帧、敏感词命中、审核日志预留字段
   - 实现 `/uploads/**` 静态资源映射，支持视频播放和关键帧访问。
   - 实现 `GET /api/videos/{id}/play` 播放跳转接口。

7. SpringBoot 调用 FastAPI 并持久化 AI 结果
   - 新增实体：
     - `SensitiveWord`
     - `VideoFrame`
     - `SensitiveHit`
     - `AiReviewResult`
   - 新增对应 Repository。
   - 实现 `POST /api/videos/{id}/analyze`：
     - 查询视频记录
     - 查询启用的敏感词
     - 调用 FastAPI `/ai/analyze`
     - 保存视频元数据到 `video`
     - 保存关键帧到 `video_frame`
     - 保存敏感词命中到 `sensitive_hit`
     - 保存 AI 分析结果到 `ai_review_result`
     - 根据风险等级更新视频状态
   - 更新详情接口，使其返回完整 AI 初审证据。

8. 前端真实接口接入
   - 后端 `WebConfig` 增加 `/api/**` 跨域配置，允许 `http://localhost:5173` 调用 SpringBoot 接口。
   - 新增 `frontend-vue/src/api/client.js`，统一封装：
     - `uploadVideo`
     - `analyzeVideo`
     - `fetchVideos`
     - `fetchVideoDetail`
     - `toAssetUrl`
   - 更新前端路由，新增 `/videos/:id` 视频详情页。
   - 更新上传页面：
     - 支持选择视频文件
     - 支持填写标题、描述、上传人 ID
     - 上传成功后可直接触发 AI 分析
     - 分析完成后跳转视频详情页
   - 更新视频管理页面：
     - 接入真实视频列表接口
     - 支持按处理状态和风险等级筛选
     - 支持进入详情和重新分析
   - 新增视频详情页面：
     - 展示视频播放器
     - 展示处理状态、风险等级、风险分、视频时长
     - 展示 AI 分析结果
     - 展示敏感词命中
     - 展示视频抽帧

9. 文档维护
   - 更新 `docs/api.md`，补充 SpringBoot 和 FastAPI 接口说明。
   - 更新 `docs/database.md`，说明核心表职责。
   - 创建 `docs/demo-script.md`，记录后续 5 分钟演示流程草稿。
   - 创建 `docs/collaboration-guide.md`，说明队友如何使用 Git/GitHub 一起编辑项目。
   - 创建 `docs/project-progress.md`，说明当前项目进展、里程碑和待办任务。
   - 创建 `docs/acceptance-test-guide.md`，说明如何启动项目并进行页面/接口验收。
   - 重写 `docs/dev-log.md`，修复历史乱码，使其可直接作为汇报材料。

10. 开发环境整理
   - 打开 IDEA 项目。
   - 使用可见 PowerShell 窗口运行三端服务，便于观察日志。
   - 按用户要求清理不必要的 PowerShell 窗口，仅保留必要服务窗口：
     - `VideoGuard SpringBoot :8080`
     - `VideoGuard FastAPI :8000`
     - `VideoGuard Vue :5173`

### 验证结果

- `mvn -DskipTests package`：通过。
- Vue 构建 `npm run build`：通过。
- FastAPI 依赖安装与导入检查：通过。
- MySQL 数据库：
  - `video_guard` 创建成功。
  - 7 张表创建成功。
  - 测试用户导入成功。
  - 敏感词导入成功。
- 服务健康检查：
  - `http://localhost:8080/api/health` 返回 `{"status":"ok"}`
  - `http://localhost:8000/ai/health` 返回 `{"status":"ok"}`
  - `http://localhost:5173/videos/5` 返回 `200`
- 视频上传验证：
  - 上传测试 MP4 成功。
  - `video` 表产生记录。
  - `/api/videos` 可查询列表。
  - `/api/videos/{id}` 可查询详情。
  - `/uploads/videos/{filename}.mp4` 静态访问返回 `200`。
- AI 分析验证：
  - 对测试视频 ID `5` 调用 `POST /api/videos/5/analyze` 成功。
  - 分析后 `video` 表更新结果：
    - `status = AI_SUSPICIOUS`
    - `ai_risk_level = SUSPICIOUS`
    - `ai_risk_score = 40`
    - `duration = 2`
    - `width = 320`
    - `height = 180`
    - `fps = 10`
  - `video_frame` 表写入 1 条关键帧记录。
  - `sensitive_hit` 表写入 1 条敏感词命中记录。
  - `ai_review_result` 表写入 1 条 AI 审核结果记录。
  - 关键帧静态访问验证通过：`/uploads/frames/5/frame_0000.jpg` 返回 `200`。
- 前端联调验证：
  - `GET /api/videos?aiRiskLevel=SUSPICIOUS` 可返回测试视频。
  - `GET /api/videos/5` 可返回 AI 分析结果、关键帧和敏感词命中。
  - CORS 检查通过：`Origin=http://localhost:5173` 时，后端返回 `Access-Control-Allow-Origin=http://localhost:5173`。
  - 冒烟测试上传视频 ID `7`：
    - 上传状态：`UPLOADED`
    - 分析后状态：`AI_PASSED`
    - 风险等级：`PASS`
    - 风险分：`5`
    - 关键帧数量：`1`
    - 敏感词命中数量：`0`

### 遇到的问题与处理

1. 端口占用
   - 问题：`8080` 被其他本地应用占用。
   - 处理：经确认允许后释放 `8080`，将 SpringBoot 恢复到标准端口 `8080`。

2. GitHub HTTPS 无法连接
   - 问题：本机到 GitHub `443` 端口连接失败。
   - 处理：改用 SSH 推送，生成 SSH key 并添加到 GitHub，最终推送成功。

3. MySQL 密码不确定
   - 问题：初始尝试 `root/root` 和空密码失败。
   - 处理：确认本机 MySQL 密码为 `1234`。

4. seed 中文导入乱码
   - 问题：MySQL 客户端导入中文敏感词时字符集不正确。
   - 处理：在 `seed.sql` 中加入 `SET NAMES utf8mb4;`，并在 README 中记录导入时使用 `--default-character-set=utf8mb4`。

5. Windows PowerShell 中文显示乱码
   - 问题：PowerShell 测试 multipart 中文字段、JSON 响应时，控制台显示可能为乱码。
   - 处理：使用数据库 HEX、浏览器页面和 UTF-8 读取方式确认实际数据正确；在验收指南中提示优先用浏览器、Postman/Apifox 或 Python 测试中文。

6. 前端上传返回字段不一致
   - 问题：上传接口返回字段为 `videoId`，前端初始写法误用 `id`。
   - 处理：修正上传页逻辑，使用 `videoId` 触发 AI 分析和跳转详情页。

7. 前端筛选枚举与后端状态不一致
   - 问题：前端初始使用 `AI_PASS`、`AI_REJECTED`，后端实际状态为 `AI_PASSED`、`AI_VIOLATION`。
   - 处理：修正视频管理页筛选值。

### Git 提交记录

已完成并推送的历史提交：

- `de572b8 chore: initialize VideoGuard project`
- `0cc39f3 chore: lock frontend dependencies`
- `33d0abe feat: implement FastAPI analysis MVP`
- `40517b3 chore: merge remote initial history`
- `1b69e4d feat: add video upload APIs`
- `95033b9 fix: support local MySQL and multipart text encoding`
- `55e6c28 feat: persist AI analysis results`
- `3a4bc81 docs: record AI analysis progress`

本次前端联调和文档拆分待提交。

### 当前项目状态

- `main`：已推送到 GitHub，作为稳定基础版本。
- `dev`：已推送到 GitHub，包含最新开发进展；本次前端联调和文档拆分即将提交。
- 当前主要功能完成度：
  - 项目骨架：完成
  - GitHub 协作：完成
  - FastAPI AI MVP：完成
  - SpringBoot 视频上传/列表/详情：完成
  - SpringBoot 调用 FastAPI 并入库：完成
  - MySQL 接入：完成
  - 前端真实接口接入：完成
  - 人工复审：未开始
  - 统计看板真实数据：未开始
  - 登录与角色：未开始

### 下一步计划

1. 实现人工复审模块
   - 查询待复审视频。
   - 审核员提交最终结论。
   - 写入 `review_log`。
   - 更新视频最终审核状态。

2. 实现统计看板真实数据
   - 总视频数。
   - 待复审数量。
   - 风险等级分布。
   - 每日上传趋势。
   - 违规类别分布。

3. 实现登录与角色
   - 简化登录。
   - 区分普通用户、审核员、管理员。

4. 整理演示材料
   - 准备正常视频和风险视频。
   - 完善 5 分钟演示脚本。
   - 整理课程报告中的系统架构、数据库设计和核心代码说明。

## 2026-06-08 人工复审模块第一版完成

### 本次目标

- 实现人工复审后端接口。
- 实现人工复审前端工作台。
- 将人工复审结果写入 `video` 表和 `review_log` 表。
- 更新项目进展、API 文档和交互验收指南。

### 完成工作

- 新增 `ReviewLog` 实体，对应数据库 `review_log` 表。
- 新增 `ReviewLogRepository`。
- 新增复审 DTO：
  - `ReviewSubmitRequest`
  - `ReviewLogResponse`
- 新增 `ReviewService`：
  - 查询待复审任务。
  - 查询复审详情。
  - 提交人工复审结论。
  - 查询复审日志。
- 新增 `ReviewController`：
  - `GET /api/review/tasks`
  - `GET /api/review/tasks/{videoId}`
  - `POST /api/review/tasks/{videoId}/submit`
  - `GET /api/review/logs/{videoId}`
- 更新 `VideoService.detail`，让视频详情返回复审日志。
- 更新 `VideoDetailResponse`，将 `reviewLogs` 调整为结构化复审日志列表。
- 更新前端 API 客户端，新增复审相关方法：
  - `fetchReviewTasks`
  - `fetchReviewTask`
  - `submitReview`
  - `fetchReviewLogs`
- 重写 `ReviewView.vue`：
  - 左侧展示待复审任务列表。
  - 右侧展示视频播放器、AI 风险信息、敏感词命中。
  - 支持填写审核员 ID、复审结论和审核意见。
  - 支持提交复审并刷新复审日志。
- 更新 `VideoDetailView.vue`，展示复审日志。
- 更新 `docs/api.md`、`docs/project-progress.md`、`docs/acceptance-test-guide.md`。

### 验证结果

- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- SpringBoot 重启成功，`http://localhost:8080/api/health` 返回正常。
- Vue 页面 `http://localhost:5173/review` 返回 `200`。
- `GET /api/review/tasks` 可返回待复审任务，当前保留视频 ID `5` 作为可疑样例。
- 复审冒烟测试视频 ID `8`：
  - 提交人工复审成功。
  - 提交后状态：`MANUAL_REJECTED`
  - 最终结论：`REJECT`
  - `review_log` 可查询到复审记录。

### 当前项目状态

- 人工复审第一版已完成。
- 现在系统已具备课程演示中的核心闭环：

```text
视频上传 -> AI 分析 -> 证据入库 -> 人工复审 -> 复审日志入库 -> 视频最终结论更新
```

### 下一步计划

- 开始实现统计看板真实数据：
  - 总视频数。
  - 待复审数量。
  - 风险等级分布。
  - 每日上传趋势。
  - 敏感词类别分布。

## 2026-06-08 统计看板真实数据第一版完成

### 本次目标

- 实现统计看板后端接口。
- 将 Vue 统计看板从静态占位改为真实数据库数据。
- 使用图表展示视频审核进展和风险分布。

### 完成工作

- 新增统计 DTO：
  - `CountItemResponse`
  - `StatisticsOverviewResponse`
- 新增 `StatisticsService`。
- 新增 `StatisticsController`。
- 在 `VideoRepository` 中新增聚合查询：
  - 今日上传数量。
  - 待复审数量。
  - 已人工复审数量。
  - AI 通过数量。
  - 风险等级分布。
  - 处理状态分布。
  - 近 7 日上传趋势。
- 在 `SensitiveHitRepository` 中新增敏感类别分布统计。
- 前端 API 客户端新增统计接口方法。
- 重写 `DashboardView.vue`：
  - 顶部指标展示总视频数、今日上传、AI 通过率、待复审、已人工复审。
  - 使用 ECharts 展示风险等级分布。
  - 使用 ECharts 展示近 7 日上传趋势。
  - 使用 ECharts 展示处理状态分布。
  - 使用 ECharts 展示敏感类别分布。
- 更新 `docs/api.md`、`docs/project-progress.md`、`docs/acceptance-test-guide.md` 和本开发日志。

### 验证结果

- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- 修复一次 JPQL 日期聚合查询问题：`date_format` 返回类型需显式 `cast(... as string)`，否则 SpringBoot 启动时 Repository 查询校验失败。
- SpringBoot 重启成功，`http://localhost:8080/api/health` 返回正常。
- Vue 页面 `http://localhost:5173/dashboard` 返回 `200`。
- 统计接口验证结果：
  - `GET /api/statistics/overview` 返回：
    - `totalVideos = 5`
    - `todayUploads = 5`
    - `pendingReviews = 1`
    - `manualReviewed = 1`
    - `aiPassRate = 60.0`
  - `GET /api/statistics/risk-distribution` 返回 `PASS`、`SUSPICIOUS`。
  - `GET /api/statistics/status-distribution` 返回 `AI_PASSED`、`AI_SUSPICIOUS`、`MANUAL_REJECTED`。
  - `GET /api/statistics/daily-upload?days=7` 返回 `2026-06-08` 当日上传数量。
  - `GET /api/statistics/category-distribution` 返回 `violence` 类别命中数量。

### 当前项目状态

- 统计看板真实数据第一版已完成。
- 系统已具备课程演示需要的主要业务闭环：

```text
视频上传 -> AI 分析 -> 证据入库 -> 人工复审 -> 复审日志入库 -> 统计看板汇总展示
```

### 下一步计划

- 实现简化登录与角色展示。
- 实现敏感词管理第一版。
- 整理最终演示脚本和课程报告材料。

## 2026-06-08 敏感词管理第一版完成

### 本次目标

- 实现敏感词管理后端接口。
- 实现前端“敏感词管理”页面。
- 让 AI 分析使用的敏感词库可以通过页面维护。

### 完成工作

- 新增敏感词 DTO：
  - `SensitiveWordRequest`
  - `SensitiveWordResponse`
- 新增 `SensitiveWordService`。
- 新增 `SensitiveWordController`。
- 扩展 `SensitiveWordRepository`，支持动态筛选。
- 后端新增接口：
  - `GET /api/sensitive-words`
  - `POST /api/sensitive-words`
  - `PUT /api/sensitive-words/{id}`
  - `DELETE /api/sensitive-words/{id}`
- 前端 API 客户端新增敏感词管理方法。
- 新增 `SensitiveWordsView.vue`：
  - 支持按类别和启用状态筛选。
  - 支持新增敏感词。
  - 支持编辑敏感词。
  - 支持启用/停用敏感词。
  - 支持删除敏感词。
- 更新侧边栏和路由，新增“敏感词管理”入口。
- 更新 `docs/api.md`、`docs/project-progress.md`、`docs/acceptance-test-guide.md` 和本开发日志。

### 验证结果

- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- SpringBoot 重启成功，`http://localhost:8080/api/health` 返回正常。
- Vue 页面 `http://localhost:5173/sensitive-words` 返回 `200`。
- 敏感词接口冒烟测试通过：
  - 初始敏感词数量：`6`
  - 新增测试词成功，生成 ID `7`
  - 编辑测试词成功，权重改为 `44`
  - 停用测试词成功，`enabled = 0`
  - 按 `category=custom&enabled=0` 筛选可查到测试词
  - 删除测试词成功，删除后筛选结果为 `0`

### 当前项目状态

- 敏感词管理第一版已完成。
- 现在系统具备：

```text
敏感词配置 -> 视频上传 -> AI 分析 -> 证据入库 -> 人工复审 -> 统计看板
```

### 下一步计划

- 实现简化登录与角色展示。
- 整理最终演示脚本和课程报告材料。

## 2026-06-09 简化登录与角色展示第一版完成

### 本次目标

- 完成课程演示所需的简化登录功能。
- 在前端显示当前登录用户和角色。
- 确认三端服务端口和运行状态，处理本机 `8080` 端口占用问题。
- 同步更新 API 文档、项目进展规划和交互验收指南。

### 完成工作

- 后端新增用户登录相关代码：
  - `User` 实体，对应数据库 `user` 表。
  - `UserRepository`，支持按用户名查询。
  - `LoginRequest`、`UserResponse` 两个 DTO。
  - `AuthService`，支持演示阶段的简化登录逻辑。
  - `AuthController`，提供 `POST /api/auth/login` 和 `GET /api/auth/me`。
- 前端新增和完善登录交互：
  - 登录页支持选择 `admin`、`reviewer`、`user` 三类演示账号。
  - 登录成功后将用户信息保存到 `localStorage`。
  - 顶部栏展示当前用户名和角色。
  - 支持退出登录并返回登录页。
- 端口调整：
  - 本机 `8080` 被 NI Application Web Server 占用，普通权限无法停止。
  - SpringBoot 已统一切换到 `8081`。
  - 前端 API 基础地址同步改为 `http://localhost:8081`。
- 文档维护：
  - `docs/api.md` 补充登录接口说明。
  - `docs/project-progress.md` 更新当前进展和下一步任务。
  - `docs/acceptance-test-guide.md` 补充登录验收流程和接口命令。

### 验证结果

- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- `http://localhost:8081/api/health` 返回 `{"status":"ok"}`。
- `POST /api/auth/login` 使用 `reviewer / 123456` 登录成功，返回角色 `REVIEWER`。
- `GET /api/auth/me?userId=2` 返回审核员用户信息。
- `http://localhost:5173/login` 返回 `200`。
- `GET /api/statistics/overview` 可正常返回统计数据。

### 遇到的问题与处理

1. `8080` 端口被占用
   - 问题：`8080` 被 `NI Application Web Server` 占用。
   - 处理：尝试停止服务时权限不足，因此将 SpringBoot 改为 `8081`，并同步更新前端和文档中的接口地址。

2. PowerShell 中文显示乱码
   - 问题：PowerShell 读取 UTF-8 中文文件时显示为乱码。
   - 处理：使用 Node 按 UTF-8 读取文件确认内容正常，避免误判文件损坏。

### 当前项目状态

- 登录与角色展示第一版已完成。
- 当前可演示主链路：

```text
登录选择角色 -> 敏感词配置 -> 视频上传 -> AI 分析 -> 人工复审 -> 统计看板
```

### 下一步计划

1. 整理最终演示脚本。
2. 准备课程报告材料：系统架构、数据库设计、核心代码说明、测试结果。
3. 视时间补充更严格的角色权限控制。

## 2026-06-09 项目完整验收测试

### 本次目标

- 查清 `8080` 端口占用来源。
- 对当前 MVP 做一次完整业务闭环测试。
- 判断项目功能是否已经达到课程演示要求。

### 端口排查结果

- 当前 `8080` 端口未被监听，已经空闲。
- 之前占用 `8080` 的服务是 `NIApplicationWebServer`，显示名为 `NI Application Web Server`，属于 NI/Multisim 相关软件。
- 当前服务状态：
  - `NIApplicationWebServer`：Stopped，StartType 为 Automatic。
  - `NIApplicationWebServer64`：Stopped，StartType 为 Disabled。
  - `NISystemWebServer`：Running，但未占用 `8080`。
- 尝试停止和禁用 `NIApplicationWebServer` 时被系统拒绝，原因是当前 PowerShell 没有管理员权限。

### 完整测试结果

- 健康检查通过：
  - SpringBoot：`http://localhost:8081/api/health`
  - FastAPI：`http://localhost:8000/ai/health`
  - Vue：`http://localhost:5173/login`
- 登录测试通过：
  - `reviewer / 123456` 登录成功，返回角色 `REVIEWER`。
- 敏感词管理测试通过：
  - 新增临时敏感词 `codex_risk_20260609` 成功。
  - 编辑权重成功。
  - 删除临时敏感词成功。
- 视频上传测试通过：
  - 上传本地测试视频成功，生成 `videoId=10`。
- AI 分析测试通过：
  - 视频 `10` 分析后状态为 `AI_SUSPICIOUS`。
  - 风险等级为 `SUSPICIOUS`。
  - 风险分为 `50.0`。
  - 抽取关键帧 `1` 张。
  - 敏感词命中 `1` 条。
- 人工复审测试通过：
  - 视频 `10` 提交人工复审成功。
  - 最终状态为 `MANUAL_REJECTED`。
  - 复审日志数量为 `1`。
- 统计接口测试通过：
  - `GET /api/statistics/overview` 正常返回总视频数、今日上传、待复审、人工复审和 AI 通过率。
- 前端页面测试通过：
  - `/login`、`/dashboard`、`/upload`、`/videos`、`/review`、`/sensitive-words` 均返回 `200`。
- 构建验证通过：
  - `mvn -DskipTests package`：通过。
  - `npm run build`：通过。

### 当前结论

- 当前 MVP 功能已经达到课程演示要求。
- 已完成的核心链路为：

```text
登录 -> 敏感词管理 -> 视频上传 -> AI 分析 -> 人工复审 -> 统计看板
```

- 剩余工作主要是课程材料整理，不是核心功能开发：
  - 最终演示脚本。
  - 课程报告材料。
  - 架构图、数据库设计图、核心代码说明。

## 2026-06-09 按改进需求规格完成权限与审核流程改造

### 本次目标

- 按《改进需求规格》改造状态字段、角色权限、审核流程和前端角色视图。
- 将上传后的 AI 预审从手动触发改为后台自动执行。
- 将用户角色和审核状态统一为中文业务口径。

### 完成工作

- 数据库与实体：
  - `video` 表新增 `violation_category` 字段。
  - `status` 改为 `已上传`、`预审中`、`复审中`、`待申诉`、`通过`、`驳回`。
  - `ai_risk_level` 改为 `正常`、`可疑`、`违规`。
  - `user.role` 改为 `一般用户`、`审核员`、`管理员`。
- 权限与认证：
  - 新增注册接口，注册用户默认角色为 `一般用户`。
  - 登录成功后返回 JWT Token。
  - 新增后端拦截器，按 Token 中的角色限制接口访问。
  - 管理员可在用户管理页修改用户角色。
- 审核流程：
  - 上传接口不再接收前端传入的 `uploaderId`，改为从 Token 中读取。
  - 新增后台定时预审任务，自动分析状态为 `已上传` 的视频。
  - AI 返回 `正常` 时视频进入 `通过`；AI 返回 `可疑/违规` 时视频进入 `复审中`。
  - 复审提交支持 `通过`、`驳回`、`待申诉`，并要求填写复审意见。
  - 复审提交后不可再次修改。
- 前端视图：
  - 一般用户仅显示“视频上传”“我的上传”。
  - 审核员仅显示“人工复审”。
  - 管理员显示“统计看板”“视频管理”“敏感词管理”“用户管理”。
  - 一般用户详情页隐藏 AI 风险分、敏感词命中、关键帧和复审日志。
  - 审核员详情页显示元数据、播放器、关键帧、敏感词命中、AI 分数和复审日志。

### 验证结果

- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- 登录返回中文角色：
  - `admin -> 管理员`
  - `reviewer -> 审核员`
  - `user -> 一般用户`
- 普通用户访问统计接口返回 `403`，权限拦截生效。
- 普通用户上传视频时不传 `uploaderId`，上传成功后状态为 `已上传`。
- 后台自动预审生效，测试视频 `videoId=11` 自动从 `已上传` 变为 `复审中`。
- 审核员可查看 `videoId=11` 的 AI 风险等级、风险分、违规类别、敏感词命中和关键帧。
- 审核员提交 `待申诉` 成功，再次提交返回 `400`，满足“提交后不可修改”。

### 问题处理

- 通过 PowerShell 管道执行中文 SQL 时，数据库中部分中文被写成 `???`。
- 已改用 UTF-8 十六进制 SQL 修复本机数据库中的角色、状态和类别数据。

### 当前状态

- 改进需求中的核心功能已经落地。
- 剩余可选增强：
  - 更强 AI 模型接入。
  - 更精细的前端页面视觉优化。
  - 将本次本机迁移 SQL 整理成正式迁移脚本。

## 2026-06-09 用户显示名字段补充

### 本次目标

- 解决登录后页面显示 `admin`、`reviewer`、`user` 或角色名，不像真实用户名的问题。
- 将“登录账号”和“页面显示用户名”分离，便于课堂演示和后续多人协作扩展。

### 完成工作

- 数据库：
  - `user` 表新增 `display_name` 字段。
  - `sql/schema.sql` 已同步正式表结构。
  - `sql/migration-20260609-improvements.sql` 已补充兼容迁移逻辑，老数据会自动填充展示名。
  - 演示账号展示名调整为：
    - `admin`：系统管理员
    - `reviewer`：审核员一号
    - `user`：普通用户一号
- 后端：
  - `User` 实体新增 `displayName` 字段。
  - `UserResponse` 返回 `displayName`，前端无需再用角色或登录账号充当用户名。
  - `RegisterRequest` 支持传入 `displayName`。
  - 注册时如果没有填写展示名，则自动使用登录账号作为展示名。
- 前端：
  - 登录页将账号输入标注为“登录账号”。
  - 注册页新增“用户名”输入框，对应页面展示名。
  - 演示账号按钮显示“系统管理员”“审核员一号”“普通用户一号”。
  - 顶部栏、登录成功提示、用户管理列表优先展示 `displayName`。

### 验证结果

- 本机数据库已确认 `admin`、`reviewer`、`user` 的展示名与角色正确。
- 后端登录接口返回内容已包含 `displayName`。
- `mvn -DskipTests package`：通过。
- `npm run build`：通过。
- `git diff --check`：通过，仅有 Windows 换行提示。

### 当前状态

- 用户身份展示细节已补齐。
- 后续重点仍是最终演示、报告材料整理和可选 AI 高级模型增强。

## 2026-06-09 复审提交与中文编码修复

### 本次目标

- 继续完善改进需求中的复审流程细节。
- 避免前端伪造 `reviewerId`，让复审日志中的审核员来自 JWT 登录态。
- 修复 Windows 环境下 Maven 未声明 UTF-8 编码导致中文状态常量可能编译异常的问题。

### 完成工作

- 后端：
  - `ReviewSubmitRequest` 移除 `reviewerId` 字段。
  - `ReviewController` 从请求属性 `currentUserId` 读取当前审核员 ID。
  - `ReviewService` 写入复审日志时使用 JWT 中的审核员 ID。
  - `ReviewLogResponse` 新增 `reviewerDisplayName`，复审日志可显示“审核员一号”等真实用户名。
  - `VideoService` 和 `ReviewService` 返回复审日志时补充审核员展示名。
  - `AiReviewResultResponse` 对历史 AI 风险等级做中文归一化，避免详情页继续显示 `SUSPICIOUS` 等旧值。
  - `pom.xml` 增加 `project.build.sourceEncoding=UTF-8`，确保中文状态、角色、类别常量按 UTF-8 编译。
- 前端：
  - 复审提交不再发送 `reviewerId`。
  - 复审日志表和视频详情页复审日志显示审核员展示名。
  - JSON 请求头统一为 `application/json; charset=utf-8`。
- 文档：
  - 更新 `docs/api.md` 中复审提交请求体和复审日志响应。
  - 更新 `docs/acceptance-test-guide.md` 中登录、上传、自动预审、复审验收步骤。
  - 更新 `docs/database.md` 中中文状态、风险等级和角色说明。

### 验证结果

- `mvn clean -DskipTests package`：通过。
- `npm run build`：通过。
- 使用审核员 Token 提交复审时，请求体不传 `reviewerId`，提交成功。
- 复审日志返回 `reviewerId=2` 和 `reviewerDisplayName=审核员一号`。
- 验证后已将演示视频 `videoId=5` 复原为 `复审中`，保留为课堂演示待复审样例。
- 发现通过 PowerShell 内联脚本直接写中文会变成 `???`，接口验证改用 Unicode 转义，避免误判。

## 2026-06-10 前端审核流程与详情页展示优化

### 本次目标

- 按新的演示需求优化登录页、视频管理页、人工复审页和视频详情页。
- 将人工复审从单页工作台拆分为“复审列表 + 复审处理页”。
- 让视频详情页按用户角色展示不同的信息分组。
- 将较长的 ASR 文本从详情页中移出，改为独立页面查看。
- 同步更新 API 文档和前端变更说明。

### 完成工作

1. 登录页调整
   - 删除登录页中的“演示账号”一行。
   - 删除演示账号快捷填充逻辑。
   - 登录账号和密码默认改为空，页面不再直接暴露演示账号入口。

2. 管理员视频管理页调整
   - 删除“上传视频”按钮。
   - 管理员视频管理页只保留筛选、刷新和查看详情能力。
   - 普通用户上传流程仍保留在“视频上传”页面。

3. 人工复审页面重构
   - `/review` 改为纯列表页。
   - 列表列结构对齐管理员视频管理页，包含视频标题、状态、AI 风险等级、违规类别、时长、上传时间和操作。
   - 新增状态筛选，支持 `复审中`、`通过`、`驳回`、`待申诉`。
   - 风险等级筛选支持 `可疑`、`违规`。
   - 违规类别筛选支持 `暴力`、`色情`、`政治敏感`。
   - 操作列提供“详情”和“复审”入口。

4. 复审处理页拆分
   - 新增 `/review/:id` 复审处理页。
   - 复审页保留视频播放、审核信息、复审表单、敏感命中、关键帧和复审日志。
   - 复审页不再展示视频时长、分辨率、文件大小、上传者和上传时间等基础元数据。
   - 复审表单会根据当前视频状态默认选择 `通过`、`驳回` 或 `待申诉`。

5. 复审规则调整
   - 后端 `GET /api/review/tasks` 默认返回 `复审中`、`通过`、`驳回`、`待申诉` 四类视频。
   - 后端 `POST /api/review/tasks/{videoId}/submit` 放宽提交限制，允许这四类状态的视频重新审核。
   - 每次重新审核仍会更新 `video` 表并追加一条 `review_log`。

6. 视频详情页展示优化
   - 视频详情页右侧信息区统一改为 `el-descriptions`。
   - 信息分为两组：
     - 视频信息：处理状态、时长、分辨率、文件大小、上传者、上传时间。
     - 审核信息：AI 风险等级、违规类别、最终风险分、文本风险分、图像风险分。
   - 一般用户只看到视频信息组，且不显示上传者。
   - 审核员和管理员可以看到视频信息组和审核信息组。
   - 后端视频详情响应新增 `uploaderUsername` 和 `uploaderDisplayName`，用于展示上传者账号和显示名。

7. ASR 文本查看页
   - 新增 `/videos/:id/asr` 页面。
   - 视频详情页和复审页不再直接展示 ASR 长文本，只提供“查看 ASR 文本”链接。
   - ASR 页面使用独立文本区域展示完整识别文本，支持长文本换行和滚动。
   - ASR 页面仅允许审核员和管理员访问。

8. 文档维护
   - 更新 `docs/api.md`，补充视频详情上传者字段和复审任务状态规则。
   - 新增 `docs/frontend-review-ui-changes.md`，记录前端复审页面调整和对后端接口的影响。

### 验证结果

- `npm run build`：通过。
- `mvn -DskipTests package`：通过。
- 前端新增路由 `/review/:id` 和 `/videos/:id/asr` 能正常参与构建。
- 视频详情页不再直接渲染 ASR 长文本。
- 复审列表可按处理状态、风险等级和违规类别筛选。
- 复审提交规则已允许 `复审中`、`通过`、`驳回`、`待申诉` 四类状态。

### 注意事项

- 构建时仍有 Vite chunk 体积警告和 Rollup 注释警告，不影响当前演示功能。
- 当前工作区仍有历史未提交修改，包含 `backend-springboot/src/main/resources/application.yml` 和 `frontend-vue/package-lock.json`。
- 本次新增的 ASR 查看页依赖视频详情接口中的 `aiResult.asrText` 字段；如果后续接入真实 ASR 服务，需要确保该字段继续返回完整文本。

### 当前项目状态

- 前端角色视图和复审流程已更接近最终演示形态。
- 当前可演示链路为：

```text
一般用户登录 -> 上传视频 -> 后台自动 AI 预审 -> 审核员筛选并复审视频 -> 查看 ASR 文本与审核证据 -> 管理员查看视频详情和统计
```

### 下一步计划

1. 用真实演示视频走一次完整验收。
2. 检查课程报告中的页面截图是否需要更新。
3. 整理最终演示脚本，重点说明角色权限、复审流程和 AI 证据展示。
[三问华为韬定律：区别在哪？困难在哪？别人为什么不做？_哔哩哔哩_bilibili.mp4](../../../../%E4%B8%89%E9%97%AE%E5%8D%8E%E4%B8%BA%E9%9F%AC%E5%AE%9A%E5%BE%8B%EF%BC%9A%E5%8C%BA%E5%88%AB%E5%9C%A8%E5%93%AA%EF%BC%9F%E5%9B%B0%E9%9A%BE%E5%9C%A8%E5%93%AA%EF%BC%9F%E5%88%AB%E4%BA%BA%E4%B8%BA%E4%BB%80%E4%B9%88%E4%B8%8D%E5%81%9A%EF%BC%9F_%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9_bilibili.mp4)
## 2026-06-11 跟进队友 GitHub 修改

### 本次目标

- 拉取并检查队友合并到 GitHub `dev` 分支的修改。
- 修复远程提交后本地前端无法构建的问题。
- 保持本机默认数据库配置可运行，同时不影响队友通过环境变量覆盖配置。

### 完成工作

- 使用 `git fetch` 和 `git pull --ff-only origin dev` 同步远程 `dev`。
- 确认队友提交 `6-10前端改进` 已合并到本地。
- 发现并修复两个缺口：
  - 路由引用了 `AsrTextView.vue` 和 `ReviewDetailView.vue`，但文件未随提交上传。
  - `application.yml` 默认数据库密码被改为队友本机密码，已恢复为 `${DB_PASSWORD:1234}`。
- 新增 `/review/:id` 复审处理页。
- 新增 `/videos/:id/asr` ASR 文本查看页。
- 补充 `docs/frontend-review-ui-changes.md`，记录队友前端改动和本次修复说明。

### 验证结果

- 后端 `mvn -DskipTests package`：通过。
- 前端初次 `npm run build`：失败，原因是缺少 `AsrTextView.vue`。
- 修复后 `npm run build`：通过。
- `git diff --check`：通过，仅有 Windows 换行提示。
- 三端服务已启动：
  - Vue：`http://localhost:5173`
  - SpringBoot：`http://localhost:8081`
  - FastAPI：`http://localhost:8000`
- 健康检查通过：
  - `GET /api/health` 返回 `200`。
  - `GET /ai/health` 返回 `200`。
- 页面路由检查通过：
  - `/login` 返回 `200`。
  - `/review` 返回 `200`。
  - `/review/5` 返回 `200`。
  - `/videos/5/asr` 返回 `200`。
- 审核员登录和复审接口验证通过：
  - `reviewer / 123456` 登录返回 `审核员一号 / 审核员`。
  - `GET /api/review/tasks` 返回复审列表。
  - `GET /api/review/tasks/5` 返回视频详情，包含上传者展示名 `普通用户一号`。

### 问题处理

- 队友提交中新增了 `/review/:id` 和 `/videos/:id/asr` 路由，但缺少对应页面文件，导致前端构建失败；已补充页面文件。
- 队友将本地默认 MySQL 密码改为 `JYX628`，会导致当前电脑默认启动失败；已恢复为 `${DB_PASSWORD:1234}`，其他成员可继续用环境变量覆盖本机密码。

## 2026-06-11 管理页顶部筛选区优化

### 本次目标

- 按页面截图反馈，优化视频管理和敏感词管理页顶部筛选区过高、过散的问题。
- 保留筛选能力，同时让页面首屏更直接展示数据。
- 继续统一复审、用户、我的上传、详情类页面的顶部操作区样式。

### 完成工作

- 视频管理页：
  - 保留“处理状态”“风险等级”“违规类别”三个筛选项。
  - 将筛选项改为标签 + 固定宽度下拉框的紧凑横向布局。
  - 刷新按钮移到工具栏右侧，并添加图标。
- 敏感词管理页：
  - 保留“敏感类别”“启用状态”两个筛选项。
  - 将刷新和新增按钮收拢到右侧操作区，并添加图标。
  - 窄屏下筛选区自动换行，避免内容挤压。
- 复审任务页：
  - 将“处理状态”“风险等级”“违规类别”筛选区调整为同款紧凑布局。
  - 刷新按钮统一放到右侧操作区。
- 其他页面：
  - 我的上传、用户管理、视频详情、复审详情、ASR 文本页的顶部按钮统一为右侧操作组。
  - 为刷新、返回、上传等常用操作补充图标，提升识别度。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已检查 `/videos`、`/sensitive-words`、`/review`、`/users`、`/my-uploads`，本地页面均返回 `200`。
- 已执行 `git diff --check`，无空白格式错误，仅有 Windows 换行提示。

## 2026-06-11 抽帧图片访问修复与分页展示

### 本次目标

- 检查详情页“视频抽帧”区域图片破图问题。
- 将抽帧列表从一次性全部展示改为分页展示，降低详情页视觉负担。

### 问题定位

- 本地 `uploads/frames/12` 下已经生成抽帧 jpg 文件，说明 FastAPI 抽帧功能本身有产物。
- 访问 `http://localhost:8081/uploads/frames/12/frame_0000.jpg` 返回 `404`，说明问题在 SpringBoot 静态资源目录映射。
- 原配置使用 `../uploads`，当 SpringBoot 从项目根目录启动时会指向错误目录。

### 完成工作

- 后端：
  - 新增 `UploadPathResolver`，统一解析上传目录。
  - `WebConfig` 和 `VideoService` 改为使用统一解析后的上传目录。
  - 默认上传目录改为项目根目录下的 `uploads`。
  - 保证从项目根目录或 `backend-springboot` 目录启动时，都能找到同一份上传文件。
- 前端：
  - 视频详情页抽帧区域改为分页展示，每页 12 帧。
  - 复审详情页关键帧区域同步改为分页展示。
  - 增加“共 N 帧”提示和空状态提示。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已执行 `mvn -DskipTests package`，后端打包通过。
- 已重启 SpringBoot，新 PID 为 `32744`。
- 已验证 `http://localhost:8081/api/health` 返回 `{"status":"ok"}`。
- 已验证 `http://localhost:8081/uploads/frames/12/frame_0000.jpg` 返回 `200 image/jpeg`。
- 已通过管理员登录后请求 `GET /api/videos/12`，确认接口返回 `59` 帧，第一帧地址为 `/uploads/frames/12/frame_0000.jpg`。

## 2026-06-11 视频播放路径兼容修复

### 本次目标

- 检查视频详情页播放器无法播放的问题。
- 修复历史上传视频和当前上传目录不一致导致的视频文件访问失败。

### 问题定位

- 视频 12 的数据库路径为 `/uploads/videos/d0405dcf-101b-4721-852e-1374db6bda98.mp4`。
- 该视频文件实际保存在历史目录 `D:/zaproject/Real_Projects/uploads/videos`。
- 上一次修复后，后端默认服务项目内目录 `D:/zaproject/Real_Projects/VideoGuard/uploads`，因此抽帧图片正常，但历史上传的视频文件访问不到。

### 完成工作

- `UploadPathResolver` 增加候选上传目录能力：
  - 优先使用项目内 `uploads`。
  - 同时兼容历史目录 `../uploads`。
- `WebConfig` 的 `/uploads/**` 静态资源映射改为挂载多个候选目录。
- `VideoService` 重新分析视频时，也会从候选目录里查找真实存在的视频文件。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已执行 `mvn -DskipTests package`，后端打包通过。
- 已重启 SpringBoot，新 PID 为 `37832`。
- 已验证 `http://localhost:8081/api/health` 返回 `{"status":"ok"}`。
- 已验证视频文件 `HEAD /uploads/videos/d0405dcf-101b-4721-852e-1374db6bda98.mp4` 返回 `200`，`Content-Type` 为 `video/mp4`。
- 已验证视频 Range 请求返回 `206`，支持浏览器播放器分段加载。
- 已复查抽帧图片仍返回 `200 image/jpeg`。

## 2026-06-11 ASR 语音转文字接入

### 本次目标

- 从高级 AI 能力中优先接入 ASR 语音转文字。
- 让 ASR 文本进入现有敏感词检测和风险评分链路。

### 完成工作

- AI 服务：
  - 新增 `POST /ai/asr` 接口，支持按视频路径单独执行语音转文字。
  - `/ai/analyze` 不再使用空字符串作为 ASR 文本，而是调用真实 ASR 转写。
  - 使用 `ffmpeg` 从视频中提取 16kHz 单声道 wav 音频。
  - 使用 `faster-whisper` 执行本地 Whisper 转写。
  - 支持环境变量配置：
    - `VIDEOGUARD_ASR_MODEL`，默认 `tiny`。
    - `VIDEOGUARD_ASR_LANGUAGE`，默认 `zh`，可设为 `auto`。
    - `VIDEOGUARD_ASR_ENABLED=false` 可临时关闭综合分析中的 ASR。
  - 综合分析中 ASR 失败会降级为空文本，避免单个模型问题阻断整体视频审核。
- 依赖和文档：
  - `ai-service-fastapi/requirements.txt` 新增 `faster-whisper` 和 `requests`。
  - `docs/api.md` 新增 `/ai/asr` 接口说明。

### 验证结果

- 已执行 `python -m py_compile app/main.py`，AI 服务代码语法检查通过。
- 已执行 `pip install -r requirements.txt`，ASR 依赖安装成功。
- 已用项目 `.venv` 重启 FastAPI，新 PID 为 `36308`。
- 已验证 `http://localhost:8000/ai/health` 返回 `{"status":"ok"}`。
- 已调用 `/ai/asr` 分析视频 12，成功返回中文语音转写文本。
- 已调用 `/ai/text-detect`，使用 ASR 文本命中词“华为”，返回 `source_type=ASR`、`asr_score=40`。
- 已调用 `/ai/analyze`，确认 ASR 命中进入综合评分：`asr_score=40`、`final_score=40`、`risk_level=SUSPICIOUS`。
- 已执行 `npm run build` 和 `mvn -DskipTests package`，前端与后端构建通过。

## 2026-06-11 审核员敏感词建议与 ASR 回填

### 本次目标

- 给审核员开放敏感词管理的有限权限，让一线审核员能提交新词建议。
- 解决 ASR 页面仍显示“暂无 ASR 文本”的问题，让旧视频可以单独刷新 ASR。

### 完成工作

- 敏感词权限：
  - 审核员可进入敏感词管理页。
  - 审核员可查看敏感词列表。
  - 审核员可提交敏感词建议，但后端强制 `enabled = 0`，不会立即参与 AI 检测。
  - 审核员不能编辑、启用、停用或删除敏感词。
  - 管理员保留完整敏感词管理能力。
- ASR 回填：
  - 后端新增 `POST /api/videos/{id}/asr/refresh`。
  - 审核员和管理员可触发旧视频单独刷新 ASR。
  - 刷新后保存 `asrText`，并按已启用敏感词重新生成 ASR 命中和 `asrScore`。
  - ASR 页面新增“生成 ASR / 刷新 ASR”按钮。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已执行 `mvn -DskipTests package`，后端打包通过。
- 已重启 SpringBoot，新 PID 为 `30268`。
- 已验证审核员 `GET /api/sensitive-words` 返回 `200`。
- 已验证审核员 `POST /api/sensitive-words` 返回 `200`，且新词强制 `enabled = 0`。
- 已验证审核员 `PUT/DELETE /api/sensitive-words/{id}` 返回 `403`。
- 已验证管理员可删除测试敏感词。
- 已用审核员调用 `POST /api/videos/12/asr/refresh`，返回 `200`，视频 12 回填 ASR 文本长度 `1775`。

## 2026-06-11 前端白屏容错修复

### 本次目标

- 处理浏览器访问 `localhost:5173` 页面空白的问题。

### 问题定位

- Vite 前端服务可正常返回 HTML，`localhost:5173` 返回 `200`。
- 页面白屏更可能是浏览器本地 `localStorage` 中 `videoguard_user` 数据损坏或格式不兼容，导致 `JSON.parse` 抛错，Vue 启动被中断。

### 完成工作

- 新增 `frontend-vue/src/utils/session.js`。
- 统一封装用户会话读取、保存、清理逻辑。
- `App.vue`、路由守卫、视频详情页、敏感词页改用容错读取。
- 如果本地用户缓存损坏，会自动清理 `videoguard_user` 和 `videoguard_token`，并回到登录页，避免整页白屏。
- 已重启 Vite 前端服务，新监听进程为 `13436`。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已验证 `http://localhost:5173` 返回 `200`。
- 已重启前端服务并确认 `5173` 端口正常监听。

## 2026-06-11 管理员敏感词审核页拆分

### 本次目标

- 将管理员处理审核员提交的敏感词建议从“敏感词管理”中拆出来。
- 保持页面简洁，避免待审核建议和正式启用词库混在一起。

### 完成工作

- 新增管理员专用页面 `frontend-vue/src/views/SensitiveWordAuditView.vue`。
- 新增路由 `/sensitive-word-audit`，仅管理员可访问。
- 管理员侧边栏新增“敏感词审核”入口。
- 审核页只查询 `enabled = 0` 的待处理敏感词。
- 审核页支持：
  - 查看待审核数量、最高权重、类别数量。
  - 按类别筛选。
  - 点击“通过”将敏感词启用，进入正式 AI 检测词库。
  - 点击“驳回”删除该条建议。
- 原“敏感词管理”页调整为启用词库维护页，默认只展示 `enabled = 1` 的正式敏感词。

### 验证结果

- 已执行 `npm run build`，前端构建通过。
- 已验证 `/sensitive-word-audit` 可由 Vite 正常返回页面。

## 2026-06-15 腾讯云 ASR API 接入

### 本次目标

- 将当前本地 Whisper ASR 扩展为可切换的腾讯云 ASR API。
- 保留本地 `faster-whisper` 作为备用方案，避免没有云端密钥或额度时项目完全不可用。

### 完成工作

- AI 服务新增 `VIDEOGUARD_ASR_PROVIDER` 配置：
  - `local`：继续使用本地 `faster-whisper`。
  - `tencent`：调用腾讯云录音文件识别。
- 新增腾讯云 ASR 配置项：
  - `TENCENT_SECRET_ID`
  - `TENCENT_SECRET_KEY`
  - `TENCENT_ASR_REGION`
  - `TENCENT_ASR_ENGINE_MODEL_TYPE`
  - `TENCENT_ASR_AUDIO_BITRATE`
  - `TENCENT_ASR_TIMEOUT_SEC`
- AI 服务会先用 FFmpeg 从视频中提取 16kHz 单声道 MP3 音频，再提交腾讯云 ASR。
- 腾讯云本地音频上传限制为 5MB，代码中已加入大小检查和明确错误提示。
- `/ai/asr` 与 `/ai/analyze` 的外部接口保持不变，SpringBoot 不需要改动。
- 更新 `ai-service-fastapi/requirements.txt`，新增 `tencentcloud-sdk-python`。
- 新增 `ai-service-fastapi/.env.example`，提供腾讯云 ASR 本地配置模板。
- AI 服务启动时会自动读取 `ai-service-fastapi/.env`，真实密钥不提交 Git。
- 更新 `docs/api.md`，补充腾讯云 ASR 配置说明。

### 验证结果

- 已执行 `.venv\Scripts\python.exe -m pip install -r requirements.txt`，腾讯云 SDK 安装成功。
- 已执行 `.venv\Scripts\python.exe -m py_compile app\main.py`，AI 服务语法检查通过。
- 已验证腾讯云 SDK 中 `CreateRecTaskRequest` 和 `DescribeTaskStatusRequest` 可正常导入和构造。
- 已重启 FastAPI，当前监听 PID 为 `32864`，`http://localhost:8000/ai/health` 返回 `{"status":"ok"}`。
- 已用本地视频测试腾讯云 ASR 前置音频提取，成功生成 16kHz 单声道 MP3，示例大小约 `180688` 字节。
- 由于尚未配置 `TENCENT_SECRET_ID` 和 `TENCENT_SECRET_KEY`，本次未实际消耗腾讯云免费额度调用转写接口。

### 后续实测

- 已在本机 `ai-service-fastapi/.env` 配置腾讯云 `SecretId` 和 `SecretKey`，该文件受 `.gitignore` 保护，不提交仓库。
- 已真实调用 `/ai/asr` 走腾讯云 ASR，接口返回 `200`。
- 已确认腾讯云 ASR 返回中文文本，示例视频转写文本长度约 `95` 字。
- 已对腾讯云结果中的时间戳前缀做清洗，页面展示时只保留正文。

## 2026-06-15 腾讯云 ASR 质量优化

### 本次目标

- 处理腾讯云默认识别中“控烟条例/禁止吸烟”等词被误识别的问题。
- 在不购买额外大模型资源包的前提下，提高课程演示视频的语音转文字可用性。

### 完成工作

- 尝试腾讯云大模型引擎 `16k_zh_en`，腾讯云返回资源包不足，当前免费资源不可用。
- 测试音视频领域引擎 `16k_zh_video`，接口可正常调用。
- 为腾讯云 ASR 请求增加 `HotwordList` 临时热词参数支持。
- 新增 `TENCENT_ASR_HOTWORD_LIST` 配置，支持 `词|权重,词|权重` 格式。
- 新增 `TENCENT_ASR_CORRECTIONS` 后处理纠错配置，支持 `错词=>正确词` 格式。
- 将本机 ASR 音频码率提高到 `64k`，减少压缩带来的识别损失。
- 本机 `.env` 已配置控烟场景热词和“定制吸烟=>禁止吸烟”等纠错项。

### 验证结果

- 已重启 FastAPI 并实际调用 `/ai/asr`。
- 优化前示例误识别为“控制吸烟材料”“定制吸烟”。
- 优化后示例输出为“兰州市公共场所控制吸烟条例规定了公共场所是禁止吸烟的，请您禁止吸烟”。

## 2026-06-17 阿里云 ASR 与视频审核接入

### 本次目标

- 将 AI 服务扩展为支持阿里云统一 provider。
- 使用 OSS 作为云端文件中转，让百炼 ASR 和阿里云视频审核都能访问本地上传的视频/音频。

### 完成工作

- 新增阿里云配置项：
  - `DASHSCOPE_API_KEY`
  - `ALIYUN_ACCESS_KEY_ID`
  - `ALIYUN_ACCESS_KEY_SECRET`
  - `ALIYUN_REGION_ID`
  - `ALIYUN_OSS_BUCKET`
  - `ALIYUN_OSS_ENDPOINT`
- 新增 `VIDEOGUARD_ASR_PROVIDER=aliyun`：
  - 使用 FFmpeg 从视频提取 16kHz 单声道 MP3。
  - 上传临时音频文件到 OSS。
  - 使用签名 URL 调用百炼非实时 ASR。
  - 轮询异步任务并下载转写结果。
  - 清理临时 OSS 对象。
- 新增 `VIDEOGUARD_VIDEO_DETECT_PROVIDER=aliyun`：
  - 上传视频到 OSS。
  - 调用阿里云视频文件审核接口。
  - 将审核结果映射为当前系统已有的 `label/confidence/risk_score` 结构。
- 更新 `ai-service-fastapi/.env.example` 和 `docs/api.md`。

### 验证结果

- 已安装 `oss2`、`alibabacloud-green20220302` 等新增依赖。
- 已验证 OSS 可上传、生成签名 URL，并删除临时对象。
- 已真实调用百炼 ASR，返回正常中文转写文本。
- 已修复百炼 ASR 结果解析重复问题，当前示例输出约 `98` 字。
- 已通过 `/ai/asr` 接口验证阿里 ASR provider，返回 `200`。
- 已通过 `/ai/analyze` 验证“阿里 ASR + 本地视频检测”组合，返回 `200`，帧抽取和综合评分正常。
- 已尝试调用阿里云视频审核接口，阿里返回 `commodityCode is invalid: lvwang_cip_public_cn`，说明当前账号尚未开通对应内容安全增强版商品或权限不足。
- 为避免主流程被未开通的视频审核服务阻塞，本机 `.env` 当前设置为 `VIDEOGUARD_ASR_PROVIDER=aliyun`、`VIDEOGUARD_VIDEO_DETECT_PROVIDER=local`。

## 2026-06-17 阿里云 AI 审核能力补强

### 本次目标

- 解决“ASR 质量仍偏低”和“AI 内容安全审查未真正实现”的问题。
- 在内容安全增强版商品未开通的情况下，也要用阿里百炼模型完成可验收的视频内容审核。

### 完成工作

- ASR 侧：
  - 尝试 `qwen3-asr-flash-filetrans`，该模型不接受当前 OSS 签名 URL，返回 `InvalidParameter.MalformedURL`。
  - 回退到已实测可用的 `paraformer-v2`。
  - 将 ASR 音频码率配置提高到 `96k`。
  - 新增 `ALIYUN_ASR_CORRECTIONS`，支持阿里 ASR 后处理纠错。
  - 本机已配置控烟、违规、诈骗、赌博等热词，并修正“写二守爷=>吸二手烟”等常见错词。
- 视频审核侧：
  - 新增 `ALIYUN_VIDEO_DETECT_MODE=vl`。
  - 使用百炼兼容 OpenAI 接口调用视频理解模型 `qwen3.5-flash`。
  - 将模型输出约束为 JSON，并映射为系统已有的 `label/confidence/risk_score`。
  - `VIDEOGUARD_VIDEO_DETECT_PROVIDER=aliyun` 现在可以在未开通内容安全增强版的情况下完成视频内容安全分类。
  - 保留 `green` 模式，后续开通阿里内容安全增强版后仍可切换。

### 验证结果

- 已重启 FastAPI，`/ai/health` 返回 `200`。
- 已调用 `/ai/analyze` 验证“阿里 ASR + 百炼视频理解审核”组合，接口返回 `200`。
- ASR 示例输出已优化为“叔叔，我不要吸二手烟。先生你好，兰州市公共场所控制吸烟条例规定了公共场所是禁止吸烟的...”。
- 视频内容审核示例返回 `label=normal`、`confidence=0.95`、`risk_score=5`。

## 2026-06-17 违规标签多分类改造

### 工作内容

- 将视频内容审核从单一违规标签改为多标签结果，一个视频可同时标记为 `暴力`、`政治敏感`、`色情`、`其他违规`。
- AI 服务侧约束百炼视频理解模型输出 `labels` 数组，并兼容本地/阿里云旧格式的 `label` 字段。
- 后端继续复用 `video.violation_category` 和 `video_frame.label` 字段，以逗号分隔形式保存多个类别，避免大规模表结构重做。
- 后端列表筛选、复审任务筛选改为包含匹配，选择 `暴力` 时可筛出 `暴力,政治敏感` 这类多标签视频。
- 人工复审页违规类别改为多选，审核员可一次提交多个违规类别。
- 统计看板的违规类别分布会拆分多标签分别计数，而不是把 `暴力,政治敏感` 当成一个新类别。
- 前端视频管理、人工复审、视频详情、复审详情页面将违规类别展示为多个标签，关键帧也会展示模型返回的多标签。

### 数据库变更

- `video.violation_category` 调整为 `VARCHAR(128)`。
- `video_frame.label` 调整为 `VARCHAR(128)`。
- 新增迁移脚本：`sql/migration-20260617-multi-category.sql`。

## 2026-06-17 复审详情页 AI 重新分析入口修正

### 工作内容

- 根据页面验收反馈，恢复视频管理和人工复审列表的简洁操作按钮样式。
- 将复审详情页右上角原“刷新”按钮改为“AI 重新分析”。
- “AI 重新分析”会调用视频重新分析接口，完成后自动刷新当前复审详情页数据。
- 修复审核员点击“AI 重新分析”显示请求失败的问题：后端鉴权已允许审核员调用 `POST /api/videos/{id}/analyze`。

### 验证情况

- 已执行 `npm run build`，前端构建通过。
- 已重启 SpringBoot 后端。
- 使用审核员 token 调用 `POST /api/videos/999999/analyze`，返回 `400 Video not found` 而非 `403 Permission denied`，说明权限已放通。

## 2026-06-17 自动内容分类加分项实现

### 工作内容

- 按课程设计“自动分类（可选，加分项）”要求，实现视频一级内容分类。
- AI 服务新增 `POST /ai/content-category`，支持单独按标题、描述、ASR 文本和视频内容分类。
- 现有 `POST /ai/analyze` 已集成自动分类，分析结果会额外返回 `content_category`。
- 分类类别固定为：
  - 新闻资讯
  - 娱乐搞笑
  - 教育科普
  - 生活记录
  - 商品广告
  - 其他
- 分类实现策略：
  - 优先调用阿里百炼视频理解模型，结合视频画面、标题、描述和 ASR 文本分类。
  - 视频理解不可用时，调用阿里百炼文本模型，基于标题、描述和 ASR 文本分类。
  - API 不可用时，使用本地关键词规则兜底，避免主分析流程中断。
- 已将分类结果接入审核策略阈值：
  - 教育科普：复审阈值 45，违规阈值 80。
  - 新闻资讯：复审阈值 30，违规阈值 85。
  - 商品广告：复审阈值 20，违规阈值 60。
  - 娱乐搞笑：复审阈值 30，违规阈值 65。
  - 生活记录/其他：复审阈值 30，违规阈值 70。
- 后端新增保存字段：
  - `content_category`
  - `category_confidence`
  - `category_reason`
  - `review_strategy`
- 前端视频管理、人工复审列表、视频详情、复审详情页展示内容分类和审核策略。

### 数据库变更

- `video` 表新增内容分类相关字段。
- 新增迁移脚本：`sql/migration-20260617-content-category.sql`。
- 本机 MySQL 已执行迁移。

### 验证情况

- 已执行 `python -m py_compile ai-service-fastapi/app/main.py`。
- 已执行 `mvn -q -DskipTests compile`。
- 已执行 `npm run build`。
- 已重启 FastAPI 和 SpringBoot。
- 已调用 `/ai/content-category`，示例返回 `教育科普`、`confidence=0.85`、`review_strategy=教育类策略`。
- 已通过 SpringBoot `POST /api/videos/10/analyze` 完整链路验证，分析后返回并保存 `contentCategory`、`categoryConfidence`、`reviewStrategy`。
- 已验证策略阈值函数：
  - `教育科普 + 40分 -> PASS`
  - `生活记录 + 40分 -> SUSPICIOUS`
  - `商品广告 + 25分 -> SUSPICIOUS`
  - `新闻资讯 + 75分 -> SUSPICIOUS`

## 2026-06-17 AI 重新分析请求失败修复

### 问题现象

- 复审详情页点击“AI 重新分析”后，前端提示“请求失败”。

### 原因定位

- 后端日志显示 FastAPI 返回 `502 Bad Gateway`。
- 根因是阿里百炼视频理解接口对部分视频返回 `DataInspectionFailed: Input video data may contain inappropriate content`。
- 之前代码将该错误直接抛给 SpringBoot，导致整个 `/api/videos/{id}/analyze` 请求失败。

### 修复内容

- AI 服务视频审核调用失败时不再中断主流程。
- 当百炼视频理解因为内容安全检查拒绝输入时，系统将视频内容结果降级为：
  - `label = suspicious`
  - `image_score = 70`
  - `confidence = 0.75`
- 这样视频会进入人工复审，而不是前端请求失败。

### 验证情况

- 已执行 `python -m py_compile ai-service-fastapi/app/main.py`。
- 已执行 `mvn -q -DskipTests compile`。
- 已重启 FastAPI。
- 已使用审核员账号调用 `POST /api/videos/13/analyze`，接口返回成功，并生成：
  - AI 风险等级：可疑
  - 最终风险分：70
  - 内容分类：新闻资讯
  - 审核策略：新闻类策略

## 2026-06-17 视频详情布局与统计通过率修复

### 调整内容

- 优化视频详情页布局：
  - 原先右侧同时展示视频信息、自动分类、审核信息，页面右侧过长。
  - 调整为左侧展示播放器，并将“视频信息”移动到播放器下方。
  - 右侧只保留“自动分类”和“审核信息”，降低页面纵向堆叠压力。
- 修复统计看板 AI 通过率：
  - 原口径只统计“已上传/预审中”状态的视频，已经通过或进入复审流程的视频未计入分母，容易显示为 0。
  - 新口径改为：已产生 AI 风险等级的视频中，`AI 风险等级=正常` 的占比。

### 验证情况

- 已执行 `mvn -q -DskipTests compile`。
- 已执行 `npm run build`。
- 已重启 SpringBoot 后端。
- 已调用 `GET /api/statistics/overview`，返回 `aiPassRate=60.0`，不再固定为 0。
- 已在浏览器打开 `http://localhost:5173/videos/12` 验证详情页布局，视频信息已位于播放器下方。

## 2026-06-18 多模态模型降本切换

### 调整内容

- 将视频内容审核和视频一级分类使用的多模态模型从 `qwen3.5-flash` 切换为 `qwen3-vl-flash`。
- `qwen3-vl-flash` 面向图像与视频理解，当前中国内地价格更低，并具有独立免费额度。
- 视频审核和视频分类请求显式关闭思考模式，并将最大输出限制为 512 Token，减少无效输出消耗并提高 JSON 返回稳定性。
- 同步更新本地 `.env`、`.env.example`、代码默认值和 API 文档；真实密钥仍只保存在被 Git 忽略的 `.env` 中。

### 验证情况

- 已执行 `python -m py_compile app/main.py`。
- 已重启 FastAPI，`GET /ai/health` 返回 `status=ok`。
- 已使用短视频调用 `POST /ai/content-category`，新模型返回 `教育科普`、`confidence=0.95`，证明云端调用成功。
