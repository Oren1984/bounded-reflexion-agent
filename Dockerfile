# syntax=docker/dockerfile:1
# Sandbox image: the only place agent-generated code is executed.
# It contains Python and pytest, nothing else. No project code, no credentials.
FROM python:3.12-slim

# Optional: behind a TLS-inspecting proxy, pass the proxy CA bundle as a build secret
#   docker build --secret id=ca,src=/path/to/ca-bundle.pem -t bra-sandbox .
# Without the secret this is a plain pip install.
RUN --mount=type=secret,id=ca,target=/tmp/ca.pem,required=false \
    if [ -s /tmp/ca.pem ]; then export PIP_CERT=/tmp/ca.pem; fi \
    && pip install --no-cache-dir pytest==9.1.1 \
    && useradd --uid 1000 --create-home sandbox

USER sandbox
WORKDIR /eval
