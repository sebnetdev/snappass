FROM python:2.7-slim

# Set the working directory to /app
WORKDIR /app

# Copy the snappass contents into the container at /app
COPY ./snappass /app
COPY requirements.txt /tmp

RUN pip install --trusted-host pypi.python.org -r /tmp/requirements.txt && \
	groupadd -r snappass && \
    useradd -r -g snappass snappass && \
    chown -R snappass /app && \
    chgrp -R snappass /app

USER snappass

# Default Flask port
EXPOSE 5000

# Define environment variable
ENV NAME SnapPass

CMD ["python", "main.py"]
