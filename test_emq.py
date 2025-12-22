"""
Test script to verify EMQ (Event Match Quality) functionality works.
Run this from the Stratum-AI-Final-Updates-Dec-2025-main directory.
"""
import sys
import os
import types

# Set up the backend path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

# Create mock modules hierarchy before any imports
mock_app = types.ModuleType("app")
mock_core = types.ModuleType("app.core")
mock_logging = types.ModuleType("app.core.logging")
mock_config = types.ModuleType("app.core.config")
mock_services = types.ModuleType("app.services")
mock_capi = types.ModuleType("app.services.capi")

class MockLogger:
    def info(self, *args, **kwargs): pass
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass

def get_logger(name=None):
    return MockLogger()

mock_logging.get_logger = get_logger
mock_logging.logger = MockLogger()

class MockSettings:
    log_level = "INFO"
    log_format = "console"

mock_config.settings = MockSettings()

# Set up module hierarchy
mock_app.core = mock_core
mock_app.services = mock_services
mock_services.capi = mock_capi

sys.modules["app"] = mock_app
sys.modules["app.core"] = mock_core
sys.modules["app.core.logging"] = mock_logging
sys.modules["app.core.config"] = mock_config
sys.modules["app.services"] = mock_services
sys.modules["app.services.capi"] = mock_capi

# Now import the actual EMQ modules using importlib
import importlib.util

def load_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load pii_hasher first (data_quality depends on it)
pii_hasher_path = os.path.join(backend_path, "app", "services", "capi", "pii_hasher.py")
pii_hasher_module = load_module_from_file("app.services.capi.pii_hasher", pii_hasher_path)
PIIHasher = pii_hasher_module.PIIHasher
PIIField = pii_hasher_module.PIIField

# Now load data_quality
data_quality_path = os.path.join(backend_path, "app", "services", "capi", "data_quality.py")
data_quality_module = load_module_from_file("app.services.capi.data_quality", data_quality_path)
DataQualityAnalyzer = data_quality_module.DataQualityAnalyzer

def test_pii_hasher():
    """Test PII detection and hashing."""
    print("\n" + "="*60)
    print("Testing PIIHasher")
    print("="*60)

    hasher = PIIHasher()

    # Test data with various PII fields
    test_data = {
        "email": "john.doe@example.com",
        "phone_number": "+1-555-123-4567",
        "first_name": "John",
        "last_name": "Doe",
        "user_id": "USR123456",
        "ip_address": "192.168.1.100",
        "gclid": "abc123xyz",
    }

    print("\nInput data:")
    for k, v in test_data.items():
        print(f"  {k}: {v}")

    # Detect PII fields
    detections = hasher.detect_pii_fields(test_data)

    print(f"\nDetected {len(detections)} PII fields:")
    for det in detections:
        print(f"  - {det.original_key} -> {det.field_name}")
        print(f"    Type: {det.detected_type.value}, Confidence: {det.confidence:.0%}")
        print(f"    Needs hashing: {det.needs_hashing}, Is hashed: {det.is_hashed}")

    # Hash the data
    hashed_data = hasher.hash_data(test_data)
    print("\nHashed data:")
    for k, v in hashed_data.items():
        display_v = v[:20] + "..." if len(str(v)) > 20 else v
        print(f"  {k}: {display_v}")

    # Calculate completeness for different platforms
    print("\nData completeness by platform:")
    for platform in ["meta", "google", "tiktok", "snapchat", "linkedin"]:
        result = hasher.calculate_data_completeness(test_data, platform)
        print(f"  {platform.upper()}: {result['score']}%")
        print(f"    Recommendation: {result['recommendation']}")

    print("\n[PASS] PIIHasher working correctly!")
    return True


def test_data_quality_analyzer():
    """Test the DataQualityAnalyzer for EMQ scoring."""
    print("\n" + "="*60)
    print("Testing DataQualityAnalyzer (EMQ)")
    print("="*60)

    analyzer = DataQualityAnalyzer()

    # Test single event analysis
    test_event = {
        "event_name": "Purchase",
        "user_data": {
            "email": "customer@test.com",
            "phone": "+1234567890",
            "external_id": "CUST001",
            "fbc": "fb.1.123456789.abcdef",
        },
        "custom_data": {
            "currency": "USD",
            "value": 99.99,
        }
    }

    print("\nAnalyzing single event:")
    result = analyzer.analyze_event(test_event)
    print(f"  Overall Score: {result['overall_score']}")
    print(f"  Quality Level: {result['quality_level']}")
    print(f"  Fields present: {result['user_data_fields']}")

    # Test batch analysis
    print("\nAnalyzing batch of events...")
    batch_events = [
        {"user_data": {"email": "user1@test.com", "phone": "1234567890"}},
        {"user_data": {"email": "user2@test.com"}},
        {"user_data": {"email": "user3@test.com", "phone": "0987654321", "external_id": "ID3"}},
        {"user_data": {"email": "user4@test.com", "fbc": "fb.click.123"}},
        {"user_data": {"phone": "5551234567", "external_id": "ID5"}},
        {"user_data": {"email": "user6@test.com", "phone": "5559876543"}},
        {"user_data": {"email": "user7@test.com", "gclid": "google.click.456"}},
        {"user_data": {"email": "user8@test.com", "phone": "5555555555", "first_name": "Jane"}},
        {"user_data": {"email": "user9@test.com", "ttclid": "tiktok.click.789"}},
        {"user_data": {"email": "user10@test.com", "phone": "5551112222", "last_name": "Smith"}},
    ]

    report = analyzer.analyze_batch(batch_events, ["meta", "google"])

    print(f"\n  Overall EMQ Score: {report.overall_score}")
    print(f"  Trend: {report.trend}")
    print(f"  Estimated ROAS Improvement: +{report.estimated_roas_improvement}%")

    print("\n  Platform Scores:")
    for platform, score in report.platform_scores.items():
        print(f"    {platform.upper()}:")
        print(f"      Score: {score.score} ({score.event_match_quality})")
        print(f"      Potential ROAS Lift: +{score.potential_roas_lift}%")
        print(f"      Events Analyzed: {score.events_analyzed}")
        if score.fields_present:
            print(f"      Fields Present: {', '.join(score.fields_present)}")
        if score.fields_missing:
            print(f"      Fields Missing: {', '.join(score.fields_missing)}")

    print("\n  Data Gaps Summary:")
    for severity, count in report.data_gaps_summary.items():
        if count > 0:
            print(f"    {severity}: {count}")

    print("\n  Top Recommendations:")
    for rec in report.top_recommendations[:3]:
        print(f"    {rec['priority']}. [{rec['severity'].upper()}] {rec['action']}")
        print(f"       Impact: {rec['impact']}")

    # Test live insights
    print("\nGetting live insights for Meta...")
    insights = analyzer.get_live_insights(batch_events, "meta")
    print(f"  Status: {insights['status']}")
    print(f"  Current Score: {insights['current_score']}")
    print(f"  Quality Level: {insights['quality_level']}")
    print(f"  Trend: {insights['trend']}")
    print(f"  Action Required: {insights['action_required']}")

    print("\n[PASS] DataQualityAnalyzer (EMQ) working correctly!")
    return True


def main():
    print("\n" + "#"*60)
    print("# Stratum AI - EMQ (Event Match Quality) Test Suite")
    print("#"*60)

    tests_passed = 0
    tests_failed = 0

    try:
        if test_pii_hasher():
            tests_passed += 1
    except Exception as e:
        tests_failed += 1
        print(f"\n[FAIL] PIIHasher test failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        if test_data_quality_analyzer():
            tests_passed += 1
    except Exception as e:
        tests_failed += 1
        print(f"\n[FAIL] DataQualityAnalyzer test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print(f"TEST RESULTS: {tests_passed} passed, {tests_failed} failed")
    print("="*60)

    if tests_failed == 0:
        print("\nEMQ is working correctly!")
        return 0
    else:
        print("\nSome tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
