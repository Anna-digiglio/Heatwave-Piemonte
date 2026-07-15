"""
maps.py - Utility per le mappe Folium.
"""

from shapely import wkt
from shapely.geometry import mapping


def wkt_to_geojson(wkt_str: str) -> dict:
    """Converte una geometria WKT in un dict GeoJSON (richiesto da folium.GeoJson)."""
    return mapping(wkt.loads(wkt_str))
