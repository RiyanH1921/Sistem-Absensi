import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees) using Haversine formula.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')

    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in meters
    r = 6371000
    return round(c * r, 2)

def is_within_radius(user_lat: float, user_lon: float, center_lat: float, center_lon: float, max_radius_m: float = 100.0):
    """
    Validates if user coordinate is within maximum radius in meters.
    Returns (is_valid: bool, distance_meters: float)
    """
    if center_lat is None or center_lon is None:
        return True, 0.0  # Geofence not enforced if center not set
    
    distance = haversine_distance(user_lat, user_lon, center_lat, center_lon)
    return distance <= max_radius_m, distance
