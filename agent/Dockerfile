FROM python:3.11-slim

WORKDIR /app

COPY agent/requirements.txt /app/agent-requirements.txt
RUN pip install --no-cache-dir -r /app/agent-requirements.txt

# Copy the agent
COPY agent/ /app/agent/

ENV PYTHONPATH=/app

CMD ["python", "-m", "agent.main"]
