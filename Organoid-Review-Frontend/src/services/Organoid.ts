import { useQuery } from '@tanstack/react-query';

// Ustawienie adresu API (możesz to przenieść do zmiennych środowiskowych .env)
const API_URL = 'http://localhost:5000';

// Definicja typu danych (zgodna z tym co zwraca Twój Python)
export interface Organoid {
  id: number;
  name: string;
}

// 1. Czysta funkcja fetchująca (API Call)
const fetchOrganoids = async (): Promise<Organoid[]> => {
  const response = await fetch(`${API_URL}/organoid/`);
  
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania organoidów');
  }

  return response.json();
};

// 2. Custom Hook (React Query)
export const useOrganoids = () => {
  return useQuery({
    queryKey: ['organoids'], // Unikalny klucz do cache'owania
    queryFn: fetchOrganoids,
    staleTime: 1000 * 60 * 5, // (Opcjonalnie) Dane są świeże przez 5 minut
  });
};