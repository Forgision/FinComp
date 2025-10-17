# OpenAlgo SpecKit Migration

This project is a reference implementation of a FastAPI-based service, migrated from the original OpenAlgo codebase to strictly adhere to the standards defined in the [SpecKit Constitution](.specify/memory/constitution.md). The primary goal is to create a modular, highly testable, and maintainable service that serves as a template for future projects within the SpecKit ecosystem.

## Project Constitution

This project is governed by a strict constitution that outlines our core principles for development. All contributions MUST adhere to these standards. Please review the [constitution](.specify/memory/constitution.md) before contributing.

Key principles include:
- **Strict Code Quality**: Adherence to PEP 8, automated linting, and consistent naming conventions.
- **Comprehensive Testing**: Non-negotiable Test-Driven Development (TDD) with 90% code coverage.
- **API Design and Consistency**: RESTful APIs with Pydantic models for validation.
- **Performance as a Feature**: A focus on writing and benchmarking performant code.
- **Modular Architecture**: A defined project structure with dependency injection.
- **User Experience Consistency**: A consistent design language and user experience.
- **Frontend Technology Stack**: Use of HTML/JS/CSS with Jinja2 for server-side rendering.

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
