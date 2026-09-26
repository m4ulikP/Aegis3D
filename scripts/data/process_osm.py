import json
from pathlib import Path


# ============================================================
# AEGIS3D — OSM BUILDING PROCESSOR
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "data" / "raw" / "gis" / "delhi_buildings.geojson"
OUTPUT_FILE = ROOT / "data" / "processed" / "gis" / "delhi_buildings.json"


def parse_number(value):
    """Safely convert an OSM numeric tag to float."""
    if value is None:
        return None

    try:
        # Handle values such as "18 m"
        return float(str(value).replace("m", "").strip())
    except (ValueError, TypeError):
        return None


def parse_levels(value):
    """Safely convert building:levels to integer."""
    if value is None:
        return None

    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def get_building_name(tags):
    """Choose the most useful available building name."""
    return (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("addr:housename")
        or None
    )


def process_building(feature):
    """Convert one GeoJSON building feature into Aegis3D format."""

    properties = feature.get("properties", {})
    tags = properties.get("tags", properties)

    osm_id = (
        properties.get("id")
        or properties.get("@id")
        or properties.get("osm_id")
    )

    geometry = feature.get("geometry")

    if not geometry:
        return None

    # We only want actual building features.
    if "building" not in tags:
        return None

    building_type = tags.get("building")

    return {
        "building_id": f"osm/{osm_id}" if osm_id else None,

        "osm_id": osm_id,

        "name": get_building_name(tags),

        "building_type": building_type,

        "levels": parse_levels(tags.get("building:levels")),

        "height_m": parse_number(tags.get("height")),

        "status": "HEALTHY",

        "geometry": geometry,

        "source": {
            "provider": "OpenStreetMap",
            "license": "ODbL"
        }
    }


def main():

    print("=" * 60)
    print("AEGIS3D OSM BUILDING PROCESSOR")
    print("=" * 60)

    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find input file:\n{INPUT_FILE}"
        )

    # --------------------------------------------------------
    # Load GeoJSON
    # --------------------------------------------------------

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Input type: {data.get('type')}")

    features = data.get("features", [])

    print(f"Input features: {len(features)}")

    # --------------------------------------------------------
    # Process buildings
    # --------------------------------------------------------

    buildings = []

    for feature in features:

        building = process_building(feature)

        if building is not None:
            buildings.append(building)

    # --------------------------------------------------------
    # Output structure
    # --------------------------------------------------------

    output = {
        "dataset": {
            "name": "Aegis3D Delhi Building Dataset",
            "source": "OpenStreetMap",
            "license": "ODbL",
            "feature_count": len(buildings)
        },

        "buildings": buildings
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    named = sum(
        1 for b in buildings
        if b["name"]
    )

    with_height = sum(
        1 for b in buildings
        if b["height_m"] is not None
    )

    with_levels = sum(
        1 for b in buildings
        if b["levels"] is not None
    )

    print()
    print("-" * 60)
    print("PROCESSING COMPLETE")
    print("-" * 60)

    print(f"Buildings extracted: {len(buildings)}")
    print(f"Named buildings:     {named}")
    print(f"With height:         {with_height}")
    print(f"With floor levels:   {with_levels}")

    print()
    print(f"Output:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()