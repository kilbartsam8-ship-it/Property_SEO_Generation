import requests

API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_BROCHURE_LEN = 3000
REQUEST_TIMEOUT_SECONDS = 30

FIELDS = [
    "Project Name",
    "Location",
    "Property Type",
    "BHK & Area",
    "Price Range",
    "Possession Status",
    "USP / Highlights",
    "Amenities",
    "Nearby Landmarks",
    "Target Audience",
]


class ExtractionError(Exception):
    """Raised when info extraction fails."""


def _blank_payload() -> dict:
    return {field: "" for field in FIELDS}


def extract_info_from_text(text: str, api_key: str, model: str) -> dict:
    brochure_text = (text or "").strip()
    if not brochure_text:
        return _blank_payload()

    if len(brochure_text) > MAX_BROCHURE_LEN:
        brochure_text = brochure_text[:MAX_BROCHURE_LEN]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    prompt = (
        "Extract the following property details from the brochure text below. "
        "Respond ONLY with a valid JSON object with the following fields as keys. "
        "Do not include any explanation, markdown, or text outside the JSON. "
        "If a field is not present, return an empty string for it. "
        f"Fields: {', '.join(FIELDS)}.\n\nBrochure Text:\n{brochure_text}\n"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ExtractionError(f"Extraction request failed: {exc}") from exc

    if response.status_code != 200:
        raise ExtractionError(f"Extraction API returned {response.status_code}: {response.text}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ExtractionError(f"Unexpected extraction response format: {exc}") from exc

    import json
    import re

    match = re.search(r"\{[\s\S]*\}", content)
    candidate = match.group(0) if match else content

    try:
        parsed = json.loads(candidate)
    except Exception as exc:
        fallback = _blank_payload()
        fallback["error"] = f"Failed to parse JSON: {exc}"
        fallback["raw"] = content
        return fallback

    normalized = _blank_payload()
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            normalized[key] = value
    return normalized
