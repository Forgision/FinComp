import json
import subprocess
from collections import defaultdict


def run_ruff_check(directories):
    """Runs ruff check on a list of directories and returns parsed JSON output."""
    print(f"Running ruff check on {directories}...")
    command = ["ruff", "check", "--exit-zero", "--output-format", "json"] + directories
    result = subprocess.run(command, capture_output=True, text=True)

    if result.stderr:
        print("Error running ruff:")
        print(result.stderr)

    if result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Could not parse JSON from ruff output.")
            print("Ruff output:", result.stdout)
            return []
    return []


def generate_markdown_report(errors, output_file="ruff_report.md"):
    """Generates a markdown report from a list of ruff errors."""
    if not errors:
        report_content = "# Ruff Report\n\nNo errors found.\n"
    else:
        errors_by_file = defaultdict(list)
        for error in errors:
            errors_by_file[error["filename"]].append(error)

        report_content = "# Ruff Report\n\n"
        for filename, file_errors in sorted(errors_by_file.items()):
            report_content += f"## Errors in `{filename}`\n\n"
            report_content += "| Line | Column | Code | Message | Fixable |\n"
            report_content += "|------|--------|------|---------|---------|\n"
            for error in sorted(
                file_errors,
                key=lambda x: (x["location"]["row"], x["location"]["column"]),
            ):
                fixable_indicator = "✅" if error.get("fix") else "❌"
                message = error["message"].replace(
                    "|", r"\|"
                )  # Escape pipe characters in message
                report_content += (
                    f"| {error['location']['row']} | {error['location']['column']} "
                    f"| `{error['code']}` | {message} | {fixable_indicator} |\n"
                )
            report_content += "\n"

    with open(output_file, "w") as f:
        f.write(report_content)
    print(f"Report generated at {output_file}")


if __name__ == "__main__":
    target_dirs = ["app", "test"]

    print(f"Checking directories: {', '.join(target_dirs)}")

    errors = run_ruff_check(target_dirs)

    if errors:
        print(f"\nFound {len(errors)} errors.")
        generate_markdown_report(errors)

        print("\n--- Ruff Errors Summary (Console) ---")
        errors_by_file = defaultdict(list)
        for error in errors:
            errors_by_file[error["filename"]].append(error)

        for file, file_errors in sorted(errors_by_file.items()):
            print(f"\nErrors in {file}:")
            for error in sorted(
                file_errors,
                key=lambda x: (x["location"]["row"], x["location"]["column"]),
            ):
                fixable = " (fixable)" if error.get("fix") else ""
                print(
                    f"  - L{error['location']['row']}:{error['location']['column']}"
                    f"[{error['code']}] {error['message']}{fixable}"
                )
    else:
        print("\nNo ruff errors found in any files.")
        # Also generate an empty report
        generate_markdown_report([])
