## Brief overview
This rule set outlines the preferred strategy for addressing `ruff` linting errors, particularly when auto-fixing mechanisms are not fully effective. It emphasizes a systematic approach to ensure code quality and maintainability within the FinComp project.

## Development workflow
- **Iterative Error Resolution:** When encountering a large number of linting errors, adopt an iterative approach:
    - Generate a comprehensive report of all errors.
    - Categorize errors by type and frequency to identify prevalent issues.
    - Attempt `ruff` auto-fixes for fixable errors.
    - Re-generate the report to assess the impact of auto-fixes.
    - For persistent or non-auto-fixable errors, consider custom scripting for programmatic fixes.
    - Manually address remaining errors, prioritizing common or critical issues.
- **Validation:** Always re-run static analysis and re-generate reports after applying fixes to confirm resolution and identify any new issues.

## Coding best practices
- **Whitespace Management:** Pay close attention to `W293` (blank line contains whitespace) and `W291` (trailing whitespace) errors. If `ruff --fix` does not resolve these, a programmatic approach (e.g., a custom Python script) may be necessary to ensure consistent whitespace removal.

## Project context
- **Ruff Configuration:** Ensure `ruff.toml` is correctly configured to exclude irrelevant directories (e.g., `.garbage`) to avoid unnecessary linting reports.
- **Tool Integration:** Leverage custom Python scripts to automate `ruff` execution, report generation, and error categorization, enhancing efficiency in large codebases.

## Other guidelines
- **Problem-Solving:** When encountering persistent issues with automated tools, break down the problem into smaller, manageable pieces and explore alternative programmatic solutions.