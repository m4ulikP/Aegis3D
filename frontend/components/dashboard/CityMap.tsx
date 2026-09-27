"use client";

import { useEffect, useRef, useState } from "react";
import DigitalTwinViewer from "../building/DigitalTwinViewer";

import * as maplibregl from "maplibre-gl";
import type {
    MapLayerMouseEvent,
    MapMouseEvent,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

/*
 * Fixed Aegis3D demonstration building.
 *
 * This is intentionally subtle on the city map.
 * There is no permanent label or marker.
 */
const DEMO_BUILDING_ID = "osm/way/351561090";

/* -------------------------------------------------------------------------- */
/* TYPES                                                                      */
/* -------------------------------------------------------------------------- */

type SelectedBuilding = {
    building_id: string;
    osm_id: string;
    name: string | null;
    building_type: string | null;
    levels: number | null;
    height: number | null;
    status: string;
};

type BuildingRecord = {
    building_id: string;
    osm_id: string;
    name: string | null;
    building_type: string | null;
    levels: number | null;
    height_m: number | null;
    status?: string;
    geometry: GeoJSON.Geometry;
    source?: {
        provider?: string;
        license?: string;
    };
};

type BuildingDataset = {
    metadata?: {
        name?: string;
        source?: string;
        license?: string;
        feature_count?: number;
    };

    buildings: BuildingRecord[];
};

/* -------------------------------------------------------------------------- */
/* HELPERS                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Recursively walks a GeoJSON geometry's coordinates and
 * extends a MapLibre LngLatBounds object.
 */
function extendGeometryBounds(
    bounds: maplibregl.LngLatBounds,
    geometry: GeoJSON.Geometry
) {
    const visitCoordinates = (
        coordinates: unknown
    ): void => {
        if (
            Array.isArray(coordinates) &&
            coordinates.length >= 2 &&
            typeof coordinates[0] === "number" &&
            typeof coordinates[1] === "number"
        ) {
            bounds.extend([
                coordinates[0],
                coordinates[1],
            ]);

            return;
        }

        if (Array.isArray(coordinates)) {
            coordinates.forEach(
                visitCoordinates
            );
        }
    };

    if ("coordinates" in geometry) {
        visitCoordinates(
            geometry.coordinates
        );
    }
}

/* -------------------------------------------------------------------------- */
/* COMPONENT                                                                  */
/* -------------------------------------------------------------------------- */

export default function CityMap() {
    const mapContainer =
        useRef<HTMLDivElement | null>(null);

    const map =
        useRef<maplibregl.Map | null>(null);

    /*
     * Stores the currently selected building's
     * MapLibre feature ID.
     */
    const selectedFeatureId =
        useRef<string | null>(null);

    const [
        selectedBuilding,
        setSelectedBuilding,
    ] = useState<SelectedBuilding | null>(
        null
    );

    const [mapReady, setMapReady] =
        useState(false);

    /*
     * Controls whether the full-screen
     * structural digital twin is visible.
     */
    const [showDigitalTwin, setShowDigitalTwin] =
        useState(false);

    /* ---------------------------------------------------------------------- */
    /* MAP INITIALIZATION                                                     */
    /* ---------------------------------------------------------------------- */

    useEffect(() => {
        if (!mapContainer.current) {
            return;
        }

        /*
         * Prevent initializing the map twice.
         */
        if (map.current) {
            return;
        }

        /*
         * MapLibre worker.
         *
         * This is required because we are serving
         * the worker ourselves from /public/maplibre.
         */
        maplibregl.setWorkerUrl(
            "/maplibre/maplibre-gl-worker.mjs"
        );

        /* ------------------------------------------------------------------ */
        /* CREATE MAP                                                         */
        /* ------------------------------------------------------------------ */

        const instance =
            new maplibregl.Map({
                container:
                    mapContainer.current,

                style: {
                    version: 8,

                    sources: {},

                    layers: [
                        {
                            id: "background",

                            type: "background",

                            paint: {
                                "background-color":
                                    "#0b1220",
                            },
                        },
                    ],
                },

                /*
                 * Initial Delhi position.
                 */
                center: [
                    77.2167,
                    28.6448,
                ],

                zoom: 12,

                attributionControl:
                    false,
            });

        map.current = instance;

        /* ------------------------------------------------------------------ */
        /* NAVIGATION CONTROLS                                                */
        /* ------------------------------------------------------------------ */

        instance.addControl(
            new maplibregl.NavigationControl(),
            "top-right"
        );

        /* ------------------------------------------------------------------ */
        /* MAP LOAD                                                           */
        /* ------------------------------------------------------------------ */

        instance.on(
            "load",
            async () => {
                try {
                    /* ------------------------------------------------------ */
                    /* LOAD ALL GIS DATA                                      */
                    /* ------------------------------------------------------ */

                    const [
                        buildingResponse,
                        roadsResponse,
                        landcoverResponse,
                    ] = await Promise.all([
                        fetch(
                            "/data/delhi_buildings.json"
                        ),

                        fetch(
                            "/data/delhi_roads.geojson"
                        ),

                        fetch(
                            "/data/delhi_landcover.geojson"
                        ),
                    ]);

                    if (
                        !buildingResponse.ok
                    ) {
                        throw new Error(
                            `Failed to load buildings: ${buildingResponse.status}`
                        );
                    }

                    if (
                        !roadsResponse.ok
                    ) {
                        throw new Error(
                            `Failed to load roads: ${roadsResponse.status}`
                        );
                    }

                    if (
                        !landcoverResponse.ok
                    ) {
                        throw new Error(
                            `Failed to load landcover: ${landcoverResponse.status}`
                        );
                    }

                    const buildingDataset =
                        (await buildingResponse.json()) as BuildingDataset;

                    const roadsGeoJSON =
                        (await roadsResponse.json()) as GeoJSON.FeatureCollection;

                    const landcoverGeoJSON =
                        (await landcoverResponse.json()) as GeoJSON.FeatureCollection;

                    /* ------------------------------------------------------ */
                    /* CONVERT AEGIS3D BUILDING DATA TO GEOJSON              */
                    /* ------------------------------------------------------ */

                    const buildingFeatures =
                        buildingDataset.buildings.map(
                            (
                                building
                            ) => ({
                                type:
                                    "Feature" as const,

                                /*
                                 * This ID is important.
                                 *
                                 * It allows feature-state to
                                 * identify the selected building.
                                 */
                                id: building.building_id,

                                geometry:
                                    building.geometry,

                                properties: {
                                    building_id:
                                        building.building_id,

                                    osm_id:
                                        building.osm_id,

                                    name:
                                        building.name,

                                    building_type:
                                        building.building_type,

                                    levels:
                                        building.levels,

                                    height:
                                        building.height_m,

                                    status:
                                        building.status ??
                                        "HEALTHY",
                                },
                            })
                        );

                    const buildingsGeoJSON:
                        GeoJSON.FeatureCollection =
                    {
                        type: "FeatureCollection",

                        features:
                            buildingFeatures,
                    };

                    /* ------------------------------------------------------ */
                    /* BUILDING SOURCE                                        */
                    /* ------------------------------------------------------ */

                    instance.addSource(
                        "buildings",
                        {
                            type: "geojson",

                            data:
                                buildingsGeoJSON,
                        }
                    );

                    /* ------------------------------------------------------ */
                    /* LANDCOVER SOURCE                                       */
                    /* ------------------------------------------------------ */

                    instance.addSource(
                        "landcover",
                        {
                            type: "geojson",

                            data:
                                landcoverGeoJSON,
                        }
                    );

                    /* ------------------------------------------------------ */
                    /* ROAD SOURCE                                             */
                    /* ------------------------------------------------------ */

                    instance.addSource(
                        "roads",
                        {
                            type: "geojson",

                            data:
                                roadsGeoJSON,
                        }
                    );

                    /* ====================================================== */
                    /* WATER                                                   */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "water",

                        type: "fill",

                        source: "landcover",

                        filter: [
                            "==",
                            [
                                "get",
                                "natural",
                            ],
                            "water",
                        ],

                        paint: {
                            "fill-color":
                                "#102a43",

                            "fill-opacity":
                                0.9,
                        },
                    });

                    /* ====================================================== */
                    /* GREEN AREAS                                             */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "green-areas",

                        type: "fill",

                        source: "landcover",

                        filter: [
                            "any",

                            [
                                "==",
                                [
                                    "get",
                                    "leisure",
                                ],
                                "park",
                            ],

                            [
                                "==",
                                [
                                    "get",
                                    "leisure",
                                ],
                                "garden",
                            ],

                            [
                                "==",
                                [
                                    "get",
                                    "landuse",
                                ],
                                "grass",
                            ],

                            [
                                "==",
                                [
                                    "get",
                                    "landuse",
                                ],
                                "recreation_ground",
                            ],
                        ],

                        paint: {
                            "fill-color":
                                "#163b2d",

                            "fill-opacity":
                                0.75,
                        },
                    });

                    /* ====================================================== */
                    /* MAJOR ROADS                                             */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "roads-major",

                        type: "line",

                        source: "roads",

                        filter: [
                            "match",

                            [
                                "get",
                                "highway",
                            ],

                            [
                                "motorway",
                                "motorway_link",
                                "trunk",
                                "trunk_link",
                                "primary",
                                "primary_link",
                            ],

                            true,

                            false,
                        ],

                        paint: {
                            "line-color":
                                "#374151",

                            "line-width": [
                                "interpolate",

                                [
                                    "linear",
                                ],

                                ["zoom"],

                                10,
                                1,

                                13,
                                2,

                                16,
                                4,
                            ],

                            "line-opacity":
                                0.9,
                        },
                    });

                    /* ====================================================== */
                    /* SECONDARY ROADS                                         */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "roads-secondary",

                        type: "line",

                        source: "roads",

                        filter: [
                            "match",

                            [
                                "get",
                                "highway",
                            ],

                            [
                                "secondary",
                                "secondary_link",
                                "tertiary",
                                "tertiary_link",
                            ],

                            true,

                            false,
                        ],

                        paint: {
                            "line-color":
                                "#293241",

                            "line-width": [
                                "interpolate",

                                [
                                    "linear",
                                ],

                                ["zoom"],

                                10,
                                0.7,

                                13,
                                1.4,

                                16,
                                2.5,
                            ],

                            "line-opacity":
                                0.8,
                        },
                    });

                    /* ====================================================== */
                    /* LOCAL ROADS                                             */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "roads-local",

                        type: "line",

                        source: "roads",

                        filter: [
                            "match",

                            [
                                "get",
                                "highway",
                            ],

                            [
                                "residential",
                                "living_street",
                                "unclassified",
                                "service",
                            ],

                            true,

                            false,
                        ],

                        paint: {
                            "line-color":
                                "#202938",

                            "line-width": [
                                "interpolate",

                                [
                                    "linear",
                                ],

                                ["zoom"],

                                10,
                                0.4,

                                13,
                                0.8,

                                16,
                                1.5,
                            ],

                            "line-opacity":
                                0.65,
                        },
                    });

                    /* ====================================================== */
                    /* BUILDING FILL                                           */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "buildings-fill",

                        type: "fill",

                        source: "buildings",

                        paint: {
                            /*
                             * Color:
                             *
                             * Demo building:
                             * slightly lighter blue.
                             *
                             * Selected building:
                             * bright cyan.
                             *
                             * Normal buildings:
                             * normal blue.
                             */
                            "fill-color": [
                                "case",

                                [
                                    "==",

                                    [
                                        "get",
                                        "building_id",
                                    ],

                                    DEMO_BUILDING_ID,
                                ],

                                "#4f8fcf",

                                [
                                    "boolean",

                                    [
                                        "feature-state",
                                        "selected",
                                    ],

                                    false,
                                ],

                                "#38bdf8",

                                "#3b82f6",
                            ],

                            /*
                             * Opacity:
                             *
                             * Demo building:
                             * only slightly more visible.
                             */
                            "fill-opacity": [
                                "case",

                                [
                                    "==",

                                    [
                                        "get",
                                        "building_id",
                                    ],

                                    DEMO_BUILDING_ID,
                                ],

                                0.45,

                                [
                                    "boolean",

                                    [
                                        "feature-state",
                                        "selected",
                                    ],

                                    false,
                                ],

                                0.8,

                                0.38,
                            ],
                        },
                    });

                    /* ====================================================== */
                    /* BUILDING OUTLINE                                        */
                    /* ====================================================== */

                    instance.addLayer({
                        id: "buildings-outline",

                        type: "line",

                        source: "buildings",

                        paint: {
                            /*
                             * Demo site gets a very subtle
                             * cyan outline.
                             */
                            "line-color": [
                                "case",

                                [
                                    "==",

                                    [
                                        "get",
                                        "building_id",
                                    ],

                                    DEMO_BUILDING_ID,
                                ],

                                "#7dd3fc",

                                [
                                    "boolean",

                                    [
                                        "feature-state",
                                        "selected",
                                    ],

                                    false,
                                ],

                                "#e0f2fe",

                                "#60a5fa",
                            ],

                            "line-width": [
                                "case",

                                /*
                                 * Demo building.
                                 */
                                [
                                    "==",

                                    [
                                        "get",
                                        "building_id",
                                    ],

                                    DEMO_BUILDING_ID,
                                ],

                                1.5,

                                /*
                                 * Selected building.
                                 */
                                [
                                    "boolean",

                                    [
                                        "feature-state",
                                        "selected",
                                    ],

                                    false,
                                ],

                                2.5,

                                /*
                                 * Normal buildings.
                                 */
                                0.8,
                            ],

                            "line-opacity": [
                                "case",

                                [
                                    "==",

                                    [
                                        "get",
                                        "building_id",
                                    ],

                                    DEMO_BUILDING_ID,
                                ],

                                0.8,

                                [
                                    "boolean",

                                    [
                                        "feature-state",
                                        "selected",
                                    ],

                                    false,
                                ],

                                1,

                                0.7,
                            ],
                        },
                    });

                    /* ====================================================== */
                    /* FIT MAP TO BUILDINGS                                    */
                    /* ====================================================== */

                    const bounds =
                        new maplibregl.LngLatBounds();

                    buildingFeatures.forEach(
                        (feature) => {
                            extendGeometryBounds(
                                bounds,
                                feature.geometry
                            );
                        }
                    );

                    if (!bounds.isEmpty()) {
                        instance.fitBounds(
                            bounds,
                            {
                                padding: 50,

                                duration: 0,

                                maxZoom: 14,
                            }
                        );
                    }

                    /* ====================================================== */
                    /* BUILDING HOVER                                         */
                    /* ====================================================== */

                    instance.on(
                        "mouseenter",
                        "buildings-fill",
                        () => {
                            instance.getCanvas().style.cursor =
                                "pointer";
                        }
                    );

                    instance.on(
                        "mouseleave",
                        "buildings-fill",
                        () => {
                            instance.getCanvas().style.cursor =
                                "";
                        }
                    );

                    /* ====================================================== */
                    /* BUILDING CLICK                                          */
                    /* ====================================================== */

                    instance.on(
                        "click",
                        "buildings-fill",
                        (
                            event: MapLayerMouseEvent
                        ) => {
                            const feature =
                                event.features?.[0];

                            if (!feature) {
                                return;
                            }

                            /* ---------------------------------------------- */
                            /* CLEAR PREVIOUS SELECTION                       */
                            /* ---------------------------------------------- */

                            if (
                                selectedFeatureId.current !==
                                null
                            ) {
                                instance.setFeatureState(
                                    {
                                        source:
                                            "buildings",

                                        id:
                                            selectedFeatureId.current,
                                    },

                                    {
                                        selected:
                                            false,
                                    }
                                );
                            }

                            /* ---------------------------------------------- */
                            /* GET BUILDING ID                                 */
                            /* ---------------------------------------------- */

                            const buildingId =
                                String(
                                    feature
                                        .properties
                                        ?.building_id ??
                                    feature.id
                                );

                            /* ---------------------------------------------- */
                            /* SELECT BUILDING                                 */
                            /* ---------------------------------------------- */

                            instance.setFeatureState(
                                {
                                    source:
                                        "buildings",

                                    id:
                                        buildingId,
                                },

                                {
                                    selected:
                                        true,
                                }
                            );

                            selectedFeatureId.current =
                                buildingId;

                            /* ---------------------------------------------- */
                            /* EXTRACT PROPERTIES                              */
                            /* ---------------------------------------------- */

                            const properties =
                                feature.properties ??
                                {};

                            const building:
                                SelectedBuilding =
                            {
                                building_id:
                                    buildingId,

                                osm_id:
                                    properties.osm_id ??
                                    buildingId,

                                name:
                                    properties.name ||
                                    null,

                                building_type:
                                    properties.building_type ||
                                    null,

                                levels:
                                    properties.levels !==
                                        null &&
                                        properties.levels !==
                                        undefined &&
                                        properties.levels !==
                                        ""
                                        ? Number(
                                            properties.levels
                                        )
                                        : null,

                                height:
                                    properties.height !==
                                        null &&
                                        properties.height !==
                                        undefined &&
                                        properties.height !==
                                        ""
                                        ? Number(
                                            properties.height
                                        )
                                        : null,

                                status:
                                    properties.status ??
                                    "HEALTHY",
                            };

                            setSelectedBuilding(
                                building
                            );

                            /* ---------------------------------------------- */
                            /* ZOOM TO BUILDING                                */
                            /* ---------------------------------------------- */

                            const selectedBounds =
                                new maplibregl.LngLatBounds();

                            extendGeometryBounds(
                                selectedBounds,
                                feature.geometry
                            );

                            if (
                                !selectedBounds.isEmpty()
                            ) {
                                instance.fitBounds(
                                    selectedBounds,
                                    {
                                        padding: {
                                            top: 100,

                                            bottom: 100,

                                            left: 100,

                                            /*
                                             * Leave space for
                                             * the right-side
                                             * building panel.
                                             */
                                            right: 430,
                                        },

                                        maxZoom: 17,

                                        duration: 700,
                                    }
                                );
                            }
                        }
                    );

                    /* ====================================================== */
                    /* EMPTY MAP CLICK                                        */
                    /* ====================================================== */

                    instance.on(
                        "click",
                        (
                            event: MapMouseEvent
                        ) => {
                            const features =
                                instance.queryRenderedFeatures(
                                    event.point,

                                    {
                                        layers: [
                                            "buildings-fill",
                                        ],
                                    }
                                );

                            /*
                             * If we clicked a building,
                             * let the building click handler
                             * handle it.
                             */
                            if (
                                features.length >
                                0
                            ) {
                                return;
                            }

                            /* ---------------------------------------------- */
                            /* CLEAR SELECTION                                */
                            /* ---------------------------------------------- */

                            if (
                                selectedFeatureId.current !==
                                null
                            ) {
                                instance.setFeatureState(
                                    {
                                        source:
                                            "buildings",

                                        id:
                                            selectedFeatureId.current,
                                    },

                                    {
                                        selected:
                                            false,
                                    }
                                );
                            }

                            selectedFeatureId.current =
                                null;

                            setSelectedBuilding(
                                null
                            );
                        }
                    );

                    /* ------------------------------------------------------ */
                    /* MAP READY                                              */
                    /* ------------------------------------------------------ */

                    setMapReady(true);

                    console.log(
                        "AEGIS3D CITY MAP LOADED"
                    );
                } catch (error) {
                    console.error(
                        "Failed to initialize Aegis3D city map:",
                        error
                    );
                }
            }
        );

        /* ------------------------------------------------------------------ */
        /* CLEANUP                                                            */
        /* ------------------------------------------------------------------ */

        return () => {
            instance.remove();

            map.current = null;
        };
    }, []);

    /* ---------------------------------------------------------------------- */
    /* CLOSE BUILDING PANEL                                                  */
    /* ---------------------------------------------------------------------- */

    const closeBuildingPanel = () => {
        if (
            map.current &&
            selectedFeatureId.current !==
            null
        ) {
            map.current.setFeatureState(
                {
                    source: "buildings",

                    id:
                        selectedFeatureId.current,
                },

                {
                    selected: false,
                }
            );
        }

        selectedFeatureId.current = null;

        setSelectedBuilding(null);
    };

    /* ---------------------------------------------------------------------- */
    /* RENDER                                                                 */
    /* ---------------------------------------------------------------------- */

    return (
        <div
            style={{
                position: "relative",

                width: "100%",

                height: "100%",

                overflow: "hidden",

                background:
                    "#0b1220",
            }}
        >
            {/* ============================================================= */}
            {/* MAP                                                           */}
            {/* ============================================================= */}

            <div
                ref={mapContainer}
                style={{
                    position: "absolute",

                    inset: 0,
                }}
            />

            {/* ============================================================= */}
            {/* MAP LOADING INDICATOR                                         */}
            {/* ============================================================= */}

            {!mapReady && (
                <div
                    style={{
                        position:
                            "absolute",

                        top: 20,

                        left: 20,

                        padding:
                            "8px 12px",

                        borderRadius: 8,

                        background:
                            "rgba(15, 23, 42, 0.85)",

                        border:
                            "1px solid rgba(148, 163, 184, 0.15)",

                        color:
                            "#94a3b8",

                        fontSize: 12,

                        backdropFilter:
                            "blur(8px)",

                        zIndex: 10,
                    }}
                >
                    Loading Aegis3D city map...
                </div>
            )}

            {/* ============================================================= */}
            {/* BUILDING INFORMATION PANEL                                    */}
            {/* ============================================================= */}

            {selectedBuilding && (
                <div
                    style={{
                        position:
                            "absolute",

                        top: 80,

                        right: 20,

                        width: 330,

                        padding: 20,

                        borderRadius: 12,

                        background:
                            "rgba(15, 23, 42, 0.94)",

                        border:
                            "1px solid rgba(148, 163, 184, 0.18)",

                        boxShadow:
                            "0 20px 50px rgba(0, 0, 0, 0.35)",

                        backdropFilter:
                            "blur(14px)",

                        color:
                            "#e2e8f0",

                        zIndex: 20,
                    }}
                >
                    {/* ----------------------------------------------------- */}
                    {/* PANEL HEADER                                           */}
                    {/* ----------------------------------------------------- */}

                    <div
                        style={{
                            display:
                                "flex",

                            alignItems:
                                "flex-start",

                            justifyContent:
                                "space-between",

                            gap: 12,

                            marginBottom:
                                18,
                        }}
                    >
                        <div>
                            <div
                                style={{
                                    fontSize:
                                        11,

                                    fontWeight:
                                        600,

                                    letterSpacing:
                                        "0.12em",

                                    color:
                                        selectedBuilding.building_id ===
                                            DEMO_BUILDING_ID
                                            ? "#67e8f9"
                                            : "#64748b",

                                    marginBottom:
                                        6,
                                }}
                            >
                                {selectedBuilding.building_id ===
                                    DEMO_BUILDING_ID
                                    ? "AEGIS3D DEMONSTRATION SITE"
                                    : "BUILDING SELECTED"}
                            </div>

                            <div
                                style={{
                                    fontSize:
                                        20,

                                    fontWeight:
                                        600,

                                    color:
                                        "#f8fafc",
                                }}
                            >
                                {selectedBuilding.name ??
                                    "Unnamed Building"}
                            </div>
                        </div>

                        <button
                            onClick={
                                closeBuildingPanel
                            }
                            aria-label="Close"
                            style={{
                                border:
                                    "none",

                                background:
                                    "transparent",

                                color:
                                    "#64748b",

                                fontSize:
                                    20,

                                cursor:
                                    "pointer",

                                lineHeight:
                                    1,

                                padding: 0,
                            }}
                        >
                            ×
                        </button>
                    </div>

                    {/* ----------------------------------------------------- */}
                    {/* STATUS BADGE                                          */}
                    {/* ----------------------------------------------------- */}

                    <div
                        style={{
                            display:
                                "inline-flex",

                            alignItems:
                                "center",

                            gap: 7,

                            padding:
                                "5px 9px",

                            borderRadius:
                                999,

                            background:
                                "rgba(34, 197, 94, 0.10)",

                            border:
                                "1px solid rgba(34, 197, 94, 0.18)",

                            color:
                                "#86efac",

                            fontSize:
                                11,

                            fontWeight:
                                600,

                            marginBottom:
                                18,
                        }}
                    >
                        <span
                            style={{
                                width: 6,

                                height: 6,

                                borderRadius:
                                    "50%",

                                background:
                                    "#4ade80",
                            }}
                        />

                        {
                            selectedBuilding.status
                        }
                    </div>

                    {/* ----------------------------------------------------- */}
                    {/* BUILDING DETAILS                                      */}
                    {/* ----------------------------------------------------- */}

                    <div
                        style={{
                            display:
                                "grid",

                            gap: 12,
                        }}
                    >
                        {/* Type */}

                        <div
                            style={{
                                display:
                                    "flex",

                                justifyContent:
                                    "space-between",

                                gap: 20,
                            }}
                        >
                            <span
                                style={{
                                    color:
                                        "#64748b",

                                    fontSize:
                                        12,
                                }}
                            >
                                Type
                            </span>

                            <span
                                style={{
                                    color:
                                        "#cbd5e1",

                                    fontSize:
                                        12,
                                }}
                            >
                                {
                                    selectedBuilding.building_type ??
                                    "Unknown"
                                }
                            </span>
                        </div>

                        {/* Levels */}

                        <div
                            style={{
                                display:
                                    "flex",

                                justifyContent:
                                    "space-between",

                                gap: 20,
                            }}
                        >
                            <span
                                style={{
                                    color:
                                        "#64748b",

                                    fontSize:
                                        12,
                                }}
                            >
                                Levels
                            </span>

                            <span
                                style={{
                                    color:
                                        "#cbd5e1",

                                    fontSize:
                                        12,
                                }}
                            >
                                {
                                    selectedBuilding.levels ??
                                    "Unknown"
                                }
                            </span>
                        </div>

                        {/* Height */}

                        <div
                            style={{
                                display:
                                    "flex",

                                justifyContent:
                                    "space-between",

                                gap: 20,
                            }}
                        >
                            <span
                                style={{
                                    color:
                                        "#64748b",

                                    fontSize:
                                        12,
                                }}
                            >
                                Height
                            </span>

                            <span
                                style={{
                                    color:
                                        "#cbd5e1",

                                    fontSize:
                                        12,
                                }}
                            >
                                {selectedBuilding.height !==
                                    null
                                    ? `${selectedBuilding.height} m`
                                    : "Unknown"}
                            </span>
                        </div>

                        {/* OSM ID */}

                        <div
                            style={{
                                display:
                                    "flex",

                                justifyContent:
                                    "space-between",

                                gap: 20,
                            }}
                        >
                            <span
                                style={{
                                    color:
                                        "#64748b",

                                    fontSize:
                                        12,
                                }}
                            >
                                OSM ID
                            </span>

                            <span
                                style={{
                                    color:
                                        "#94a3b8",

                                    fontSize:
                                        11,

                                    maxWidth:
                                        190,

                                    overflow:
                                        "hidden",

                                    textOverflow:
                                        "ellipsis",

                                    whiteSpace:
                                        "nowrap",
                                }}
                            >
                                {
                                    selectedBuilding.osm_id
                                }
                            </span>
                        </div>
                    </div>

                    {/* ----------------------------------------------------- */}
                    {/* DIVIDER                                               */}
                    {/* ----------------------------------------------------- */}

                    <div
                        style={{
                            height: 1,

                            background:
                                "rgba(148, 163, 184, 0.10)",

                            margin:
                                "20px 0",
                        }}
                    />

                    {/* ----------------------------------------------------- */}
                    {/* BIM SECTION                                            */}
                    {/* ----------------------------------------------------- */}

                    {selectedBuilding.building_id ===
                        DEMO_BUILDING_ID ? (
                        <>
                            <div
                                style={{
                                    fontSize:
                                        12,

                                    color:
                                        "#94a3b8",

                                    marginBottom:
                                        12,

                                    lineHeight:
                                        1.5,
                                }}
                            >
                                Structural BIM
                                digital twin
                                available for
                                this
                                demonstration
                                site.
                            </div>

                            <button
                                onClick={() => {
                                    setShowDigitalTwin(
                                        true
                                    );
                                }}
                                style={{
                                    width:
                                        "100%",

                                    padding:
                                        "11px 14px",

                                    border:
                                        "1px solid rgba(103, 232, 249, 0.35)",

                                    borderRadius:
                                        8,

                                    background:
                                        "rgba(34, 211, 238, 0.10)",

                                    color:
                                        "#67e8f9",

                                    fontSize:
                                        12,

                                    fontWeight:
                                        600,

                                    cursor:
                                        "pointer",
                                }}
                            >
                                Open 3D Digital Twin
                            </button>
                        </>
                    ) : (
                        <>
                            <div
                                style={{
                                    fontSize:
                                        12,

                                    color:
                                        "#64748b",

                                    marginBottom:
                                        12,

                                    lineHeight:
                                        1.5,
                                }}
                            >
                                No structural
                                BIM model is
                                linked to this
                                building.
                            </div>

                            <button
                                disabled
                                style={{
                                    width:
                                        "100%",

                                    padding:
                                        "11px 14px",

                                    border:
                                        "1px solid rgba(148, 163, 184, 0.10)",

                                    borderRadius:
                                        8,

                                    background:
                                        "rgba(148, 163, 184, 0.05)",

                                    color:
                                        "#475569",

                                    fontSize:
                                        12,

                                    fontWeight:
                                        600,

                                    cursor:
                                        "not-allowed",
                                }}
                            >
                                No BIM Model Linked
                            </button>
                        </>
                    )}
                </div>
            )}

            {/* ============================================================= */}
            {/* DIGITAL TWIN                                                  */}
            {/* ============================================================= */}

            {showDigitalTwin && (
                <DigitalTwinViewer
                    onClose={() =>
                        setShowDigitalTwin(false)
                    }
                />
            )}
        </div>
    );
}