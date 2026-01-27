import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

const API_URL = import.meta.env.VITE_API_URL;

export interface Organoid {
  id: number;
  name: string;
  isInitialized?: boolean;
  isProcessedGlb?: boolean;
  isInCurrentRdf?: boolean;
}

export interface OrganoidUploadPayload {
  name: string;
  file: File;
  
}

const fetchOrganoids = async (): Promise<Organoid[]> => {
  const response = await fetch(`${API_URL}organoid/`);
  
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania organoidów');
  }

  return response.json();
};

const fetchOrganoid = async (id: number): Promise<Organoid> => {
  const response = await fetch(`${API_URL}organoid/${id}/`);
  
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania organoidów');
  }

  return response.json();
};

const uploadOrganoid = async ({ name, file }: OrganoidUploadPayload): Promise<any> => {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('file', file);

  const response = await fetch(`${API_URL}dataset/`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Wystąpił błąd podczas dodawania organoidu');
  }

  return response.json();
};

export const useOrganoid = (id: number) => {
  return useQuery({
    queryKey: ['organoidModel', id], 
    queryFn: () => fetchOrganoid(id),
  });
};


export const useOrganoids = () => {
  return useQuery({
    queryKey: ['organoidModel'], 
    queryFn: fetchOrganoids,
  });
};

export const useCreateOrganoid = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadOrganoid,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organoidModel'] });
    },
  });
};