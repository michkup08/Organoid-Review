import React, { useState, Suspense, useEffect, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, Html, useProgress } from '@react-three/drei';
import { DualSyncedModels } from './ModelReview';
import { Pause, PlayArrow } from '@mui/icons-material';
import { useOrganoidModel } from '../services/GlbOrganoid';

function Loader() {
  const { progress } = useProgress();
  return <Html center style={{ color: 'black' }}>{progress.toFixed(0)} % loaded</Html>;
}

const getModelUrl = (data: any): string | null => {
  if (!data) return null;
  if (data instanceof Blob) {
    return URL.createObjectURL(data);
  }
  if (typeof data === 'string') {
    return data;
  }
  return null;
};

const ModelInterface = ({ orgId }: { orgId?: number }) => {
  const [sliderValue, setSliderValue] = useState(0.0);
  const [isPlaying, setIsPlaying] = useState(false);

  const { data: innerModelData, isLoading: innerLoading } = orgId 
    ? useOrganoidModel({ id: orgId, type: 'inner' }) 
    : { data: null, isLoading: false };
    
  const { data: outerModelData, isLoading: outerLoading } = orgId 
    ? useOrganoidModel({ id: orgId, type: 'outer' }) 
    : { data: null, isLoading: false };

  const innerUrl = useMemo(() => getModelUrl(innerModelData), [innerModelData]);
  const outerUrl = useMemo(() => getModelUrl(outerModelData), [outerModelData]);

  useEffect(() => {
    return () => {
      if (innerUrl && innerUrl.startsWith('blob:')) URL.revokeObjectURL(innerUrl);
      if (outerUrl && outerUrl.startsWith('blob:')) URL.revokeObjectURL(outerUrl);
    };
  }, [innerUrl, outerUrl]);

  useEffect(() => {
    let intervalId: number;
    if (isPlaying) {
      intervalId = setInterval(() => {
        setSliderValue((prev) => {
          if (prev >= 1.0) {
            setIsPlaying(false);
            return 1.0;
          }
          return Math.min(prev + 0.003, 1.0);
        });
      }, 16);
    }
    return () => { if (intervalId) clearInterval(intervalId); };
  }, [isPlaying]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSliderValue(parseFloat(e.target.value));
  };

  const isReady = !innerLoading && !outerLoading && innerUrl && outerUrl;

  return (
    <div style={{ background: '#eee', display: 'flex', flexDirection: 'column', height: '100%', flexGrow: 1 }}>
      
      <div style={{ flexGrow: 1, position: 'relative', minHeight: 0 }}>
        {!isReady ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
             {orgId ? "Pobieranie modeli..." : "Wybierz organoid, aby załadować model."}
          </div>
        ) : (
          <Canvas 
            camera={{ position: [0, 2, 5], fov: 50 }}
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
          >
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
            <Environment preset="city" />
            
            <Suspense fallback={<Loader />}>
              <DualSyncedModels
                innerUrl={innerUrl}
                outerUrl={outerUrl}
                animationProgress={sliderValue}
              />
            </Suspense>
            <OrbitControls makeDefault />
          </Canvas>
        )}
      </div>

      <div style={{ 
        padding: '20px', 
        background: '#eee', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        opacity: isReady ? 1 : 0.5,
        pointerEvents: isReady ? 'all' : 'none'
      }}>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          style={{ 
            marginBottom: '10px', background: 'white', borderRadius: '20%', 
            width: '60px', height: '40px', display: 'flex', alignItems: 'center', 
            justifyContent: 'center', cursor: 'pointer', boxShadow: '0 2px 5px rgba(0,0,0,0.2)' 
          }}
        >
          {isPlaying ? <Pause style={{ color: 'black' }} /> : <PlayArrow style={{ color: 'black' }} />}
        </button>
        
        <input
          type="range"
          min="0.0"
          max="1.0"
          step="0.001"
          value={sliderValue}
          onChange={handleSliderChange}
          style={{ width: '80%', cursor: 'pointer' }}
        />
      </div>
    </div>
  );
};

export default ModelInterface;