from typing import Iterable, List


class ReceiverAcquisition:
    """Models the receiver-side acquisition scaling of the virtual PZT."""

    def __init__(self, gain: float = 5.0):
        if gain <= 0:
            raise ValueError(f"gain must be positive, got {gain}")

        self.gain = float(gain)

    def apply(self, samples: Iterable[float]) -> List[float]:
        """Apply receiver/acquisition gain to propagated samples."""
        return [float(sample) * self.gain for sample in samples]