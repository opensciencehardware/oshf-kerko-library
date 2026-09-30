FROM whiskyechobravo/kerkoapp:1.3.0

# Dependencies for scripts/build_covers.py: poppler renders PDF first pages,
# pdf2image/pillow handle the images, requests downloads covers from URLs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pdf2image pillow requests
