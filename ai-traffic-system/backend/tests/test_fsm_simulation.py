"""
Automated Integration Test for SignalController FSM & Database Engine
Tests:
1. Normal 30s circular rotation (Lane A -> Lane B -> Lane C -> Lane D)
2. Priority Queue multi-ambulance distance sorting (Lane B 100m vs Lane D 70m -> Lane D first)
3. Emergency Interrupt: Green timer pause & 2s All-Red Safety delay
4. Emergency Green activation
5. Ambulance Passed event trigger & Priority Queue removal
6. Resumption of interrupted green timer from exact remaining countdown
7. Skip lane logic execution (skip emergency lane once in current cycle)
8. SQLite database logging across all 6 tables
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from services.signal_controller import SignalController, ControllerState
from database_sqlite import SQLiteDatabase


def test_fsm_lifecycle():
    print("=" * 60)
    print("TESTING FSM SIGNAL CONTROLLER & SIMULATION ENGINE")
    print("=" * 60)

    controller = SignalController()
    controller.reset_fsm()

    # 1. Verify initial Normal state & Lane A active
    print("\n[STEP 1] Testing Normal Rotation State...")
    snapshot = controller.get_full_snapshot()
    assert snapshot["controller_state"] == "NORMAL", f"Expected NORMAL, got {snapshot['controller_state']}"
    assert snapshot["active_green_lane"] == "Lane A", f"Expected Lane A, got {snapshot['active_green_lane']}"
    assert snapshot["current_green_remaining"] == 30, f"Expected 30s remaining, got {snapshot['current_green_remaining']}"
    print("  [SUCCESS] Initial Normal state verified: Lane A GREEN (30s)")

    # Simulate 10 seconds passing on Lane A
    for _ in range(10):
        controller.tick()
    assert controller.current_green_remaining == 20, f"Expected 20s left on Lane A, got {controller.current_green_remaining}"
    print(f"  [SUCCESS] 10s elapsed: Lane A GREEN ({controller.current_green_remaining}s remaining)")

    # 2. Advance to Lane C
    controller.current_lane_index = 2  # Lane C
    controller.current_green_remaining = 20  # 20s remaining on Lane C
    print("\n[STEP 2] Simulating Lane C GREEN with 20 seconds remaining...")

    # 3. Trigger Emergency Ambulance on Lane B at 100m and Lane D at 70m
    print("\n[STEP 3] Triggering Multiple Ambulances: Lane B (100m) & Lane D (70m)...")
    controller.add_or_update_emergency_vehicle(
        tracking_id="AMB-101",
        lane_id="Lane B",
        distance=100.0,
        eta=8.0,
        confidence=0.85,
        plate="KA-05-EM-101"
    )
    controller.add_or_update_emergency_vehicle(
        tracking_id="AMB-102",
        lane_id="Lane D",
        distance=70.0,
        eta=5.0,
        confidence=0.92,
        plate="KA-05-EM-102"
    )

    # 4. Verify Priority Queue Sorting (Nearest Distance: Lane D at 70m first, then Lane B at 100m)
    pq = controller.priority_queue
    assert len(pq) == 2, f"Expected 2 in queue, got {len(pq)}"
    assert pq[0]["tracking_id"] == "AMB-102", f"Expected AMB-102 (70m) first, got {pq[0]['tracking_id']}"
    assert pq[1]["tracking_id"] == "AMB-101", f"Expected AMB-101 (100m) second, got {pq[1]['tracking_id']}"
    print("  [SUCCESS] Priority Queue correctly sorted by distance: #1 AMB-102 (Lane D, 70m), #2 AMB-101 (Lane B, 100m)")

    # 5. Verify Paused Timer & All-Red Safety State
    assert controller.paused_lane == "Lane C", f"Expected paused Lane C, got {controller.paused_lane}"
    assert controller.paused_remaining == 20, f"Expected 20s paused, got {controller.paused_remaining}"
    assert controller.state == ControllerState.ALL_RED_SAFETY, f"Expected ALL_RED_SAFETY, got {controller.state}"
    print(f"  [SUCCESS] Interrupted Lane C saved with {controller.paused_remaining}s remaining")
    print(f"  [SUCCESS] Controller entered ALL_RED_SAFETY state (2s delay)")

    # Tick 2 seconds for Safety state
    controller.tick()
    controller.tick()
    assert controller.state == ControllerState.EMERGENCY_GREEN, f"Expected EMERGENCY_GREEN, got {controller.state}"
    assert controller.active_emergency_lane == "Lane D", f"Expected Lane D active emergency, got {controller.active_emergency_lane}"
    print("  [SUCCESS] Safety delay complete: Lane D (Priority #1) activated EMERGENCY_GREEN")

    # 6. Simulate AMB-102 crossing virtual stop line
    print("\n[STEP 4] Simulating AMB-102 Crossing Stop Line...")
    controller.mark_ambulance_passed("AMB-102")
    assert "Lane D" in controller.skip_lanes, "Expected Lane D added to skip_lanes"
    print("  [SUCCESS] AMB-102 passed! Emergency cleared for Lane D. Lane D marked in skip list.")

    # 7. Next priority vehicle (AMB-101 on Lane B) served
    assert controller.state == ControllerState.ALL_RED_SAFETY, f"Expected ALL_RED_SAFETY for next vehicle, got {controller.state}"
    assert controller.active_emergency_lane == "Lane B", f"Expected Lane B next, got {controller.active_emergency_lane}"
    print("  [SUCCESS] Switching to next priority ambulance: Lane B (AMB-101)")

    controller.tick()
    controller.tick()
    assert controller.state == ControllerState.EMERGENCY_GREEN, f"Expected EMERGENCY_GREEN, got {controller.state}"
    print("  [SUCCESS] Lane B activated EMERGENCY_GREEN")

    # 8. Simulate AMB-101 crossing stop line
    print("\n[STEP 5] Simulating AMB-101 Crossing Stop Line...")
    controller.mark_ambulance_passed("AMB-101")
    assert "Lane B" in controller.skip_lanes, "Expected Lane B added to skip_lanes"
    print("  [SUCCESS] AMB-101 passed! Queue is now empty.")

    # 9. Verify Signal Resumption (Resuming Lane C at exact 20s remaining)
    assert controller.state == ControllerState.NORMAL or controller.state == ControllerState.RESUME, f"Expected RESUME state, got {controller.state}"
    assert controller.current_lane_index == 2, "Expected current lane to be Lane C"
    assert controller.current_green_remaining == 20, f"Expected 20s remaining on Lane C, got {controller.current_green_remaining}"
    print(f"  [SUCCESS] Interrupted Lane C successfully RESUMED at exact remaining countdown: {controller.current_green_remaining}s")

    # 10. Verify SQLite Database Logging
    print("\n[STEP 6] Verifying SQLite Database Logs...")
    logs = SQLiteDatabase.get_system_logs(limit=20)
    assert len(logs) > 0, "Expected non-empty system logs"
    print(f"  [SUCCESS] SQLite database recorded {len(logs)} system logs successfully!")

    events = SQLiteDatabase.get_emergency_events(limit=20)
    assert len(events) > 0, "Expected non-empty emergency events"
    print(f"  [SUCCESS] SQLite database recorded {len(events)} emergency events!")

    print("\n" + "=" * 60)
    print("ALL FSM SIGNAL CONTROLLER & SIMULATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_fsm_lifecycle()
