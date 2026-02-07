import { ArrowLeft} from "@mui/icons-material";
import ModelInterface from "../components/ModelInterface";
import { useNavigate, useParams } from "react-router-dom";
import { useGlobalGrowth, useLyapunov, useLyapunovData, useMetrics, useOptimizationHistory, useOrganoid, useOrthoSlices, useProcessOrganoid } from "../services/Organoid";
import { useSocket } from "../context/SocketContext";
import { Line } from 'react-chartjs-2';
import { useEffect, useRef } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { useGeminiResponse } from "../services/Gemini";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const SingleSetInterface = () => {
  const navigate = useNavigate();
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const { id } = useParams();
  const { data: organoidData, isLoading, error } = useOrganoid(+(id ?? 0));
  const { serverState, isConnected } = useSocket();
  const { mutate: processOrganoid } = useProcessOrganoid();
  const { data: metricsData } = useMetrics(+(id ?? 0));
  const { data: orthoSlicesData } = useOrthoSlices(+(id ?? 0));
  const { data: lyapunovDataForChart } = useLyapunovData(+(id ?? 0));
  const { data: optymazationHistoryData } = useOptimizationHistory(+(id ?? 0));
  const { data: globalGrowthData } = useGlobalGrowth(+(id ?? 0));

  const { mutate: geminiQuestion, data: geminiResponse, isPending: geminiLoading, error: geminiError } = useGeminiResponse(
    `Przeanalizuj wyniki modelu dyfuzji dla organoidu o id ${id}. 
    
    Podsumuj kluczowe metryki i oceń jakość dopasowania.
    Oto surowe dane do analizy:
    
    1. Metryki (Metrics): 
    ${metricsData ? JSON.stringify(metricsData, null, 2) : 'brak danych'}
    
    2. Dane wykresu Lyapunova (Lyapunov Chart Data): 
    ${lyapunovDataForChart ? JSON.stringify(lyapunovDataForChart) : 'brak danych'}
    
    3. Historia optymalizacji (Optimization History): 
    ${optymazationHistoryData ? JSON.stringify(optymazationHistoryData) : 'brak danych'}
    
    4. Globalny wzrost (Global Growth): 
    ${globalGrowthData ? JSON.stringify(globalGrowthData) : 'brak danych'}`
  );

  useEffect(() => {
    if (!geminiLoading && geminiResponse) {
      mainContainerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
    
  }, [geminiLoading, geminiResponse]);

  return (
    <div 
      style={{ width: 'calc(100vw - 15px)', minHeight: '100vh', background: '#e8e8e8', display: 'flex', flexDirection: 'column' }}
      ref={mainContainerRef}>
      <div style={{ 
        padding: '20px', 
        background: '#eee', 
        boxShadow: '0 -7px 10px rgba(0,0,0,0.1)',
        flexGrow: 1,
        borderRadius: '20px',
        margin: '10px',
        minHeight: '600px',
        display: 'flex', 
        flexDirection: 'column',
      }}>
        <label
          style={{
            fontSize: '18px',
            fontWeight: 'bold',
            marginBottom: '10px',
            marginLeft: '80px'
          }}
        >
          Reprezentacja modelu 3D:
        </label>
        {isLoading ? (
          <div style={{marginLeft: '80px'}}>
            <label>Ładowanie danych organoidu...</label>
          </div>
        ) : error ? (
          <div style={{marginLeft: '80px'}}>
            <label>Błąd: {error?.message}</label>
          </div>
        ) : !organoidData?.isInitialized ? (
          <div style={{marginLeft: '80px', display: 'flex', flexDirection: 'column', gap: '10px'}}>
            <label>Organoid nie został jeszcze zainicjalizowany.</label>
            <button
              className="sendButton"
              style={{maxWidth: 300}}
              onClick={() => {
                processOrganoid(+(id ?? 0));
                navigate('/');
              }}
              disabled={serverState.status == 'processing' || serverState.current_task !== null || !isConnected}
            >
              Generuj plik glb
            </button>
          </div>
        ) : !organoidData?.isProcessedGlb ? (
          <div style={{marginLeft: '80px'}}>
            <label>Model organoidu nie został jeszcze utworzony</label>
            <button
              className="sendButton"
              style={{maxWidth: 300}}
              onClick={() => {
                processOrganoid(+(id ?? 0));
                navigate('/');
              }}
              disabled={serverState.status == 'processing' || serverState.current_task !== null || !isConnected}
            >
              Generuj plik glb
            </button>
          </div>
        ) : (
          <ModelInterface orgId={+(id ?? 0)} />
        )}
        
      </div>
      {<div
        style={{ 
          padding: '20px', 
          background: '#eee', 
          boxShadow: '0 -7px 10px rgba(0,0,0,0.1)',
          borderRadius: '20px',
          margin: '10px'
        }}
      >
        <label
          style={{
            fontSize: '18px',
            fontWeight: 'bold',
          }}
        >
          Zamodelowany model dyfuzji ciała organoidu (przekrój i rozkład w 3D):
        </label>
        <div style={{
          display: 'flex', 
          flexDirection: 'column',
          gap: '20px',
          marginTop: '10px'
          }}>
          <div style={{
            flexGrow: 1,
            maxWidth: '100%'
          }}>
            <img 
                src={orthoSlicesData}
                alt="Maski" 
                style={{ 
                  objectFit: 'contain', 
                  borderRadius: '20px',
                  width: '100%',
                  height: 'auto',
                }} 
              />
          </div>
          <div style={{ 
            flexGrow: 1,
            maxWidth: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            
          }}>
            {metricsData && (
              <table style={{ backgroundColor: '#fff', padding: 10, borderRadius: 20, borderCollapse: 'collapse' }}>
                <tbody>
                  {Object.entries(metricsData).map(([key, value]) => (
                    <tr key={key}>
                      <td style={{ padding: '5px 10px', fontWeight: 'bold' }}>{key}</td>
                      <td style={{ padding: '5px 10px' }}>{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
      </div>
      <div style={{ 
        flexGrow: 1,
        maxWidth: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        
      }}>
        {lyapunovDataForChart && <Line
          options={{
            responsive: true,
            plugins: {
              legend: {
                position: 'top' as const,
              },
              title: {
                display: true,
                text: 'Wykres wykładnika Lyapunova',
              },
            },
          }}
          data={{
            labels: lyapunovDataForChart?.time,
            datasets: [
              {
                label: 'log_distance',
                data: lyapunovDataForChart?.log_distance,
                borderColor: 'blue',
              },
              {
                label: 'trend_line',
                data: lyapunovDataForChart?.trend_line,
                borderColor: 'red',
              }
            ]
          }}
        />}
      </div>
      <div style={{ 
        flexGrow: 1,
        maxWidth: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        
      }}>
        {optymazationHistoryData && <Line
          options={{
            responsive: true,
            plugins: {
              legend: {
                position: 'top' as const,
              },
              title: {
                display: true,
                text: 'Proces optymalizacji - historia zmian parametrów D i Rho',
              },
            },
          }}
          data={{
            labels: optymazationHistoryData?.iteration,
            datasets: [
              {
                label: 'D',
                data: optymazationHistoryData?.D,
                borderColor: 'yellow',
              },
              {
                label: 'Rho',
                data: optymazationHistoryData?.Rho,
                borderColor: 'green',
              }
            ]
          }}
        />}
      </div>
      <div style={{ 
        flexGrow: 1,
        maxWidth: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        
      }}>
        {globalGrowthData && <Line
          options={{
            responsive: true,
            plugins: {
              legend: {
                position: 'top' as const,
              },
              title: {
                display: true,
                text: 'Proces optymalizacji - historia zmian parametrów D i Rho',
              },
            },
          }}
          data={{
            labels: globalGrowthData?.time,
            datasets: [
              {
                label: 'D',
                data: globalGrowthData?.real_total_intensity,
                borderColor: 'blue',
              },
              {
                label: 'Rho',
                data: globalGrowthData?.model_total_intensity,
                borderColor: 'red',
              }
            ]
          }}
        />}
      </div>
      <div>
          <button 
            onClick={() => {geminiQuestion()}}
            className="sendButton"
            disabled={geminiLoading}>
            {geminiLoading ? 'Generowanie...' : 'Analiuj wyniki modelu'}
          </button>
          {geminiResponse && (
            <div style={{ marginTop: '20px', background: '#f0f0f0', padding: '10px', borderRadius: '10px' }}>
              <strong>Analiza wyników modelu:</strong>
              <p>{geminiResponse}</p>
            </div>
          )}
          {geminiError && (
            <div style={{ marginTop: '20px', background: '#f0f0f0', padding: '10px', borderRadius: '10px' }}>
              <strong>Błąd podczas analizy wyników modelu:</strong>
              <p>{geminiError.message}</p>
            </div>
          )}
      </div>
      </div>}
      <div style={{ 
          padding: '5px', 
          background: '#eee',
          boxShadow: '0 0px 5px rgba(0,0,0,0.5)',
          opacity: 0.8,
          position: 'fixed',
          top: '20px',
          left: '20px',
          zIndex: 1000,
          borderRadius: '50%',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '50px',
          height: '50px'
        }}
        onClick={() => { navigate('/')}}
        >
        <ArrowLeft style={{ color: 'black', cursor: 'pointer', width: '40', height: '40'}}/>
      </div>
    </div>
  );
}

export default SingleSetInterface;