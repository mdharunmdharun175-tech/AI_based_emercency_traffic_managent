"""
Unit Tests for Multi-Feature Ambulance Verification Pipeline & Dynamic Signal Control
"""

import time
import numpy as np
from services.ambulance_tracker import (
    AmbulanceTracker,
    calculate_combined_confidence_score,
    detect_roof_flasher_lights,
    detect_ambulance_text,
    detect_medical_symbols,
    verify_vehicle_shape,
)
from services.signal_controller import SignalController, ControllerState


def test_combined_confidence_score_calculation():
    """Verify weighted combined confidence score math."""
    # Perfect score across all 6 features
    score_100 = calculate_combined_confidence_score(
        yolo_score=1.0,
        roof_light_score=1.0,
        text_score=1.0,
        symbol_score=1.0,
        shape_score=1.0,
        ocr_score=1.0,
    )
    assert score_100 == 1.0

    # Typical multi-feature detection scenario
    # Roof=0.90 (0.27), Text=1.0 (0.25), Shape=0.80 (0.12), YOLO=0.90 (0.135), Symbol=0.90 (0.09), OCR=0.90 (0.045) -> Sum = 0.91 (91%)
    score_typical = calculate_combined_confidence_score(
        yolo_score=0.90,
        roof_light_score=0.90,
        text_score=1.0,
        symbol_score=0.90,
        shape_score=0.80,
        ocr_score=0.90,
    )
    assert score_typical == 0.91

    # False positive candidate missing roof lights, text, and medical symbols
    # Roof=0.0 (0.0), Text=0.0 (0.0), Shape=0.20 (0.03), YOLO=0.50 (0.075), Symbol=0.0 (0.0), OCR=0.0 (0.0) -> 0.105 (10.5%)
    score_fp = calculate_combined_confidence_score(
        yolo_score=0.50,
        roof_light_score=0.0,
        text_score=0.0,
        symbol_score=0.0,
        shape_score=0.20,
        ocr_score=0.0,
    )
    assert score_fp == 0.105
    assert score_fp < 0.80  # Fails 80% threshold!


def test_roof_flasher_light_detection():
    """Verify HSV roof light flasher detection on synthetic ROI."""
    # Synthetic frame with top flashing red/blue bar
    roi = np.zeros((100, 100, 3), dtype=np.uint8)
    # Draw red flasher light on roof (top 35%)
    roi[5:20, 10:40] = (0, 0, 255)  # BGR Red
    # Draw blue flasher light on roof
    roi[5:20, 60:90] = (255, 0, 0)  # BGR Blue

    has_lights, score = detect_roof_flasher_lights(roi)
    assert has_lights is True
    assert score > 0.50


def test_ambulance_text_detection():
    """Verify AMBULANCE text pattern matching with substring tolerance."""
    has_text, score, matched = detect_ambulance_text(None, ocr_text="KA-05 AMBULANCE 108")
    assert has_text is True
    assert score == 1.0
    assert matched == "AMBULANCE"

    has_text_partial, score_p, matched_p = detect_ambulance_text(None, ocr_text="AMBU-EMG-108")
    assert has_text_partial is True
    assert score_p == 0.90


def test_multi_frame_verification_tracker():
    """Verify tracked vehicle requires consecutive frames & combined score >= threshold before verification."""
    tracker = AmbulanceTracker(confirmation_threshold=0.80)
    
    det = {
        "confidence": 0.90,
        "is_emergency": True,
        "type": "ambulance",
        "bbox": {"x": 100, "y": 100, "width": 80, "height": 70},
        "roof_lights_detected": True,
        "roof_light_score": 0.90,
        "text_detected": True,
        "text_score": 0.95,
        "symbol_detected": True,
        "symbol_score": 0.90,
        "plate_number": "KA-05-EM-108",
    }

    # Frame 1: Track created (frame_count = 1) -> Not verified yet (requires >=2 frames)
    res1 = tracker.process_detections([det], lane_id="Lane B", frame_height=360)
    assert len(res1) == 1
    assert res1[0]["verified"] is False

    # Frame 2: Same tracked vehicle (frame_count = 2) -> Verified!
    res2 = tracker.process_detections([det], lane_id="Lane B", frame_height=360)
    assert len(res2) == 1
    assert res2[0]["verified"] is True
    assert res2[0]["combined_score"] >= 0.80


def test_dynamic_emergency_signal_control():
    """Verify dynamic emergency signal control holds GREEN until stop-line crossing and serves priority queue."""
    controller = SignalController()
    assert controller.state == ControllerState.NORMAL
    assert controller.current_lane_index == 0  # Lane A active green (30s)

    # 1. Detect Ambulance on Lane B at 150m (score 90%)
    controller.add_or_update_emergency_vehicle(
        tracking_id="AMB-101",
        lane_id="Lane B",
        distance=150.0,
        eta=10.0,
        confidence=0.90,
        plate="KA-05-EM-101",
        roof_lights_detected=True,
        combined_score=0.90,
    )

    # Signal pauses active Lane A, saves remaining countdown, enters ALL_RED_SAFETY for 2s
    assert controller.state == ControllerState.ALL_RED_SAFETY
    assert controller.paused_lane == "Lane A"
    assert controller.paused_remaining == 30

    # 2. Advance 2 ticks (2 seconds)
    controller.tick()  # timer 2 -> 1
    controller.tick()  # timer 1 -> 0 -> transitions to EMERGENCY_GREEN

    assert controller.state == ControllerState.EMERGENCY_GREEN
    assert controller.active_emergency_lane == "Lane B"

    # Signal states check: Lane B GREEN (countdown 0), all others RED
    signals = controller.get_signal_states()
    assert signals["Lane B"]["color"] == "GREEN"
    assert signals["Lane A"]["color"] == "RED"

    # Advance 10 ticks (10 seconds) -> State MUST REMAIN EMERGENCY_GREEN indefinitely!
    for _ in range(10):
        controller.tick()
    assert controller.state == ControllerState.EMERGENCY_GREEN
    assert controller.active_emergency_lane == "Lane B"

    # 3. Simulate Stop Line Crossing event
    controller.mark_ambulance_passed("AMB-101")

    # Priority queue now empty -> Controller enters RESUME state and restores Lane A with saved 30s countdown
    assert controller.state == ControllerState.RESUME
    assert controller.current_lane_index == 0  # Lane A
    assert controller.current_green_remaining == 30
    assert "Lane B" in controller.skip_lanes


def test_multiple_ambulances_priority_queue():
    """Verify nearest ambulance receives priority and queue automatically serves next ambulance."""
    controller = SignalController()

    # Ambulance 1: Lane B at 120m
    controller.add_or_update_emergency_vehicle(
        tracking_id="AMB-201",
        lane_id="Lane B",
        distance=120.0,
        eta=8.0,
        confidence=0.85,
        combined_score=0.85,
    )

    # Ambulance 2: Lane D at 60m (NEAREST -> HIGHER PRIORITY!)
    controller.add_or_update_emergency_vehicle(
        tracking_id="AMB-202",
        lane_id="Lane D",
        distance=60.0,
        eta=4.0,
        confidence=0.92,
        combined_score=0.92,
    )

    # Verify priority queue sorting: AMB-202 (Lane D) is #1 Rank
    assert controller.priority_queue[0]["tracking_id"] == "AMB-202"
    assert controller.priority_queue[0]["lane_id"] == "Lane D"
    assert controller.active_emergency_lane == "Lane D"

    # Pass All-Red 2s delay
    controller.tick()
    controller.tick()
    assert controller.state == ControllerState.EMERGENCY_GREEN
    assert controller.active_emergency_lane == "Lane D"

    # AMB-202 (Lane D) crosses stop line
    controller.mark_ambulance_passed("AMB-202")

    # Next in queue is AMB-201 (Lane B) -> Switches to ALL_RED_SAFETY then Lane B
    assert controller.state == ControllerState.ALL_RED_SAFETY
    assert controller.active_emergency_lane == "Lane B"

    controller.tick()
    controller.tick()
    assert controller.state == ControllerState.EMERGENCY_GREEN
    assert controller.active_emergency_lane == "Lane B"

    # AMB-201 (Lane B) crosses stop line
    controller.mark_ambulance_passed("AMB-201")

    # Queue empty -> Resume interrupted normal signal
    assert controller.state == ControllerState.RESUME
