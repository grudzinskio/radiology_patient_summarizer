cd C:\Users\weinbendera\Repos\hack-4-health-2026-radiohead

# Create new venv with Python 3.12

py -3.12 -m venv .venv

# Activate it

.venv\Scripts\activate

# Install everything

pip install -r requirements.txt

# After pip install -r requirements.txt, run:

pip install scipy  # Install first with prebuilt wheels
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz --no-deps

# Start server

uvicorn backend.app.main:app --reload
