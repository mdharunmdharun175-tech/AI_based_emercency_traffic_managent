"""
Hardware Abstraction Interface Module (v1.0)
Defines an abstract interface for traffic signal hardware (ESP32, Arduino, Raspberry Pi, GPIO).
Allows software-only simulation mode by default (MockHardwareSignalInterface) and seamless
hardware integration in future phases without altering core detection logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HardwareSignalInterface(ABC):
    """Abstract Base Class for Traffic Signal Hardware Drivers."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize hardware connection (Serial/GPIO)."""
        pass

    @abstractmethod
    def set_signal_state(self, lane_id: str, state: str) -> bool:
        """
        Send signal state change command to hardware.
        lane_id: 'Lane A', 'Lane B', 'Lane C', 'Lane D'
        state: 'RED', 'YELLOW', 'GREEN'
        """
        pass

    @abstractmethod
    def close(self):
        """Close hardware connection safely."""
        pass


class MockHardwareSignalInterface(HardwareSignalInterface):
    """Software-Only Simulation Driver. Logs signal commands without physical hardware."""

    def __init__(self):
        self.is_connected = False
        self.current_states: Dict[str, str] = {
            "Lane A": "RED",
            "Lane B": "RED",
            "Lane C": "RED",
            "Lane D": "RED",
        }

    def initialize(self) -> bool:
        self.is_connected = True
        logger.info("📡 Hardware Interface: Initialized in Software Simulation Mode (Mock Driver)")
        return True

    def set_signal_state(self, lane_id: str, state: str) -> bool:
        self.current_states[lane_id] = state.upper()
        logger.debug(f"🔌 [SIMULATED HARDWARE] Signal Command -> {lane_id}: {state.upper()}")
        return True

    def close(self):
        self.is_connected = False
        logger.info("🔌 [SIMULATED HARDWARE] Connection closed")
