# Optional NIP-57 zap receipt signing key.
# Put the key (hex or nsec) in data/nip57-private-key inside the app data folder,
# then restart the app. If the file is missing, zap receipts stay disabled.
if [ -f "${APP_DATA_DIR}/data/nip57-private-key" ]; then
    export NIP57_PRIVATE_KEY="$(tr -d '[:space:]' < "${APP_DATA_DIR}/data/nip57-private-key")"
fi
