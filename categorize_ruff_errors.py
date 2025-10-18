import re
from collections import Counter


def categorize_errors(report_path="ruff_report.md"):
    error_codes = []
    with open(report_path, "r") as f:
        for line in f:
            match = re.search(r"\| `([A-Z]\d{3})` \|", line)
            if match:
                error_codes.append(match.group(1))
    return Counter(error_codes)


if __name__ == "__main__":
    error_counts = categorize_errors()
    print("Ruff Error Categories:")
    for code, count in error_counts.most_common():
        print(f"- {code}: {count} occurrences")
