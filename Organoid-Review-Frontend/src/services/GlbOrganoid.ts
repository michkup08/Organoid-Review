import { useQuery } from '@tanstack/react-query';

const API_URL = import.meta.env.VITE_API_URL;

const fetchOrganoidModel = async ({id, type} : {id: number, type: 'inner' | 'outer'}): Promise<any> => {
    const response = await fetch(`${API_URL}/organoid/${id}/${type}`);
    
    if (!response.ok) {
        throw new Error('Wystąpił błąd podczas pobierania organoidów');
    }

    return response.json();
};

export const useOrganoidModel = ({id, type} : {id: number, type: 'inner' | 'outer'}) => {
//   return useQuery({
//     queryKey: ['organoids'], 
//     queryFn: () => fetchOrganoidModel({id, type}),
//   });
    const url = id ? `${API_URL}/organoid/${id}/${type}` : null;

    return {
        data: url,       // Tutaj zwracamy string (URL), a nie Blob/JSON
        isLoading: false,// "Pobieranie" w tym hooku jest natychmiastowe (bo tylko tworzymy string)
                        // Prawdziwe ładowanie obsłuży <Suspense> w Canvasie
        error: null
    };
};