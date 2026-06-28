# Use a slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Make sure the data directory exists
RUN mkdir -p data

# Install apscheduler for in-container scheduling
RUN pip install apscheduler

# Expose port for Streamlit (optional)
EXPOSE 8501

# Run the master script that starts both the bot and the scheduler
CMD ["python", "run_production.py"]