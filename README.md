# OpenAlgo SpecKit Migration

This project is a reference implementation of a FastAPI-based service, migrated from the original OpenAlgo codebase to strictly adhere to the standards defined in the [SpecKit Constitution](.specify/memory/constitution.md). The primary goal is to create a modular, highly testable, and maintainable service that serves as a template for future projects within the SpecKit ecosystem.

## Project Constitution

This project is governed by a strict constitution that outlines our core principles for development. All contributions MUST adhere to these standards. Please review the [constitution](.specify/memory/constitution.md) before contributing.

Key principles include:
- **Technology Stack**: A Python/FastAPI backend and a JavaScript/CSS frontend.
- **Strict Project Structure**: Adherence to the structure in `.specify/memory/structure.md`.
- **API-First Design**: All functionality is exposed through a RESTful API.
- **Declarative Configuration**: Project configuration is managed through declarative files.
- **Comprehensive Testing**: All new features or bug fixes must be accompanied by corresponding tests.
- **Standardized Tooling**: `uv` for environment management and script execution.
- **Centralized Logging**: Use of the logger from `app.utils.logging`.
- **Strict Code Quality**: Adherence to PEP 8, `black` formatting, and `ruff` linting.
- **Comprehensive Unit Testing**: Use of `unittest` framework and high code coverage.
- **User Experience Consistency**: Adherence to the DaisyUI design system.
- **Code Documentation**: Docstrings for all public APIs and complex logic.
- **Static Typing**: Mandatory use of type hints in all new code.

## Getting Started

### Prerequisites
- Python >=3.12
- `uv` for environment management

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/openalgo-speckit-migration.git
   cd openalgo-speckit-migration
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

### Minimum Hardware Requirements

To run OpenAlgo we recommend:
- 2GB RAM or 0.5GB RAM with 2GB of Swap Memory
- 1GB disk space
- 1vCPU

## Contributing

We welcome contributions! If you're interested in improving the application or adding new features, please fork the repository and submit a pull request. All contributions must adhere to the principles outlined in the [project constitution](.specify/memory/constitution.md).

## License

OpenAlgo is released under the AGPL V3.0 License. See the `LICENSE` file for more details.

## Disclaimer

This software is for educational purposes only. Do not risk money which
you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.
