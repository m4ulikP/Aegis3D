"""
Reduced-order structural damage model for Aegis3D.

The model represents a fixed structural anomaly selected by IFC GUID.
It does not represent experimentally calibrated damage mechanics or
finite-element analysis.

The damage model modifies propagation characteristics based on the
geometric influence of the selected component on a propagation path.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DamageEffect:
    """
    Propagation perturbation caused by the selected damaged component.

    attenuation_multiplier:
        Multiplier applied to the primary propagated waveform.

    delay_shift_samples:
        Additional arrival delay applied to the primary waveform.

    scattering_amplitude:
        Relative amplitude of the secondary scattered response.

    scattering_delay_samples:
        Additional delay between the primary arrival and the
        secondary scattered response.
    """

    attenuation_multiplier: float
    delay_shift_samples: int
    scattering_amplitude: float
    scattering_delay_samples: int


class DamageModel:
    """
    Selectable single-component anomaly model.

    Only one component can be selected as damaged at a time.
    """

    def __init__(
        self,
        attenuation_strength: float = 0.25,
        max_delay_shift_samples: int = 3,
        max_scattering_amplitude: float = 0.65,
        scattering_delay_ms: float = 1.0,
    ) -> None:

        if not 0.0 <= attenuation_strength <= 1.0:
            raise ValueError(
                "attenuation_strength must be between 0 and 1"
            )

        if max_delay_shift_samples < 0:
            raise ValueError(
                "max_delay_shift_samples cannot be negative"
            )

        if not 0.0 <= max_scattering_amplitude <= 1.0:
            raise ValueError(
                "max_scattering_amplitude must be between 0 and 1"
            )

        if scattering_delay_ms <= 0.0:
            raise ValueError(
                "scattering_delay_ms must be positive"
            )

        self.attenuation_strength = attenuation_strength
        self.max_delay_shift_samples = max_delay_shift_samples
        self.max_scattering_amplitude = max_scattering_amplitude
        self.scattering_delay_ms = scattering_delay_ms

        self._damaged_component_guid: Optional[str] = None

    @property
    def damaged_component_guid(self) -> Optional[str]:
        return self._damaged_component_guid

    def set_damaged_component(self, ifc_guid: str) -> None:
        """Select the single IFC component used for the anomaly."""

        if not ifc_guid:
            raise ValueError(
                "ifc_guid cannot be empty"
            )

        self._damaged_component_guid = ifc_guid

    def clear_damaged_component(self) -> None:
        """Return the simulation to the healthy structural state."""

        self._damaged_component_guid = None

    def is_active(self) -> bool:
        return self._damaged_component_guid is not None

    def get_path_effect(
        self,
        component_influences: list[dict],
        sample_rate_hz: float = 100000.0,
    ) -> DamageEffect:
        """
        Calculate the anomaly effect on one propagation path.

        component_influences must come from the fixed
        propagation_network.json metadata.

        The geometric influence controls how strongly the selected
        damaged component affects this path.
        """

        if sample_rate_hz <= 0:
            raise ValueError(
                f"sample_rate_hz must be positive, got {sample_rate_hz}"
            )

        # Healthy path.
        if not self.is_active():
            return DamageEffect(
                attenuation_multiplier=1.0,
                delay_shift_samples=0,
                scattering_amplitude=0.0,
                scattering_delay_samples=0,
            )

        selected_guid = self._damaged_component_guid

        influence = 0.0

        for component in component_influences:
            if component["ifc_guid"] == selected_guid:
                influence = float(
                    component["influence_factor"]
                )
                break

        # The selected component does not influence this path.
        if influence <= 0.0:
            return DamageEffect(
                attenuation_multiplier=1.0,
                delay_shift_samples=0,
                scattering_amplitude=0.0,
                scattering_delay_samples=0,
            )

        # ---------------------------------------------------------
        # Primary-wave perturbation
        # ---------------------------------------------------------

        attenuation_multiplier = (
            1.0
            - self.attenuation_strength * influence
        )

        delay_shift_samples = round(
            self.max_delay_shift_samples * influence
        )

        # ---------------------------------------------------------
        # Secondary scattered response
        # ---------------------------------------------------------

        scattering_amplitude = (
            self.max_scattering_amplitude * influence
        )

        scattering_delay_samples = max(
            1,
            round(
                self.scattering_delay_ms
                * 0.001
                * sample_rate_hz
            ),
        )

        return DamageEffect(
            attenuation_multiplier=max(
                0.05,
                attenuation_multiplier,
            ),
            delay_shift_samples=delay_shift_samples,
            scattering_amplitude=scattering_amplitude,
            scattering_delay_samples=scattering_delay_samples,
        )

    def describe(self) -> str:
        if not self.is_active():
            return "Healthy structural state"

        return (
            "Structural anomaly selected at IFC component "
            f"{self._damaged_component_guid}"
        )