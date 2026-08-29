import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.intelligence.evidence_scorer import EvidenceScorer
from app.intelligence.schemas import EvidenceRelationship

# 35-pair deterministic benchmark evaluation fixture for Evidence Linking
# NOTE: Synthetic Evidence-Linking Benchmark Only. Not a claim of real-world ground truth.
EVIDENCE_BENCHMARK_PAIRS: List[Dict[str, Any]] = [
    # 1. Direct Supporting Evidence: GDELT Mumbai flood news matching Citizen Andheri flood
    {
        "id": "evi-01-direct-supporting-news",
        "inc_title": "Severe waterlogging near Andheri subway",
        "inc_desc": "Water knee-deep near railway station subway.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.1197,
        "inc_lon": 72.8468,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Andheri, Mumbai",
        "evi_title": "Heavy rains cause severe waterlogging at Andheri subway in Mumbai",
        "evi_desc": "Subway traffic suspended as water levels rise outside Andheri station.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 2. Direct Supporting Social Evidence: Mastodon post from on-the-ground citizen
    {
        "id": "evi-02-direct-supporting-mastodon",
        "inc_title": "Kurla railway tracks waterlogged",
        "inc_desc": "Local trains delayed due to submerged tracks at Kurla.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0726,
        "inc_lon": 72.8845,
        "inc_time": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "inc_loc": "Kurla, Mumbai",
        "evi_title": "Kurla station tracks flooded #MumbaiRains",
        "evi_desc": "Water overflowing on tracks at Kurla station right now, trains halted.",
        "evi_source": "MASTODON",
        "evi_pub_time": datetime(2026, 8, 29, 11, 15, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 3. Direct Supporting News: Local news portal reporting Bengaluru cloudburst
    {
        "id": "evi-03-bengaluru-flood-news-supporting",
        "inc_title": "Severe cloudburst flooding Whitefield roads",
        "inc_desc": "Sudden torrential rain in Whitefield IT area.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 12.9698,
        "inc_lon": 77.7500,
        "inc_time": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "inc_loc": "Whitefield, Bengaluru",
        "evi_title": "Heavy rains and localized inundation in Whitefield Bengaluru",
        "evi_desc": "Localized storm causes severe waterlogging over Whitefield area.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 15, 10, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 4. Contextual Government Release: PIB preparedness review (Not proof of occurrence)
    {
        "id": "evi-04-contextual-pib-preparedness",
        "inc_title": "Flooding in low lying neighborhoods in Mumbai",
        "inc_desc": "Water entering residential ground floors.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0760,
        "inc_lon": 72.8777,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Mumbai, Maharashtra",
        "evi_title": "Minister chairs monsoon flood preparedness review meeting",
        "evi_desc": "NDRF teams deployed as precautionary measure to monitor flood situation.",
        "evi_source": "GOVERNMENT_PIB",
        "evi_pub_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.CONTEXTUAL,
    },
    # 5. Foreign Event (Nepal Floods) vs Mumbai Incident: MUST be IRRELEVANT
    {
        "id": "evi-05-foreign-nepal-news-irrelevant",
        "inc_title": "Waterlogging in Mumbai coastal belt",
        "inc_desc": "High tide surges water onto promenade.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0760,
        "inc_lon": 72.8777,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Mumbai, Maharashtra",
        "evi_title": "Severe floods in Nepal claim 20 lives after cloudburst",
        "evi_desc": "Rivers overflow across eastern Nepal as continuous rains batter Kathmandu.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 6. Distant City (Delhi news vs Mumbai Incident): MUST be IRRELEVANT
    {
        "id": "evi-06-different-city-delhi-vs-mumbai",
        "inc_title": "Waterlogging in Andheri Mumbai",
        "inc_desc": "Roads flooded in western suburbs.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.1197,
        "inc_lon": 72.8468,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Andheri, Mumbai",
        "evi_title": "Severe waterlogging at ITO junction Delhi after heavy rain",
        "evi_desc": "Traffic halted near ITO and Pragati Maidan in New Delhi.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 7. Old Historical Article (> 48h horizon): MUST be IRRELEVANT
    {
        "id": "evi-07-old-historical-article-irrelevant",
        "inc_title": "Waterlogging in Andheri subway",
        "inc_desc": "Subway closed due to water accumulation.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.1197,
        "inc_lon": 72.8468,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Andheri, Mumbai",
        "evi_title": "Memories of 2005 Mumbai floods and underpass submergence",
        "evi_desc": "A retrospective look at historical urban drainage issues in Mumbai.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2020, 7, 26, 10, 0, tzinfo=timezone.utc),  # 6 years earlier
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 8. Incompatible Hazard (Heatwave news vs Flood Incident): MUST be IRRELEVANT
    {
        "id": "evi-08-incompatible-hazard-heatwave-vs-flood",
        "inc_title": "Flash flooding in residential sectors",
        "inc_desc": "Heavy cloudburst fills street drains.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0760,
        "inc_lon": 72.8777,
        "inc_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "inc_loc": "Mumbai, Maharashtra",
        "evi_title": "Scorching heatwave warning issued across district",
        "evi_desc": "Dry heatwave conditions with zero rain expected for next week.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 12, 15, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 9. Contradictory Evidence: Explicit Debunking Statement
    {
        "id": "evi-09-contradictory-debunking-evidence",
        "inc_title": "Bridge collapse reported near Dadar TT circle",
        "inc_desc": "Citizen reports bridge collapse under flood waters.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0178,
        "inc_lon": 72.8478,
        "inc_time": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "inc_loc": "Dadar, Mumbai",
        "evi_title": "Police denies reports of bridge collapse near Dadar TT circle",
        "evi_desc": "Traffic police confirms fake news; no waterlogging at Dadar bridge.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 14, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.CONTRADICTORY,
    },
    # 10. Related Evidence: Broader Regional Weather in Same State
    {
        "id": "evi-10-related-regional-monsoon-news",
        "inc_title": "Waterlogging in Sion railway colony",
        "inc_desc": "Water accumulation inside residential colony in Sion.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0390,
        "inc_lon": 72.8619,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Sion, Mumbai",
        "evi_title": "Widespread monsoon showers lash Maharashtra coastal belt",
        "evi_desc": "Continuous rain reported across Konkan region and Mumbai metropolitan area.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 45, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.RELATED,
    },
    # 11. Chennai T Nagar Rain Evidence -> SUPPORTING
    {
        "id": "evi-11-chennai-tnagar-supporting",
        "inc_title": "Usman road in T Nagar flooded",
        "inc_desc": "Vehicles moving slowly in knee deep water.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 13.0418,
        "inc_lon": 80.2341,
        "inc_time": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "inc_loc": "T Nagar, Chennai",
        "evi_title": "Usman road in T Nagar inundated after sudden cloudburst",
        "evi_desc": "Shops flooded in commercial hub of T Nagar Chennai.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 16, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 12. Chennai vs Kolkata -> IRRELEVANT
    {
        "id": "evi-12-chennai-vs-kolkata-irrelevant",
        "inc_title": "Usman road in T Nagar flooded",
        "inc_desc": "Flooding in Chennai.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 13.0418,
        "inc_lon": 80.2341,
        "inc_time": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "inc_loc": "Chennai, Tamil Nadu",
        "evi_title": "Waterlogging reported in Park Street Kolkata",
        "evi_desc": "Heavy rain downpour floods streets in Kolkata.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 16, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 13. Delhi Lajpat Nagar Flood News -> SUPPORTING
    {
        "id": "evi-13-delhi-lajpat-supporting",
        "inc_title": "Lajpat Nagar flyover underpass flooded",
        "inc_desc": "Vehicles stranded in underpass.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 28.5677,
        "inc_lon": 77.2433,
        "inc_time": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "inc_loc": "Lajpat Nagar, New Delhi",
        "evi_title": "Lajpat Nagar underpass closed due to waterlogging in South Delhi",
        "evi_desc": "Traffic diverted around submerged underpass near Lajpat Nagar metro station.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 15, 25, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 14. Delhi Flood News Portal Report -> SUPPORTING
    {
        "id": "evi-14-delhi-flood-news-supporting",
        "inc_title": "Flash flooding at Lajpat Nagar",
        "inc_desc": "Water level rising rapidly.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 28.5677,
        "inc_lon": 77.2433,
        "inc_time": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "inc_loc": "Lajpat Nagar, New Delhi",
        "evi_title": "Severe urban waterlogging and traffic disruption in South Delhi",
        "evi_desc": "Emergency response teams manage inundation in Lajpat Nagar area.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 15, 15, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 15. Social Post with Ambiguous Location ("Monsoon is coming") -> IRRELEVANT
    {
        "id": "evi-15-ambiguous-social-post",
        "inc_title": "Waterlogging in Bandra",
        "inc_desc": "Street waterlogged.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0596,
        "inc_lon": 72.8295,
        "inc_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "inc_loc": "Bandra, Mumbai",
        "evi_title": "Rain clouds looking dark today #nature",
        "evi_desc": "I love the cloudy weather outside today.",
        "evi_source": "MASTODON",
        "evi_pub_time": datetime(2026, 8, 29, 12, 10, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 16. Missing Location on Evidence -> RELATED
    {
        "id": "evi-16-missing-evidence-location",
        "inc_title": "Heavy rainfall causes road damage",
        "inc_desc": "Asphalt broken by surging water.",
        "inc_cat": "HEAVY_RAINFALL",
        "inc_lat": None,
        "inc_lon": None,
        "inc_time": datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc),
        "inc_loc": None,
        "evi_title": "Monsoon rains continue across country",
        "evi_desc": "Heavy precipitation recorded across northern and central river basins.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 9, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.RELATED,
    },
    # 17. Kochi MG Road Flood Supporting -> SUPPORTING
    {
        "id": "evi-17-kochi-supporting",
        "inc_title": "MG road in Kochi submerged",
        "inc_desc": "Flood water enters commercial shops.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 9.9312,
        "inc_lon": 76.2673,
        "inc_time": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "inc_loc": "Kochi, Kerala",
        "evi_title": "Severe flooding on MG Road Kochi after torrential rains",
        "evi_desc": "Inundation halts traffic on MG Road in Kochi city.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 11, 40, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 18. Cyclone Coast News vs Inland Landslide Incident (Distant 80km) -> IRRELEVANT
    {
        "id": "evi-18-cyclone-coast-vs-inland-landslide",
        "inc_title": "Landslide blocks Araku ghat road",
        "inc_desc": "Boulders collapse across highway.",
        "inc_cat": "LANDSLIDE",
        "inc_lat": 18.3333,
        "inc_lon": 82.8833,
        "inc_time": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "inc_loc": "Araku Valley",
        "evi_title": "Cyclone storm surge batters Visakhapatnam port",
        "evi_desc": "High waves crash into coastal harbor at Visakhapatnam port.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 14, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 19. Shimla Hill Rains News -> SUPPORTING
    {
        "id": "evi-19-shimla-rainfall-supporting",
        "inc_title": "Nonstop rainfall in Shimla town",
        "inc_desc": "Heavy showers cause localized mud accumulation on roads.",
        "inc_cat": "HEAVY_RAINFALL",
        "inc_lat": 31.1048,
        "inc_lon": 77.1734,
        "inc_time": datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc),
        "inc_loc": "Shimla, Himachal Pradesh",
        "evi_title": "Shimla receives torrential monsoon rainfall overnight",
        "evi_desc": "Continuous rains trigger mud flow across Shimla hills.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 8, 45, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 20. Foreign City Kathmandu vs Dehradun Incident -> IRRELEVANT
    {
        "id": "evi-20-kathmandu-foreign-vs-dehradun",
        "inc_title": "River surge in Dehradun foothills",
        "inc_desc": "Water levels rise near Dehradun bridge.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 30.3165,
        "inc_lon": 78.0322,
        "inc_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "inc_loc": "Dehradun, Uttarakhand",
        "evi_title": "Bagmati river in Kathmandu overflows danger mark",
        "evi_desc": "Heavy flooding reported across Kathmandu valley in Nepal.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 12, 15, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 21. Chembur Mumbai Waterlogging News -> SUPPORTING
    {
        "id": "evi-21-chembur-supporting",
        "inc_title": "Postal colony in Chembur flooded",
        "inc_desc": "Water logging on main access road in Chembur.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0522,
        "inc_lon": 72.8995,
        "inc_time": datetime(2026, 8, 29, 9, 30, tzinfo=timezone.utc),
        "inc_loc": "Chembur, Mumbai",
        "evi_title": "Waterlogging hits Chembur postal colony in Mumbai",
        "evi_desc": "Severe street inundation near Chembur postal colony after morning showers.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 22. Drought News vs Thunderstorm Incident -> IRRELEVANT
    {
        "id": "evi-22-drought-vs-thunderstorm",
        "inc_title": "Severe lightning strike in Hyderabad",
        "inc_desc": "Transformer damaged by lightning.",
        "inc_cat": "LIGHTNING",
        "inc_lat": 17.3850,
        "inc_lon": 78.4867,
        "inc_time": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "inc_loc": "Hyderabad, Telangana",
        "evi_title": "Severe drought and dry conditions persist across district",
        "evi_desc": "Zero rainfall for months causing severe water table depletion.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 15, 10, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 23. State Disaster Advisory PIB Release -> CONTEXTUAL
    {
        "id": "evi-23-state-advisory-pib",
        "inc_title": "Waterlogging in Thane city",
        "inc_desc": "Streets inundated in Thane.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.2183,
        "inc_lon": 72.9781,
        "inc_time": datetime(2026, 8, 29, 13, 0, tzinfo=timezone.utc),
        "inc_loc": "Thane, Maharashtra",
        "evi_title": "State government issues advisory issued for coastal districts of Maharashtra",
        "evi_desc": "Authorities monitoring situation on contingency plans.",
        "evi_source": "GOVERNMENT_PIB",
        "evi_pub_time": datetime(2026, 8, 29, 13, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.CONTEXTUAL,
    },
    # 24. Delhi Yamuna News Portal Evidence -> SUPPORTING
    {
        "id": "evi-24-delhi-yamuna-news-supporting",
        "inc_title": "Yamuna river water level surging in Delhi",
        "inc_desc": "Water entering low lying flood plains near Yamuna.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 28.6139,
        "inc_lon": 77.2090,
        "inc_time": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "inc_loc": "Delhi",
        "evi_title": "Yamuna river water level rises causing flood alert in Delhi",
        "evi_desc": "Rising river water enters low-lying flood plains near Delhi.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 11, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 25. High semantic similarity but 72 hours later -> IRRELEVANT
    {
        "id": "evi-25-high-sim-72h-later",
        "inc_title": "Andheri subway inundated with water",
        "inc_desc": "Traffic halted at Andheri.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.1197,
        "inc_lon": 72.8468,
        "inc_time": datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Andheri, Mumbai",
        "evi_title": "Andheri subway inundated with water",
        "evi_desc": "Traffic halted at Andheri subway.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),  # 78h later
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 26. Mastodon Post confirming Bandra Linking road waterlogging -> SUPPORTING
    {
        "id": "evi-26-mastodon-bandra-supporting",
        "inc_title": "Bandra linking road waterlogged",
        "inc_desc": "Water level knee deep outside shops.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0596,
        "inc_lon": 72.8295,
        "inc_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "inc_loc": "Bandra, Mumbai",
        "evi_title": "Bandra linking road flooded with knee deep rain water #MumbaiFloods",
        "evi_desc": "Cars submerged near Bandra shopping center right now.",
        "evi_source": "MASTODON",
        "evi_pub_time": datetime(2026, 8, 29, 12, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 27. Contradictory Rumour Debunking in Kurla -> CONTRADICTORY
    {
        "id": "evi-27-kurla-contradictory",
        "inc_title": "Kurla railway bridge washed away",
        "inc_desc": "Citizen reports bridge collapse in Kurla.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0726,
        "inc_lon": 72.8845,
        "inc_time": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "inc_loc": "Kurla, Mumbai",
        "evi_title": "Railway authorities confirm fake news on Kurla bridge",
        "evi_desc": "Rumour debunked; traffic completely normal and bridge safe in Kurla.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 11, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.CONTRADICTORY,
    },
    # 28. Patna river flood vs Guwahati incident -> IRRELEVANT
    {
        "id": "evi-28-patna-vs-guwahati-irrelevant",
        "inc_title": "Flooding in low lying neighborhoods of Guwahati",
        "inc_desc": "Brahmaputra water enters homes in Guwahati.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 26.1445,
        "inc_lon": 91.7362,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Guwahati, Assam",
        "evi_title": "Ganga river levels rise causing flooding in Patna",
        "evi_desc": "Low lying areas flooded in Patna Bihar.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 29. Bengaluru Whitefield Tree Fall Supporting -> SUPPORTING
    {
        "id": "evi-29-bengaluru-tree-fall-supporting",
        "inc_title": "Uprooted tree blocking 100ft road Indiranagar",
        "inc_desc": "Heavy winds down large tree near Indiranagar.",
        "inc_cat": "THUNDERSTORM",
        "inc_lat": 12.9784,
        "inc_lon": 77.6408,
        "inc_time": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "inc_loc": "Indiranagar, Bengaluru",
        "evi_title": "Massive tree fall blocks Indiranagar 100ft road after thunderstorm",
        "evi_desc": "Traffic diverted in Indiranagar Bengaluru as storm winds topple tree.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 16, 25, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 30. Coldwave in Shimla News -> SUPPORTING
    {
        "id": "evi-30-coldwave-shimla-supporting",
        "inc_title": "Severe frost and subzero cold in Shimla",
        "inc_desc": "Frost blankets roads.",
        "inc_cat": "COLDWAVE",
        "inc_lat": 31.1048,
        "inc_lon": 77.1734,
        "inc_time": datetime(2026, 8, 29, 6, 0, tzinfo=timezone.utc),
        "inc_loc": "Shimla, Himachal Pradesh",
        "evi_title": "Severe coldwave alert issued as frost blankets Shimla hills",
        "evi_desc": "Subzero temperatures and icy roads recorded in Shimla.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 6, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 31. Pakistan flood news vs Punjab incident -> IRRELEVANT (Foreign country)
    {
        "id": "evi-31-foreign-pakistan-vs-punjab",
        "inc_title": "River overflow in Amritsar district",
        "inc_desc": "Canal overflow in Amritsar.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 31.6340,
        "inc_lon": 74.8723,
        "inc_time": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "inc_loc": "Amritsar, Punjab",
        "evi_title": "Severe flash floods in Pakistan Punjab cause widespread damage",
        "evi_desc": "Raging rivers inundate villages across Pakistan.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 10, 30, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
    # 32. Heavy rainfall news matching flood incident in same town -> SUPPORTING
    {
        "id": "evi-32-heavy-rain-matching-flood",
        "inc_title": "Inundation in Dadar TT circle",
        "inc_desc": "Water accumulation at Dadar circle.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0178,
        "inc_lon": 72.8478,
        "inc_time": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "inc_loc": "Dadar, Mumbai",
        "evi_title": "Heavy rainfall downpour lashes Dadar in central Mumbai",
        "evi_desc": "Dadar TT circle submerged under knee deep water.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 14, 20, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 33. National overview weather report -> RELATED
    {
        "id": "evi-33-national-overview-related",
        "inc_title": "Urban waterlogging in Pune",
        "inc_desc": "Roads flooded in Pune city.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 18.5204,
        "inc_lon": 73.8567,
        "inc_time": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "inc_loc": "Pune, Maharashtra",
        "evi_title": "Monsoon rains active across Western Ghats and Maharashtra",
        "evi_desc": "Continuous rainfall recorded in Pune and surrounding hills.",
        "evi_source": "GDELT",
        "evi_pub_time": datetime(2026, 8, 29, 15, 45, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.RELATED,
    },
    # 34. Borivali waterlogging social evidence -> SUPPORTING
    {
        "id": "evi-34-borivali-supporting",
        "inc_title": "Western express highway blocked near Borivali",
        "inc_desc": "Waterlogging near Borivali highway junction.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.2307,
        "inc_lon": 72.8567,
        "inc_time": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "inc_loc": "Borivali, Mumbai",
        "evi_title": "Borivali highway completely waterlogged right now #MumbaiRains",
        "evi_desc": "Vehicles moving at crawling speed near Borivali flyover.",
        "evi_source": "MASTODON",
        "evi_pub_time": datetime(2026, 8, 29, 14, 15, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.SUPPORTING,
    },
    # 35. Unrelated Sports News with "Flood" Metaphor -> IRRELEVANT
    {
        "id": "evi-35-metaphor-sports-irrelevant",
        "inc_title": "Flash flooding in residential sectors",
        "inc_desc": "Heavy cloudburst fills street drains.",
        "inc_cat": "FLOOD_WATERLOGGING",
        "inc_lat": 19.0760,
        "inc_lon": 72.8777,
        "inc_time": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "inc_loc": "Mumbai, Maharashtra",
        "evi_title": "Fans flood stadium as cricket tournament begins",
        "evi_desc": "Huge crowds flood entrance gates for opening match.",
        "evi_source": "NEWS_PORTAL",
        "evi_pub_time": datetime(2026, 8, 29, 12, 10, tzinfo=timezone.utc),
        "expected": EvidenceRelationship.IRRELEVANT,
    },
]


def run_evidence_benchmark_evaluation(scorer: EvidenceScorer) -> Dict[str, Any]:
    """Run benchmark evaluation fixture against EvidenceScorer policy and compute metrics.

    Label: Synthetic Evidence-Linking Benchmark Only.
    """
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    exact_matches = 0
    results = []

    for pair in EVIDENCE_BENCHMARK_PAIRS:
        assessment = scorer.score_link(
            incident_id=uuid.uuid4(),
            evidence_id=uuid.uuid4(),
            incident_title=pair["inc_title"],
            incident_desc=pair.get("inc_desc"),
            incident_cat=pair["inc_cat"],
            incident_lat=pair.get("inc_lat"),
            incident_lon=pair.get("inc_lon"),
            incident_time=pair.get("inc_time"),
            incident_loc_name=pair.get("inc_loc"),
            evidence_title=pair["evi_title"],
            evidence_snippet=pair.get("evi_desc"),
            evidence_source_type=pair.get("evi_source", "NEWS_PORTAL"),
            evidence_pub_time=pair.get("evi_pub_time"),
        )

        expected = pair["expected"]
        actual = assessment.relationship_type

        # Binary linking classification: Is it a valid link (not IRRELEVANT)?
        expected_is_link = expected != EvidenceRelationship.IRRELEVANT
        actual_is_link = actual != EvidenceRelationship.IRRELEVANT

        if expected_is_link:
            if actual_is_link:
                tp += 1
            else:
                fn += 1
        else:
            if actual_is_link:
                fp += 1
            else:
                tn += 1

        is_exact = expected == actual
        if is_exact:
            exact_matches += 1

        results.append(
            {
                "id": pair["id"],
                "expected": expected.value,
                "actual": actual.value,
                "overall_score": assessment.overall_score,
                "passed": is_exact,
            }
        )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "dataset_name": "Synthetic Evidence-Linking Benchmark Only",
        "total_pairs": len(EVIDENCE_BENCHMARK_PAIRS),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "exact_relationship_matches": exact_matches,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "all_passed": all(r["passed"] for r in results),
        "results": results,
    }
