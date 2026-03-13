import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

from .config import DEFAULT_MODEL, ConfigError, Settings, load_settings
from .models import PropertyInput
from .services.context_service import ContextService
from .services.seo_pipeline import SeoPipeline
from .services.seo_schema import to_clean_list
from .services.validation import is_valid_url

LOGGER = logging.getLogger("seo_property_app")
OUTPUT_DIR = Path("output")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SEO property content JSON in terminal")
    parser.add_argument("--file", type=str, default="", help="Optional path to property info file (PDF/DOCX/CSV)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Groq model name")
    parser.add_argument("--no-summarize", action="store_true", help="Disable summarization for long PDF text")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        settings = load_settings(model=args.model, no_summarize=args.no_summarize)
    except ConfigError as exc:
        LOGGER.error(str(exc))
        print(f"\n{exc}")
        return 1

    app = SeoPropertyCli(settings)
    return app.run(file_path=args.file or None)


class SeoPropertyCli:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.context_service = ContextService(settings)
        self.pipeline = SeoPipeline(settings)

    def run(self, file_path: str | None = None) -> int:
        print("\nSEO PROPERTY CONTENT GENERATOR (JSON)")

        extracted_text, extracted_info, resolved_file_path = self._extract_context(file_path)
        user_input = self._collect_user_input(extracted_info)
        website_text = self.context_service.extract_website_context(user_input.property_url)

        try:
            seo_payload = self.pipeline.generate(
                user_input=user_input,
                brochure_text=extracted_text,
                website_text=website_text,
                file_label=resolved_file_path,
            )
        except Exception as exc:
            LOGGER.exception("Generation failed")
            print(f"\nGeneration failed: {exc}")
            return 1

        final_payload = {
            "status": "ok",
            "input": {
                "property_name": user_input.project_name,
                "property_info_file": resolved_file_path,
                "property_url": user_input.property_url,
                "property_type": user_input.property_type,
                "listing_type": user_input.listing_type,
                "location": user_input.location,
                "bhk_area": user_input.bhk_area,
                "amenities": to_clean_list(user_input.amenities),
                "usp_or_highlights": user_input.usp,
                "target_audience": user_input.target_audience,
                "tone_preference": user_input.tone_preference,
                "keywords": to_clean_list(user_input.keywords),
            },
            "source_context": {
                "file_text_used": bool(extracted_text.strip()),
                "url_text_used": bool(website_text.strip()),
            },
            "seo_content": seo_payload,
        }

        saved_file = self._save_output(user_input.project_name, final_payload)
        self._print_output(final_payload, saved_file)
        return 0

    def _extract_context(self, file_path: str | None) -> tuple[str, dict[str, Any], str]:
        chosen_path = file_path or input("\nProperty info file path (PDF/DOCX/CSV) or press Enter to skip: ").strip()
        if not chosen_path:
            return "", {}, ""

        path = Path(chosen_path.strip('"').strip("'"))
        if not path.exists() or not path.is_file():
            print("\nFile not found. Continuing without file extraction.")
            return "", {}, ""

        try:
            text = self.context_service.extract_path_text(path)
            if not text.strip():
                print("\nNo text extracted from file. Continuing with manual input.")
                return "", {}, str(path)
            info = self.context_service.extract_structured_info(text)
            return text, info, str(path)
        except Exception as exc:
            LOGGER.exception("File processing failed")
            print(f"\nFile processing issue: {exc}")
            return "", {}, str(path)

    def _collect_user_input(self, extracted_info: dict[str, Any]) -> PropertyInput:
        print("\n--- REQUIRED INPUTS ---")
        project_name = self._ask_required("Property name", extracted_info, "Project Name")
        property_url = self._ask_url("Property URL (optional)")
        property_type = self._ask_required("Property type", extracted_info, "Property Type")
        listing_type = self._ask_required("Listing type (sale/rent/commercial/etc)")
        location = self._ask_required("Location", extracted_info, "Location")
        bhk_area = self._ask_required("BHK and area", extracted_info, "BHK & Area")
        amenities = self._ask_required("Amenities (comma separated)", extracted_info, "Amenities")
        usp = self._ask_required("USP or highlights", extracted_info, "USP / Highlights")
        target_audience = self._ask_required("Target audience", extracted_info, "Target Audience")
        tone_preference = self._ask_required("Tone preference (luxury/friendly/professional/etc)")
        keywords = input("Keywords (optional, comma separated): ").strip()

        return PropertyInput(
            project_name=project_name,
            property_url=property_url,
            property_type=property_type,
            listing_type=listing_type,
            location=location,
            bhk_area=bhk_area,
            amenities=amenities,
            usp=usp,
            target_audience=target_audience,
            tone_preference=tone_preference,
            keywords=keywords,
        )

    def _ask_required(self, label: str, info: dict[str, Any] | None = None, key: str | None = None) -> str:
        default_value = ""
        if info is not None and key:
            default_value = str(info.get(key, "")).strip()

        while True:
            value = input(f"{label} [{default_value}]: ").strip() if default_value else input(f"{label}: ").strip()
            final = value or default_value
            if final:
                return final
            print(f"{label} is required.")

    def _ask_url(self, label: str) -> str:
        while True:
            value = input(f"{label}: ").strip()
            if not value:
                return ""
            if is_valid_url(value):
                return value
            print("Invalid URL. Use full URL with http/https.")

    @staticmethod
    def _sanitize_filename(project_name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", project_name)
        return cleaned or "output"

    def _save_output(self, project_name: str, payload: dict[str, Any]) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        file_path = OUTPUT_DIR / f"{self._sanitize_filename(project_name)}_SEO.json"
        file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return file_path

    @staticmethod
    def _print_output(payload: dict[str, Any], file_path: Path) -> None:
        print("\n" + "=" * 60)
        print("GENERATED SEO CONTENT (JSON)")
        print("=" * 60)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"\nSaved as: {file_path}")

