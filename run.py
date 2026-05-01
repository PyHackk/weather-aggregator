# run.py
"""Application entry point."""
from app import create_app

app = create_app('development')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
    
    
    
    
    
    
    
    
    
    
    #!/bin/bash
set -e

# ==============================================================================
# QDI API - Container Entrypoint
# ------------------------------------------------------------------------------
# Loads internal SSL certificates into the system trust store so the application
# can establish secure connections to CyberArk, S3, and other internal services.
#
# This runs once at container startup, before handing off to the main process
# (gunicorn for the API, celery for the worker).
# ==============================================================================

CERTS_DIR="/app/certs"
SYSTEM_CERTS_DIR="/usr/local/share/ca-certificates"

echo "[entrypoint] Starting certificate loading process..."

if [ -d "$CERTS_DIR" ]; then
    cert_count=0

    # Copy each .pem file into the system trust store with a .crt extension
    # (update-ca-certificates only registers files ending in .crt)
    for cert in "$CERTS_DIR"/*.pem; do
        [ -f "$cert" ] || continue
        filename=$(basename "$cert" .pem)
        cp "$cert" "$SYSTEM_CERTS_DIR/${filename}.crt"
        cert_count=$((cert_count + 1))
        echo "[entrypoint] Loaded certificate: ${filename}.pem"
    done

    if [ "$cert_count" -gt 0 ]; then
        update-ca-certificates --fresh > /dev/null 2>&1
        echo "[entrypoint] Successfully registered $cert_count certificate(s)"
    else
        echo "[entrypoint] No .pem certificates found in $CERTS_DIR"
    fi

    # Tell Python's requests and httpx libraries where the trust bundle lives
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    echo "[entrypoint] Python SSL environment configured"

else
    echo "[entrypoint] WARNING: $CERTS_DIR not found, skipping certificate loading"
fi

echo "[entrypoint] Startup complete. Launching: $@"
echo "------------------------------------------------------------"

# Hand off control to the actual service command (defined in api.yml)
exec "$@"






# Install the entrypoint script that loads SSL certificates at startup
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Every container built from this image runs the entrypoint first.
# The entrypoint loads SSL certs, then executes whatever command is passed.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command (overridden per-service in qdi-api.yml)
CMD ["/bin/bash"]







sudo docker exec -it $(sudo docker ps -q -f name=api_api) python3 -c "
import requests
try:
    r = requests.get('https://cmppcia-docker.artifactory.cib.echonet', timeout=5, verify=True)
    print(f'SSL handshake OK - HTTP status: {r.status_code}')
except requests.exceptions.SSLError as e:
    print(f'SSL FAILED: {e}')
except Exception as e:
    print(f'Other error (not SSL related): {type(e).__name__}: {e}')
"
