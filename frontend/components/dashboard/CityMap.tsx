"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

export default function CityMap() {
    const mapContainer = useRef<HTMLDivElement | null>(null);
    const map = useRef<maplibregl.Map | null>(null);

    useEffect(() => {
        if (!mapContainer.current || map.current) return;

        map.current = new maplibregl.Map({
            container: mapContainer.current,

            style: {
                version: 8,
                sources: {},
                layers: [
                    {
                        id: "background",
                        type: "background",
                        paint: {
                            "background-color": "#111827",
                        },
                    },
                ],
            },

            center: [77.21, 28.63],
            zoom: 13,
        });

        map.current.addControl(
            new maplibregl.NavigationControl(),
            "top-right"
        );

        map.current.on("load", async () => {
            console.log("MAPLIBRE LOADED — loading building data");

            const response = await fetch("/data/delhi_buildings.json");

            if (!response.ok) {
                throw new Error("Failed to load Delhi building data");
            }

            const dataset = await response.json();

            console.log("RAW DATASET:", dataset);
            console.log("BUILDING COUNT:", dataset.buildings?.length);

            /*
             * Our processed Aegis3D dataset is wrapped like:
             *
             * {
             *   metadata: {...},
             *   buildings: [...]
             * }
             *
             * MapLibre expects a GeoJSON FeatureCollection,
             * so convert our buildings into GeoJSON Features.
             */

            const geojson = {
                type: "FeatureCollection" as const,

                features: dataset.buildings.map((building: any) => ({
                    type: "Feature" as const,

                    id: building.building_id,

                    properties: {
                        building_id: building.building_id,
                        osm_id: building.osm_id,
                        name: building.name,
                        building_type: building.building_type,
                        levels: building.levels,
                        height: building.height,
                        status: building.status,
                    },

                    geometry: building.geometry,
                })),
            };

            console.log(
                "GEOJSON FEATURES:",
                geojson.features.length
            );

            const bounds = new maplibregl.LngLatBounds();

            geojson.features.forEach((feature: any) => {
                const geometry = feature.geometry;

                if (!geometry) return;

                if (geometry.type === "Polygon") {
                    geometry.coordinates[0].forEach(
                        ([lng, lat]: [number, number]) => {
                            bounds.extend([lng, lat]);
                        }
                    );
                }

                if (geometry.type === "MultiPolygon") {
                    geometry.coordinates.forEach((polygon: any) => {
                        polygon[0].forEach(
                            ([lng, lat]: [number, number]) => {
                                bounds.extend([lng, lat]);
                            }
                        );
                    });
                }
            });

            if (!bounds.isEmpty()) {
                map.current?.fitBounds(bounds, {
                    padding: 60,
                    duration: 0,
                });
            }

            map.current?.addSource("buildings", {
                type: "geojson",
                data: geojson,
            });

            map.current?.addLayer({
                id: "building-fills",
                type: "fill",
                source: "buildings",

                paint: {
                    "fill-color": "#3b82f6",
                    "fill-opacity": 0.55,
                },
            });

            map.current?.addLayer({
                id: "building-outlines",
                type: "line",
                source: "buildings",

                paint: {
                    "line-color": "#60a5fa",
                    "line-width": 1,
                },
            });

            console.log("BUILDING DATA LOADED");
        });

        return () => {
            map.current?.remove();
            map.current = null;
        };
    }, []);

    return (
        <div
            ref={mapContainer}
            style={{
                width: "100%",
                height: "100%",
            }}
        />
    );
}