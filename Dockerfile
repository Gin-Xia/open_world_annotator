FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /opt/ml/model

COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt

COPY backend /opt/ml/model/backend
COPY backend/inference/inference.py /opt/ml/model/inference.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/opt/ml/model

ENTRYPOINT ["python", "inference.py"]
