from dataclasses import dataclass


@dataclass
class PropertyInput:
    project_name: str
    property_url: str
    property_type: str
    listing_type: str
    location: str
    bhk_area: str
    amenities: str
    usp: str
    target_audience: str
    tone_preference: str
    keywords: str
