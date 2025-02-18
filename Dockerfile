# Use official Python image
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Copy requirements from app directory
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code from the correct location
COPY app/ .

# Expose port 5000 for Flask
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
