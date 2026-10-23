"""Register the extra (non-handover) sources in the `sources` table."""
from ..db import insert

EXTRA_SOURCES = [
    dict(source_id="src_usgs", source_name="USGS Earthquake Hazards Program", source_type="official_agency",
         source_url="https://earthquake.usgs.gov", authority_level=5, officiality="official",
         timestamp_precision="exact", geographic_precision="coordinate", license="Public domain",
         retrieval_method="api", credibility_tier="A", layer="sensor", notes="FDSN event API"),
    dict(source_id="src_openmeteo", source_name="Open-Meteo (ERA5 archive / forecast)", source_type="research",
         source_url="https://open-meteo.com", authority_level=4, officiality="semi_official",
         timestamp_precision="exact", geographic_precision="coordinate", license="CC BY 4.0",
         retrieval_method="api", credibility_tier="A", layer="sensor", notes="Gridded weather; measured/reanalysis"),
    dict(source_id="src_nws", source_name="US National Weather Service (via IEM AFOS archive)",
         source_type="official_agency", source_url="https://mesonet.agron.iastate.edu/wx/afos/",
         authority_level=5, officiality="official", timestamp_precision="exact", geographic_precision="region",
         license="Public domain (US Gov)", retrieval_method="api", credibility_tier="A", layer="official"),
    dict(source_id="src_google_news", source_name="Google News RSS (publisher headlines)", source_type="news_media",
         source_url="https://news.google.com", authority_level=3, officiality="unofficial",
         timestamp_precision="exact", geographic_precision="city", license="Headlines + links only",
         retrieval_method="rss", credibility_tier="C", layer="local_news"),
    dict(source_id="src_youtube", source_name="YouTube channel RSS (news channels)", source_type="news_media",
         source_url="https://www.youtube.com", authority_level=3, officiality="unofficial",
         timestamp_precision="exact", geographic_precision="region", license="Metadata only",
         retrieval_method="rss", credibility_tier="C", layer="local_news"),
    dict(source_id="src_synthetic", source_name="SachVerify synthetic scenarios (clearly labelled)",
         source_type="synthetic", authority_level=1, officiality="unofficial", timestamp_precision="exact",
         geographic_precision="coordinate", license="Project-generated", retrieval_method="synthetic",
         credibility_tier="A", layer="official", notes="Synthetic stand-ins for official alerts in demo scenarios"),
    dict(source_id="src_tipline", source_name="Tipline submissions", source_type="social_media",
         authority_level=1, officiality="unofficial", timestamp_precision="approximate",
         geographic_precision="unknown", retrieval_method="manual_download", credibility_tier="D", layer="social"),
]


def ensure_sources():
    for s in EXTRA_SOURCES:
        insert("sources", s)
