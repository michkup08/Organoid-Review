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


export const fetchMetrics = async (organoidId: number): Promise<{ [key: string]: number }> => {
  if (organoidId === 0) return {};
  const response = await fetch(`${API_URL}metrics/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania metryk organoidu');
  }
  return response.json();
}

export const fetchOrthoSlices = async (organoidId: number): Promise<string> => {
  if (organoidId === 0) return '';
  const response = await fetch(`${API_URL}orthoSlices/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania porównania przekrojów organoidu');
  }
  const imageBlob = await response.blob();
  return URL.createObjectURL(imageBlob);
}

export const fetchLyapunovImage = async (organoidId: number): Promise<string> => {
  if (organoidId === 0) return '';
  const response = await fetch(`${API_URL}lyapunov/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania porównania przekrojów organoidu');
  }
  const imageBlob = await response.blob();
  return URL.createObjectURL(imageBlob);
}

type ChartDataLyapunov = {
  time: number[];
  log_distance: number[];
  trend_line: number[];
  lambda: number;
}

export const fetchLyapunovData = async (organoidId: number): Promise<ChartDataLyapunov> => {
  if (organoidId === 0) return null as any;
  const response = await fetch(`${API_URL}lyapunov_data/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania danych do wykresu Lyapunova organoidu');
  }
  return response.json();
}

type ChartDataOptymalizationHistory = {
  iteration: number[];
  D: number[];
  Rho: number[];
}

export const fetchOptimizationHistory = async (organoidId: number): Promise<ChartDataOptymalizationHistory> => {
  if (organoidId === 0) return null as any;
  const response = await fetch(`${API_URL}optimization_history/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania historii optymalizacji organoidu');
  }
  return response.json();
}

type ChartDataGlobalGwowth = {
  time: number[];
  real_total_intensity: number[];
  model_total_intensity: number[];
}

export const fetchGlobalGrowth = async (organoidId: number): Promise<ChartDataGlobalGwowth> => {
  if (organoidId === 0) return null as any;
  const response = await fetch(`${API_URL}global_growth/${organoidId}/`);
  if (!response.ok) {
    throw new Error('Wystąpił błąd podczas pobierania danych do wykresu globalnego wzrostu organoidu');
  }
  return response.json();
}

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

const processOrganoid = async ({ organoidId }: {organoidId: number}): Promise<any> => {
  const formData = new FormData();
  formData.append('organoidId', organoidId.toString());

  const response = await fetch(`${API_URL}organoid/process/`, {
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

export const useProcessOrganoid = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ( organoidId: number ) => processOrganoid({ organoidId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organoidModel'] });
    },
  });
};

export const useMetrics = (organoidId: number) => {
  return useQuery({
    queryKey: ['metrics', organoidId], 
    queryFn: () => fetchMetrics(organoidId),
  });
}

export const useOrthoSlices = (organoidId: number) => {
  return useQuery({
    queryKey: ['orthoSlices', organoidId], 
    queryFn: () => fetchOrthoSlices(organoidId),
  });
}

export const useLyapunov = (organoidId: number) => {
  return useQuery({
    queryKey: ['lyapunovImage', organoidId], 
    queryFn: () => fetchLyapunovImage(organoidId),
  });
}

export const useLyapunovData = (organoidId: number) => {
  return useQuery({
    queryKey: ['lyapunovData', organoidId], 
    queryFn: () => fetchLyapunovData(organoidId),
  });
}

export const useOptimizationHistory = (organoidId: number) => {
  return useQuery({
    queryKey: ['optimizationHistory', organoidId], 
    queryFn: () => fetchOptimizationHistory(organoidId),
  });
}

export const useGlobalGrowth = (organoidId: number) => {
  return useQuery({
    queryKey: ['globalGrowth', organoidId], 
    queryFn: () => fetchGlobalGrowth(organoidId),
  });
}