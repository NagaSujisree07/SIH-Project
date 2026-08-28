import calendar
from datetime import datetime
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.query import QueryRequest, SpatialBoundingBox

# Known oceanographic parameter keywords -> Canonical schema parameter name
PARAMETER_PATTERNS = [
    # (regex pattern, canonical parameter name)
    (r"\b(?:oxygen\s+saturation|o2\s*sat(?:uration)?)\b", "oxygen_saturation_pct"),
    (r"\b(?:dissolved\s+oxygen|oxygen|doxy|o2)\b", "dissolved_oxygen_umol_kg"),
    (r"\b(?:temperature|temp|thermal|warm|cold|degrees?\s*c)\b", "temperature_C"),
    (r"\b(?:salinity|sal|salt|psal|psu)\b", "salinity"),
    (r"\b(?:pressure|pres|dbar)\b", "pressure_dbar"),
    (r"\b(?:density)\b", "density_kg_m3"),
    (r"\b(?:chlorophyll(?:-?a)?|chla|phytoplankton)\b", "chlorophyll_mg_m3"),
    (r"\b(?:nitrate|no3)\b", "nitrate_umol_kg"),
    (r"\b(?:ph|acidity|alkalinity)\b", "pH"),
    (r"\b(?:par|photosynthetically|radiation|solar\s+radiation|irradiance)\b", "PAR_umol_m2_s"),
]

# Named oceanic basins and their bounding boxes (WGS84 SRID 4326)
KNOWN_REGIONS: Dict[str, SpatialBoundingBox] = {
    "arabian sea": SpatialBoundingBox(min_lat=8.0, max_lat=25.0, min_lon=55.0, max_lon=77.0),
    "bay of bengal": SpatialBoundingBox(min_lat=5.0, max_lat=22.0, min_lon=80.0, max_lon=95.0),
    "indian ocean": SpatialBoundingBox(min_lat=-45.0, max_lat=25.0, min_lon=40.0, max_lon=110.0),
    "north atlantic": SpatialBoundingBox(min_lat=0.0, max_lat=65.0, min_lon=-80.0, max_lon=0.0),
    "south atlantic": SpatialBoundingBox(min_lat=-60.0, max_lat=0.0, min_lon=-60.0, max_lon=20.0),
    "atlantic ocean": SpatialBoundingBox(min_lat=-60.0, max_lat=65.0, min_lon=-80.0, max_lon=20.0),
    "north pacific": SpatialBoundingBox(min_lat=0.0, max_lat=65.0, min_lon=120.0, max_lon=180.0),
    "south pacific": SpatialBoundingBox(min_lat=-60.0, max_lat=0.0, min_lon=-180.0, max_lon=-70.0),
    "equatorial pacific": SpatialBoundingBox(min_lat=-10.0, max_lat=10.0, min_lon=-180.0, max_lon=-80.0),
    "pacific ocean": SpatialBoundingBox(min_lat=-60.0, max_lat=65.0, min_lon=120.0, max_lon=-70.0),
    "southern ocean": SpatialBoundingBox(min_lat=-80.0, max_lat=-45.0, min_lon=-180.0, max_lon=180.0),
    "antarctic": SpatialBoundingBox(min_lat=-85.0, max_lat=-50.0, min_lon=-180.0, max_lon=180.0),
    "mediterranean": SpatialBoundingBox(min_lat=30.0, max_lat=46.0, min_lon=-6.0, max_lon=36.0),
    "mediterranean sea": SpatialBoundingBox(min_lat=30.0, max_lat=46.0, min_lon=-6.0, max_lon=36.0),
}

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


class DeterministicParser:
    """
    Deterministic rule-based NLP parser that converts unstructured natural language
    oceanographic queries into safe, structured QueryRequest filters without requiring an external LLM.
    """

    @classmethod
    def parse(
        cls,
        prompt: str,
        base_request: Optional[QueryRequest] = None,
    ) -> Tuple[QueryRequest, Dict[str, Any]]:
        """
        Parse a natural language query into a structured QueryRequest and detailed ai_context.
        """
        if not prompt or not prompt.strip():
            empty_req = base_request or QueryRequest()
            return empty_req, {
                "received_prompt": prompt,
                "parsed_intent": {},
                "parser_used": "deterministic_fallback",
                "status": "empty_prompt",
                "explanation": "No prompt provided.",
            }

        text = prompt.strip()
        text_lower = text.lower()

        extracted_float_ids: List[str] = cls._extract_float_ids(text)
        extracted_depth_range: Optional[Dict[str, float]] = cls._extract_depth_range(text_lower)
        extracted_parameters: List[str] = cls._extract_parameters(text_lower)
        extracted_bbox: Optional[SpatialBoundingBox] = cls._extract_spatial(text, text_lower)
        extracted_start_date, extracted_end_date = cls._extract_dates(text_lower)

        # Count extracted entities
        entities_found = (
            len(extracted_float_ids) > 0
            or extracted_depth_range is not None
            or len(extracted_parameters) > 0
            or extracted_bbox is not None
            or extracted_start_date is not None
            or extracted_end_date is not None
        )

        # Merge with base_request if provided (explicit fields in base_request override NLP if present)
        effective_float_ids = (
            base_request.float_ids if (base_request and base_request.float_ids)
            else (extracted_float_ids or None)
        )
        effective_depth_range = (
            base_request.depth_range if (base_request and base_request.depth_range)
            else extracted_depth_range
        )
        effective_parameters = (
            base_request.parameters if (base_request and base_request.parameters)
            else (extracted_parameters or None)
        )
        effective_bbox = (
            base_request.bounding_box if (base_request and base_request.bounding_box)
            else extracted_bbox
        )
        effective_start_date = (
            base_request.start_date if (base_request and base_request.start_date)
            else extracted_start_date
        )
        effective_end_date = (
            base_request.end_date if (base_request and base_request.end_date)
            else extracted_end_date
        )
        effective_limit = base_request.limit if (base_request and base_request.limit is not None) else 50
        effective_offset = base_request.offset if (base_request and base_request.offset is not None) else 0

        # Construct final QueryRequest
        query_request = QueryRequest(
            float_ids=effective_float_ids,
            bounding_box=effective_bbox,
            start_date=effective_start_date,
            end_date=effective_end_date,
            parameters=effective_parameters,
            depth_range=effective_depth_range,
            natural_language_prompt=prompt,
            limit=effective_limit,
            offset=effective_offset,
        )

        # Generate explanation and status
        if not entities_found and not (base_request and (
            base_request.float_ids or base_request.depth_range or base_request.parameters or base_request.bounding_box
        )):
            status = "ambiguous_or_unsupported"
            explanation = (
                "Could not identify any ARGO oceanographic parameters, float IDs, depth ranges, "
                "regions, or dates in the prompt. Please specify ocean parameters (temperature, salinity, oxygen), "
                "float IDs (e.g. ARGO_001), depth ranges (e.g. upper 100m), or ocean regions (e.g. Arabian Sea)."
            )
        else:
            status = "success"
            parts = []
            if effective_float_ids:
                parts.append(f"float ID(s): {', '.join(effective_float_ids)}")
            if effective_parameters:
                parts.append(f"parameters: {', '.join(effective_parameters)}")
            if effective_depth_range:
                min_d = effective_depth_range.get("min", 0)
                max_d = effective_depth_range.get("max", "max")
                parts.append(f"depth range: {min_d}m to {max_d}m")
            if effective_bbox:
                parts.append(
                    f"bounding box: [{effective_bbox.min_lat}, {effective_bbox.min_lon}] to "
                    f"[{effective_bbox.max_lat}, {effective_bbox.max_lon}]"
                )
            if effective_start_date or effective_end_date:
                s_str = effective_start_date.strftime("%Y-%m-%d") if effective_start_date else "beginning"
                e_str = effective_end_date.strftime("%Y-%m-%d") if effective_end_date else "present"
                parts.append(f"date range: {s_str} to {e_str}")

            explanation = f"Extracted {'; '.join(parts)}." if parts else "Query parsed."

        ai_context = {
            "received_prompt": prompt,
            "parsed_intent": {
                "float_ids": effective_float_ids,
                "bounding_box": effective_bbox.model_dump() if effective_bbox else None,
                "depth_range": effective_depth_range,
                "parameters": effective_parameters,
                "start_date": effective_start_date.isoformat() if effective_start_date else None,
                "end_date": effective_end_date.isoformat() if effective_end_date else None,
            },
            "parser_used": "deterministic_rules",
            "status": status,
            "explanation": explanation,
        }

        return query_request, ai_context

    @classmethod
    def _extract_float_ids(cls, text: str) -> List[str]:
        """Extract ARGO float IDs (e.g. ARGO_001, ARGO_1, ARGO001, or numeric WMO IDs)."""
        found_ids: Set[str] = set()

        # ARGO_xxx pattern
        for match in re.finditer(r"\bARGO[_-]?(\d+)\b", text, re.IGNORECASE):
            num = match.group(1).zfill(3)
            found_ids.add(f"ARGO_{num}")

        # Float ID xxx pattern (e.g. "float 2900001" or "float ARGO_001")
        for match in re.finditer(r"\bfloat\s*(?:id|#)?\s*([A-Za-z0-9_]+)\b", text, re.IGNORECASE):
            val = match.group(1).upper()
            if val.startswith("ARGO"):
                found_ids.add(val)
            elif val.isdigit() and len(val) >= 4:
                found_ids.add(val)

        return sorted(list(found_ids))

    @classmethod
    def _extract_depth_range(cls, text_lower: str) -> Optional[Dict[str, float]]:
        """Extract vertical depth ranges from natural language."""
        # 1. "upper <num> meters/m/dbar" or "top <num> m"
        m = re.search(r"\b(?:upper|top)\s+(\d+(?:\.\d+)?)\s*(?:m|meters?|meter|dbar)?\b", text_lower)
        if m:
            return {"min": 0.0, "max": float(m.group(1))}

        # 2. "surface to <num> meters/m"
        m = re.search(r"\b(?:surface\s+to|surface\s*-\s*)\s*(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\b", text_lower)
        if m:
            return {"min": 0.0, "max": float(m.group(1))}

        # 3. "between <num1> and <num2> meters/m/dbar" or "<num1> to <num2> meters"
        m = re.search(
            r"\bbetween\s+(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\b",
            text_lower,
        )
        if m:
            v1, v2 = float(m.group(1)), float(m.group(2))
            return {"min": min(v1, v2), "max": max(v1, v2)}

        # 4. "from <num1> to <num2> meters/m/dbar"
        m = re.search(
            r"\bfrom\s+(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\b",
            text_lower,
        )
        if m:
            v1, v2 = float(m.group(1)), float(m.group(2))
            return {"min": min(v1, v2), "max": max(v1, v2)}

        # 5. "below <num> meters" / "deeper than <num> m"
        m = re.search(r"\b(?:below|deeper\s+than)\s+(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\b", text_lower)
        if m:
            return {"min": float(m.group(1))}

        # 6. "shallower than <num> meters" / "above <num> meters"
        m = re.search(r"\b(?:shallower\s+than|above)\s+(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)?\b", text_lower)
        if m:
            return {"min": 0.0, "max": float(m.group(1))}

        # 7. "at <num> meters depth" / "depth of <num> meters"
        m = re.search(r"\b(?:at|depth\s+of)\s+(\d+(?:\.\d+)?)\s*(?:m|meters?|dbar)\s+depth\b", text_lower)
        if m:
            val = float(m.group(1))
            return {"min": max(0.0, val - 5.0), "max": val + 5.0}

        return None

    @classmethod
    def _extract_parameters(cls, text_lower: str) -> List[str]:
        """Extract canonical parameter names from natural language."""
        found: Set[str] = set()
        for pattern, param_name in PARAMETER_PATTERNS:
            if re.search(pattern, text_lower):
                found.add(param_name)
        return sorted(list(found))

    @classmethod
    def _extract_spatial(cls, text: str, text_lower: str) -> Optional[SpatialBoundingBox]:
        """Extract spatial bounding box from named ocean regions or coordinate proximity."""
        # 1. Check known oceanic regions first
        for region_name, bbox in KNOWN_REGIONS.items():
            if region_name in text_lower:
                return bbox

        # 2. Check coordinate + radius proximity ("near 42.0 latitude and -42.0 longitude within 500 km")
        coord_match = re.search(
            r"(?:near|at|around|coordinates?)\s*(-?\d+(?:\.\d+)?)\s*(?:deg|°|degrees?)?\s*(?:lat|latitude)?,?\s*(?:and)?\s*(-?\d+(?:\.\d+)?)\s*(?:deg|°|degrees?)?\s*(?:lon|longitude)?",
            text_lower,
        )

        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))

                # Check radius
                radius_match = re.search(
                    r"(?:within|radius\s*(?:of)?|distance\s*(?:of)?)\s*(\d+(?:\.\d+)?)\s*(?:km|kilometers?|kilometer|nm|miles?)\b",
                    text_lower,
                )
                radius_km = float(radius_match.group(1)) if radius_match else 500.0

                # Compute approximate geodesic bounding box
                delta_lat = radius_km / 111.0
                cos_lat = max(0.1, math.cos(math.radians(lat)))
                delta_lon = radius_km / (111.0 * cos_lat)

                min_lat = max(-90.0, lat - delta_lat)
                max_lat = min(90.0, lat + delta_lat)
                min_lon = max(-180.0, lon - delta_lon)
                max_lon = min(180.0, lon + delta_lon)

                return SpatialBoundingBox(
                    min_lat=round(min_lat, 4),
                    max_lat=round(max_lat, 4),
                    min_lon=round(min_lon, 4),
                    max_lon=round(max_lon, 4),
                )
            except Exception:
                pass

        return None

    @classmethod
    def _extract_dates(cls, text_lower: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract temporal boundaries (start_date, end_date)."""
        # 1. "between August 1 and August 5, 2026" or "between August 1, 2026 and August 5, 2026"
        month_names = "|".join(MONTH_MAP.keys())
        m = re.search(
            rf"\bbetween\s+({month_names})\s+(\d+)(?:st|nd|rd|th)?(?:,?\s*(\d{{4}}))?\s+and\s+({month_names})?\s*(\d+)(?:st|nd|rd|th)?,?\s*(\d{{4}})\b",
            text_lower,
        )
        if m:
            m1_name, d1_str, y1_str, m2_name, d2_str, y2_str = m.groups()
            year = int(y2_str)
            m1 = MONTH_MAP[m1_name]
            m2 = MONTH_MAP[m2_name] if m2_name else m1
            d1 = int(d1_str)
            d2 = int(d2_str)
            try:
                start_dt = datetime(year, m1, d1, 0, 0, 0)
                end_dt = datetime(year, m2, d2, 23, 59, 59)
                return start_dt, end_dt
            except Exception:
                pass

        # 2. "from YYYY-MM-DD to YYYY-MM-DD"
        m = re.search(r"\bfrom\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})\b", text_lower)
        if m:
            try:
                start_dt = datetime.fromisoformat(m.group(1))
                end_dt = datetime.fromisoformat(m.group(2)).replace(hour=23, minute=59, second=59)
                return start_dt, end_dt
            except Exception:
                pass

        # 3. "in August 2026"
        m = re.search(rf"\bin\s+({month_names})\s+(\d{{4}})\b", text_lower)
        if m:
            m_name, y_str = m.groups()
            year = int(y_str)
            month = MONTH_MAP[m_name]
            _, last_day = calendar.monthrange(year, month)
            try:
                start_dt = datetime(year, month, 1, 0, 0, 0)
                end_dt = datetime(year, month, last_day, 23, 59, 59)
                return start_dt, end_dt
            except Exception:
                pass

        # 4. "in 2026" / "year 2026"
        m = re.search(r"\b(?:in|year)\s+(\d{4})\b", text_lower)
        if m:
            year = int(m.group(1))
            try:
                start_dt = datetime(year, 1, 1, 0, 0, 0)
                end_dt = datetime(year, 12, 31, 23, 59, 59)
                return start_dt, end_dt
            except Exception:
                pass

        # 5. "since YYYY-MM-DD" or "after YYYY-MM-DD"
        m = re.search(r"\b(?:since|after)\s+(\d{4}-\d{2}-\d{2})\b", text_lower)
        if m:
            try:
                return datetime.fromisoformat(m.group(1)), None
            except Exception:
                pass

        # 6. "before YYYY-MM-DD" or "until YYYY-MM-DD"
        m = re.search(r"\b(?:before|until)\s+(\d{4}-\d{2}-\d{2})\b", text_lower)
        if m:
            try:
                return None, datetime.fromisoformat(m.group(1)).replace(hour=23, minute=59, second=59)
            except Exception:
                pass

        return None, None
