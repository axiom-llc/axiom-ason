FROM python:3.12-slim
WORKDIR /app
COPY axiom-apex /app/axiom-apex
COPY axiom-ason /app/axiom-ason
RUN pip install --no-cache-dir /app/axiom-apex
RUN pip install --no-cache-dir -e /app/axiom-ason
CMD ["tail", "-f", "/dev/null"]
