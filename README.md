# SwingLens

## Description
   SwingLens is a monorepo application structured with a React frontend and a FastAPI backend.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Testing:** Pytest

## Frontend Setup & Run Commands

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```

## Backend Setup & Run Commands

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Set up virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run FastAPI development server:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Current Status
Initial project template — no trading logic implemented.
# SwingLens
