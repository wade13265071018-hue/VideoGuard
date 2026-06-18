from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from base64 import b64encode
from functools import lru_cache
from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="VideoGuard AI Service")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICE_ROOT = PROJECT_ROOT / "ai-service-fastapi"
TENCENT_ASR_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(AI_SERVICE_ROOT / ".env")


class MetadataRequest(BaseModel):
    video_id: int
    video_path: str


class FrameExtractRequest(MetadataRequest):
    frame_interval_sec: int = Field(default=5, ge=1)


class AsrRequest(MetadataRequest):
    language: str | None = Field(default=None, description="ISO language code, e.g. zh. Empty means auto detect.")


class SensitiveWord(BaseModel):
    word: str
    category: str
    weight: int = Field(default=10, ge=0)


class TextDetectRequest(BaseModel):
    video_id: int
    title: str = ""
    description: str = ""
    asr_text: str = ""
    sensitive_words: list[SensitiveWord] = Field(default_factory=list)


class FrameItem(BaseModel):
    frame_path: str
    timestamp_sec: float


class ImageDetectRequest(BaseModel):
    video_id: int
    frames: list[FrameItem] = Field(default_factory=list)


class AnalyzeRequest(FrameExtractRequest):
    title: str = ""
    description: str = ""
    sensitive_words: list[SensitiveWord] = Field(default_factory=list)


class ContentCategoryRequest(MetadataRequest):
    title: str = ""
    description: str = ""
    asr_text: str = ""


@app.get("/ai/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/metadata")
def metadata(request: MetadataRequest) -> dict:
    video_path = resolve_video_path(request.video_path)
    ensure_file_exists(video_path)
    return {"video_id": request.video_id, **extract_metadata(video_path)}


@app.post("/ai/extract-frames")
def extract_frames(request: FrameExtractRequest) -> dict:
    video_path = resolve_video_path(request.video_path)
    ensure_file_exists(video_path)
    frames = extract_video_frames(video_path, request.video_id, request.frame_interval_sec)
    return {"video_id": request.video_id, "frames": frames}


@app.post("/ai/asr")
def asr(request: AsrRequest) -> dict:
    video_path = resolve_video_path(request.video_path)
    ensure_file_exists(video_path)
    asr_text = transcribe_video_audio(video_path, language=request.language, fail_silently=False)
    return {"video_id": request.video_id, "asr_text": asr_text}


@app.post("/ai/text-detect")
def text_detect(request: TextDetectRequest) -> dict:
    hits: list[dict] = []
    text_score = 0
    asr_score = 0

    sources = [
        ("TITLE", request.title),
        ("DESCRIPTION", request.description),
        ("ASR", request.asr_text),
    ]
    for source_type, text in sources:
        for sensitive_word in request.sensitive_words:
            if sensitive_word.word and sensitive_word.word in text:
                hit = {
                    "source_type": source_type,
                    "word": sensitive_word.word,
                    "category": sensitive_word.category,
                    "weight": sensitive_word.weight,
                    "context_text": build_context(text, sensitive_word.word),
                }
                hits.append(hit)
                if source_type == "ASR":
                    asr_score += sensitive_word.weight
                else:
                    text_score += sensitive_word.weight

    return {
        "video_id": request.video_id,
        "hits": hits,
        "text_score": min(100, text_score),
        "asr_score": min(100, asr_score),
    }


@app.post("/ai/image-detect")
def image_detect(request: ImageDetectRequest) -> dict:
    detector = ModelImageDetector()
    frames = [detector.detect(frame) for frame in request.frames]
    image_score = max([frame["risk_score"] for frame in frames], default=0)
    return {"video_id": request.video_id, "frames": frames, "image_score": image_score}


@app.post("/ai/content-category")
def content_category(request: ContentCategoryRequest) -> dict:
    video_path = resolve_video_path(request.video_path)
    ensure_file_exists(video_path)
    result = classify_content_category(video_path, request.title, request.description, request.asr_text)
    return {"video_id": request.video_id, **result}


@app.post("/ai/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    video_path = resolve_video_path(request.video_path)
    ensure_file_exists(video_path)

    video_metadata = extract_metadata(video_path)
    frame_result = extract_video_frames(video_path, request.video_id, request.frame_interval_sec)
    asr_text = transcribe_video_audio(video_path, fail_silently=True)
    text_result = text_detect(
        TextDetectRequest(
            video_id=request.video_id,
            title=request.title,
            description=request.description,
            asr_text=asr_text,
            sensitive_words=request.sensitive_words,
        )
    )
    image_result = analyze_video_content(video_path, request.video_id, frame_result)
    category_result = classify_content_category(video_path, request.title, request.description, asr_text)

    text_score = text_result["text_score"]
    asr_score = text_result["asr_score"]
    image_score = image_result["image_score"]
    final_score = max(text_score, asr_score, image_score)
    risk_level = score_to_risk_level(final_score, category_result["category"])

    return {
        "video_id": request.video_id,
        "metadata": video_metadata,
        "frames": image_result["frames"],
        "asr_text": asr_text,
        "text_hits": text_result["hits"],
        "scores": {
            "text_score": text_score,
            "image_score": image_score,
            "asr_score": asr_score,
            "final_score": final_score,
        },
        "risk_level": risk_level,
        "content_category": category_result,
    }


def classify_content_category(video_path: Path, title: str, description: str, asr_text: str) -> dict:
    provider = os.getenv("VIDEOGUARD_CONTENT_CATEGORY_PROVIDER", "aliyun").strip().lower()
    if provider in {"aliyun", "alibaba", "dashscope"} and os.getenv("DASHSCOPE_API_KEY"):
        try:
            object_key, signed_url = upload_file_to_aliyun_oss(video_path, "category")
            try:
                return call_dashscope_content_category(signed_url, title, description, asr_text)
            finally:
                cleanup_aliyun_oss_object(object_key)
        except Exception:
            pass
        try:
            return call_dashscope_content_category_text(title, description, asr_text)
        except Exception:
            pass
    return classify_content_category_locally(title, description, asr_text)


def call_dashscope_content_category(video_url: str, title: str, description: str, asr_text: str) -> dict:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("ALIYUN_CATEGORY_MODEL", os.getenv("ALIYUN_VIDEO_MODEL", "qwen3-vl-flash"))
    prompt = (
        "你是短视频一级内容分类模型。请结合视频画面、标题、描述和音频转写文本进行分类。"
        "只能从以下类别中选择一个：新闻资讯、娱乐搞笑、教育科普、生活记录、商品广告、其他。"
        "分类用于后续设定审核策略，不是违规判定。"
        "请只输出严格 JSON："
        "{\"category\":\"教育科普\",\"confidence\":0.90,\"reason\":\"简短中文原因\"}\n"
        f"标题：{title or '无'}\n"
        f"描述：{description or '无'}\n"
        f"ASR文本：{trim_text(asr_text, 2400) or '无'}"
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "video_url", "video_url": {"url": video_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0,
        "enable_thinking": False,
        "max_tokens": 512,
    }
    data = requests_post_json(
        DASHSCOPE_CHAT_URL,
        payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=int(os.getenv("ALIYUN_CATEGORY_REQUEST_TIMEOUT_SEC", "120")),
    )
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    parsed = parse_json_object(content)
    if not parsed:
        raise HTTPException(status_code=502, detail=f"DashScope content category returned invalid JSON: {content[:300]}")
    return normalize_content_category_result(parsed)


def call_dashscope_content_category_text(title: str, description: str, asr_text: str) -> dict:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("ALIYUN_CATEGORY_TEXT_MODEL", "qwen-turbo")
    prompt = (
        "你是短视频一级内容分类模型。请根据标题、描述和音频转写文本进行分类。"
        "只能从以下类别中选择一个：新闻资讯、娱乐搞笑、教育科普、生活记录、商品广告、其他。"
        "分类用于后续设定审核策略，不是违规判定。"
        "请只输出严格 JSON："
        "{\"category\":\"教育科普\",\"confidence\":0.90,\"reason\":\"简短中文原因\"}\n"
        f"标题：{title or '无'}\n"
        f"描述：{description or '无'}\n"
        f"ASR文本：{trim_text(asr_text, 3000) or '无'}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    data = requests_post_json(
        DASHSCOPE_CHAT_URL,
        payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=int(os.getenv("ALIYUN_CATEGORY_REQUEST_TIMEOUT_SEC", "120")),
    )
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    parsed = parse_json_object(content)
    if not parsed:
        raise HTTPException(status_code=502, detail=f"DashScope text category returned invalid JSON: {content[:300]}")
    return normalize_content_category_result(parsed)


def classify_content_category_locally(title: str, description: str, asr_text: str) -> dict:
    text = f"{title} {description} {asr_text}".lower()
    rules = [
        ("教育科普", ["教程", "教学", "课程", "学习", "知识", "科普", "讲解", "python", "数学", "英语"], 0.72),
        ("新闻资讯", ["新闻", "资讯", "报道", "发布会", "时事", "社会", "现场", "官方", "通报"], 0.70),
        ("娱乐搞笑", ["搞笑", "娱乐", "段子", "喜剧", "挑战", "游戏", "音乐", "舞蹈", "鬼畜"], 0.70),
        ("商品广告", ["优惠", "购买", "下单", "直播间", "同款", "折扣", "带货", "商品", "链接"], 0.68),
        ("生活记录", ["日常", "生活", "记录", "vlog", "旅行", "美食", "宠物", "家人", "今天"], 0.66),
    ]
    for category, keywords, confidence in rules:
        if any(keyword in text for keyword in keywords):
            return build_content_category(category, confidence, "根据标题、描述或 ASR 文本关键词自动归类。")
    return build_content_category("其他", 0.55, "未命中明确主题特征，归入其他类别。")


def normalize_content_category_result(result: dict) -> dict:
    category = normalize_content_category(str(result.get("category") or "其他"))
    try:
        confidence = float(result.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(1.0, confidence))
    reason = str(result.get("reason") or "")[:200]
    return build_content_category(category, confidence, reason)


def build_content_category(category: str, confidence: float, reason: str) -> dict:
    normalized = normalize_content_category(category)
    suspicious_threshold, violation_threshold = category_risk_thresholds(normalized)
    return {
        "category": normalized,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "reason": reason[:200],
        "review_strategy": category_review_strategy(normalized),
        "suspicious_threshold": suspicious_threshold,
        "violation_threshold": violation_threshold,
    }


def normalize_content_category(category: str) -> str:
    text = (category or "").strip().lower()
    if any(word in text for word in ["新闻", "资讯", "news"]):
        return "新闻资讯"
    if any(word in text for word in ["娱乐", "搞笑", "funny", "entertainment"]):
        return "娱乐搞笑"
    if any(word in text for word in ["教育", "科普", "教程", "education", "science"]):
        return "教育科普"
    if any(word in text for word in ["生活", "日常", "记录", "vlog", "life"]):
        return "生活记录"
    if any(word in text for word in ["广告", "商品", "带货", "ad", "commerce"]):
        return "商品广告"
    return "其他"


def category_review_strategy(category: str) -> str:
    return {
        "新闻资讯": "新闻类策略",
        "娱乐搞笑": "娱乐类策略",
        "教育科普": "教育类策略",
        "生活记录": "默认策略",
        "商品广告": "广告类策略",
    }.get(category, "默认策略")


def category_risk_thresholds(category: str) -> tuple[int, int]:
    if category == "教育科普":
        return 45, 80
    if category == "新闻资讯":
        return 30, 85
    if category == "商品广告":
        return 20, 60
    if category == "娱乐搞笑":
        return 30, 65
    return 30, 70


def trim_text(text: str, max_length: int) -> str:
    value = text or ""
    return value if len(value) <= max_length else value[:max_length] + "..."


class ModelImageDetector:
    def detect(self, frame: FrameItem) -> dict:
        frame_name = Path(frame.frame_path).name.lower()
        labels: list[str] = []
        if "violence" in frame_name:
            labels.append("violence")
        if "porn" in frame_name:
            labels.append("porn")
        if "politics" in frame_name or "political" in frame_name:
            labels.append("politics")
        if "ad" in frame_name:
            labels.append("ad")
        if "illegal" in frame_name:
            labels.append("illegal")

        if labels:
            label = ",".join(labels)
            confidence = 0.95
            risk_score = 80
        else:
            label = "normal"
            confidence = 0.90
            risk_score = 5

        return {
            "frame_path": frame.frame_path,
            "timestamp_sec": frame.timestamp_sec,
            "label": label,
            "confidence": confidence,
            "risk_score": risk_score,
        }


def analyze_video_content(video_path: Path, video_id: int, frame_result: list[dict]) -> dict:
    provider = os.getenv("VIDEOGUARD_VIDEO_DETECT_PROVIDER", "").strip().lower()
    if provider in {"aliyun", "alibaba"}:
        try:
            return detect_video_content_by_aliyun(video_path, video_id, frame_result)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Aliyun video detection failed: {exc}") from exc
    return image_detect(
        ImageDetectRequest(
            video_id=video_id,
            frames=[FrameItem(**frame) for frame in frame_result],
        )
    )


def detect_video_content_by_aliyun(video_path: Path, video_id: int, frame_result: list[dict]) -> dict:
    if os.getenv("ALIYUN_VIDEO_DETECT_MODE", "vl").strip().lower() in {"vl", "qwen", "model"}:
        try:
            return detect_video_content_by_dashscope_vl(video_path, video_id, frame_result)
        except HTTPException as exc:
            return build_video_content_fallback(video_id, frame_result, exc.detail)
    object_key, signed_url = upload_file_to_aliyun_oss(video_path, "moderation")
    try:
        task_id = create_aliyun_video_moderation_task(signed_url)
        moderation_result = poll_aliyun_video_moderation_task(task_id)
        labels, confidence, risk_score = summarize_aliyun_video_moderation(moderation_result)
        label = ",".join(labels) if labels else "normal"
        frames = [
            {
                "frame_path": frame["frame_path"],
                "timestamp_sec": frame["timestamp_sec"],
                "label": label,
                "confidence": confidence,
                "risk_score": risk_score,
            }
            for frame in frame_result
        ]
        return {"video_id": video_id, "frames": frames, "image_score": risk_score}
    except HTTPException as exc:
        return build_video_content_fallback(video_id, frame_result, exc.detail)
    finally:
        cleanup_aliyun_oss_object(object_key)


def detect_video_content_by_dashscope_vl(video_path: Path, video_id: int, frame_result: list[dict]) -> dict:
    object_key, signed_url = upload_file_to_aliyun_oss(video_path, "moderation")
    try:
        moderation_result = call_dashscope_video_moderation(signed_url)
        labels = normalize_label_list(moderation_result.get("labels") or moderation_result.get("label") or "normal")
        label = ",".join(labels) if labels else "normal"
        confidence = float(moderation_result.get("confidence") or 0.75)
        risk_score = int(moderation_result.get("risk_score") or 0)
        frames = [
            {
                "frame_path": frame["frame_path"],
                "timestamp_sec": frame["timestamp_sec"],
                "label": label,
                "confidence": confidence,
                "risk_score": risk_score,
            }
            for frame in frame_result
        ]
        return {"video_id": video_id, "frames": frames, "image_score": risk_score}
    finally:
        cleanup_aliyun_oss_object(object_key)


def build_video_content_fallback(video_id: int, frame_result: list[dict], detail: object) -> dict:
    detail_text = str(detail).lower()
    risk_score = 50
    label = "suspicious"
    confidence = 0.60
    if "data_inspection_failed" in detail_text or "inappropriate content" in detail_text:
        risk_score = 70
        label = "suspicious"
        confidence = 0.75
    frames = [
        {
            "frame_path": frame["frame_path"],
            "timestamp_sec": frame["timestamp_sec"],
            "label": label,
            "confidence": confidence,
            "risk_score": risk_score,
        }
        for frame in frame_result
    ]
    return {"video_id": video_id, "frames": frames, "image_score": risk_score}


def call_dashscope_video_moderation(video_url: str) -> dict:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DASHSCOPE_API_KEY is required for DashScope video moderation.")
    model = os.getenv("ALIYUN_VIDEO_MODEL", "qwen3-vl-flash")
    prompt = (
        "你是短视频内容安全审核模型。请审核视频画面、字幕和可见文字，只输出严格 JSON，不要输出解释。"
        "这是多标签任务，一个视频可以同时属于 violence, porn, politics, illegal, ad, suspicious。"
        "如果没有明显风险，labels 输出 [\"normal\"]。如果同时有暴力和政治内容，labels 输出 [\"violence\",\"politics\"]。"
        "risk_score 为 0-100 整数，normal 通常 0-10，疑似 30-69，明确违规 70-100。"
        "JSON 格式：{\"labels\":[\"normal\"],\"risk_score\":5,\"confidence\":0.90,\"reason\":\"简短中文原因\"}"
    )
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "video_url", "video_url": {"url": video_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0,
        "enable_thinking": False,
        "max_tokens": 512,
    }
    data = requests_post_json(
        DASHSCOPE_CHAT_URL,
        payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=int(os.getenv("ALIYUN_VIDEO_REQUEST_TIMEOUT_SEC", "120")),
    )
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    parsed = parse_json_object(content)
    if not parsed:
        raise HTTPException(status_code=502, detail=f"DashScope video moderation returned invalid JSON: {content[:300]}")
    return normalize_dashscope_video_moderation(parsed)


def parse_json_object(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def normalize_dashscope_video_moderation(result: dict) -> dict:
    labels = normalize_label_list(result.get("labels") or result.get("label") or "normal")
    try:
        risk_score = int(float(result.get("risk_score", 5)))
    except (TypeError, ValueError):
        risk_score = 5
    risk_score = max(0, min(100, risk_score))
    try:
        confidence = float(result.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(1.0, confidence))
    if (not labels or labels == ["normal"]) and risk_score >= 30:
        labels = ["suspicious"]
    return {
        "labels": labels,
        "label": ",".join(labels) if labels else "normal",
        "risk_score": risk_score,
        "confidence": confidence,
        "reason": str(result.get("reason") or "")[:200],
    }


def upload_file_to_aliyun_oss(file_path: Path, prefix: str) -> tuple[str, str]:
    try:
        import oss2
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Aliyun OSS dependency is missing. Run pip install -r ai-service-fastapi/requirements.txt.",
        ) from exc

    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET")
    bucket_name = os.getenv("ALIYUN_OSS_BUCKET")
    endpoint = os.getenv("ALIYUN_OSS_ENDPOINT")
    if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
        raise HTTPException(
            status_code=500,
            detail="ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, ALIYUN_OSS_BUCKET and ALIYUN_OSS_ENDPOINT are required.",
        )

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, normalize_oss_endpoint(endpoint), bucket_name)
    object_key = f"videoguard/{prefix}/{uuid.uuid4().hex}{file_path.suffix.lower()}"
    bucket.put_object_from_file(object_key, str(file_path))
    expires = int(os.getenv("ALIYUN_OSS_SIGNED_URL_EXPIRES", "3600"))
    signed_url = bucket.sign_url("GET", object_key, expires)
    return object_key, signed_url


def cleanup_aliyun_oss_object(object_key: str) -> None:
    if os.getenv("ALIYUN_OSS_KEEP_OBJECTS", "false").lower() in {"1", "true", "yes", "on"}:
        return
    try:
        import oss2

        access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID")
        access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET")
        bucket_name = os.getenv("ALIYUN_OSS_BUCKET")
        endpoint = os.getenv("ALIYUN_OSS_ENDPOINT")
        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            return
        bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), normalize_oss_endpoint(endpoint), bucket_name)
        bucket.delete_object(object_key)
    except Exception:
        pass


def normalize_oss_endpoint(endpoint: str | None) -> str:
    endpoint = (endpoint or "").strip()
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    return f"https://{endpoint}"


def create_aliyun_video_moderation_task(video_url: str) -> str:
    try:
        from alibabacloud_green20220302.client import Client as GreenClient
        from alibabacloud_green20220302 import models as green_models
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Aliyun Green dependency is missing. Run pip install -r ai-service-fastapi/requirements.txt.",
        ) from exc

    client = GreenClient(
        open_api_models.Config(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID"),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET"),
            endpoint=os.getenv("ALIYUN_GREEN_ENDPOINT", "green-cip.cn-shanghai.aliyuncs.com"),
            region_id=os.getenv("ALIYUN_REGION_ID", "cn-beijing"),
        )
    )
    service = os.getenv("ALIYUN_GREEN_VIDEO_SERVICE", "videoDetection")
    request = green_models.VideoModerationRequest(
        service=service,
        service_parameters=json.dumps({"url": video_url}, ensure_ascii=False),
    )
    response = client.video_moderation(request)
    data = response.to_map()
    ensure_aliyun_green_success(data, "video moderation")
    task_id = find_first_key(data, {"taskId", "task_id", "TaskId"})
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Aliyun video moderation response missing task id: {data}")
    return str(task_id)


def poll_aliyun_video_moderation_task(task_id: str) -> dict:
    try:
        from alibabacloud_green20220302.client import Client as GreenClient
        from alibabacloud_green20220302 import models as green_models
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Aliyun Green dependency is missing.") from exc

    client = GreenClient(
        open_api_models.Config(
            access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID"),
            access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET"),
            endpoint=os.getenv("ALIYUN_GREEN_ENDPOINT", "green-cip.cn-shanghai.aliyuncs.com"),
            region_id=os.getenv("ALIYUN_REGION_ID", "cn-beijing"),
        )
    )
    timeout_sec = int(os.getenv("ALIYUN_GREEN_TIMEOUT_SEC", "300"))
    interval_sec = float(os.getenv("ALIYUN_GREEN_POLL_INTERVAL_SEC", "5"))
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        request = green_models.VideoModerationResultRequest(service_parameters=json.dumps({"taskId": task_id}))
        response = client.video_moderation_result(request)
        data = response.to_map()
        ensure_aliyun_green_success(data, "video moderation result")
        status = str(find_first_key(data, {"status", "Status", "taskStatus", "TaskStatus"}) or "").lower()
        if status in {"success", "succeeded", "finish", "finished", "done"} or "riskLevel" in json.dumps(data):
            return data
        if status in {"failed", "failure", "error", "canceled"}:
            raise HTTPException(status_code=502, detail=f"Aliyun video moderation task failed: {data}")
        time.sleep(interval_sec)
    raise HTTPException(status_code=504, detail=f"Aliyun video moderation task timed out after {timeout_sec} seconds.")


def summarize_aliyun_video_moderation(result: dict) -> tuple[list[str], float, int]:
    result_text = json.dumps(result, ensure_ascii=False)
    risk_level = str(find_first_key(result, {"riskLevel", "RiskLevel", "risk_level"}) or "").lower()
    labels = collect_values_by_key(result, {"label", "Label", "riskLabel", "RiskLabel", "riskTips"})
    label_text = ",".join(str(label) for label in labels if label)
    combined = f"{risk_level} {label_text} {result_text}".lower()
    if any(word in combined for word in ["high", "block", "violation", "porn", "terrorism", "violence", "ad"]):
        return normalize_label_list(label_text or "violation"), 0.9, 80
    if any(word in combined for word in ["medium", "review", "疑似", "manual"]):
        return normalize_label_list(label_text or "suspicious"), 0.75, 50
    return normalize_label_list(label_text or "normal"), 0.9, 5


def normalize_label_list(value) -> list[str]:
    raw_values: list[str] = []
    if isinstance(value, list):
        for item in value:
            raw_values.extend(split_label_text(str(item)))
    else:
        raw_values.extend(split_label_text(str(value)))

    labels: list[str] = []
    for raw in raw_values:
        label = normalize_aliyun_label(raw)
        if label == "normal":
            continue
        if label and label not in labels:
            labels.append(label)
    return labels or ["normal"]


def split_label_text(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,，;/；、\s]+", text or "") if item.strip()]


def normalize_aliyun_label(label: str) -> str:
    lowered = label.lower()
    if "normal" in lowered or "pass" in lowered or "正常" in label:
        return "normal"
    if "porn" in lowered or "sexual" in lowered or "色情" in label or "涉黄" in label:
        return "porn"
    if "violence" in lowered or "terrorism" in lowered or "violent" in lowered or "暴力" in label or "恐怖" in label:
        return "violence"
    if "politics" in lowered or "political" in lowered or "政治" in label or "涉政" in label:
        return "politics"
    if "illegal" in lowered or "违法" in label or "违规" in label:
        return "illegal"
    if lowered in {"ad", "ads", "advertisement", "advertising"} or "广告" in label:
        return "ad"
    if "suspicious" in lowered or "疑似" in label:
        return "suspicious"
    return label[:64] or "normal"


def ensure_aliyun_green_success(data: dict, action: str) -> None:
    body = data.get("body") if isinstance(data, dict) else None
    code = body.get("Code") if isinstance(body, dict) else None
    if code not in {None, 200, "200"}:
        message = body.get("Message") or body
        raise HTTPException(status_code=502, detail=f"Aliyun {action} failed: {message}")


def find_first_key(value, keys: set[str]):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                return item
            found = find_first_key(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_first_key(item, keys)
            if found is not None:
                return found
    return None


def collect_values_by_key(value, keys: set[str]) -> list:
    values = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                values.append(item)
            values.extend(collect_values_by_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            values.extend(collect_values_by_key(item, keys))
    return values


def requests_post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="requests dependency is missing.") from exc
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON response from {url}: {response.text[:300]}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Request failed: {data}")
    return data


def requests_get_json(url: str, headers: dict, timeout: int) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="requests dependency is missing.") from exc
    response = requests.get(url, headers=headers, timeout=timeout)
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON response from {url}: {response.text[:300]}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Request failed: {data}")
    return data


def resolve_video_path(video_path: str) -> Path:
    path = Path(video_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_file_exists(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Video file not found: {path}")


def extract_metadata(video_path: Path) -> dict:
    if shutil.which("ffprobe"):
        return extract_metadata_by_ffprobe(video_path)
    return extract_metadata_by_opencv(video_path)


def transcribe_video_audio(video_path: Path, language: str | None = None, fail_silently: bool = False) -> str:
    if not is_asr_enabled():
        return ""
    try:
        provider = os.getenv("VIDEOGUARD_ASR_PROVIDER", "local").strip().lower()
        if provider in {"aliyun", "alibaba", "dashscope"}:
            return transcribe_video_audio_by_aliyun(video_path)
        if provider in {"tencent", "tencentcloud", "tencent_cloud"}:
            return transcribe_video_audio_by_tencent(video_path)
        return transcribe_video_audio_locally(video_path, language)
    except HTTPException:
        if fail_silently:
            return ""
        raise
    except Exception as exc:
        if fail_silently:
            return ""
        raise HTTPException(status_code=500, detail=f"ASR transcription failed: {exc}") from exc


def is_asr_enabled() -> bool:
    return os.getenv("VIDEOGUARD_ASR_ENABLED", "true").lower() not in {"0", "false", "no", "off"}


def transcribe_video_audio_locally(video_path: Path, language: str | None = None) -> str:
    audio_path = extract_audio_for_local_asr(video_path)
    try:
        model = get_asr_model(
            os.getenv("VIDEOGUARD_ASR_MODEL", "tiny"),
            os.getenv("VIDEOGUARD_ASR_DEVICE", "cpu"),
            os.getenv("VIDEOGUARD_ASR_COMPUTE_TYPE", "int8"),
        )
        selected_language = language if language is not None else os.getenv("VIDEOGUARD_ASR_LANGUAGE", "zh")
        if selected_language in {"", "auto", "AUTO"}:
            selected_language = None
        segments, _ = model.transcribe(
            str(audio_path),
            language=selected_language,
            vad_filter=True,
            beam_size=5,
        )
        return normalize_asr_text(segment.text for segment in segments)
    finally:
        cleanup_temp_audio(audio_path)


def transcribe_video_audio_by_tencent(video_path: Path) -> str:
    audio_path = extract_audio_for_tencent_asr(video_path)
    try:
        task_id = create_tencent_asr_task(audio_path)
        return poll_tencent_asr_task(task_id)
    finally:
        cleanup_temp_audio(audio_path)


def transcribe_video_audio_by_aliyun(video_path: Path) -> str:
    audio_path = extract_audio_for_aliyun_asr(video_path)
    object_key, signed_url = upload_file_to_aliyun_oss(audio_path, "asr")
    try:
        task_id = create_aliyun_asr_task(signed_url)
        return poll_aliyun_asr_task(task_id)
    finally:
        cleanup_temp_audio(audio_path)
        cleanup_aliyun_oss_object(object_key)


def extract_audio_for_asr(video_path: Path) -> Path:
    return extract_audio_for_local_asr(video_path)


def extract_audio_for_local_asr(video_path: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=500, detail="ffmpeg is required for ASR audio extraction.")

    temp_dir = Path(tempfile.mkdtemp(prefix="videoguard-asr-"))
    audio_path = temp_dir / "audio.wav"
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        detail = result.stderr.strip() or "No audio stream could be extracted."
        raise HTTPException(status_code=400, detail=f"ASR audio extraction failed: {detail}")
    return audio_path


def extract_audio_for_tencent_asr(video_path: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=500, detail="ffmpeg is required for ASR audio extraction.")

    temp_dir = Path(tempfile.mkdtemp(prefix="videoguard-asr-"))
    audio_path = temp_dir / "audio.mp3"
    bitrate = os.getenv("TENCENT_ASR_AUDIO_BITRATE", "24k")
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        bitrate,
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        detail = result.stderr.strip() or "No audio stream could be extracted."
        raise HTTPException(status_code=400, detail=f"ASR audio extraction failed: {detail}")
    if audio_path.stat().st_size > TENCENT_ASR_MAX_UPLOAD_BYTES:
        size_mb = audio_path.stat().st_size / 1024 / 1024
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=413,
            detail=(
                f"Tencent ASR local upload is limited to 5 MB. "
                f"Extracted audio is {size_mb:.2f} MB. Use a shorter video or configure COS URL mode later."
            ),
        )
    return audio_path


def extract_audio_for_aliyun_asr(video_path: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise HTTPException(status_code=500, detail="ffmpeg is required for ASR audio extraction.")

    temp_dir = Path(tempfile.mkdtemp(prefix="videoguard-asr-"))
    audio_path = temp_dir / "audio.mp3"
    bitrate = os.getenv("ALIYUN_ASR_AUDIO_BITRATE", "64k")
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        bitrate,
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        detail = result.stderr.strip() or "No audio stream could be extracted."
        raise HTTPException(status_code=400, detail=f"ASR audio extraction failed: {detail}")
    return audio_path


def create_aliyun_asr_task(file_url: str) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DASHSCOPE_API_KEY is required for Aliyun ASR.")

    payload = {
        "model": os.getenv("ALIYUN_ASR_MODEL", "qwen3-asr-flash-filetrans"),
        "input": {"file_urls": [file_url]},
        "parameters": build_aliyun_asr_parameters(),
    }
    response = requests_post_json(
        DASHSCOPE_BASE_URL,
        payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        timeout=30,
    )
    task_id = (response.get("output") or {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"Aliyun ASR response missing task_id: {response}")
    return task_id


def build_aliyun_asr_parameters() -> dict:
    parameters: dict[str, object] = {}
    hotwords = os.getenv("ALIYUN_ASR_HOTWORDS", "").strip()
    if hotwords:
        parameters["hot_words"] = [word.strip() for word in hotwords.split(",") if word.strip()]
    return parameters


def poll_aliyun_asr_task(task_id: str) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    timeout_sec = int(os.getenv("ALIYUN_ASR_TIMEOUT_SEC", "300"))
    interval_sec = float(os.getenv("ALIYUN_ASR_POLL_INTERVAL_SEC", "5"))
    deadline = time.monotonic() + timeout_sec
    task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    while time.monotonic() < deadline:
        response = requests_get_json(
            task_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        output = response.get("output") or {}
        status = str(output.get("task_status") or "").upper()
        if status == "SUCCEEDED":
            return fetch_aliyun_asr_transcript(output)
        if status in {"FAILED", "CANCELED", "UNKNOWN"}:
            raise HTTPException(status_code=502, detail=f"Aliyun ASR task failed: {response}")
        time.sleep(interval_sec)
    raise HTTPException(status_code=504, detail=f"Aliyun ASR task timed out after {timeout_sec} seconds.")


def fetch_aliyun_asr_transcript(output: dict) -> str:
    results = output.get("results") or []
    texts: list[str] = []
    for item in results:
        transcription_url = item.get("transcription_url") or item.get("url")
        if transcription_url:
            result = requests_get_json(transcription_url, headers={}, timeout=60)
            texts.extend(extract_text_from_aliyun_asr_result(result))
        else:
            texts.extend(extract_text_from_aliyun_asr_result(item))
    return apply_aliyun_asr_corrections(normalize_asr_text(texts))


def extract_text_from_aliyun_asr_result(result: object) -> list[str]:
    texts: list[str] = []
    if isinstance(result, dict):
        child_texts: list[str] = []
        for key in ("sentences", "transcripts", "segments", "results"):
            value = result.get(key)
            if isinstance(value, list):
                for item in value:
                    child_texts.extend(extract_text_from_aliyun_asr_result(item))
            elif isinstance(value, dict):
                child_texts.extend(extract_text_from_aliyun_asr_result(value))
        if child_texts:
            return child_texts
        for key in ("text", "transcript", "sentence"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                texts.append(value.strip())
    elif isinstance(result, list):
        for item in result:
            texts.extend(extract_text_from_aliyun_asr_result(item))
    return texts


def apply_aliyun_asr_corrections(text: str) -> str:
    correction_config = os.getenv("ALIYUN_ASR_CORRECTIONS", "").strip()
    if not correction_config:
        return text
    corrected = text
    for item in correction_config.split(","):
        if "=>" not in item:
            continue
        source, target = item.split("=>", 1)
        source = source.strip()
        target = target.strip()
        if source and target:
            corrected = corrected.replace(source, target)
    return corrected


def create_tencent_asr_task(audio_path: Path) -> int:
    try:
        from tencentcloud.asr.v20190614 import asr_client, models
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Tencent ASR dependency is missing. Run pip install -r ai-service-fastapi/requirements.txt.",
        ) from exc

    secret_id = os.getenv("TENCENT_SECRET_ID")
    secret_key = os.getenv("TENCENT_SECRET_KEY")
    if not secret_id or not secret_key:
        raise HTTPException(status_code=500, detail="TENCENT_SECRET_ID and TENCENT_SECRET_KEY are required.")

    http_profile = HttpProfile()
    http_profile.endpoint = "asr.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    client = asr_client.AsrClient(
        credential.Credential(secret_id, secret_key),
        os.getenv("TENCENT_ASR_REGION", "ap-shanghai"),
        client_profile,
    )

    payload = {
        "EngineModelType": os.getenv("TENCENT_ASR_ENGINE_MODEL_TYPE", "16k_zh"),
        "ChannelNum": int(os.getenv("TENCENT_ASR_CHANNEL_NUM", "1")),
        "ResTextFormat": int(os.getenv("TENCENT_ASR_RES_TEXT_FORMAT", "0")),
        "SourceType": 1,
        "Data": b64encode(audio_path.read_bytes()).decode("ascii"),
        "DataLen": audio_path.stat().st_size,
    }
    hotword_list = os.getenv("TENCENT_ASR_HOTWORD_LIST", "").strip()
    if hotword_list:
        payload["HotwordList"] = hotword_list
    req = models.CreateRecTaskRequest()
    req.from_json_string(json.dumps(payload))
    try:
        response = client.CreateRecTask(req)
    except TencentCloudSDKException as exc:
        raise HTTPException(status_code=502, detail=f"Tencent ASR task creation failed: {exc}") from exc

    data = json.loads(response.to_json_string()).get("Data") or {}
    task_id = data.get("TaskId")
    if task_id is None:
        raise HTTPException(status_code=502, detail=f"Tencent ASR response missing TaskId: {data}")
    return int(task_id)


def poll_tencent_asr_task(task_id: int) -> str:
    from tencentcloud.asr.v20190614 import asr_client, models
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile

    secret_id = os.getenv("TENCENT_SECRET_ID")
    secret_key = os.getenv("TENCENT_SECRET_KEY")
    http_profile = HttpProfile()
    http_profile.endpoint = "asr.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    client = asr_client.AsrClient(
        credential.Credential(secret_id, secret_key),
        os.getenv("TENCENT_ASR_REGION", "ap-shanghai"),
        client_profile,
    )

    timeout_sec = int(os.getenv("TENCENT_ASR_TIMEOUT_SEC", "180"))
    interval_sec = float(os.getenv("TENCENT_ASR_POLL_INTERVAL_SEC", "3"))
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        req = models.DescribeTaskStatusRequest()
        req.from_json_string(json.dumps({"TaskId": task_id}))
        try:
            response = client.DescribeTaskStatus(req)
        except TencentCloudSDKException as exc:
            raise HTTPException(status_code=502, detail=f"Tencent ASR task polling failed: {exc}") from exc
        data = json.loads(response.to_json_string()).get("Data") or {}
        status = data.get("Status")
        status_text = data.get("StatusStr") or data.get("ErrorMsg") or ""
        if status == 2 or str(status_text).lower() in {"success", "finished", "complete", "completed"}:
            return normalize_tencent_asr_text(data.get("Result", ""))
        if status == 3 or str(status_text).lower() in {"failed", "failure", "error"}:
            raise HTTPException(status_code=502, detail=f"Tencent ASR task failed: {status_text or data}")
        time.sleep(interval_sec)

    raise HTTPException(status_code=504, detail=f"Tencent ASR task timed out after {timeout_sec} seconds.")


@lru_cache(maxsize=4)
def get_asr_model(model_size: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="ASR dependency is missing. Install faster-whisper from ai-service-fastapi/requirements.txt.",
        ) from exc

    model_dir = os.getenv("VIDEOGUARD_ASR_MODEL_DIR")
    return WhisperModel(model_size, device=device, compute_type=compute_type, download_root=model_dir)


def normalize_asr_text(parts) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def normalize_tencent_asr_text(text: str) -> str:
    text = re.sub(r"\[\d+:\d+(?:\.\d+)?,\d+:\d+(?:\.\d+)?\]\s*", "", text or "")
    text = apply_asr_corrections(text)
    return normalize_asr_text([text])


def apply_asr_corrections(text: str) -> str:
    correction_config = os.getenv("TENCENT_ASR_CORRECTIONS", "").strip()
    if not correction_config:
        return text
    corrected = text
    for item in correction_config.split(","):
        if "=>" not in item:
            continue
        source, target = item.split("=>", 1)
        source = source.strip()
        target = target.strip()
        if source and target:
            corrected = corrected.replace(source, target)
    return corrected


def cleanup_temp_audio(audio_path: Path) -> None:
    shutil.rmtree(audio_path.parent, ignore_errors=True)


def extract_metadata_by_ffprobe(video_path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        stream = json.loads(result.stdout)["streams"][0]
        fps = parse_fps(stream.get("r_frame_rate", "0/1"))
        duration = float(stream.get("duration") or 0)
        return {
            "duration": round(duration, 3),
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "fps": round(fps, 3),
            "file_size": video_path.stat().st_size,
        }
    except (subprocess.CalledProcessError, KeyError, ValueError, IndexError) as exc:
        raise HTTPException(status_code=500, detail=f"ffprobe metadata extraction failed: {exc}") from exc


def extract_metadata_by_opencv(video_path: Path) -> dict:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise HTTPException(status_code=400, detail=f"Unable to open video file: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if fps > 0 else 0
    metadata_result = {
        "duration": round(duration, 3),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
        "fps": round(fps, 3),
        "file_size": video_path.stat().st_size,
    }
    capture.release()
    return metadata_result


def extract_video_frames(video_path: Path, video_id: int, frame_interval_sec: int) -> list[dict]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise HTTPException(status_code=400, detail=f"Unable to open video file: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if fps > 0 else 0
    output_dir = PROJECT_ROOT / "uploads" / "frames" / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamps = build_timestamps(duration, frame_interval_sec)
    frames: list[dict] = []
    for index, timestamp_sec in enumerate(timestamps):
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000)
        ok, frame = capture.read()
        if not ok:
            continue
        relative_path = Path("uploads") / "frames" / str(video_id) / f"frame_{index:04d}.jpg"
        output_path = PROJECT_ROOT / relative_path
        cv2.imwrite(str(output_path), frame)
        frames.append(
            {
                "frame_path": relative_path.as_posix(),
                "timestamp_sec": round(timestamp_sec, 3),
            }
        )

    capture.release()
    if not frames:
        raise HTTPException(status_code=400, detail=f"No frames could be extracted from: {video_path}")
    return frames


def build_timestamps(duration: float, frame_interval_sec: int) -> list[float]:
    if duration <= 0:
        return [0]
    timestamps = []
    current = 0.0
    while current <= duration:
        timestamps.append(current)
        current += frame_interval_sec
    return timestamps or [0]


def parse_fps(value: str) -> float:
    if "/" not in value:
        return float(value)
    numerator, denominator = value.split("/", 1)
    denominator_value = float(denominator)
    if denominator_value == 0:
        return 0
    return float(numerator) / denominator_value


def build_context(text: str, word: str, radius: int = 12) -> str:
    index = text.find(word)
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(text), index + len(word) + radius)
    return text[start:end]


def score_to_risk_level(score: int | float, category: str | None = None) -> str:
    suspicious_threshold, violation_threshold = category_risk_thresholds(category or "")
    if score < suspicious_threshold:
        return "PASS"
    if score < violation_threshold:
        return "SUSPICIOUS"
    return "VIOLATION"
