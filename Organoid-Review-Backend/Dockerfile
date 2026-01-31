# BAZA: Czyste Ubuntu 22.04 (zamiast obrazu MathWorks)
FROM ubuntu:22.04

# Zapobiega pytaniom o strefę czasową podczas instalacji apt
ENV DEBIAN_FRONTEND=noninteractive

USER root

# 1. Instalacja Pythona, narzędzi systemowych i bibliotek dla Blendera
# libgl1-mesa-glx, libxi6, etc. są krytyczne, aby Blender ruszył na Linuxie
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    build-essential \
    libmysqlclient-dev \
    wget \
    xz-utils \
    pkg-config \
    libgl1-mesa-glx \
    libxi6 \
    libxrender1 \
    libxxf86vm1 \
    libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# 2. Tworzymy środowisko wirtualne (VENV)
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Aktualizujemy pip
RUN pip install --upgrade pip

# 3. Instalacja Blendera (Wersja 3.6 LTS)
WORKDIR /opt/blender
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.5-linux-x64.tar.xz \
    && tar -xvf blender-3.6.5-linux-x64.tar.xz --strip-components=1 \
    && rm blender-3.6.5-linux-x64.tar.xz
ENV PATH="/opt/blender:$PATH"

# 4. Konfiguracja aplikacji Python
WORKDIR /app
COPY requirements.txt .

# Instalacja bibliotek (Flask, SQLAlchemy itp.)
RUN pip install --no-cache-dir -r requirements.txt

# --- TU BYŁA INSTALACJA MATLAB ENGINE - USUNIĘTA ---

# 5. Kopiowanie kodu aplikacji
COPY . .

# Tworzenie folderów na dane
RUN mkdir -p tiffs matlab glbs/inner glbs/outer blender_scripts

# 6. Tworzenie użytkownika (bezpieczeństwo)
# Nie używamy już usera 'matlab', tworzymy własnego 'appuser'
RUN useradd -m -s /bin/bash appuser
RUN chown -R appuser:appuser /app /opt/venv

# Przełączenie na zwykłego użytkownika
USER appuser

EXPOSE 5000

CMD ["sh", "-c", "flask db upgrade && python app.py"]