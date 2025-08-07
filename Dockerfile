FROM python:3.13.5-slim
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
USER app
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]