import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.intelligence.duplicate_scorer import DuplicateScorer
from app.intelligence.schemas import DuplicateDecision

# Expanded 30-pair deterministic benchmark evaluation dataset
BENCHMARK_EVALUATION_PAIRS: List[Dict[str, Any]] = [
    # 1. (A) Obvious Same-Event Duplicate: Andheri station subway, 15m delta, FLOOD_WATERLOGGING
    {
        "id": "pair-01-obvious-duplicate",
        "title_a": "Severe waterlogging near Andheri station",
        "desc_a": "Water knee-deep near Andheri railway station subway entrance.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.1197,
        "lon_a": 72.8468,
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Andheri station, Mumbai",
        "title_b": "Knee-deep water outside Andheri station",
        "desc_b": "Subway completely inundated, traffic halted near Andheri station.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.1205,
        "lon_b": 72.8475,
        "time_b": datetime(2026, 8, 29, 10, 15, tzinfo=timezone.utc),
        "loc_b": "Andheri, Mumbai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 2. (B) Near Duplicate (different phrasing): Kurla subway, 20m delta, FLOOD
    {
        "id": "pair-02-near-duplicate-phrasing",
        "title_a": "Kurla subway inundated after heavy showers",
        "desc_a": "Vehicles stranded as water rises inside Kurla subway.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0726,
        "lon_a": 72.8845,
        "time_a": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "loc_a": "Kurla, Mumbai",
        "title_b": "Vehicles trapped in water at Kurla underpass",
        "desc_b": "Flooding in Kurla underpass following morning downpour.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0730,
        "lon_b": 72.8850,
        "time_b": datetime(2026, 8, 29, 11, 20, tzinfo=timezone.utc),
        "loc_b": "Kurla subway, Mumbai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 3. (C) Same Text & Location, Different Time (48h later): Must be DISTINCT
    {
        "id": "pair-03-different-time-48h",
        "title_a": "Waterlogging near Andheri station",
        "desc_a": "Heavy water accumulation around subway.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.1197,
        "lon_a": 72.8468,
        "time_a": datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Andheri station, Mumbai",
        "title_b": "Waterlogging near Andheri station",
        "desc_b": "Heavy water accumulation around subway.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.1197,
        "lon_b": 72.8468,
        "time_b": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_b": "Andheri station, Mumbai",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 4. (D) Same Text, Different Cities (Mumbai vs Delhi): Must be DISTINCT
    {
        "id": "pair-04-different-cities-mumbai-delhi",
        "title_a": "Heavy downpour causing severe road waterlogging",
        "desc_a": "Traffic severely disrupted due to heavy water accumulation.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0760,
        "lon_a": 72.8777,  # Mumbai
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Mumbai, Maharashtra",
        "title_b": "Heavy downpour causing severe road waterlogging",
        "desc_b": "Traffic severely disrupted due to heavy water accumulation.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 28.6139,
        "lon_b": 77.2090,  # Delhi
        "time_b": datetime(2026, 8, 29, 10, 30, tzinfo=timezone.utc),
        "loc_b": "Delhi",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 5. (E) Nearby Different Incidents (> 2.5km): Andheri vs Kurla (7.5km away) -> DISTINCT
    {
        "id": "pair-05-nearby-distinct-localities",
        "title_a": "Flooded street in Andheri",
        "desc_a": "Water accumulation on road in Andheri.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.1197,
        "lon_a": 72.8468,  # Andheri
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Andheri, Mumbai",
        "title_b": "Flooded street in Kurla",
        "desc_b": "Water accumulation on road in Kurla.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0726,
        "lon_b": 72.8845,  # Kurla (~7.5 km away)
        "time_b": datetime(2026, 8, 29, 10, 10, tzinfo=timezone.utc),
        "loc_b": "Kurla, Mumbai",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 6. (F) Same City, Distant Localities: Mumbai South (Colaba) vs Borivali (35km) -> DISTINCT
    {
        "id": "pair-06-same-city-distant-localities",
        "title_a": "Heavy rain downpour and waterlogging in Borivali",
        "desc_a": "Waterlogging on Western Express Highway near Borivali.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.2307,
        "lon_a": 72.8567,  # Borivali
        "time_a": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "loc_a": "Borivali, Mumbai",
        "title_b": "Waterlogging near Dadar circle",
        "desc_b": "Traffic halted near Dadar TT circle.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0178,
        "lon_b": 72.8478,  # Dadar (~24 km away)
        "time_b": datetime(2026, 8, 29, 14, 15, tzinfo=timezone.utc),
        "loc_b": "Dadar, Mumbai",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 7. (G) Same Locality, 6 Hours Apart (> 3h max window): Must be DISTINCT
    {
        "id": "pair-07-same-locality-different-time-6h",
        "title_a": "Morning waterlogging at Connaught Place",
        "desc_a": "Waterlogging cleared by municipal pumps.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 28.6315,
        "lon_a": 77.2167,
        "time_a": datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc),
        "loc_a": "Connaught Place, New Delhi",
        "title_b": "Evening flash storm at Connaught Place",
        "desc_b": "Fresh storm causes new waterlogging in evening.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 28.6315,
        "lon_b": 77.2167,
        "time_b": datetime(2026, 8, 29, 14, 30, tzinfo=timezone.utc),  # 6.5h delta
        "loc_b": "Connaught Place, New Delhi",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 8. (H) Same Category, Different Events (Bengaluru Indiranagar vs Whitefield): DISTINCT
    {
        "id": "pair-08-bengaluru-indiranagar-vs-whitefield",
        "title_a": "Uprooted tree blocking 100ft road Indiranagar",
        "desc_a": "Heavy winds down large tree near 12th main Indiranagar.",
        "cat_a": "THUNDERSTORM",
        "lat_a": 12.9784,
        "lon_a": 77.6408,  # Indiranagar
        "time_a": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "loc_a": "Indiranagar, Bengaluru",
        "title_b": "Storm winds smash billboard in Whitefield",
        "desc_b": "Commercial billboard collapse in Whitefield IT corridor.",
        "cat_b": "THUNDERSTORM",
        "lat_b": 12.9698,
        "lon_b": 77.7500,  # Whitefield (12km away)
        "time_b": datetime(2026, 8, 29, 16, 15, tzinfo=timezone.utc),
        "loc_b": "Whitefield, Bengaluru",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 9. (I) Related Hazard Categories, Different Events (Heavy Rain vs Landslide): DISTINCT
    {
        "id": "pair-09-related-hazards-distinct-places",
        "title_a": "Continuous rainfall in Shimla hills",
        "desc_a": "Non-stop rains recorded throughout Shimla town.",
        "cat_a": "HEAVY_RAINFALL",
        "lat_a": 31.1048,
        "lon_a": 77.1734,
        "time_a": datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc),
        "loc_a": "Shimla, Himachal Pradesh",
        "title_b": "Debris landslide blocking highway at Bilaspur",
        "desc_b": "Massive landslide halts highway traffic at Bilaspur.",
        "cat_b": "LANDSLIDE",
        "lat_b": 31.3326,
        "lon_b": 76.7606,  # 50km away
        "time_b": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_b": "Bilaspur, Himachal Pradesh",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 10. (J) Incompatible Hazard Categories (Heatwave vs Flood): Must be DISTINCT
    {
        "id": "pair-10-incompatible-categories-heatwave-flood",
        "title_a": "Extreme heatwave conditions reported in city",
        "desc_a": "Temperatures cross 44C with severe dry heat wave.",
        "cat_a": "HEATWAVE",
        "lat_a": 19.0760,
        "lon_a": 72.8777,
        "time_a": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "loc_a": "Mumbai, Maharashtra",
        "title_b": "Flash flood submerging streets",
        "desc_b": "Torrential rain causes deep urban flooding.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0760,
        "lon_b": 72.8777,
        "time_b": datetime(2026, 8, 29, 12, 10, tzinfo=timezone.utc),
        "loc_b": "Mumbai, Maharashtra",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 11. (K) Missing Coordinates with High Text Overlap: Must be POSSIBLE_MATCH
    {
        "id": "pair-11-missing-coordinates-high-text",
        "title_a": "Bridge collapse feared as flood waters breach embankment",
        "desc_a": "Local authorities evacuate residents near raging river waters.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": None,
        "lon_a": None,
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": None,
        "title_b": "Bridge collapse feared as flood waters breach embankment",
        "desc_b": "Local authorities evacuate residents near raging river waters.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": None,
        "lon_b": None,
        "time_b": datetime(2026, 8, 29, 10, 10, tzinfo=timezone.utc),
        "loc_b": None,
        "expected": DuplicateDecision.POSSIBLE_MATCH,
    },
    # 12. (L) Missing Timestamp with Known Location & Text: Must be POSSIBLE_MATCH
    {
        "id": "pair-12-missing-timestamp",
        "title_a": "Subway waterlogged near Sion station",
        "desc_a": "Buses diverted due to high water level under railway bridge.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0390,
        "lon_a": 72.8619,
        "time_a": None,
        "loc_a": "Sion, Mumbai",
        "title_b": "Sion railway subway inundated with flood water",
        "desc_b": "Traffic diverted around flooded Sion underpass.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0390,
        "lon_b": 72.8619,
        "time_b": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_b": "Sion, Mumbai",
        "expected": DuplicateDecision.POSSIBLE_MATCH,
    },
    # 13. (M) Missing Both Coordinates and Timestamp: Must be POSSIBLE_MATCH or DISTINCT
    {
        "id": "pair-13-missing-both-coords-time",
        "title_a": "Severe storm damage to power lines across district",
        "desc_a": "Power outages reported as gale winds snap electricity poles.",
        "cat_a": "THUNDERSTORM",
        "lat_a": None,
        "lon_a": None,
        "time_a": None,
        "loc_a": None,
        "title_b": "Severe storm damage to power lines across district",
        "desc_b": "Power outages reported as gale winds snap electricity poles.",
        "cat_b": "THUNDERSTORM",
        "lat_b": None,
        "lon_b": None,
        "time_b": None,
        "loc_b": None,
        "expected": DuplicateDecision.POSSIBLE_MATCH,
    },
    # 14. (N) Ambiguous Place Name Without Context (Rajpur MP vs Rajpur UK): DISTINCT
    {
        "id": "pair-14-ambiguous-place-distinct-states",
        "title_a": "Flash flood in Rajpur Barwani",
        "desc_a": "Heavy rain floods market area in Rajpur Barwani MP.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 21.9333,
        "lon_a": 75.1333,  # Rajpur, MP
        "time_a": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "loc_a": "Rajpur, Barwani, Madhya Pradesh",
        "title_b": "Flash flood in Rajpur Dehradun",
        "desc_b": "Raging stream washes over Rajpur road in Dehradun.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 30.3833,
        "lon_b": 78.0833,  # Rajpur, Uttarakhand (~1000km)
        "time_b": datetime(2026, 8, 29, 11, 15, tzinfo=timezone.utc),
        "loc_b": "Rajpur, Dehradun, Uttarakhand",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 15. (O) Foreign Location vs Indian Incident (Nepal floods vs Mumbai): Must be DISTINCT
    {
        "id": "pair-15-foreign-nepal-vs-mumbai",
        "title_a": "Nepal flash floods kill dozens as rivers overflow",
        "desc_a": "Disaster authorities respond to catastrophic flooding across Nepal.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": None,
        "lon_a": None,
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Nepal",
        "title_b": "Severe flood in Mumbai coastal areas",
        "desc_b": "High tide and heavy showers flood lowlands in Mumbai.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0760,
        "lon_b": 72.8777,
        "time_b": datetime(2026, 8, 29, 10, 15, tzinfo=timezone.utc),
        "loc_b": "Mumbai, Maharashtra",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 16. (P) Cross-Source Match (Citizen Report vs IMD Warning for same locality/time): DUPLICATE
    {
        "id": "pair-16-cross-source-citizen-imd-match",
        "title_a": "Severe waterlogging near Whitefield station",
        "desc_a": "Citizen video shows heavy water accumulation at Whitefield railway bridge.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 12.9698,
        "lon_a": 77.7500,
        "time_a": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "loc_a": "Whitefield, Bengaluru",
        "title_b": "IMD Flash Alert: Inundation in Whitefield area",
        "desc_b": "Heavy localized cloudburst reported inundating Whitefield road networks.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 12.9705,
        "lon_b": 77.7510,
        "time_b": datetime(2026, 8, 29, 15, 10, tzinfo=timezone.utc),
        "loc_b": "Whitefield, Bengaluru",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 17. (Q) Multi-Report Clustering (Third duplicate in Bandra): DUPLICATE
    {
        "id": "pair-17-third-duplicate-bandra",
        "title_a": "Waterlogged road at Bandra Linking road",
        "desc_a": "Stores flooded near Bandra Shopping center.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0596,
        "lon_a": 72.8295,
        "time_a": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "loc_a": "Bandra, Mumbai",
        "title_b": "Bandra linking road flooded with knee deep rain water",
        "desc_b": "Traffic at a standstill on Bandra linking road.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0600,
        "lon_b": 72.8300,
        "time_b": datetime(2026, 8, 29, 12, 25, tzinfo=timezone.utc),
        "loc_b": "Bandra, Mumbai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 18. (R) Unrelated Hazard Pair: Coldwave vs Heatwave (Strictly Incompatible): DISTINCT
    {
        "id": "pair-18-coldwave-vs-heatwave",
        "title_a": "Severe coldwave alert issued as frost blankets region",
        "desc_a": "Sub-zero temperatures recorded with heavy frost.",
        "cat_a": "COLDWAVE",
        "lat_a": 31.1048,
        "lon_a": 77.1734,
        "time_a": datetime(2026, 8, 29, 6, 0, tzinfo=timezone.utc),
        "loc_a": "Shimla",
        "title_b": "Heatwave conditions persist",
        "desc_b": "Extreme temperatures continue unabated.",
        "cat_b": "HEATWAVE",
        "lat_b": 31.1048,
        "lon_b": 77.1734,
        "time_b": datetime(2026, 8, 29, 6, 10, tzinfo=timezone.utc),
        "loc_b": "Shimla",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 19. (S) Same Text, Distant Eastern Cities (Patna vs Guwahati): DISTINCT
    {
        "id": "pair-19-patna-vs-guwahati",
        "title_a": "Flooding in low lying neighborhoods after river surge",
        "desc_a": "Water enters residential houses near river bank.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 25.5941,
        "lon_a": 85.1376,  # Patna
        "time_a": datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        "loc_a": "Patna, Bihar",
        "title_b": "Flooding in low lying neighborhoods after river surge",
        "desc_b": "Water enters residential houses near river bank.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 26.1445,
        "lon_b": 91.7362,  # Guwahati (~700km)
        "time_b": datetime(2026, 8, 29, 10, 20, tzinfo=timezone.utc),
        "loc_b": "Guwahati, Assam",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 20. (T) Sub-Word Phrasing Variations ("inundated tracks" vs "waterlogged rails"): DUPLICATE
    {
        "id": "pair-20-sub-word-phrasing-kurla",
        "title_a": "Kurla railway station tracks inundated with muddy water",
        "desc_a": "Train operations suspended due to high water on railway tracks.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0726,
        "lon_a": 72.8845,
        "time_a": datetime(2026, 8, 29, 13, 0, tzinfo=timezone.utc),
        "loc_a": "Kurla, Mumbai",
        "title_b": "Waterlogged rail lines halt suburban trains at Kurla",
        "desc_b": "Local trains delayed as water covers railway tracks at Kurla.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0728,
        "lon_b": 72.8848,
        "time_b": datetime(2026, 8, 29, 13, 15, tzinfo=timezone.utc),
        "loc_b": "Kurla station, Mumbai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 21. Chembur waterlogging duplicate: DUPLICATE
    {
        "id": "pair-21-chembur-waterlogging",
        "title_a": "Chembur postal colony flooded",
        "desc_a": "Water logging in Chembur postal colony road.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 19.0522,
        "lon_a": 72.8995,
        "time_a": datetime(2026, 8, 29, 9, 30, tzinfo=timezone.utc),
        "loc_a": "Chembur, Mumbai",
        "title_b": "Chembur roads flooded near postal colony",
        "desc_b": "Severe water accumulation near Chembur postal colony.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 19.0525,
        "lon_b": 72.8998,
        "time_b": datetime(2026, 8, 29, 9, 45, tzinfo=timezone.utc),
        "loc_b": "Chembur, Mumbai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 22. Chennai T. Nagar waterlogging duplicate: DUPLICATE
    {
        "id": "pair-22-chennai-tnagar-duplicate",
        "title_a": "Heavy rain inundates Usman road T Nagar",
        "desc_a": "Usman road in T Nagar flooded with knee high water.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 13.0418,
        "lon_a": 80.2341,
        "time_a": datetime(2026, 8, 29, 17, 0, tzinfo=timezone.utc),
        "loc_a": "T Nagar, Chennai",
        "title_b": "Water logging in T Nagar commercial streets",
        "desc_b": "Heavy rains flood Usman road shopping district in T Nagar.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 13.0422,
        "lon_b": 80.2345,
        "time_b": datetime(2026, 8, 29, 17, 15, tzinfo=timezone.utc),
        "loc_b": "T. Nagar, Chennai",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 23. Chennai T. Nagar vs Velachery (8km away in Chennai): DISTINCT
    {
        "id": "pair-23-chennai-tnagar-vs-velachery",
        "title_a": "Waterlogging in T Nagar",
        "desc_a": "Flooded street in T Nagar.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 13.0418,
        "lon_a": 80.2341,  # T Nagar
        "time_a": datetime(2026, 8, 29, 17, 0, tzinfo=timezone.utc),
        "loc_a": "T Nagar, Chennai",
        "title_b": "Waterlogging in Velachery",
        "desc_b": "Flooded street in Velachery lake area.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 12.9815,
        "lon_b": 80.2180,  # Velachery (~7.5 km away)
        "time_b": datetime(2026, 8, 29, 17, 10, tzinfo=timezone.utc),
        "loc_b": "Velachery, Chennai",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 24. Lightning strike vs Drought (Incompatible): DISTINCT
    {
        "id": "pair-24-lightning-vs-drought",
        "title_a": "Lightning strike damages tower",
        "desc_a": "Severe thunder and lightning strike in afternoon.",
        "cat_a": "LIGHTNING",
        "lat_a": 17.3850,
        "lon_a": 78.4867,
        "time_a": datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc),
        "loc_a": "Hyderabad",
        "title_b": "Severe agricultural drought and dry conditions",
        "desc_b": "Zero rainfall for months causing crop failure.",
        "cat_b": "DROUGHT",
        "lat_b": 17.3850,
        "lon_b": 78.4867,
        "time_b": datetime(2026, 8, 29, 15, 10, tzinfo=timezone.utc),
        "loc_b": "Hyderabad",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 25. Delhi Lajpat Nagar waterlogging duplicate: DUPLICATE
    {
        "id": "pair-25-delhi-lajpat-nagar-duplicate",
        "title_a": "Underpass flooded near Lajpat Nagar metro station",
        "desc_a": "Vehicles submerged under Lajpat Nagar flyover.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 28.5677,
        "lon_a": 77.2433,
        "time_a": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "loc_a": "Lajpat Nagar, New Delhi",
        "title_b": "Lajpat Nagar underpass waterlogged after heavy downpour",
        "desc_b": "Traffic diverted near Lajpat Nagar flyover due to waterlogging.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 28.5680,
        "lon_b": 77.2438,
        "time_b": datetime(2026, 8, 29, 16, 20, tzinfo=timezone.utc),
        "loc_b": "Lajpat Nagar, New Delhi",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 26. Delhi Lajpat Nagar vs Rohini (25km away): DISTINCT
    {
        "id": "pair-26-delhi-lajpat-vs-rohini",
        "title_a": "Flooding at Lajpat Nagar underpass",
        "desc_a": "Heavy water accumulation in Lajpat Nagar.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 28.5677,
        "lon_a": 77.2433,  # South Delhi
        "time_a": datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
        "loc_a": "Lajpat Nagar, New Delhi",
        "title_b": "Flooding at Rohini sector road",
        "desc_b": "Heavy water accumulation in Rohini.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 28.7495,
        "lon_b": 77.0565,  # North West Delhi (25km away)
        "time_b": datetime(2026, 8, 29, 16, 15, tzinfo=timezone.utc),
        "loc_b": "Rohini, Delhi",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 27. Kochi rainfall duplicate: DUPLICATE
    {
        "id": "pair-27-kochi-duplicate",
        "title_a": "Water accumulation on MG Road Kochi",
        "desc_a": "Continuous monsoon showers flood MG road in Kochi.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 9.9312,
        "lon_a": 76.2673,
        "time_a": datetime(2026, 8, 29, 11, 0, tzinfo=timezone.utc),
        "loc_a": "Kochi, Kerala",
        "title_b": "MG Road Kochi waterlogged after heavy showers",
        "desc_b": "Traffic slow on MG Road Kochi due to street flooding.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 9.9318,
        "lon_b": 76.2680,
        "time_b": datetime(2026, 8, 29, 11, 20, tzinfo=timezone.utc),
        "loc_b": "Kochi, Kerala",
        "expected": DuplicateDecision.DUPLICATE,
    },
    # 28. Cyclone wind alert vs Landslide (Related but distant 80km): DISTINCT
    {
        "id": "pair-28-cyclone-coast-vs-inland-landslide",
        "title_a": "Cyclone gale winds battering coast at Visakhapatnam",
        "desc_a": "Severe storm surges hitting coastal Visakhapatnam port.",
        "cat_a": "CYCLONE",
        "lat_a": 17.6868,
        "lon_a": 83.2185,
        "time_a": datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc),
        "loc_a": "Visakhapatnam, Andhra Pradesh",
        "title_b": "Landslide blocking ghat road in hills",
        "desc_b": "Boulders fall across Araku valley ghat road.",
        "cat_b": "LANDSLIDE",
        "lat_b": 18.3333,
        "lon_b": 82.8833,  # Araku hills (~90km away)
        "time_b": datetime(2026, 8, 29, 14, 30, tzinfo=timezone.utc),
        "loc_b": "Araku Valley",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 29. Foreign City Kathmandu vs India Dehradun: DISTINCT
    {
        "id": "pair-29-kathmandu-vs-dehradun",
        "title_a": "Heavy downpour causes Bagmati river surge in Kathmandu",
        "desc_a": "River levels exceed danger mark in Kathmandu valley.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": 27.7172,
        "lon_a": 85.3240,  # Kathmandu, Nepal
        "time_a": datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
        "loc_a": "Kathmandu, Nepal",
        "title_b": "Heavy downpour causes river surge in Dehradun",
        "desc_b": "River levels rise in Dehradun foothills.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": 30.3165,
        "lon_b": 78.0322,  # Dehradun, India (~750km away)
        "time_b": datetime(2026, 8, 29, 12, 15, tzinfo=timezone.utc),
        "loc_b": "Dehradun, Uttarakhand",
        "expected": DuplicateDecision.DISTINCT,
    },
    # 30. High text overlap with unresolved location (POSSIBLE_MATCH): POSSIBLE_MATCH
    {
        "id": "pair-30-unresolved-location-river-breach",
        "title_a": "Severe river embankment breach flooding adjoining villages",
        "desc_a": "Villagers evacuated to relief shelters as waters surge.",
        "cat_a": "FLOOD_WATERLOGGING",
        "lat_a": None,
        "lon_a": None,
        "time_a": datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc),
        "loc_a": None,
        "title_b": "Severe river embankment breach flooding adjoining villages",
        "desc_b": "Villagers evacuated to relief shelters as waters surge.",
        "cat_b": "FLOOD_WATERLOGGING",
        "lat_b": None,
        "lon_b": None,
        "time_b": datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc),
        "loc_b": None,
        "expected": DuplicateDecision.POSSIBLE_MATCH,
    },
]


def run_benchmark_evaluation(scorer: DuplicateScorer) -> Dict[str, Any]:
    """Run benchmark evaluation dataset against DuplicateScorer policy and compute metrics."""
    tp = 0  # True Duplicate predicted as DUPLICATE
    fp = 0  # Non-Duplicate predicted as DUPLICATE (CRITICAL: False Merges)
    fn = 0  # True Duplicate predicted as DISTINCT or POSSIBLE_MATCH
    tn = 0  # Non-Duplicate predicted as non-DUPLICATE (DISTINCT or POSSIBLE_MATCH)
    results = []

    for pair in BENCHMARK_EVALUATION_PAIRS:
        assessment = scorer.score_pair(
            report_a_id=uuid.uuid4(),
            report_b_id=uuid.uuid4(),
            title_a=pair["title_a"],
            title_b=pair["title_b"],
            desc_a=pair.get("desc_a"),
            desc_b=pair.get("desc_b"),
            cat_a=pair["cat_a"],
            cat_b=pair["cat_b"],
            lat_a=pair.get("lat_a"),
            lon_a=pair.get("lon_a"),
            lat_b=pair.get("lat_b"),
            lon_b=pair.get("lon_b"),
            time_a=pair.get("time_a"),
            time_b=pair.get("time_b"),
            loc_name_a=pair.get("loc_a"),
            loc_name_b=pair.get("loc_b"),
        )

        expected = pair["expected"]
        actual = assessment.decision

        if expected == DuplicateDecision.DUPLICATE:
            if actual == DuplicateDecision.DUPLICATE:
                tp += 1
            else:
                fn += 1
        else:
            if actual == DuplicateDecision.DUPLICATE:
                fp += 1
            else:
                tn += 1

        results.append(
            {
                "id": pair["id"],
                "expected": expected.value,
                "actual": actual.value,
                "overall_score": assessment.overall_score,
                "passed": (expected == actual),
            }
        )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "dataset_name": "synthetic_evaluation_benchmark_v1",
        "total_pairs": len(BENCHMARK_EVALUATION_PAIRS),
        "true_positives": tp,
        "false_positives": fp,
        "false_merges": fp,  # Explicitly highlight critical safety metric
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "all_passed": all(r["passed"] for r in results),
        "results": results,
    }


def evaluate_threshold_sensitivity(
    candidate_thresholds: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate performance trade-offs across candidate duplicate confirmed thresholds."""
    thresholds = candidate_thresholds or [0.65, 0.70, 0.75, 0.80, 0.85]
    sensitivity_results = []

    for thresh in thresholds:
        test_scorer = DuplicateScorer(confirmed_threshold=thresh)
        metrics = run_benchmark_evaluation(test_scorer)
        sensitivity_results.append(
            {
                "confirmed_threshold": thresh,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "false_merges": metrics["false_merges"],
                "false_negatives": metrics["false_negatives"],
            }
        )

    return sensitivity_results
