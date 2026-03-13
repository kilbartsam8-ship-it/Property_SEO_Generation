from groq import Groq

from ..config import Settings
from ..models import PropertyInput
from .prompt_builder import build_seo_prompt
from .seo_generator import generate_seo_markdown
from .seo_schema import enforce_seo_schema, parse_llm_json


class SeoPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = Groq(api_key=settings.groq_api_key)

    def generate(self, user_input: PropertyInput, brochure_text: str, website_text: str, file_label: str) -> dict:
        prompt = build_seo_prompt(
            user_input=user_input,
            brochure_text=brochure_text,
            website_text=website_text,
            file_label=file_label,
        )
        llm_output = generate_seo_markdown(self.client, self.settings.model, prompt)
        raw_payload = parse_llm_json(llm_output)
        return enforce_seo_schema(raw_payload, user_input)

