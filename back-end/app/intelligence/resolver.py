import logging
from typing import Any, Dict, List, Optional

from app.intelligence.extractor import EntityExtractor, entity_extractor
from app.intelligence.gazetteer import (
    AMBIGUOUS_PLACES,
    FOREIGN_LOCATIONS,
    INDIAN_CITIES,
    INDIAN_LOCALITIES,
    INDIAN_STATES,
)
from app.intelligence.schemas import (
    ExtractedEntity,
    LocationCandidate,
    LocationResolutionResult,
    ResolutionMethod,
    ResolutionStatus,
)

logger = logging.getLogger(__name__)


class LocationResolver:
    """Core foundation for geographic entity and location resolution."""

    def __init__(self, extractor: Optional[EntityExtractor] = None) -> None:
        self.extractor = extractor or entity_extractor

    def resolve(
        self,
        text: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        locality: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = "India",
        location_name: Optional[str] = None,
        is_human_corrected: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocationResolutionResult:
        """Resolve geographic entity mentions and coordinates with strict safety rules.

        Point Resolution Safety:
        - Confidence reflects certainty of the INCIDENT POINT (latitude/longitude), not merely
          recognition of a broad region.
        - State-only and country-only entities return latitude=None, longitude=None, confidence=0.0.
        - is_human_corrected defaults strictly to False; only explicit operator overrides may
          set is_human_corrected=True and method=HUMAN_CORRECTION.
        """
        extra_meta = dict(metadata or {})

        # 1. STRUCTURED / PRE-EXISTING COORDINATES
        if latitude is not None and longitude is not None:
            if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
                method = (
                    ResolutionMethod.HUMAN_CORRECTION
                    if is_human_corrected
                    else ResolutionMethod.STRUCTURED_COORDINATES
                )
                place = (
                    location_name or locality or city or f"Coord({latitude:.4f}, {longitude:.4f})"
                )
                return LocationResolutionResult(
                    original_text=text or location_name,
                    place_name=place,
                    locality=locality,
                    city=city,
                    district=district,
                    state=state,
                    country=country or "India",
                    latitude=latitude,
                    longitude=longitude,
                    confidence=1.0,
                    resolution_status=ResolutionStatus.RESOLVED,
                    resolution_method=method,
                    provider="human_override" if is_human_corrected else "source_coordinates",
                    is_human_corrected=is_human_corrected,
                    metadata=extra_meta,
                )
            else:
                return LocationResolutionResult(
                    original_text=text or location_name,
                    confidence=0.0,
                    resolution_status=ResolutionStatus.UNRESOLVED,
                    resolution_method=ResolutionMethod.STRUCTURED_COORDINATES,
                    provider="validator",
                    is_human_corrected=False,
                    metadata={
                        **extra_meta,
                        "error": f"Coordinates out of bounds ({latitude}, {longitude})",
                    },
                )

        # 2. STRUCTURED ADMINISTRATIVE ATTRIBUTES
        if locality or location_name:
            target_loc = (locality or location_name or "").strip().lower()
            if target_loc in INDIAN_LOCALITIES:
                loc_data = INDIAN_LOCALITIES[target_loc]
                return LocationResolutionResult(
                    original_text=location_name or locality,
                    place_name=f"{loc_data['locality']}, {loc_data['city']}",
                    locality=loc_data["locality"],
                    city=loc_data["city"],
                    district=loc_data.get("district"),
                    state=loc_data["state"],
                    country="India",
                    latitude=loc_data["lat"],
                    longitude=loc_data["lon"],
                    confidence=0.95,
                    resolution_status=ResolutionStatus.RESOLVED,
                    resolution_method=ResolutionMethod.PLACE_DICTIONARY,
                    provider="internal_gazetteer",
                    is_human_corrected=False,
                    metadata=extra_meta,
                )

        if city:
            target_city = city.strip().lower()
            if target_city in INDIAN_CITIES:
                c_data = INDIAN_CITIES[target_city]
                return LocationResolutionResult(
                    original_text=city,
                    place_name=f"{c_data['city']}, {c_data['state']}",
                    city=c_data["city"],
                    district=c_data.get("district"),
                    state=c_data["state"],
                    country="India",
                    latitude=c_data["lat"],
                    longitude=c_data["lon"],
                    confidence=0.90,
                    resolution_status=ResolutionStatus.RESOLVED,
                    resolution_method=ResolutionMethod.EXACT_ADMIN_MATCH,
                    provider="internal_gazetteer",
                    is_human_corrected=False,
                    metadata=extra_meta,
                )

        if state:
            target_state = state.strip().lower()
            if target_state in INDIAN_STATES:
                s_data = INDIAN_STATES[target_state]
                return LocationResolutionResult(
                    original_text=state,
                    place_name=s_data["state"],
                    state=s_data["state"],
                    country="India",
                    latitude=None,  # State-only: ZERO fabricated centroid
                    longitude=None,  # State-only: ZERO fabricated centroid
                    confidence=0.0,  # Zero point-resolution confidence
                    resolution_status=ResolutionStatus.RESOLVED,
                    resolution_method=ResolutionMethod.EXACT_ADMIN_MATCH,
                    provider="internal_gazetteer",
                    is_human_corrected=False,
                    metadata={**extra_meta, "granularity": "STATE"},
                )

        # 3. UNSTRUCTURED TEXT ENTITY EXTRACTION & RESOLUTION
        combined_text = " ".join(filter(None, [location_name, text])).strip()
        if not combined_text:
            return LocationResolutionResult(
                original_text="",
                confidence=0.0,
                resolution_status=ResolutionStatus.UNRESOLVED,
                resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
                provider="none",
                is_human_corrected=False,
                metadata={"reason": "Empty input text"},
            )

        entities: List[ExtractedEntity] = self.extractor.extract_entities(combined_text)
        if not entities:
            return LocationResolutionResult(
                original_text=combined_text,
                normalized_text=combined_text.lower(),
                confidence=0.0,
                resolution_status=ResolutionStatus.UNRESOLVED,
                resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
                provider="internal_gazetteer",
                is_human_corrected=False,
                metadata={"reason": "No geographic entity mentions recognized in text"},
            )

        localities = [e for e in entities if e.entity_type == "LOCALITY"]
        cities = [e for e in entities if e.entity_type == "CITY"]
        states = [e for e in entities if e.entity_type == "STATE"]
        foreign = [e for e in entities if e.normalized_text in FOREIGN_LOCATIONS]
        ambiguous = [e for e in entities if e.normalized_text in AMBIGUOUS_PLACES]

        # Case A: Foreign Location Detected
        if foreign:
            f_key = foreign[0].normalized_text
            f_data = FOREIGN_LOCATIONS[f_key]
            f_lat = f_data.get("lat")
            f_lon = f_data.get("lon")
            f_confidence = 0.90 if f_lat is not None else 0.0
            return LocationResolutionResult(
                original_text=combined_text,
                place_name=f_data["place_name"],
                city=f_data.get("city"),
                district=f_data.get("district"),
                country=f_data["country"],
                latitude=f_lat,  # None for country-level; coordinates for verified foreign cities
                longitude=f_lon,
                confidence=f_confidence,
                resolution_status=ResolutionStatus.RESOLVED,
                resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
                provider="foreign_gazetteer",
                is_human_corrected=False,
                metadata={**extra_meta, "foreign_entity": f_key},
            )

        # Case B: Localities (e.g. Andheri, Indiranagar, Connaught Place)
        if localities:
            loc_key = localities[0].normalized_text
            loc_data = INDIAN_LOCALITIES[loc_key]

            has_city_match = any(c.normalized_text == loc_data["city"].lower() for c in cities)
            has_state_match = any(s.normalized_text == loc_data["state"].lower() for s in states)
            confidence = 0.95 if (has_city_match or has_state_match) else 0.90

            return LocationResolutionResult(
                original_text=combined_text,
                place_name=f"{loc_data['locality']}, {loc_data['city']}",
                locality=loc_data["locality"],
                city=loc_data["city"],
                district=loc_data.get("district"),
                state=loc_data["state"],
                country="India",
                latitude=loc_data["lat"],
                longitude=loc_data["lon"],
                confidence=confidence,
                resolution_status=ResolutionStatus.RESOLVED,
                resolution_method=ResolutionMethod.PLACE_DICTIONARY,
                provider="internal_gazetteer",
                is_human_corrected=False,
                metadata={
                    **extra_meta,
                    "context_matched": bool(has_city_match or has_state_match),
                },
            )

        # Case C: Ambiguous Place (e.g. Rajpur, Bilaspur)
        if ambiguous:
            amb_key = ambiguous[0].normalized_text
            candidate_list = AMBIGUOUS_PLACES[amb_key]

            lower_comb = combined_text.lower()
            matched_candidate: Optional[Dict[str, Any]] = None
            for cand in candidate_list:
                cand_state = cand.get("state", "").lower()
                cand_district = cand.get("district", "").lower()
                cand_city = cand.get("city", "").lower()

                state_match = bool(
                    cand_state and cand_state in lower_comb and cand_state != amb_key
                )
                district_match = bool(
                    cand_district and cand_district in lower_comb and cand_district != amb_key
                )
                city_match = bool(cand_city and cand_city in lower_comb and cand_city != amb_key)

                if state_match or district_match or city_match:
                    matched_candidate = cand
                    break

            if matched_candidate:
                return LocationResolutionResult(
                    original_text=combined_text,
                    place_name=matched_candidate["place_name"],
                    locality=matched_candidate.get("locality"),
                    city=matched_candidate.get("city"),
                    district=matched_candidate.get("district"),
                    state=matched_candidate["state"],
                    country="India",
                    latitude=matched_candidate["lat"],
                    longitude=matched_candidate["lon"],
                    confidence=0.85,
                    resolution_status=ResolutionStatus.RESOLVED,
                    resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
                    provider="internal_gazetteer",
                    is_human_corrected=False,
                    metadata={**extra_meta, "disambiguated_by_context": True},
                )

            if not cities:
                candidates = [
                    LocationCandidate(
                        place_name=c["place_name"],
                        locality=c.get("locality"),
                        city=c.get("city"),
                        district=c.get("district"),
                        state=c["state"],
                        country="India",
                        latitude=c["lat"],
                        longitude=c["lon"],
                        confidence=1.0 / len(candidate_list),
                        match_type="AMBIGUOUS",
                    )
                    for c in candidate_list
                ]
                return LocationResolutionResult(
                    original_text=combined_text,
                    place_name=amb_key.capitalize(),
                    latitude=None,  # Ambiguous without context: ZERO fabricated coordinates
                    longitude=None,
                    confidence=0.0,  # Zero point-resolution confidence
                    resolution_status=ResolutionStatus.AMBIGUOUS,
                    resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
                    candidates=candidates,
                    provider="internal_gazetteer",
                    is_human_corrected=False,
                    metadata={**extra_meta, "ambiguous_match_count": len(candidates)},
                )

        # Case D: Cities / Districts (e.g. Mumbai, Bengaluru, Yadgir, Wayanad)
        if cities:
            c_key = cities[0].normalized_text
            c_data = INDIAN_CITIES[c_key]
            has_state_match = any(s.normalized_text == c_data["state"].lower() for s in states)
            confidence = 0.95 if has_state_match else 0.90

            return LocationResolutionResult(
                original_text=combined_text,
                place_name=f"{c_data['city']}, {c_data['state']}",
                city=c_data["city"],
                district=c_data.get("district"),
                state=c_data["state"],
                country="India",
                latitude=c_data["lat"],
                longitude=c_data["lon"],
                confidence=confidence,
                resolution_status=ResolutionStatus.RESOLVED,
                resolution_method=ResolutionMethod.EXACT_ADMIN_MATCH,
                provider="internal_gazetteer",
                is_human_corrected=False,
                metadata={**extra_meta, "state_context_matched": has_state_match},
            )

        # Case E: State alone (e.g. "Heavy rain across Assam")
        if states:
            s_key = states[0].normalized_text
            s_data = INDIAN_STATES[s_key]
            return LocationResolutionResult(
                original_text=combined_text,
                place_name=s_data["state"],
                state=s_data["state"],
                country="India",
                latitude=None,  # State-only: ZERO fabricated centroid
                longitude=None,  # State-only: ZERO fabricated centroid
                confidence=0.0,  # Zero point-resolution confidence
                resolution_status=ResolutionStatus.RESOLVED,
                resolution_method=ResolutionMethod.EXACT_ADMIN_MATCH,
                provider="internal_gazetteer",
                is_human_corrected=False,
                metadata={**extra_meta, "granularity": "STATE"},
            )

        # Fallback: Unresolved
        return LocationResolutionResult(
            original_text=combined_text,
            normalized_text=combined_text.lower(),
            latitude=None,
            longitude=None,
            confidence=0.0,
            resolution_status=ResolutionStatus.UNRESOLVED,
            resolution_method=ResolutionMethod.NLP_ENTITY_RESOLUTION,
            provider="internal_gazetteer",
            is_human_corrected=False,
            metadata=extra_meta,
        )


location_resolver = LocationResolver()
