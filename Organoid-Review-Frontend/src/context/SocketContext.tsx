import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';


export interface ServerLog {
    id?: number;
    timestamp: string;
    level: 'INFO' | 'ERROR' | 'SUCCESS' | 'DONE' | 'START' | 'BLENDER_COAT' | 'BLENDER_NUCLEI' | 'PIPELINE' | string;
    message: string;
    organoid_id: number | null;
}

export interface ServerState {
    status: 'waiting' | 'processing' | 'idle' | string;
    current_task: string | null;
}

interface OrganoidUpdateData {
    id: number;
    isProcessedGlb: boolean;
}

interface SocketContextType {
    socket: Socket | null;
    isConnected: boolean;
    logs: ServerLog[];
    serverState: ServerState;
    clearLogs: () => void;
}

const SOCKET_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/';

const SocketContext = createContext<SocketContextType | null>(null);

interface SocketProviderProps {
    children: ReactNode;
}

export const SocketProvider: React.FC<SocketProviderProps> = ({ children }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [logs, setLogs] = useState<ServerLog[]>([]);
    const [serverState, setServerState] = useState<ServerState>({ 
        status: 'unknown', 
        current_task: null 
    });

    useEffect(() => {
        const newSocket = io(SOCKET_URL, {
            transports: ['websocket'],
            autoConnect: true,
            reconnectionAttempts: 5,
        });

        setSocket(newSocket);

        // --- Obsługa zdarzeń ---

        newSocket.on('connect', () => {
            console.log('🔌 Socket connected:', newSocket.id);
            setIsConnected(true);
        });

        newSocket.on('disconnect', () => {
            console.log('❌ Socket disconnected');
            setIsConnected(false);
        });

        newSocket.on('connect_error', (err: Error) => {
            console.error('Socket connection error:', err);
        });


        newSocket.on('server_log', (newLog: ServerLog) => {
            setLogs((prevLogs) => [newLog, ...prevLogs].slice(0, 100));
        });

        newSocket.on('server_state', (state: ServerState) => {
            setServerState(state);
        });

        newSocket.on('organoid_update', (data: OrganoidUpdateData) => {
            console.log('✅ Organoid update received:', data);
            // Tutaj logika odświeżania, jeśli potrzebna
        });

        return () => {
            newSocket.close();
        };
    }, []);

    const clearLogs = () => setLogs([]);

    return (
        <SocketContext.Provider value={{ socket, isConnected, logs, serverState, clearLogs }}>
            {children}
        </SocketContext.Provider>
    );
};

export const useSocket = (): SocketContextType => {
    const context = useContext(SocketContext);
    if (!context) {
        throw new Error('useSocket must be used within a SocketProvider');
    }
    return context;
};