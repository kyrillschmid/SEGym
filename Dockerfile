FROM python:3.12-bookworm

# Set the working directory to /app
WORKDIR /app

RUN pip install pytest numpy

# TODO: Install requirements.txt
