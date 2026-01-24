Here's the Python 3.12.9 download link:

**Windows 64-bit installer:**
[https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe](https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe)

cd C:\Users\weinbendera\Repos\hack-4-health-2026-radiohead

# Create new venv with Python 3.12

py -3.12 -m venv .venv

# Activate it

.venv\Scripts\activate

# Install everything

pip install -r requirements.txt

# After pip install -r requirements.txt, run:

pip install scipy  # Install first with prebuilt wheels

SciSpaCy model - en_core_sci_md-0.5.4
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz --no-deps
```

Choose a Linker. (MESH recommended for Demos)

MESH Linker - 500MB - (Less data but faster, still medically focused)
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz
```

UMLS Linker - WARNING 3GB
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz
```

# Start server

uvicorn backend.app.main:app --reload
