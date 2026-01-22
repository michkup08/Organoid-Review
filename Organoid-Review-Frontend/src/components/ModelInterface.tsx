import React, { useState, Suspense, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, Html, useProgress } from '@react-three/drei';
import { DualSyncedModels } from './ModelReview';
import { Pause, PlayArrow } from '@mui/icons-material';

function Loader() {
  const { progress } = useProgress();
  return <Html center style={{ color: 'black' }}>{progress.toFixed(0)} % loaded</Html>;
}

const ModelInterface = () => {
  const [sliderValue, setSliderValue] = useState(0.0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let intervalId: number;

    if (isPlaying) {
      intervalId = setInterval(() => {
        setSliderValue((prev) => {
          if (prev >= 1.0) {
            setIsPlaying(false);
            return 1.0;
          }
          return Math.min(prev + 0.001, 1.0); 
        });
      }, 16);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPlaying]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSliderValue(parseFloat(e.target.value));
  };

  return (
    <div style={{ 
      background: '#eee', 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%', 
      flexGrow: 1,
      boxSizing: 'border-box'
    }}>
      <div style={{ flexGrow: 1, position: 'relative', minHeight: 0 }}>
        <Canvas camera={{ position: [0, 2, 5], fov: 50 }}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
          <Environment preset="city" />
          <Suspense fallback={<Loader />}>
            <DualSyncedModels
              innerUrl='/models/nuclei2.glb'
              outerUrl='/models/coat_anim.glb'
              animationProgress={sliderValue}
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
            setIsPlaying(!isPlaying);
          }}
        >
          {isPlaying ? <Pause style={{ color: 'black' }} /> : <PlayArrow style={{ color: 'black' }} />}
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