# API Design

Base URLs:

```text
SpringBoot: http://localhost:8081
FastAPI:    http://localhost:8000
```

Frontend calls SpringBoot only. SpringBoot calls FastAPI.

## 2026-06-09 Updated Business Rules

The improved version uses Chinese business values:

```text
status: 已上传, 预审中, 复审中, 待申诉, 通过, 驳回
aiRiskLevel: 正常, 可疑, 违规
violationCategory: 暴力, 色情, 政治敏感, 其他违规; multiple values are stored as comma-separated text, for example 暴力,政治敏感
contentCategory: 新闻资讯, 娱乐搞笑, 教育科普, 生活记录, 商品广告, 其他
finalResult: 正常, 可疑, 违规
roles: 一般用户, 审核员, 管理员
```

Except `/api/health`, `/api/auth/login`, and `/api/auth/register`, SpringBoot APIs require:

```text
Authorization: Bearer <JWT token>
```

Role access:

```text
一般用户: upload videos, view own uploads and limited own details
审核员: review tasks, review detail, ASR refresh, view sensitive words, submit disabled sensitive-word suggestions
管理员: dashboard, all videos, sensitive words, users
```

## Health

### GET /api/health

Response:

```json
{
  "status": "ok"
}
```

### GET /ai/health

Response:

```json
{
  "status": "ok"
}
```

## Auth

Implemented:

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
GET  /api/users
PUT  /api/users/{id}/role
```

Roles:

```text
一般用户
审核员
管理员
```

### POST /api/auth/login

Request:

```json
{
  "username": "reviewer",
  "password": "123456"
}
```

Demo rule: current seed users use `CHANGE_ME_HASH` as a placeholder password hash, so any non-empty password is accepted for classroom demonstration.

Response:

```json
{
  "id": 2,
  "username": "reviewer",
  "displayName": "审核员一号",
  "role": "审核员",
  "token": "jwt-token",
  "createdAt": "2026-06-08T21:16:38"
}
```

### POST /api/auth/register

New users are created as `一般用户`.

Request:

```json
{
  "username": "student001",
  "displayName": "李华",
  "password": "123456"
}
```

`username` is the login account. `displayName` is the name displayed in the top bar and user list. If `displayName` is empty, the backend falls back to `username`.

### PUT /api/users/{id}/role

Admin only.

```json
{
  "role": "审核员"
}
```

### GET /api/auth/me

Query parameters:

```text
userId: optional, defaults to 1
```

Example:

```bash
curl "http://localhost:8081/api/auth/me?userId=2"
```

## Videos

Planned:

```text
POST   /api/videos/upload
GET    /api/videos
GET    /api/videos/{id}
DELETE /api/videos/{id}
POST   /api/videos/{id}/analyze
```

### POST /api/videos/upload

Request: `multipart/form-data`

```text
file: video file, mp4/mov/avi
title: string
description: string
```

`uploaderId` is read from JWT. The frontend must not submit it manually.

Response:

```json
{
  "videoId": 1,
  "title": "demo",
  "filePath": "uploads/videos/uuid.mp4",
  "fileUrl": "/uploads/videos/uuid.mp4",
  "status": "已上传"
}
```

Example:

```bash
curl -X POST http://localhost:8081/api/videos/upload \
  -F "file=@D:/demo/normal.mp4" \
  -F "title=正常视频" \
  -F "description=课程演示视频"
```

### GET /api/videos

Query parameters:

```text
status: optional
aiRiskLevel: optional
```

Response:

```json
[
  {
    "id": 1,
    "title": "正常视频",
    "uploaderId": 3,
    "createdAt": "2026-06-08T20:00:00",
    "status": "已上传",
    "aiRiskLevel": null,
    "aiRiskScore": 0.0,
    "fileSize": 123456,
    "duration": null
  }
]
```

### GET /api/videos/{id}

Response:

```json
{
  "id": 1,
  "uploaderId": 3,
  "uploaderUsername": "user",
  "uploaderDisplayName": "普通用户一号",
  "title": "正常视频",
  "description": "课程演示视频",
  "originalFilename": "normal.mp4",
  "storedFilename": "uuid.mp4",
  "filePath": "uploads/videos/uuid.mp4",
  "fileUrl": "/uploads/videos/uuid.mp4",
  "fileSize": 123456,
  "duration": null,
  "width": null,
  "height": null,
  "fps": null,
  "status": "已上传",
  "aiRiskLevel": null,
  "aiRiskScore": 0.0,
  "finalResult": null,
  "finalComment": null,
  "frames": [],
  "sensitiveHits": [],
  "reviewLogs": []
}
```

### GET /api/videos/{id}/play

Redirects to the uploaded static file URL, for example:

```text
/uploads/videos/uuid.mp4
```

### POST /api/videos/{id}/analyze

Admin-only manual trigger. The improved workflow also runs automatic pre-review in the background for videos with status `已上传`.

Processing rules:

```text
正常 -> 通过, finalResult = 正常
可疑 -> 复审中
违规 -> 复审中
```

Response: same shape as `GET /api/videos/{id}`, with populated `aiResult`, `frames`, and `sensitiveHits`.

Example:

```bash
curl -X POST http://localhost:8081/api/videos/1/analyze
```

Response excerpt:

```json
{
  "id": 1,
  "status": "复审中",
  "aiRiskLevel": "可疑",
  "aiRiskScore": 40.0,
  "contentCategory": "教育科普",
  "categoryConfidence": 0.91,
  "categoryReason": "标题和语音内容均为课程讲解",
  "reviewStrategy": "教育类策略",
  "aiResult": {
    "textScore": 40.0,
    "imageScore": 5.0,
    "asrScore": 0.0,
    "finalScore": 40.0,
    "riskLevel": "可疑",
    "asrText": ""
  },
  "frames": [
    {
      "framePath": "uploads/frames/1/frame_0000.jpg",
      "frameUrl": "/uploads/frames/1/frame_0000.jpg",
      "timestampSec": 0.0,
      "label": "normal",
      "confidence": 0.9,
      "riskScore": 5.0
    }
  ],
  "sensitiveHits": [
    {
      "sourceType": "TITLE",
      "word": "测试违规",
      "category": "violence",
      "weight": 20,
      "contextText": "测试违规演示视频"
    }
  ]
}
```

### Content Category Classification

AI analysis also returns an automatic first-level content category. FastAPI combines video frames/video URL, title, description, and ASR text, then asks DashScope to select one category from:

```text
新闻资讯, 娱乐搞笑, 教育科普, 生活记录, 商品广告, 其他
```

FastAPI response excerpt:

```json
{
  "content_category": {
    "category": "教育科普",
    "confidence": 0.91,
    "reason": "标题和语音内容均为课程讲解",
    "review_strategy": "教育类策略",
    "suspicious_threshold": 45,
    "violation_threshold": 80
  }
}
```

SpringBoot stores the result in `video.content_category`, `video.category_confidence`, `video.category_reason`, and `video.review_strategy`. The category is used as a basis for later differentiated review strategies.

Strategy thresholds:

```text
教育科普: 45 / 80
新闻资讯: 30 / 85
商品广告: 20 / 60
娱乐搞笑: 30 / 65
生活记录/其他: 30 / 70
```

The first number is the manual-review threshold, and the second number is the violation threshold.

### POST /api/videos/{id}/asr/refresh

Reviewer/admin endpoint. Refreshes ASR text only, stores it in the latest AI result, recalculates ASR sensitive-word hits, and updates `asrScore`, `finalScore`, and `riskLevel`.

Response: same shape as `GET /api/videos/{id}`.

Example:

```bash
curl -X POST http://localhost:8081/api/videos/12/asr/refresh
```

## Review

Implemented:

```text
GET  /api/review/tasks
GET  /api/review/tasks/{videoId}
POST /api/review/tasks/{videoId}/submit
GET  /api/review/logs/{videoId}
```

### GET /api/review/tasks

Returns videos in the review workbench. By default, this endpoint returns videos with status `复审中`, `通过`, `驳回`, or `待申诉`.

Query parameters:

```text
status: optional, one of 复审中, 通过, 驳回, 待申诉
aiRiskLevel: optional, for example 可疑
violationCategory: optional, for example 暴力. When a video has multiple categories, filtering matches any category contained in the comma-separated value.
```

### GET /api/review/tasks/{videoId}

Returns the same shape as `GET /api/videos/{id}`, including AI evidence and existing review logs.

### POST /api/review/tasks/{videoId}/submit

Submit request:

```json
{
  "status": "驳回",
  "violationCategory": "暴力,政治敏感",
  "comment": "人工复审确认驳回。"
}
```

Rules:

```text
status = 通过   -> finalResult = 正常, violationCategory = null
status = 待申诉 -> finalResult = 可疑
status = 驳回   -> finalResult = 违规
```

The endpoint reads the reviewer from JWT, updates `video.status`, `video.final_result`, `video.violation_category`, `video.final_comment`, and appends one row to `review_log`. A video can be submitted while its status is `复审中`, `通过`, `驳回`, or `待申诉`.

### GET /api/review/logs/{videoId}

Returns manual review logs ordered by newest first.

Response:

```json
[
  {
    "id": 1,
    "videoId": 8,
    "reviewerId": 2,
    "reviewerDisplayName": "审核员一号",
    "beforeStatus": "复审中",
    "afterStatus": "驳回",
    "beforeResult": null,
    "afterResult": "违规",
    "comment": "人工复审确认驳回。",
    "createdAt": "2026-06-08T23:08:00"
  }
]
```

## Sensitive Words

Implemented:

```text
GET    /api/sensitive-words
POST   /api/sensitive-words
PUT    /api/sensitive-words/{id}
DELETE /api/sensitive-words/{id}
```

Permissions:

```text
审核员: GET list, POST suggestion only. Created words are forced to enabled = 0.
管理员: GET, POST, PUT, DELETE. Admin can enable, disable, edit, and delete words.
```

### GET /api/sensitive-words

Query parameters:

```text
category: optional
enabled: optional, 1 or 0
```

Response:

```json
[
  {
    "id": 1,
    "word": "测试违规",
    "category": "violence",
    "weight": 40,
    "enabled": 1,
    "createdAt": "2026-06-08T20:00:00"
  }
]
```

### POST /api/sensitive-words

Request:

```json
{
  "word": "测试违规",
  "category": "violence",
  "weight": 40,
  "enabled": 1
}
```

For reviewers, `enabled` in the request is ignored and the created word is stored as disabled (`enabled = 0`) until an admin enables it.

### PUT /api/sensitive-words/{id}

Admin only. Request shape is the same as `POST /api/sensitive-words`.

### DELETE /api/sensitive-words/{id}

Admin only. Deletes a sensitive word from the local rule dictionary.

## Statistics

Implemented:

```text
GET /api/statistics/overview
GET /api/statistics/risk-distribution
GET /api/statistics/daily-upload
GET /api/statistics/status-distribution
GET /api/statistics/category-distribution
```

### GET /api/statistics/overview

Response:

```json
{
  "totalVideos": 5,
  "todayUploads": 5,
  "pendingReviews": 1,
  "manualReviewed": 1,
  "aiPassed": 3,
  "aiPassRate": 60.0
}
```

### GET /api/statistics/risk-distribution

Response:

```json
[
  { "name": "正常", "count": 4 },
  { "name": "可疑", "count": 1 }
]
```

### GET /api/statistics/status-distribution

Response:

```json
[
  { "name": "通过", "count": 3 },
  { "name": "复审中", "count": 1 },
  { "name": "驳回", "count": 1 }
]
```

### GET /api/statistics/daily-upload

Query parameters:

```text
days: optional, default 7, max 30
```

Response:

```json
[
  { "name": "2026-06-08", "count": 5 }
]
```

### GET /api/statistics/category-distribution

Response:

```json
[
  { "name": "violence", "count": 1 }
]
```

## FastAPI AI Service

### POST /ai/metadata

Request:

```json
{
  "video_id": 1,
  "video_path": "D:/projects/video-guard/uploads/videos/demo.mp4"
}
```

Response:

```json
{
  "video_id": 1,
  "duration": 12.3,
  "width": 1280,
  "height": 720,
  "fps": 30.0,
  "file_size": 12345678
}
```

### POST /ai/extract-frames

Request:

```json
{
  "video_id": 1,
  "video_path": "D:/projects/video-guard/uploads/videos/demo.mp4",
  "frame_interval_sec": 5
}
```

Response:

```json
{
  "video_id": 1,
  "frames": [
    {
      "frame_path": "uploads/frames/1/frame_0000.jpg",
      "timestamp_sec": 0
    }
  ]
}
```

### POST /ai/text-detect

Request:

```json
{
  "video_id": 1,
  "title": "测试标题",
  "description": "测试描述",
  "asr_text": "",
  "sensitive_words": [
    {
      "word": "测试违规",
      "category": "violence",
      "weight": 20
    }
  ]
}
```

### POST /ai/asr

Request:

```json
{
  "video_id": 1,
  "video_path": "D:/projects/video-guard/uploads/videos/demo.mp4",
  "language": "zh"
}
```

Response:

```json
{
  "video_id": 1,
  "asr_text": "识别到的语音文本"
}
```

Notes:

- ASR supports provider switching with `VIDEOGUARD_ASR_PROVIDER`.
- `VIDEOGUARD_ASR_PROVIDER=local` uses `faster-whisper`.
- `VIDEOGUARD_ASR_PROVIDER=tencent` uses Tencent Cloud recording file recognition.
- Local default model is `tiny`; override with `VIDEOGUARD_ASR_MODEL`, for example `base` or `small`.
- Set `VIDEOGUARD_ASR_LANGUAGE=auto` or request `"language": "auto"` for local language auto-detection.
- Set `VIDEOGUARD_ASR_ENABLED=false` to temporarily skip ASR in integrated analysis.
- Tencent Cloud configuration:
  - `TENCENT_SECRET_ID`
  - `TENCENT_SECRET_KEY`
  - `TENCENT_ASR_REGION`, default `ap-shanghai`
  - `TENCENT_ASR_ENGINE_MODEL_TYPE`, default `16k_zh`
  - `TENCENT_ASR_AUDIO_BITRATE`, default `24k`
  - `TENCENT_ASR_TIMEOUT_SEC`, default `180`
  - `TENCENT_ASR_HOTWORD_LIST`, optional temporary hotwords in `word|weight,word|weight` format.
  - `TENCENT_ASR_CORRECTIONS`, optional post-ASR correction pairs in `wrong=>right,wrong=>right` format.
- Tencent local audio upload is limited to 5 MB. The service extracts 16kHz mono MP3 audio before upload. For very long videos, configure a future COS URL mode instead of local `Data` upload.
- Copy `ai-service-fastapi/.env.example` to `ai-service-fastapi/.env` and fill in Tencent credentials locally. `.env` must not be committed.

Aliyun provider:

- Set `VIDEOGUARD_ASR_PROVIDER=aliyun` to use DashScope non-realtime ASR.
- Set `VIDEOGUARD_VIDEO_DETECT_PROVIDER=aliyun` to use Alibaba Cloud video moderation.
- `ALIYUN_VIDEO_DETECT_MODE=vl` uses DashScope video understanding for content safety classification.
- `ALIYUN_VIDEO_DETECT_MODE=green` uses Alibaba Cloud Content Safety enhanced video moderation, which must be enabled separately.
- Required configuration:
  - `DASHSCOPE_API_KEY`
  - `ALIYUN_ACCESS_KEY_ID`
  - `ALIYUN_ACCESS_KEY_SECRET`
  - `ALIYUN_REGION_ID`, for example `cn-beijing`
  - `ALIYUN_OSS_BUCKET`
  - `ALIYUN_OSS_ENDPOINT`, for example `oss-cn-beijing.aliyuncs.com`
- Optional configuration:
  - `ALIYUN_ASR_MODEL`, default `paraformer-v2`
  - `ALIYUN_ASR_AUDIO_BITRATE`, default `64k`
  - `ALIYUN_ASR_HOTWORDS`
  - `ALIYUN_VIDEO_DETECT_MODE`, default `vl`
  - `ALIYUN_VIDEO_MODEL`, default `qwen3-vl-flash`
  - `ALIYUN_GREEN_ENDPOINT`, default `green-cip.cn-shanghai.aliyuncs.com`, only for `green` mode
  - `ALIYUN_GREEN_VIDEO_SERVICE`, default `videoDetection`, only for `green` mode
- Aliyun ASR uploads extracted MP3 audio to OSS, submits a signed OSS URL to DashScope, polls the async task, then deletes the temporary OSS object.
- Aliyun DashScope video moderation uploads the video to OSS, submits a signed OSS URL to a video understanding model, and maps the JSON model output to `label/confidence/risk_score`.
- Aliyun Content Safety `green` mode uploads the video to OSS and submits a signed OSS URL to Content Safety. The Alibaba Cloud account must enable the Content Safety / AI Safety Guard service first.

### POST /ai/image-detect

Request:

```json
{
  "video_id": 1,
  "frames": [
    {
      "frame_path": "uploads/frames/1/frame_0000.jpg",
      "timestamp_sec": 0
    }
  ]
}
```

### POST /ai/analyze

Request:

```json
{
  "video_id": 1,
  "video_path": "D:/projects/video-guard/uploads/videos/demo.mp4",
  "title": "demo title",
  "description": "demo description",
  "frame_interval_sec": 5,
  "sensitive_words": [
    {
      "word": "测试违规",
      "category": "violence",
      "weight": 20
    }
  ]
}
```

Response:

```json
{
  "video_id": 1,
  "metadata": {
    "duration": 32.5,
    "width": 1280,
    "height": 720,
    "fps": 30.0,
    "file_size": 10485760
  },
  "frames": [],
  "asr_text": "识别到的语音文本",
  "text_hits": [],
  "scores": {
    "text_score": 0,
    "image_score": 5,
    "asr_score": 0,
    "final_score": 5
  },
  "risk_level": "PASS"
}
```

Windows PowerShell note: when testing Chinese JSON manually, send UTF-8 bytes or use a Python client. Otherwise PowerShell may display response text as mojibake even when the API logic is correct.

Python test example:

```bash
python -c "import json, urllib.request; body={'video_id':1,'video_path':'D:/zaproject/Real_Projects/VideoGuard/uploads/videos/text_risk.mp4','title':'这个标题包含测试违规词','description':'课程演示视频','frame_interval_sec':1,'sensitive_words':[{'word':'测试违规','category':'violence','weight':40}]}; data=json.dumps(body, ensure_ascii=False).encode('utf-8'); req=urllib.request.Request('http://localhost:8000/ai/analyze', data=data, headers={'Content-Type':'application/json; charset=utf-8'}); print(urllib.request.urlopen(req).read().decode('utf-8'))"
```
