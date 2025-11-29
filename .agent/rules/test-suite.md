---
trigger: always_on
---

- Must use `pytest` as testing framework for python tests.
- Define global fixtures in [conftest.py](./tests/conftest.py) for use across all tests.
- Two types of tests real tests and mock tests. [Real tests](./tests/real) use real code except for orders e.g. don't place real order. [Mock tests](./tests/mock) use mock code via fixture. e.g. mock database operation, mock broker operation, etc.
- Define module-specific fixtures in `conftest.py` for tests within a module. e.g fixuture which only use for mock tests for [data](./tests/mocks/data) puts in [conftest.py](./tests/mocks/data/conftest.py) which are only use for tests for data.
- Define file-specific fixtures within the test file if they are only used there.