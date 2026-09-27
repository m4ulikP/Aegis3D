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
            const response = await fetch("/data/delhi_buildings.json");

            if (!response.ok) {
                throw new Error("Failed to load Delhi building data");
            }

            const buildings = await response.json();

            map.current?.addSource("buildings", {
                type: "geojson",
                data: buildings,
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