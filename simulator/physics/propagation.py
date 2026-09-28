"""
Reduced-order guided-wave propagation model for Aegis3D.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class PropagationPath:
    """
    Reduced-order actuator-to-receiver structural propagation path.

    This is a physics-inspired model for the virtual sensor simulator.
    It is not a finite-element or experimentally calibrated model.
    """

    actuator_id: str
    receiver_id: str
    component_guids: Tuple[str, ...]
    distance_m: float
    wave_velocity_m_s: float
    attenuation_db_per_m: float = 0.8

    def __post_init__(self) -> None:
        if not self.actuator_id:
            raise ValueError("actuator_id cannot be empty")

        if not self.receiver_id:
            raise ValueError("receiver_id cannot be empty")

        if self.actuator_id == self.receiver_id:
            raise ValueError(
                "actuator_id and receiver_id must be different"
            )

        if self.distance_m <= 0:
            raise ValueError(
                f"distance_m must be positive, got {self.distance_m}"
            )

        if self.wave_velocity_m_s <= 0:
            raise ValueError(
                f"wave_velocity_m_s must be positive, "
                f"got {self.wave_velocity_m_s}"
            )

        if self.attenuation_db_per_m < 0:
            raise ValueError(
                "attenuation_db_per_m cannot be negative"
            )

    @property
    def propagation_delay_s(self) -> float:
        """Signal travel time in seconds."""
        return self.distance_m / self.wave_velocity_m_s

    @property
    def propagation_delay_ms(self) -> float:
        """Signal travel time in milliseconds."""
        return self.propagation_delay_s * 1000.0

    @property
    def attenuation_db(self) -> float:
        """Total attenuation across the path in decibels."""
        return self.attenuation_db_per_m * self.distance_m

    @property
    def amplitude_factor(self) -> float:
        """
        Convert total attenuation from dB to a linear amplitude factor.

        A_linear = 10^(-attenuation_db / 20)
        """
        return 10.0 ** (-self.attenuation_db / 20.0)

    def propagate(
        self,
        samples: list[float],
        sample_rate_hz: float,
        damage_effect: Optional[object] = None,
    ) -> list[float]:
        """
        Propagate a sampled waveform through this structural path.

        Normal propagation applies:
        - amplitude attenuation
        - propagation delay

        A DamageEffect additionally applies:
        - primary-wave attenuation
        - primary arrival delay
        - secondary scattered response

        The damage model is a reduced-order simulation abstraction
        and is not experimentally calibrated.
        """

        if sample_rate_hz <= 0:
            raise ValueError(
                f"sample_rate_hz must be positive, got {sample_rate_hz}"
            )

        if not samples:
            return []

        # ---------------------------------------------------------
        # Primary propagation
        # ---------------------------------------------------------

        delay_samples = round(
            self.propagation_delay_s * sample_rate_hz
        )

        amplitude = self.amplitude_factor

        damage_attenuation = 1.0
        damage_delay = 0
        scattering_amplitude = 0.0
        scattering_delay = 0

        if damage_effect is not None:
            damage_attenuation = float(
                damage_effect.attenuation_multiplier
            )
            damage_delay = int(
                damage_effect.delay_shift_samples
            )
            scattering_amplitude = float(
                damage_effect.scattering_amplitude
            )
            scattering_delay = int(
                damage_effect.scattering_delay_samples
            )

        total_delay = delay_samples + damage_delay

        propagated = [0.0] * (
            len(samples) + total_delay
        )

        # Primary received waveform.
        for source_index, sample in enumerate(samples):
            destination_index = (
                source_index + total_delay
            )

            propagated[destination_index] += (
                sample
                * amplitude
                * damage_attenuation
            )

        # ---------------------------------------------------------
        # Secondary scattered response
        # ---------------------------------------------------------

        if scattering_amplitude > 0.0:

            scattering_start = (
                total_delay
                + scattering_delay
            )

            required_length = (
                len(samples)
                + scattering_start
            )

            if required_length > len(propagated):
                propagated.extend(
                    [0.0]
                    * (
                        required_length
                        - len(propagated)
                    )
                )

            for source_index, sample in enumerate(samples):
                destination_index = (
                    source_index
                    + scattering_start
                )

                propagated[destination_index] += (
                    sample
                    * amplitude
                    * scattering_amplitude
                )

        return propagated

    def describe(self) -> str:
        """Return a human-readable description of the path."""
        return (
            f"{self.actuator_id} -> {self.receiver_id} | "
            f"distance={self.distance_m:.2f} m | "
            f"delay={self.propagation_delay_ms:.3f} ms | "
            f"attenuation={self.attenuation_db:.2f} dB | "
            f"amplitude_factor={self.amplitude_factor:.4f}"
        )