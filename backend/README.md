# SwingLens Backend

FastAPI backend application for SwingLens.

## Setup Instructions

1. **Create Virtual Environment:**
   ```bash
   python3 -m venv .venv
   ```

2. **Activate Virtual Environment:**
   - **macOS/Linux:**
     ```bash
     source .venv/bin/activate
     ```
   - **Windows:**
     ```cmd
     .venv\Scripts\activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the FastAPI development server:
```bash
uvicorn app.main:app --reload
```

The server will run on `http://127.0.0.1:8000`.

## Health Check Endpoint

- **URL:** `/health`
- **Method:** `GET`
- **Response:** `{"status": "ok"}`
