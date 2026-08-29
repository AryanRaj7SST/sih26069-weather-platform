import re
from typing import List, Set

from app.intelligence.gazetteer import (
    AMBIGUOUS_PLACES,
    FOREIGN_LOCATIONS,
    INDIAN_CITIES,
    INDIAN_LOCALITIES,
    INDIAN_STATES,
)
from app.intelligence.schemas import ExtractedEntity


class EntityExtractor:
    """Deterministic geographic entity extractor from unstructured incident or evidence text."""

    def __init__(self) -> None:
        # Sort lookup keys by length descending for greedy longest-match
        self._all_place_keys = sorted(
            set(
                list(INDIAN_LOCALITIES.keys())
                + list(INDIAN_CITIES.keys())
                + list(INDIAN_STATES.keys())
                + list(AMBIGUOUS_PLACES.keys())
                + list(FOREIGN_LOCATIONS.keys())
            ),
            key=len,
            reverse=True,
        )

    @staticmethod
    def clean_text(text: str) -> str:
        """Strip HTML tags and excess whitespace."""
        if not text:
            return ""
        no_html = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", no_html).strip()

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Identify geographic entity mentions and offsets within the provided text."""
        cleaned = self.clean_text(text)
        if not cleaned:
            return []

        lower_text = cleaned.lower()
        extracted: List[ExtractedEntity] = []
        matched_chars: Set[int] = set()

        for key in self._all_place_keys:
            # Word boundary regex matching to avoid substring false positives (e.g. 'in')
            pattern = rf"\b{re.escape(key)}\b"
            for match in re.finditer(pattern, lower_text):
                start, end = match.span()
                span_range = range(start, end)

                # Check if this span overlaps with a longer phrase already matched
                if any(i in matched_chars for i in span_range):
                    continue

                # Determine entity type
                if key in INDIAN_LOCALITIES:
                    e_type = "LOCALITY"
                elif key in INDIAN_CITIES:
                    e_type = "CITY"
                elif key in INDIAN_STATES:
                    e_type = "STATE"
                elif key in FOREIGN_LOCATIONS:
                    e_type = (
                        "COUNTRY"
                        if key in ("nepal", "bangladesh", "sri lanka", "germany")
                        else "CITY"
                    )
                elif key in AMBIGUOUS_PLACES:
                    e_type = "AMBIGUOUS_PLACE"
                else:
                    e_type = "LOCATION"

                raw_snippet = cleaned[start:end]
                extracted.append(
                    ExtractedEntity(
                        text=raw_snippet,
                        normalized_text=key,
                        entity_type=e_type,
                        start_char=start,
                        end_char=end,
                        confidence=0.95 if e_type != "AMBIGUOUS_PLACE" else 0.70,
                    )
                )
                matched_chars.update(span_range)

        # Sort by occurrence order in the text
        extracted.sort(key=lambda e: e.start_char)
        return extracted


entity_extractor = EntityExtractor()
