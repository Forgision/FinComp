# Jules' Guide to Systematically Fixing Pylance Errors

This document outlines a robust, step-by-step workflow for identifying, fixing, and verifying Pylance errors in the project. Following this process ensures that fixes are correct, adhere to code quality standards, and do not introduce regressions.

## 1. Analysis and Planning

1.  **Understand the Error**: Receive the JSON output of Pylance errors. Identify the file path, error code (e.g., `reportCallIssue`), and the specific line of code.
2.  **Examine the Code**: Read the specified file to understand the full context of the error. A missing argument, for example, requires understanding what value that argument should have.
3.  **Formulate a Precise Plan**: Before writing any code, create a clear plan. This should include the exact change to be made and the verification steps that will follow.

## 2. Fixing the Code

1.  **Apply the Fix**: Use the appropriate tool to modify the code. For targeted changes, `replace_with_git_merge_diff` is preferred.
2.  **Confirm the Change**: After applying the fix, immediately read the file back to ensure the change was made exactly as intended.

## 3. Verification

This is a multi-stage process to guarantee code quality. All commands should be run from the repository root, within the activated virtual environment (`source .venv/bin/activate`).

### 3.1. Linting with Ruff

-   **Command**: `ruff check <path/to/file.py>`
-   **Purpose**: Catches stylistic issues, unused imports, and common programming errors.
-   **Action**: If `ruff` reports any errors, fix them before proceeding. This may involve an iterative cycle of fixing and re-running the check.

### 3.2. Type Checking with Mypy

`Mypy` ensures type safety but can be sensitive to the project's structure and dependencies.

-   **Command**: `PYTHONPATH=. mypy -p <module.path.to.file>`
    -   *Example*: `PYTHONPATH=. mypy -p app.core.schemas.traffic_db`
    -   **Note**: Using the `-p` flag with the module path is crucial for `mypy` to correctly resolve imports in this project. Directly passing a file path may lead to errors.

-   **Troubleshooting Mypy**:
    1.  **`Source file found twice` error**: This is the primary indicator that you should use the `PYTHONPATH=. mypy -p ...` command structure instead of passing a direct file path.
    2.  **`Module has no attribute` errors**: If `mypy` reports that a library (like SQLAlchemy) is missing well-known attributes (e.g., `DeclarativeBase`, `mapped_column`), it is almost always a type stub issue.
        -   **Check for conflicting stub packages**: The project's dependencies (like `SQLAlchemy >= 2.0`) often include their own high-quality, inline stubs. An older, external stub package (e.g., `sqlalchemy-stubs`) can conflict with these.
        -   **Resolution**: Uninstall the conflicting external stub package (`uv pip uninstall sqlalchemy-stubs`). This allows `mypy` to correctly find and use the modern, built-in type information.
    3.  **`Argument has incompatible type` errors**: Pay close attention to these. They often reveal subtle bugs. For example, a `ruff` suggestion to change `var == False` to `not var` might be correct for standard Python but can be a type error in a library like SQLAlchemy, which expects a `ColumnElement` instead of a raw `bool`. The fix is to use the library's specific syntax (e.g., `var.is_(False)`).

## 4. Regression Testing

1.  **Identify Tests**: If a specific test file exists for the modified module, run it directly.
2.  **Run the Full Suite**: If no specific test file is available, or to be extra cautious, run the entire test suite.
    -   **Command**: `PYTHONPATH=. pytest`
3.  **Analyze Results**: The project may have pre-existing test failures. The goal is to **ensure your changes have not introduced any new failures**. If the test output is identical before and after your change, you can be confident you have not caused a regression.

## 5. Finalization

Once all linting, type checking, and regression tests pass without new errors, the task for that file is complete. You can then confidently ask for the next set of Pylance errors.

## 6. Submission Workflow

**MANDATORY INSTRUCTION:** Do not proceed to the "PRE-CHECK COMMIT" or submission stage after fixing errors. Wait for explicit approval from the user. Your role is to fix Pylance errors one by one and request the next file until the user signals that all tasks are complete and gives the command to commit.
