# Wybierz obraz bazowy Node.js (wersja alpine jest lżejsza)
FROM node:24-alpine

# Ustaw katalog roboczy w kontenerze
WORKDIR /app

# Skopiuj pliki zależności
COPY package.json package-lock.json ./

# Zainstaluj zależności
RUN npm install

# Skopiuj resztę plików aplikacji
COPY . .

# Otwórz port, na którym działa React (domyślnie 3000)
EXPOSE 5173

# Komenda startowa
CMD ["npm", "run", "dev"]