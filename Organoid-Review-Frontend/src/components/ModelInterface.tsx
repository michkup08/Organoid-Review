import React, { useState, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, Html, useProgress } from '@react-three/drei';
import ModelReview from './ModelReview';
import { PlayArrow } from '@mui/icons-material';

function Loader() {
  const { progress } = useProgress();
  return <Html center style={{ color: 'black' }}>{progress.toFixed(0)} % loaded</Html>;
}

const ModelInterface = () => {
  // Stan dla suwaka (od 0.0 do 1.0)
  const [sliderValue, setSliderValue] = useState(0.0);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSliderValue(parseFloat(e.target.value));
  };

  return (
    <div style={{ background: '#eee', display: 'flex', flexDirection: 'column', height: '100%' }}>
      
      {/* --- Kontener 3D --- */}
      <div style={{ flexGrow: 1 }}>
        <Canvas camera={{ position: [0, 2, 5], fov: 50 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
          <Environment preset="city" />

          <Suspense fallback={<Loader />}>
            <ModelReview 
              url="/models/animacja1.glb" 
              animationProgress={sliderValue}
              opacity={0.5}
            />
          </Suspense>
          <OrbitControls makeDefault />
        </Canvas>
      </div>

      <div style={{ 
        padding: '20px', 
        background: '#eee', 
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        boxShadow: '10 10px 10px rgba(0,0,0,0.1)'
      }}>
        <button
          style={{ 
            marginBottom: '10px',
            background: 'white',
            borderRadius: '20%',
            width: '60px',
            height: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
          }}
          onClick={() => {
            setSliderValue(0.0);
            let playAnim = setInterval(() => {
              setSliderValue(prev => {
                if (prev >= 1.0) {
                  clearInterval(playAnim);
                  return 1.0;
                }
                return Math.min(prev + 0.0005, 1.0);
              });
            }, 10);
            return () => clearInterval(playAnim);
          }}
        >
          <PlayArrow style={{ color: 'black' }} />
        </button>
        <input
          id="timeline-slider"
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
}

export default ModelInterface;