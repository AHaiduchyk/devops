# First stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Copy requirements file
COPY requirements.txt ./

# Install packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install additional required packages directly in the Dockerfile
RUN pip install --no-cache-dir \
    httplib2==0.22.0 \
    idna==3.7 \
    importlib_metadata==7.1.0 \
    itsdangerous==2.2.0 \
    Jinja2==3.1.4 \
    MarkupSafe==2.1.5 \
    oauthlib==3.2.2 \
    proto-plus==1.23.0 \
    protobuf==4.25.3 \
    pyasn1==0.6.0 \
    pyasn1_modules==0.4.0 \
    pyparsing==3.1.2 \
    pytz==2024.1 \
    requests==2.32.3 \
    requests-oauthlib==2.0.0 \
    rsa==4.9 \
    uritemplate==4.1.1 \
    urllib3==2.2.1 \
    Werkzeug==3.0.3 \
    zipp==3.19.1

# Second stage
FROM python:3.9-slim AS final

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Copy the rest of the application code
COPY . .


EXPOSE 8000


ENV FLASK_APP=app.py

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
