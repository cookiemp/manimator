# Start with a slim, efficient Python base image
FROM python:3.11-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Install only the necessary dependencies. This is much smaller and faster.
# We are replacing the giant 'texlive-full' with a minimal set.
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    ffmpeg \
    libpango1.0-dev \
    # --- Minimal LaTeX installation ---
    texlive-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    dvisvgm \
    # ----------------------------------
    && rm -rf /var/lib/apt/lists/*

# Use pip to install the Manim library inside the container
RUN pip install manim

# Set a default command to run if the container is started without one.
CMD ["manim", "--help"]