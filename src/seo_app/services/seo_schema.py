import json
import re
from typing import Any

from ..models import PropertyInput

SEO_SCHEMA_DEFAULTS: dict[str, Any] = {
    "seo_title": "",
    "meta_description": "",
    "slug": "",
    "intro_paragraph": "",
    "key_features": [],
    "amenities_section": "",
    "usp_highlights_section": "",
    "target_audience_section": "",
    "location_advantages": [],
    "call_to_action": "",
    "suggested_keywords": [],
}


def to_clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return re.sub(r"\s+", " ", text).strip()


def to_clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [to_clean_text(item) for item in value]
        return [item for item in items if item]
    if isinstance(value, str):
        normalized = value
        for sep in ["\n", ";", "|"]:
            normalized = normalized.replace(sep, ",")
        items = [to_clean_text(item) for item in normalized.split(",")]
        return [item for item in items if item]
    item = to_clean_text(value)
    return [item] if item else []


def parse_llm_json(content: str) -> dict[str, Any]:
    text = content if isinstance(content, str) else str(content)
    match = re.search(r"\{[\s\S]*\}", text)
    candidate = match.group(0) if match else text
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("LLM output is not a JSON object")
    return parsed


def normalize_slug(value: str) -> str:
    slug = value.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def trim_meta_description(value: str, max_len: int = 160) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def enforce_seo_schema(payload: dict[str, Any], user_input: PropertyInput) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, default in SEO_SCHEMA_DEFAULTS.items():
        raw_value = payload.get(key, default)
        if isinstance(default, list):
            normalized[key] = to_clean_list(raw_value)
        else:
            normalized[key] = to_clean_text(raw_value)

    if not normalized["seo_title"]:
        normalized["seo_title"] = user_input.project_name

    base_slug = normalized["slug"] or normalized["seo_title"] or user_input.project_name
    normalized["slug"] = normalize_slug(base_slug)
    normalized["meta_description"] = trim_meta_description(normalized["meta_description"])
    return {key: normalized[key] for key in SEO_SCHEMA_DEFAULTS.keys()}

