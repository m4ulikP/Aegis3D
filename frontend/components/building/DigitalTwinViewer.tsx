"use client";

import { Canvas, useThree } from "@react-three/fiber";
import {
    OrbitControls,
    useGLTF,
} from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

interface DigitalTwinViewerProps {
    onClose: () => void;
}

/* =========================================================
   BUILDING
========================================================= */

function BuildingModel() {
    const { scene } = useGLTF("/models/building_demo.glb");

    const model = useMemo(() => {
        const clonedScene = scene.clone(true);

        const box = new THREE.Box3().setFromObject(clonedScene);
        const center = box.getCenter(new THREE.Vector3());

        // Center horizontally only.
        // Keep the original vertical position.
        clonedScene.position.x -= center.x;
        clonedScene.position.z -= center.z;

        return clonedScene;
    }, [scene]);

    return <primitive object={model} />;
}

/* =========================================================
   STATIC FLOOR
========================================================= */

function StaticFloor() {
    return (
        <group position={[0, -0.01, 0]}>
            <gridHelper
                args={[200, 20, "#334155", "#1e293b"]}
                position={[0, 0.01, 0]}
            />
        </group>
    );
}

/* =========================================================
   PRELOAD
========================================================= */

useGLTF.preload("/models/building_demo.glb");

/* =========================================================
   VIEWER
========================================================= */

export default function DigitalTwinViewer({
    onClose,
}: DigitalTwinViewerProps) {
    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 1000,
                background: "#020617",
            }}
        >
            {/* =====================================================
          TOP BAR
      ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 64,
                    zIndex: 10,

                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",

                    padding: "0 24px",

                    background:
                        "linear-gradient(to bottom, rgba(2,6,23,0.95), rgba(2,6,23,0.65))",

                    borderBottom:
                        "1px solid rgba(148,163,184,0.15)",

                    backdropFilter: "blur(10px)",
                }}
            >
                {/* Left */}

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 14,
                    }}
                >
                    <div
                        style={{
                            fontSize: 18,
                            fontWeight: 700,
                            letterSpacing: "0.08em",
                            color: "#f8fafc",
                        }}
                    >
                        AEGIS3D
                    </div>

                    <div
                        style={{
                            width: 1,
                            height: 22,
                            background:
                                "rgba(148,163,184,0.3)",
                        }}
                    />

                    <div
                        style={{
                            fontSize: 14,
                            color: "#94a3b8",
                        }}
                    >
                        Structural Digital Twin
                    </div>
                </div>

                {/* Right */}

                <button
                    onClick={onClose}
                    style={{
                        border:
                            "1px solid rgba(148,163,184,0.25)",

                        background:
                            "rgba(15,23,42,0.8)",

                        color: "#e2e8f0",

                        padding: "9px 16px",
                        borderRadius: 8,

                        fontSize: 13,
                        fontWeight: 500,

                        cursor: "pointer",
                    }}
                >
                    ← Back to City
                </button>
            </div>

            {/* =====================================================
          3D CANVAS
      ===================================================== */}

            <Canvas
                shadows
                dpr={[1, 2]}
                camera={{
                    position: [15, 12, 15],
                    fov: 45,
                    near: 0.1,
                    far: 5000,
                }}
                gl={{
                    antialias: true,
                }}
            >
                {/* Background */}

                <color
                    attach="background"
                    args={["#020617"]}
                />

                {/* =================================================
            LIGHTING
        ================================================= */}

                <ambientLight intensity={0.7} />

                <hemisphereLight
                    args={[
                        "#dbeafe",
                        "#0f172a",
                        1.2,
                    ]}
                />

                <directionalLight
                    castShadow
                    position={[30, 40, 20]}
                    intensity={2.2}
                    shadow-mapSize-width={2048}
                    shadow-mapSize-height={2048}
                />

                {/* =================================================
            MODEL
        ================================================= */}

                <BuildingModel />

                {/* =================================================
            STATIC FLOOR
        ================================================= */}

                <StaticFloor />

                {/* =================================================
            CAMERA CONTROLS
        ================================================= */}

                <OrbitControls
                    makeDefault
                    enableDamping
                    dampingFactor={0.08}
                    rotateSpeed={0.7}
                    panSpeed={1.5}
                    zoomSpeed={0.9}
                    minDistance={2}
                    maxDistance={500}
                    mouseButtons={{
                        LEFT: THREE.MOUSE.ROTATE,
                        MIDDLE: THREE.MOUSE.PAN,
                        RIGHT: THREE.MOUSE.PAN,
                    }}
                />
            </Canvas>

            {/* =====================================================
          CONTROL HINT
      ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    left: 20,

                    padding: "10px 14px",

                    background:
                        "rgba(15,23,42,0.8)",

                    border:
                        "1px solid rgba(148,163,184,0.15)",

                    borderRadius: 8,

                    color: "#94a3b8",
                    fontSize: 12,

                    backdropFilter: "blur(8px)",
                }}
            >
                <div>Left click · Rotate</div>
                <div>
                    Middle / Right click · Pan
                </div>
                <div>Scroll · Zoom</div>
            </div>

            {/* =====================================================
          STATUS
      ===================================================== */}

            <div
                style={{
                    position: "absolute",
                    bottom: 20,
                    right: 20,

                    display: "flex",
                    alignItems: "center",
                    gap: 8,

                    padding: "9px 13px",

                    background:
                        "rgba(15,23,42,0.8)",

                    border:
                        "1px solid rgba(148,163,184,0.15)",

                    borderRadius: 8,

                    color: "#cbd5e1",
                    fontSize: 12,

                    backdropFilter: "blur(8px)",
                }}
            >
                <div
                    style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: "#22c55e",
                        boxShadow:
                            "0 0 8px rgba(34,197,94,0.7)",
                    }}
                />

                Digital Twin Online
            </div>
        </div>
    );
}