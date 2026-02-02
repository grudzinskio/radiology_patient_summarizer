# Radiohead Backend

## Prerequisites

- Python 3.12+

You can download Python 3.12 here:  
https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe

## Installation

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment (optional but recommended):**

    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    *Note: If you need the specific spacy model:*
    ```bash
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
    ```

## Starting the Server

To run the server with hot-reload enabled (great for development), run the following command from the root of the project (or ensure your python path is set correctly):

```bash
# From the project root
python backend/src/main.py
```

The server will start at `http://127.0.0.1:8000`.

You can access the API documentation at `http://127.0.0.1:8000/docs`.
