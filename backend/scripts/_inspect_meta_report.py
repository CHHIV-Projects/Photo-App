import json
from pathlib import Path
from collections import Counter

report_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "logs" / "metadata_canonicalization_reports"
latest = sorted(report_dir.glob("meta_compare_*.json"))[-1]
data = json.loads(latest.read_text())

print(f"Report: {latest.name}")
print(f"Assets compared: {data['asset_count_compared']}")
print(f"Total mismatches: {data['total_mismatches']}")
print()

# Tally by field
field_counter = Counter()
for item in data["per_asset_mismatch_details"]:
    for m in item["mismatched_fields"]:
        field_counter[m["field"]] += 1

print("Mismatches by field:")
for field, count in field_counter.most_common():
    print(f"  {field}: {count}")

print()
print("First 3 mismatch samples:")
for item in data["per_asset_mismatch_details"][:3]:
    print(f"  PATH: {item['source_path']}")
    for m in item["mismatched_fields"]:
        print(f"    field={m['field']}  baseline={repr(m['baseline'])}  optimized={repr(m['optimized'])}")
    print()
