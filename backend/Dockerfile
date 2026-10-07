# backend/Dockerfile  
# ================================
# TODO: Complete this Dockerfile so the backend can run inside Docker.
# Refer to the Dockerfile Creation lesson (Lesson 6) for guidance.
#
# Steps to implement:
#   1. Choose a base image — python:3.11-slim is a good choice
#   2. Set a working directory  (e.g. /app)
#   3. Copy requirements.txt and install dependencies with pip
#   4. Copy the rest of the source code
#   5. Expose the port uvicorn will listen on (8000)
#   6. Set the CMD to start uvicorn
#      Hint: uvicorn main:app --host 0.0.0.0 --port 8000

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]