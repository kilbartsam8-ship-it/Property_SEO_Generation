import requests

API_URL = "https://router.huggingface.co/together/v1/chat/completions"
CHUNK_SIZE = 6000
REQUEST_TIMEOUT_SECONDS = 45
SUMMARY_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"


class SummarizationError(Exception):
    """Raised when summarization fails."""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def summarize_chunk(chunk: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": SUMMARY_MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Summarize the following property brochure content for key real estate details, "
                    "amenities, highlights, and location.\n\n"
                    f"{chunk}"
                ),
            }
        ],
        "max_tokens": 500,
        "temperature": 0.3,
    }
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise SummarizationError(f"Summarization request failed: {exc}") from exc

    if response.status_code != 200:
        raise SummarizationError(f"Summarization failed: {response.text}")

    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        raise SummarizationError(f"Unexpected summarizer response format: {exc}") from exc


def summarize_pdf_text(pdf_text: str, api_key: str) -> str:
    if not (pdf_text or "").strip():
        return ""

    if len(pdf_text) <= CHUNK_SIZE:
        return summarize_chunk(pdf_text, api_key)

    summaries: list[str] = []
    for idx, chunk in enumerate(chunk_text(pdf_text), start=1):
        try:
            summaries.append(summarize_chunk(chunk, api_key))
        except SummarizationError as exc:
            summaries.append(f"[Chunk {idx} summarization failed: {exc}]")

    combined = "\n".join(summaries)
    if len(combined) > CHUNK_SIZE:
        return summarize_chunk(combined, api_key)
    return combined
