# Organoid Review System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-18-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Status](https://img.shields.io/badge/Status-v1.0-blue)

Kompleksowa platforma do analizy, wizualizacji 3D i modelowania matematycznego organoidów.

System umożliwia przetwarzanie surowych danych mikroskopowych (`.tif`), generowanie modeli 3D (`.glb`) oraz przeprowadzanie symulacji reakcji-dyfuzji.

---

## ✨ Kluczowe Funkcjonalności

* **Przetwarzanie Obrazu:** Automatyczna konwersja stosów TIFF do meshy 3D.
* **Wizualizacja 3D:** Interaktywny podgląd organoidów w przeglądarce (React Three Fiber).
* **Modelowanie Matematyczne:** Symulacja wzrostu organoidów oparta na równaniach różniczkowych cząstkowych i modelu Reaction-Diffusion.
* **AI Analysis:** Integracja z **Google Gemini** do automatycznej interpretacji wyników symulacji i oceny jakości dopasowania modelu.
* **Metryki:** Obliczanie RMSE, AIC, korelacji Pearsona/Spearmana oraz stabilności Lapunowa.

### Wymagania
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Git

### How to run

```bash
git clone [https://github.com/michkup08/organoid-review.git](https://github.com/michkup08/organoid-review.git)
cd organoid-review
cp .env.example .env
# Uzupełnij .env o odpowiednie hasła/klucze/ścieżki