# Ruff Linting Error Resolution Strategy

## 1. Overview

This document outlines the systematic and iterative strategy for identifying, triaging, and resolving `ruff` linting errors within the FinComp project. This process has been proven effective in handling thousands of errors and should be followed to maintain code quality.

## 2. The Iterative Workflow

The core of the strategy is an iterative loop. Do not attempt to fix all errors at once. Instead, follow these steps repeatedly until all errors are resolved.

### Step 1: Generate a Comprehensive Error Report

First, generate a complete and structured report of all current linting errors. This is done using a custom script that executes `ruff check` and formats the output into a markdown file.

```bash
uv run .specify/python-tools/check_ruff_errors.py
```

This command creates `ruff_report.md`, which serves as the source of truth for the current state of linting errors.

### Step 2: Triage and Prioritize Errors

With a large number of errors, it's crucial to prioritize. Use the `.specify/python-tools/categorize_ruff_errors.py` script to analyze the report and group errors by their type (e.g., `F821`, `E722`).

```bash
uv run .specify/python-tools/categorize_ruff_errors.py
```

This script will output a summary table, allowing you to identify the most frequent error codes. **Always focus on the most common error first.** Fixing one common pattern can resolve hundreds of issues at once.

### Step 3: Attempt Automated Fixes

`Ruff` has powerful auto-fixing capabilities. Always attempt these first, as they are safe and efficient. Run the following commands in sequence:

1.  **Standard Fixes:**
    ```bash
    ruff --fix .
    ```
2.  **Unsafe Fixes:** (Use with caution, but often necessary for issues like unused imports `F401`)
    ```bash
    ruff --fix --unsafe-fixes .
    ```

After running auto-fixes, **always return to Step 1** to regenerate the report and assess the impact.

### Step 4: Perform Manual Fixes

For errors that cannot be auto-corrected, manual intervention is required. Address these errors one file at a time, based on the `ruff_report.md`.

**Key Principles for Manual Fixes:**
-   **One File at a Time:** Read the file, apply the fix using `apply_diff`, and then move to the next file.
-   **Use `apply_diff`:** For surgical changes, this is preferred over rewriting the entire file.
-   **Re-read if Necessary:** If an `apply_diff` operation fails due to content mismatch, re-read the file to get the current state before trying again.

#### Common Manual Fix Patterns:

-   **`F821` (Undefined name):**
    -   **Cause:** A variable or module is used without being imported or defined.
    -   **Fix:** Add the necessary import statement at the top of the file.
        -   `import os`
        -   `import json`
        -   `from flask import session`
        -   `import pandas as pd`

-   **`E722` (Do not use bare `except`):**
    -   **Cause:** A bare `except:` block is used, which can hide unexpected errors.
    -   **Fix:** Replace it with a more specific exception. If the goal is to catch any potential failure in a block, `except Exception:` is the standard, safe replacement.
        ```python
        # Before
        except:
            pass

        # After
        except Exception:
            pass
        ```

-   **`E402` (Module level import not at top of file):**
    -   **Cause:** An `import` statement is placed after other code.
    -   **Fix:** Move the import statement to the top of the file with the other imports.

### Step 5: Validate and Repeat

After each round of fixes (automated or manual), **always return to Step 1**:
1.  Run `uv run .specify/python-tools/check_ruff_errors.py` to generate a new report.
2.  Run `uv run .specify/python-tools/categorize_ruff_errors.py` to see the new priority list.
3.  Repeat the process.

The loop is complete when `ruff_report.md` shows "No ruff errors found."

## 3. Project-Specific Configuration

-   **Ruff Configuration (`ruff.toml`):** Ensure the project's `ruff.toml` file is correctly configured to exclude irrelevant directories (e.g., `.garbage`, `.venv`, `node_modules`) to keep reports clean and focused.