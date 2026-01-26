import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.analysis_engine.tactic_detection_v2 import TacticDetectorV2
from core.analysis_engine.schemas import TranscriptSegment

load_dotenv()

async def run_smoke_test():
    print("Initializing TacticDetectorV2 Smoke Test...")
    detector = TacticDetectorV2()
    
    test_cases = [
        ("I need to check with my manager.", "AUTHORITY", "manager_deferral"),
        ("That's company policy.", "AUTHORITY", "policy_shield"),
        ("This offer is only valid today.", "URGENCY", "deadline"),
        ("We only have one slot left.", "URGENCY", "scarcity"),
        ("The price is $50,000.", "ANCHORING", "numeric_anchor"),
        ("Can you walk me through what's included?", "NONE", "none")
    ]

    print(f"\nRunning {len(test_cases)} Test Cases (NEW Segments Only)...\n")
    
    success_count = 0
    
    for text, expected_cat, expected_sub in test_cases:
        # Create a segment for the test case
        seg = TranscriptSegment(
            text=text,
            speaker="User",
            timestamp=100.0
        )
        
        # We pass this as 'new_segments'
        # Context can be minimal/empty
        signals = await detector.detect_tactics(
            segments=[],
            new_segments=[seg],
            negotiation_type="General"
        )
        
        # Analyze result
        if not signals:
            detected_cat = "NONE"
            detected_sub = "none"
        else:
            top_signal = max(signals, key=lambda s: s.confidence)
            detected_cat = top_signal.category
            detected_sub = top_signal.subtype

        # Check pass/fail
        pass_cat = (detected_cat == expected_cat)
        # Relax subtype check for NONE or if category matches (sometimes subtypes vary slightly, but key is category)
        # But requirement says "manager" -> "manager_deferral", so we check strict if possible.
        pass_sub = (detected_sub == expected_sub) if expected_cat != "NONE" else True
        
        status = "✅ PASS" if (pass_cat and pass_sub) else "❌ FAIL"
        if status == "✅ PASS":
            success_count += 1
            
        print(f"[{status}] Input: \"{text}\"")
        print(f"   Expected: {expected_cat} ({expected_sub})")
        print(f"   Got:      {detected_cat} ({detected_sub})")
        if signals:
            print(f"   Options:  {signals[0].options}")
        print("-" * 40)

    print(f"\nSmoke Test Summary: {success_count}/{len(test_cases)} Passed")

    # Malformed JSON Robustness Test
    print("\n[Optional] Testing Malformed JSON Robustness...")
    # This acts as a manual check that we don't crash. 
    # Real unit tests mock the client, here we just trust the logic we wrote or could try to mock if needed.
    # For now, we rely on the logic review.
    print("Skipping mock injection for smoke test script simplicity, relied on code review.")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
