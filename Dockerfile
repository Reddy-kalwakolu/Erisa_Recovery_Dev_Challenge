# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy and install dependencies
# This is done first to leverage Docker's layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port gunicorn will run on
EXPOSE 8080

# Run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "erisa_project.wsgi:application"]