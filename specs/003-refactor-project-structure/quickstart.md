# Quickstart Guide

**Feature**: Project Restructuring and Validation
**Date**: 2025-10-19

This guide explains how to set up and run the restructured OpenAlgo application.

## Prerequisites

- Python 3.11
- `uv` for installing dependencies from `pyproject.toml`
- Node.js and `npm` for frontend asset building

## Installation

1.  **Install Python dependencies**:
    ```bash
    uv sync
    ```
    *(Note: Assuming a `pyproject.toml` have all dependencies installed)*

2.  **Install frontend dependencies**:
    No need because it is based on html and css with jinja2.

3.  **Build frontend assets**:
    No need because it is based on html and css with jinja2.

## Running the Application

1.  **Start the application**:
    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

2.  **Access the application**:
    The application will be available at `http://0.0.0.0:8000`.
