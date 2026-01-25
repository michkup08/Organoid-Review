import { useQuery } from '@tanstack/react-query';

const API_URL = import.meta.env.VITE_API_URL;

export interface Organoid {
  id: number;
  name: string;
}

const fetchOrganoids = async (): Promise<Organoid[]> => {
  const response = await fetch(`${API_URL}/organoid/`);
  
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania organoidów');
  }

  return response.json();
};

export const useOrganoids = () => {
  return useQuery({
    queryKey: ['organoidModel'], 
    queryFn: fetchOrganoids,
  });
};