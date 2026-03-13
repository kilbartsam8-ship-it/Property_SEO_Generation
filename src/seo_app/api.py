# import io
# from pathlib import Path
# from typing import Any

# from fastapi import FastAPI, File, Form, HTTPException, UploadFile
# from pydantic import BaseModel

# from .config import DEFAULT_MODEL, ConfigError, load_settings
# from .models import PropertyInput
# from .services.context_service import ContextService
# from .services.seo_pipeline import SeoPipeline
# from .services.validation import is_valid_url

# app = FastAPI(title="SEO Property API", version="1.0.0")


# class SeoGenerateRequest(BaseModel):
#     property_name: str
#     property_type: str
#     listing_type: str
#     location: str
#     bhk_area: str
#     amenities: str
#     usp_or_highlights: str
#     target_audience: str
#     tone_preference: str
#     property_url: str = ""
#     property_info_pdf_url: str = ""
#     property_info_file_path: str = ""
#     keywords: str = ""
#     model: str = DEFAULT_MODEL
#     no_summarize: bool = False


# @app.get("/health")
# def health() -> dict[str, str]:
#     return {"status": "ok"}


# @app.post("/seo/generate")
# async def generate_seo(
#     payload: SeoGenerateRequest,
# ) -> dict[str, Any]:
#     return await _generate_seo_internal(payload=payload, property_info_file=None)


# @app.post("/seo/generate/form")
# async def generate_seo_form(
#     property_name: str = Form(...),
#     property_type: str = Form(...),
#     listing_type: str = Form(...),
#     location: str = Form(...),
#     bhk_area: str = Form(...),
#     amenities: str = Form(...),
#     usp_or_highlights: str = Form(...),
#     target_audience: str = Form(...),
#     tone_preference: str = Form(...),
#     property_url: str = Form(""),
#     property_info_pdf_url: str = Form(""),
#     property_info_file_path: str = Form(""),
#     keywords: str = Form(""),
#     model: str = Form(DEFAULT_MODEL),
#     no_summarize: bool = Form(False),
#     property_info_file: UploadFile | None = File(default=None),
# ) -> dict[str, Any]:
#     payload = SeoGenerateRequest(
#         property_name=property_name,
#         property_type=property_type,
#         listing_type=listing_type,
#         location=location,
#         bhk_area=bhk_area,
#         amenities=amenities,
#         usp_or_highlights=usp_or_highlights,
#         target_audience=target_audience,
#         tone_preference=tone_preference,
#         property_url=property_url,
#         property_info_pdf_url=property_info_pdf_url,
#         property_info_file_path=property_info_file_path,
#         keywords=keywords,
#         model=model,
#         no_summarize=no_summarize,
#     )
#     return await _generate_seo_internal(payload=payload, property_info_file=property_info_file)


# async def _generate_seo_internal(
#     payload: SeoGenerateRequest,
#     property_info_file: UploadFile | None,
# ) -> dict[str, Any]:
#     if payload.property_url and not is_valid_url(payload.property_url):
#         raise HTTPException(status_code=400, detail="Invalid property_url. Use full http/https URL.")
#     if payload.property_info_pdf_url and not is_valid_url(payload.property_info_pdf_url):
#         raise HTTPException(status_code=400, detail="Invalid property_info_pdf_url. Use full http/https URL.")

#     try:
#         settings = load_settings(model=payload.model, no_summarize=payload.no_summarize)
#     except ConfigError as exc:
#         raise HTTPException(status_code=500, detail=str(exc)) from exc

#     context_service = ContextService(settings)
#     pipeline = SeoPipeline(settings)

#     file_text = ""
#     file_name = ""

#     file_sources = [
#         bool((payload.property_info_pdf_url or "").strip()),
#         bool((payload.property_info_file_path or "").strip()),
#         property_info_file is not None,
#     ]
#     if sum(file_sources) > 1:
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "Provide only one file input: property_info_pdf_url, "
#                 "property_info_file_path, or property_info_file."
#             ),
#         )

#     if payload.property_info_pdf_url:
#         file_name = payload.property_info_pdf_url
#         try:
#             file_text = context_service.extract_pdf_url_text(payload.property_info_pdf_url)
#         except Exception as exc:
#             raise HTTPException(status_code=400, detail=f"PDF URL processing failed: {exc}") from exc
#     elif payload.property_info_file_path:
#         path = Path(payload.property_info_file_path).expanduser()
#         if not path.is_file():
#             raise HTTPException(status_code=400, detail=f"File not found: {path}")
#         file_name = str(path)
#         try:
#             file_text = context_service.extract_path_text(path)
#         except Exception as exc:
#             raise HTTPException(status_code=400, detail=f"File path processing failed: {exc}") from exc
#     elif property_info_file is not None:
#         file_name = property_info_file.filename or "uploaded_file"
#         try:
#             content = await property_info_file.read()
#             file_text = context_service.extract_upload_text(file_name, io.BytesIO(content))
#         except Exception as exc:
#             raise HTTPException(status_code=400, detail=f"File upload processing failed: {exc}") from exc

#     # Keep request values as source-of-truth, but fallback to extracted details if optional blanks are passed.
#     extracted_info = context_service.extract_structured_info(file_text)
#     if extracted_info:
#         payload.property_type = payload.property_type or str(extracted_info.get("Property Type", "")).strip()
#         payload.location = payload.location or str(extracted_info.get("Location", "")).strip()
#         payload.bhk_area = payload.bhk_area or str(extracted_info.get("BHK & Area", "")).strip()

#     website_text = context_service.extract_website_context(payload.property_url)

#     user_input = PropertyInput(
#         project_name=payload.property_name,
#         property_url=payload.property_url,
#         property_type=payload.property_type,
#         listing_type=payload.listing_type,
#         location=payload.location,
#         bhk_area=payload.bhk_area,
#         amenities=payload.amenities,
#         usp=payload.usp_or_highlights,
#         target_audience=payload.target_audience,
#         tone_preference=payload.tone_preference,
#         keywords=payload.keywords,
#     )

#     try:
#         return pipeline.generate(
#             user_input=user_input,
#             brochure_text=file_text,
#             website_text=website_text,
#             file_label=file_name,
#         )
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
import io
from pathlib import Path
from typing import Any
import time
from unittest import result


from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from tempfile import NamedTemporaryFile
import requests
try:
    from src.seo_app.config import DEFAULT_MODEL, ConfigError, load_settings
    from src.seo_app.models import PropertyInput
    from src.seo_app.services.context_service import ContextService
    from src.seo_app.services.seo_pipeline import SeoPipeline
    from src.seo_app.services.validation import is_valid_url
except ModuleNotFoundError:
    # Support running as a script from inside src/seo_app (python api.py).
    from .config import DEFAULT_MODEL, ConfigError, load_settings
    from models import PropertyInput
    from services.context_service import ContextService
    from services.seo_pipeline import SeoPipeline
    from services.validation import is_valid_url

app = FastAPI(title="SEO Property API", version="1.0.0")


class SeoGenerateRequest(BaseModel):
    session_id: int
    inputs: dict[str, Any]
    model: str = DEFAULT_MODEL
    no_summarize: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/seo/generate")
async def generate_seo(
    payload: SeoGenerateRequest) -> dict[str, Any]:
    return await _generate_seo_internal(payload=payload)




async def _generate_seo_internal(payload: SeoGenerateRequest):

    inputs = payload.inputs   # ⭐ your API inputs

    try:
        settings = load_settings(model=payload.model, no_summarize=payload.no_summarize)
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    context_service = ContextService(settings)
    pipeline = SeoPipeline(settings)

    # ==============================
    # ✅ 1 — Handle File Input
    # ==============================

    # file_text = ""
    # file_name = ""

    # file_path = inputs.get("property_info_file_path")

    # if file_path:
    #     path = Path(file_path)

    #     if not path.exists():
    #         raise HTTPException(status_code=400, detail=f"File not found: {path}")

    #     file_name = str(path)

    #     try:
    #         file_text = context_service.extract_path_text(path)
    #     except Exception as exc:
    #         raise HTTPException(status_code=400, detail=f"File processing failed: {exc}")
    
    file_text = ""
    file_name = ""
    file_path = inputs.get("property_info_file_path") or inputs.get("property_info_pdf_url")
    file_url_fetched = False
    file_path_is_url = False
    file_extract_seconds = 0.0
    if file_path:
        extract_start = time.perf_counter()
        try:
            if is_valid_url(file_path):
                file_path_is_url = True
                # ✅ download file from URL
                response = requests.get(file_path)
                response.raise_for_status()
                file_url_fetched = True

                with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = Path(tmp_file.name)
                file_name = str(tmp_file_path)
                file_text = context_service.extract_path_text(tmp_file_path)
            else:
                path = Path(file_path).expanduser()
                if not path.exists():
                    raise HTTPException(status_code=400, detail=f"File not found: {path}")
                file_name = str(path)
                file_text = context_service.extract_path_text(path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"File processing failed: {exc}") from exc
        finally:
            file_extract_seconds = time.perf_counter() - extract_start
    # ==============================
    # ✅ 2 — Website Context
    # ==============================

    property_url = inputs.get("property_url", "")

    if property_url and not is_valid_url(property_url):
        raise HTTPException(status_code=400, detail="Invalid property_url")

    website_text = context_service.extract_website_context(property_url)

    # ==============================
    # ✅ 3 — Convert to PropertyInput
    # ==============================

    user_input = PropertyInput(
        project_name=inputs.get("property_name", ""),
        property_url=property_url,
        property_type=inputs.get("property_type", ""),
        listing_type=inputs.get("listing_type", ""),
        location=inputs.get("location", ""),
        bhk_area=inputs.get("bhk_area", ""),
        amenities=inputs.get("amenities", ""),
        usp=inputs.get("usp_or_highlights", ""),
        target_audience=inputs.get("target_audience", ""),
        tone_preference=inputs.get("tone_preference", ""),
        keywords=inputs.get("keywords", ""),
    )

    # ==============================
    # ✅ 4 — Generate SEO
    # ==============================
    
 
    
    try:
        generation_start = time.perf_counter()
        result = pipeline.generate(
            user_input=user_input,
            brochure_text=file_text,
            website_text=website_text,
            file_label=file_name,
        )
        generation_seconds = time.perf_counter() - generation_start
        result["file_path_received"] = bool(file_path)
        result["file_path_value"] = file_path or ""
        result["file_path_is_url"] = file_path_is_url
        result["file_url_fetched"] = file_url_fetched
        result["file_text_extracted"] = bool(file_text.strip())
        result["file_text_chars"] = len(file_text)
        result["file_extract_seconds"] = round(file_extract_seconds, 4)
        result["generation_seconds"] = round(generation_seconds, 4)
        result["total_seconds"] = round(file_extract_seconds + generation_seconds, 4)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")
    
