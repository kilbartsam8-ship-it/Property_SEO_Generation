from ..models import PropertyInput
from .seo_schema import to_clean_list


def build_seo_prompt(user_input: PropertyInput, brochure_text: str, website_text: str, file_label: str) -> str:
    brochure_excerpt = (brochure_text or "")[:6000]
    website_excerpt = (website_text or "")[:6000]
    keywords = to_clean_list(user_input.keywords)
    amenities = to_clean_list(user_input.amenities)

    return f"""
You are an expert real estate SEO content writer.

Use all provided inputs and contexts to produce SEO content.
Do not add fake specifics that are not supported by inputs/context.
Respond ONLY in valid JSON.

Required JSON schema:
{{
  "seo_title": "string",
  "meta_description": "string (155-160 chars)",
  "slug": "string-lowercase-hyphenated",
  "intro_paragraph": "string",
  "key_features": ["string"],
  "amenities_section": "string",
  "usp_highlights_section": "string",
  "target_audience_section": "string",
  "location_advantages": ["string"],
  "call_to_action": "string",
  "suggested_keywords": ["string"]
}}

User Inputs:
- Property Name: {user_input.project_name}
- Property Info File: {file_label or "Not provided"}
- Property URL: {user_input.property_url or "Not provided"}
- Property Type: {user_input.property_type}
- Listing Type: {user_input.listing_type}
- Location: {user_input.location}
- BHK and Area: {user_input.bhk_area}
- Amenities: {amenities}
- USP / Highlights: {user_input.usp}
- Target Audience: {user_input.target_audience}
- Tone Preference: {user_input.tone_preference}
- Keywords (optional): {keywords}

Extracted Property File Context:
{brochure_excerpt or "Not available"}

Scraped Website Context:
{website_excerpt or "Not available"}
""".strip()

