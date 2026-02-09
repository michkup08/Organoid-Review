import React from 'react';
import { useSocket, type ServerLog } from '../context/SocketContext';

// Definiujemy propsy dla komponentu
interface LogTerminalProps {
    currentOrganoidId?: number | null; // Opcjonalny, bo może być widok ogólny
}

const LogTerminal: React.FC<LogTerminalProps> = ({ currentOrganoidId }) => {
    const { logs, isConnected, serverState, clearLogs } = useSocket();

    const filteredLogs = logs.filter((log) => 
        currentOrganoidId == undefined || log.organoid_id == null || (currentOrganoidId != undefined && log.organoid_id == currentOrganoidId)
    );

    // Pomocnicza funkcja do kolorowania logów
    const getLogColor = (level: string) => {
        switch (level) {
            case 'ERROR': return '#f44336';
            case 'SUCCESS':
            case 'DONE': return '#4caf50';
            case 'BLENDER_COAT': return '#c586c0'; // Fioletowy
            case 'BLENDER_NUCLEI': return '#569cd6'; // Niebieski
            case 'START': return '#dcdcaa'; // Żółtawy
            default: return '#ce9178'; // Standardowy (np. INFO)
        }
    };

    return (
        <div style={{ 
            backgroundColor: '#1e1e1e', 
            color: '#d4d4d4', 
            padding: '20px', 
            borderRadius: '8px', 
            fontFamily: 'Consolas, "Courier New", monospace',
            marginTop: '20px',
            maxHeight: '400px',
            display: 'flex',
            flexDirection: 'column'
        }}>
            {/* Header */}
            <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                marginBottom: '10px', 
                borderBottom: '1px solid #333',
                paddingBottom: '10px'
            }}>
                <span style={{ fontSize: '0.9rem' }}>
                    STATUS: <span style={{ color: isConnected ? '#4caf50' : '#f44336', fontWeight: 'bold' }}>
                        {isConnected ? 'ONLINE' : 'OFFLINE'}
                    </span> 
                    {' | '} 
                    SERVER: <span style={{ color: '#fff' }}>{serverState.status}</span>
                    {serverState.current_task && <span style={{color: '#888', fontSize: '0.8em'}}> ({serverState.current_task})</span>}
                </span>
                
                <button 
                    onClick={clearLogs} 
                    style={{ 
                        background: 'transparent', 
                        border: '1px solid #444', 
                        color: '#aaa', 
                        cursor: 'pointer',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.8rem'
                    }}
                >
                    Clear
                </button>
            </div>

            <div style={{ 
                flex: 1, 
                display: 'flex',
                flexDirection: 'column-reverse',
                overflowY: 'auto', 
                paddingRight: '5px' 
            }}>
                {filteredLogs.length == 0 && (
                    <p style={{ color: '#555', textAlign: 'center', marginTop: '20px' }}>
                        Waiting for logs...
                    </p>
                )}
                
                {filteredLogs.map((log: ServerLog, index: number) => {
                    // Bezpieczne parsowanie daty (zakładamy format ISO)
                    const timeString = log.timestamp.split('T')[1]?.split('.')[0] || log.timestamp;

                    return (
                        <div key={index} style={{ 
                            marginBottom: '4px', 
                            borderLeft: log.level == 'ERROR' ? '3px solid #f44336' : '3px solid transparent', 
                            paddingLeft: '8px',
                            lineHeight: '1.4',
                            fontSize: '0.9rem'
                        }}>
                            <span style={{ color: '#6a9955', marginRight: '8px' }}>
                                [{timeString}]
                            </span>
                            <span style={{ 
                                fontWeight: 'bold', 
                                color: getLogColor(log.level),
                                marginRight: '8px'
                            }}>
                                [{log.level}]
                            </span>
                            <span style={{ whiteSpace: 'pre-wrap' }}>
                                {log.message}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LogTerminal;