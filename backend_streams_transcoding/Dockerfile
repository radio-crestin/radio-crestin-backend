FROM mirror.gcr.io/library/python:3.12-alpine
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY controller.py /app/
WORKDIR /app
CMD ["python3", "controller.py"]
