from app.intelligence import (
    EntityExtractor,
    LocationResolver,
    ResolutionMethod,
    ResolutionStatus,
)


def test_entity_extractor_basic_and_boundary_matching():
    """Verify entity extraction extracts full terms without false positive substrings."""
    extractor = EntityExtractor()

    # 'in' or 'a' should not falsely trigger matching
    text1 = "A storm in a town"
    entities1 = extractor.extract_entities(text1)
    assert entities1 == []

    # Real Indian entities with word boundaries
    text2 = "Floods and heavy rain reported in Andheri station, Mumbai, Maharashtra"
    entities2 = extractor.extract_entities(text2)
    assert len(entities2) >= 2
    matched_texts = [e.normalized_text for e in entities2]
    assert "andheri station" in matched_texts
    assert "mumbai" in matched_texts
    assert "maharashtra" in matched_texts


def test_automatic_resolution_defaults_is_human_corrected_to_false():
    """Verify all automatic resolution paths default strictly to is_human_corrected=False."""
    resolver = LocationResolver()

    # 1. Automatic structured coordinates
    res_coord = resolver.resolve(latitude=19.0760, longitude=72.8777)
    assert res_coord.is_human_corrected is False
    assert res_coord.resolution_method == ResolutionMethod.STRUCTURED_COORDINATES
    assert res_coord.provider == "source_coordinates"

    # 2. Automatic structured city
    res_city = resolver.resolve(city="Bengaluru")
    assert res_city.is_human_corrected is False
    assert res_city.resolution_method == ResolutionMethod.EXACT_ADMIN_MATCH
    assert res_city.provider == "internal_gazetteer"

    # 3. Automatic text locality
    res_text = resolver.resolve(text="Heavy rain near Andheri station, Mumbai")
    assert res_text.is_human_corrected is False
    assert res_text.resolution_method == ResolutionMethod.PLACE_DICTIONARY
    assert res_text.provider == "internal_gazetteer"


def test_explicit_human_override_marks_human_correction():
    """Verify manual human operator override is clearly labeled in provenance."""
    resolver = LocationResolver()
    res = resolver.resolve(
        latitude=19.1197,
        longitude=72.8468,
        location_name="Corrected Andheri Subway",
        is_human_corrected=True,
    )
    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolution_method == ResolutionMethod.HUMAN_CORRECTION
    assert res.confidence == 1.0
    assert res.is_human_corrected is True
    assert res.provider == "human_override"


def test_resolve_malformed_out_of_bounds_coordinates():
    """Verify coordinates out of WGS84 range are rejected safely."""
    resolver = LocationResolver()
    res = resolver.resolve(latitude=95.0, longitude=200.0)
    assert res.resolution_status == ResolutionStatus.UNRESOLVED
    assert res.confidence == 0.0
    assert res.latitude is None
    assert res.longitude is None
    assert res.is_human_corrected is False


def test_state_only_match_has_no_incident_coordinates():
    """Verify state-level match recognizes region without fabricating incident coordinates."""
    resolver = LocationResolver()

    # Via structured state field
    res_state = resolver.resolve(state="Maharashtra")
    assert res_state.resolution_status == ResolutionStatus.RESOLVED
    assert res_state.state == "Maharashtra"
    assert res_state.country == "India"
    assert res_state.latitude is None  # ZERO fabricated centroid
    assert res_state.longitude is None  # ZERO fabricated centroid
    assert res_state.confidence == 0.0  # Zero point-resolution confidence

    # Via free text mention
    res_text = resolver.resolve(text="Heavy continuous rain across Assam causing river surges")
    assert res_text.resolution_status == ResolutionStatus.RESOLVED
    assert res_text.state == "Assam"
    assert res_text.country == "India"
    assert res_text.latitude is None  # ZERO fabricated centroid
    assert res_text.longitude is None  # ZERO fabricated centroid
    assert res_text.confidence == 0.0  # Zero point-resolution confidence


def test_country_only_foreign_match_has_no_incident_coordinates():
    """Verify foreign country text is recognized without fabricating centroid coordinates."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Nepal floods: Death toll reaches 626, over 4,400 rescued")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.country == "Nepal"
    assert res.place_name == "Nepal"
    assert res.latitude is None  # ZERO fabricated country centroid
    assert res.longitude is None  # ZERO fabricated country centroid
    assert res.confidence == 0.0  # Zero point-resolution confidence


def test_specific_foreign_city_preserves_coordinates_with_foreign_country():
    """Verify foreign city provides coordinates explicitly labeled with foreign country."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Heavy flash floods inundate lowlands in Kathmandu")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.country == "Nepal"
    assert res.city == "Kathmandu"
    assert res.latitude == 27.7172
    assert res.longitude == 85.3240
    assert res.confidence == 0.90


def test_resolve_locality_and_city_in_text():
    """Verify free text landmark and locality + city resolution."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Heavily waterlogged near Andheri station, Mumbai")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolution_method == ResolutionMethod.PLACE_DICTIONARY
    assert res.locality == "Andheri"
    assert res.city == "Mumbai"
    assert res.state == "Maharashtra"
    assert res.latitude == 19.1197
    assert res.longitude == 72.8468
    assert res.confidence == 0.95


def test_resolve_city_and_state_in_text():
    """Verify city + state context in unstructured report description."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Heavy flooding near Yadgir, Karnataka after river overflow")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.resolution_method == ResolutionMethod.EXACT_ADMIN_MATCH
    assert res.city == "Yadgir"
    assert res.state == "Karnataka"
    assert res.latitude == 16.7375
    assert res.longitude == 77.1253
    assert res.confidence == 0.95


def test_resolve_ambiguous_place_without_context():
    """Verify ambiguous place without context returns AMBIGUOUS and NO fabricated coordinates."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Flash flood reported in Rajpur yesterday evening")

    assert res.resolution_status == ResolutionStatus.AMBIGUOUS
    assert res.latitude is None
    assert res.longitude is None
    assert res.confidence == 0.0  # Zero point-resolution confidence
    assert len(res.candidates) >= 2

    states_in_candidates = [c.state for c in res.candidates]
    assert "Uttarakhand" in states_in_candidates
    assert "Madhya Pradesh" in states_in_candidates


def test_resolve_ambiguous_place_with_disambiguating_context():
    """Verify ambiguous place with state/district context resolves successfully."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Flash flood reported in Rajpur, Dehradun, Uttarakhand")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.state == "Uttarakhand"
    assert res.district == "Dehradun"
    assert res.latitude == 30.3833
    assert res.longitude == 78.0833
    assert res.confidence == 0.85


def test_resolve_unrecognized_text():
    """Verify unrecognized text returns UNRESOLVED with zero coordinate fabrication."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Some totally generic statement about stormy weather conditions")

    assert res.resolution_status == ResolutionStatus.UNRESOLVED
    assert res.latitude is None
    assert res.longitude is None
    assert res.confidence == 0.0


def test_resolve_empty_input():
    """Verify empty or whitespace-only inputs are handled gracefully."""
    resolver = LocationResolver()
    res = resolver.resolve(text="   ", location_name="")

    assert res.resolution_status == ResolutionStatus.UNRESOLVED
    assert res.latitude is None
    assert res.longitude is None
    assert res.confidence == 0.0


def test_extractor_multiple_places_in_order_with_offsets():
    """Verify multiple place mentions extracted preserving character offsets."""
    extractor = EntityExtractor()
    text = "From Indiranagar in Bengaluru to Connaught Place in New Delhi"
    entities = extractor.extract_entities(text)

    assert len(entities) >= 4
    names = [e.text for e in entities]
    assert "Indiranagar" in names
    assert "Bengaluru" in names
    assert "Connaught Place" in names
    assert "New Delhi" in names
    assert entities[0].start_char < entities[1].start_char < entities[2].start_char


def test_resolve_multi_word_city_and_locality():
    """Verify multi-word place names (New Delhi, Connaught Place, Tamil Nadu)."""
    resolver = LocationResolver()
    res = resolver.resolve(text="Water logging at Connaught Place, New Delhi")

    assert res.resolution_status == ResolutionStatus.RESOLVED
    assert res.locality == "Connaught Place"
    assert res.city == "New Delhi"
    assert res.state == "Delhi"
    assert res.latitude == 28.6315
    assert res.longitude == 77.2167
    assert res.confidence == 0.95
