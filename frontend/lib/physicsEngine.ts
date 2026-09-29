/**
 * Aegis3D Reduced-Order Guided-Wave Physics Simulation Engine (Client-Side).
 *
 * Implements deterministic PZT actuator excitation, structural corridor propagation,
 * distance attenuation, acoustic travel time delay, structural discontinuity scattering,
 * and receiver acquisition scaling.
 *
 * Matches the mathematical specifications of simulator/physics/propagation.py,
 * damage.py, acquisition.py, and signal_generator.py.
 */

export interface CanonicalSensor {
    id: string;
    storey: string;
    ifcGuid: string;
    zoneId: number | null;
    zoneName: string | null;
    activeZone: boolean;
}

export interface ComponentInfluence {
    ifcGuid: string;
    distanceToPathM: number;
    pathPosition: number;
    influenceFactor: number;
}

export interface PropagationPathInfo {
    pathId: string;
    actuatorId: string;
    receiverId: string;
    distanceM: number;
    waveVelocityMS: number;
    attenuationDbPerM: number;
    componentGuids: string[];
    componentInfluences: ComponentInfluence[];
}

export interface SimulationResult {
    simulationId: string;
    timestamp: string;
    sourceSensor: string;
    receiverSensor: string;
    targetZoneName: string;
    targetZoneId: number | null;
    scenario: "normal" | "anomaly";
    pathId: string;
    distanceM: number;
    waveVelocityMS: number;
    propagationDelayS: number;
    propagationDelayMs: number;
    attenuationDb: number;
    amplitudeFactor: number;
    isDamaged: boolean;
    damagedComponentGuid: string | null;
    damagedComponentType: string;
    damageInfluenceFactor: number;
    primaryAttenuationMultiplier: number;
    primaryDelayShiftSamples: number;
    scatteringAmplitude: number;
    scatteringDelayMs: number;
    scatteringDelaySamples: number;
    sampleRateHz: number;
    sampleCount: number;
    excitationSamples: number[];
    primaryPropagatedSamples: number[];
    scatteredSamples: number[];
    receivedSamples: number[];
    simPeak: number;
    detectionThresholdExpected: number;
    telemetryPayload: any;
    backendResponse: any | null;
    telemetryStatus: "IDLE" | "TRANSMITTING" | "ACCEPTED" | "FAILED";
    telemetryError: string | null;
}

// 12 Canonical Aegis3D Sensors from BIM Registry
export const CANONICAL_SENSORS: CanonicalSensor[] = [
    { id: "PZT-Z01", storey: "01 - Entry Level", ifcGuid: "2Ci2k7uxXCqAqqsxOmESOv", zoneId: 2, zoneName: "Zone 2 - Substructure Pier B", activeZone: true },
    { id: "PZT-Z02", storey: "01 - Entry Level", ifcGuid: "18YHwga450Mw4Fy6M5t_8F", zoneId: 2, zoneName: "Zone 2 - Substructure Pier B", activeZone: true },
    { id: "PZT-Z03", storey: "01 - Entry Level", ifcGuid: "18YHwga450Mw4Fy6M5t_8d", zoneId: 2, zoneName: "Zone 2 - Substructure Pier B", activeZone: true },
    { id: "PZT-Z04", storey: "01 - Entry Level", ifcGuid: "18YHwga450Mw4Fy6M5t_8h", zoneId: 2, zoneName: "Zone 2 - Substructure Pier B", activeZone: true },
    { id: "PZT-Z05", storey: "02 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzBI", zoneId: 1, zoneName: "Zone 1 - Main Deck Girder", activeZone: true },
    { id: "PZT-Z06", storey: "02 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzBt", zoneId: 1, zoneName: "Zone 1 - Main Deck Girder", activeZone: true },
    { id: "PZT-Z07", storey: "02 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzBw", zoneId: 1, zoneName: "Zone 1 - Main Deck Girder", activeZone: true },
    { id: "PZT-Z08", storey: "02 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzB8", zoneId: 1, zoneName: "Zone 1 - Main Deck Girder", activeZone: true },
    { id: "PZT-Z09", storey: "03 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzCE", zoneId: null, zoneName: null, activeZone: false },
    { id: "PZT-Z10", storey: "03 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzCZ", zoneId: null, zoneName: null, activeZone: false },
    { id: "PZT-Z11", storey: "03 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzCs", zoneId: null, zoneName: null, activeZone: false },
    { id: "PZT-Z12", storey: "03 - Floor", ifcGuid: "2UD3D7uxP8kecbbBCRtzC4", zoneId: null, zoneName: null, activeZone: false },
];

// Fixed Reduced-Order Propagation Paths from BIM Model
export const CANONICAL_PATHS: PropagationPathInfo[] = [
    {
        pathId: "PATH-007",
        actuatorId: "PZT-Z04",
        receiverId: "PZT-Z05",
        distanceM: 16.30,
        waveVelocityMS: 3200.0,
        attenuationDbPerM: 0.8,
        componentGuids: ["2UD3D7uxP8kecbbBCRtz8h", "1WrzGm1SD2ev45B_OWQ3El", "2UD3D7uxP8kecbbBCRtzBI"],
        componentInfluences: [
            { ifcGuid: "1WrzGm1SD2ev45B_OWQ3El", distanceToPathM: 0.45, pathPosition: 0.52, influenceFactor: 0.6958 }
        ]
    },
    {
        pathId: "PATH-001",
        actuatorId: "PZT-Z01",
        receiverId: "PZT-Z08",
        distanceM: 9.60,
        waveVelocityMS: 3200.0,
        attenuationDbPerM: 0.8,
        componentGuids: ["2Ci2k7uxXCqAqqsxOmESOv", "17qC4eX$v65AOIXuxtQbmR", "2UD3D7uxP8kecbbBCRtzB8"],
        componentInfluences: [
            { ifcGuid: "17qC4eX$v65AOIXuxtQbmR", distanceToPathM: 0.50, pathPosition: 0.35, influenceFactor: 0.6626 }
        ]
    },
    {
        pathId: "PATH-003",
        actuatorId: "PZT-Z02",
        receiverId: "PZT-Z07",
        distanceM: 3.80,
        waveVelocityMS: 3200.0,
        attenuationDbPerM: 0.8,
        componentGuids: ["18YHwga450Mw4Fy6M5t_8F", "2UD3D7uxP8kecbbBCRtzBw"],
        componentInfluences: []
    },
    {
        pathId: "PATH-005",
        actuatorId: "PZT-Z03",
        receiverId: "PZT-Z06",
        distanceM: 3.80,
        waveVelocityMS: 3200.0,
        attenuationDbPerM: 0.8,
        componentGuids: ["18YHwga450Mw4Fy6M5t_8d", "2UD3D7uxP8kecbbBCRtzBt"],
        componentInfluences: []
    }
];

export const FIXED_DAMAGED_COMPONENT = {
    guid: "1WrzGm1SD2ev45B_OWQ3El",
    type: "IfcBeam",
    name: "Girder Shear Discontinuity Flange B",
    pathId: "PATH-007",
    influence: 0.6958,
};

/**
 * Generate a Hann-windowed PZT tone burst excitation waveform.
 * Matches simulator/signal_generator.py:generate_pzt_tone_burst.
 */
export function generatePztToneBurst(
    sampleCount: number = 10000,
    sampleRateHz: number = 100000.0,
    frequencyHz: number = 10000.0,
    amplitude: number = 0.8,
    cycles: number = 5
): number[] {
    const burstDurationS = cycles / frequencyHz;
    const burstSamples = Math.min(
        sampleCount,
        Math.max(1, Math.round(burstDurationS * sampleRateHz))
    );

    const signal = new Float64Array(sampleCount);
    for (let i = 0; i < burstSamples; i++) {
        const t = i / sampleRateHz;
        const carrier = Math.sin(2.0 * Math.PI * frequencyHz * t);
        // Hann window: 0.5 * (1 - cos(2*pi*i / N))
        const window = burstSamples > 1
            ? 0.5 * (1.0 - Math.cos((2.0 * Math.PI * i) / (burstSamples - 1)))
            : 1.0;
        signal[i] = amplitude * carrier * window;
    }

    return Array.from(signal);
}

/**
 * Run deterministic guided-wave propagation simulation through structural path.
 * Matches simulator/physics/propagation.py and damage.py.
 */
export function simulatePhysicsPropagation(
    path: PropagationPathInfo,
    scenario: "normal" | "anomaly",
    receiverGain: number = 5.0,
    sampleCount: number = 10000,
    sampleRateHz: number = 100000.0
): {
    excitation: number[];
    primaryPropagated: number[];
    scattered: number[];
    received: number[];
    delayS: number;
    delayMs: number;
    attenuationDb: number;
    amplitudeFactor: number;
    attenuationMultiplier: number;
    delayShiftSamples: number;
    scatteringAmplitude: number;
    scatteringDelaySamples: number;
    scatteringDelayMs: number;
} {
    // 1. Excitation (Hann tone burst)
    const excitation = generatePztToneBurst(sampleCount, sampleRateHz, 10000.0, 0.8, 5);

    // 2. Primary Propagation Parameters
    const delayS = path.distanceM / path.waveVelocityMS;
    const delayMs = delayS * 1000.0;
    const attenuationDb = path.attenuationDbPerM * path.distanceM;
    const amplitudeFactor = Math.pow(10.0, -attenuationDb / 20.0);

    const nominalDelaySamples = Math.round(delayS * sampleRateHz);

    // 3. Damage State Evaluation
    let attenuationMultiplier = 1.0;
    let delayShiftSamples = 0;
    let scatteringAmplitude = 0.0;
    let scatteringDelaySamples = 0;
    let scatteringDelayMs = 0.0;

    if (scenario === "anomaly") {
        let influence = 0.0;
        for (const comp of path.componentInfluences) {
            if (comp.ifcGuid === FIXED_DAMAGED_COMPONENT.guid) {
                influence = comp.influenceFactor;
                break;
            }
        }
        if (influence <= 0.0 && path.pathId === "PATH-007") {
            influence = FIXED_DAMAGED_COMPONENT.influence;
        }

        if (influence > 0.0) {
            // Damage attenuation on primary wave (weakened transmission)
            attenuationMultiplier = Math.max(0.05, 1.0 - 0.25 * influence);
            delayShiftSamples = Math.round(3 * influence);
            // Secondary scattering wave packet
            scatteringAmplitude = 0.65 * influence;
            scatteringDelayMs = 1.0; // 1.0 ms relative arrival delay
            scatteringDelaySamples = Math.max(1, Math.round(scatteringDelayMs * 0.001 * sampleRateHz));
        }
    }

    const totalPrimaryDelay = nominalDelaySamples + delayShiftSamples;
    const primaryPropagated = new Float64Array(sampleCount + totalPrimaryDelay);

    // Populate Primary Propagated Waveform
    for (let i = 0; i < excitation.length; i++) {
        primaryPropagated[i + totalPrimaryDelay] += excitation[i] * amplitudeFactor * attenuationMultiplier;
    }

    // Populate Localized Secondary Scattering Waveform
    const scattered = new Float64Array(sampleCount + totalPrimaryDelay + scatteringDelaySamples);
    if (scatteringAmplitude > 0.0) {
        const scatteringStart = totalPrimaryDelay + scatteringDelaySamples;
        // Localized scattering transfer coefficient (matches propagation.py)
        const scatteringTransferFactor = 1.05;

        for (let i = 0; i < excitation.length; i++) {
            const destIdx = i + scatteringStart;
            if (destIdx < scattered.length) {
                scattered[destIdx] += excitation[i] * scatteringAmplitude * scatteringTransferFactor;
            }
        }
    }

    // Combined Raw Propagated Signal before Receiver Scaling
    const maxLen = Math.max(primaryPropagated.length, scattered.length);
    const combinedPropagated = new Float64Array(maxLen);
    for (let i = 0; i < primaryPropagated.length; i++) {
        combinedPropagated[i] += primaryPropagated[i];
    }
    for (let i = 0; i < scattered.length; i++) {
        combinedPropagated[i] += scattered[i];
    }

    // Apply Receiver/Acquisition Scaling (5.0x)
    const received = new Float64Array(maxLen);
    for (let i = 0; i < maxLen; i++) {
        received[i] = combinedPropagated[i] * receiverGain;
    }

    const primaryScaled = Array.from(primaryPropagated).map(v => v * receiverGain);
    const scatteredScaled = Array.from(scattered).map(v => v * receiverGain);

    return {
        excitation,
        primaryPropagated: primaryScaled,
        scattered: scatteredScaled,
        received: Array.from(received),
        delayS,
        delayMs,
        attenuationDb,
        amplitudeFactor,
        attenuationMultiplier,
        delayShiftSamples,
        scatteringAmplitude,
        scatteringDelaySamples,
        scatteringDelayMs,
    };
}
