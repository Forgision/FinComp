# Project: OpenAlgo

## Project Overview

This project is **OpenAlgo**, a Flask-based Python application for algorithmic trading. It acts as a bridge between traders and various trading platforms like Amibroker, Tradingview, and others. The goal is to simplify algo trading by providing a unified API and a user-friendly interface.

The backend is built with Python and Flask, and the frontend uses a combination of Tailwind CSS and DaisyUI for a modern and responsive user interface.

**Key Technologies:**

*   **Backend:** Python, Flask, SQLAlchemy
*   **Frontend:** JavaScript, Tailwind CSS, DaisyUI, PostCSS
*   **Database:** Not explicitly defined, but likely SQLite or another relational database given the use of SQLAlchemy.
*   **Real-time:** WebSockets, ZeroMQ

## Building and Running

### Frontend (CSS)

To build the CSS for the frontend, use the following command:

```bash
npm run build:css
```

To watch for changes and automatically rebuild the CSS, use:

```bash
npm run watch:css
```

### Backend (Flask Application)

The application is started using the `start.sh` script. This script first starts a WebSocket proxy server in the background and then runs the main Flask application using `gunicorn` with `eventlet` for WebSocket support.

To run the application, execute the following command:

```bash
./start.sh
```

The application will be available at `http://0.0.0.0:5000`.

## Development Conventions

*   **Hybrid Project:** This is a hybrid project with a Python backend and a JavaScript/CSS frontend.
*   **Styling:** Frontend styling is done using Tailwind CSS and the DaisyUI component library. The source CSS file is located at `src/css/styles.css` and the output is `static/css/main.css`.
*   **Python Dependencies:** Python dependencies are managed using `pyproject.toml`.
*   **JavaScript Dependencies:** JavaScript development dependencies are managed using `package.json`.
*   **API:** The application provides a RESTful API with a unified structure across different brokers.
*   **Security:** The application includes security features like Content Security Policy (CSP), CORS protection, and CSRF protection.

### Frontend Files

The frontend assets are organized as follows:

*   **HTML Templates:** Located in `app/web/frontend/templates/`. These are Jinja2 templates rendered by Flask.
*   **CSS Files:** Source CSS is in `src/css/styles.css`. The compiled output is `static/css/main.css`. Additional CSS files for specific components (e.g., `python-editor.css`, `tradingview.css`) are located in `app/web/frontend/static/css/`.
*   **JavaScript Files:** Located in `app/web/frontend/static/js/`. These include application logic, theme management, and third-party libraries.
*   **Image & Favicon Files:** Located in `app/web/frontend/static/favicon/` and `app/web/frontend/static/images/`.
