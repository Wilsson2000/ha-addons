ARG BUILD_FROM
FROM ${BUILD_FROM}

# Upstream start.py always authenticates with the Supervisor token, which acts
# as a system user. Patch it so a long-lived token from a real admin account is
# used when set, so per-user things (like the Marketplace warning) apply.
COPY patch_start.py /patch_start.py
RUN python3 /patch_start.py /start.py && rm /patch_start.py

CMD ["python3", "/start.py"]
