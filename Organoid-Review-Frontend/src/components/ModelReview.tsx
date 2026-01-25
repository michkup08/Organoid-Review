import { useEffect, useMemo } from 'react';
import { useAnimations, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { GLTF } from 'three-stdlib';

interface AnimatedModelProps {
  url: string;
  animationProgress: number;
  opacity?: number;
  color?: string;
}

export function SingleAnimatedModel({ 
  url, 
  animationProgress, 
  opacity = 1.0,
  color
}: AnimatedModelProps) {
  // useGLTF automatycznie pobierze model z adresu URL (czy to http:// czy blob:)
  const { scene, animations } = useGLTF(url) as GLTF;
  
  // Klonowanie sceny
  const clone = useMemo(() => scene.clone(), [scene]);

  // Animacje
  const { actions, names } = useAnimations(animations, clone);

  // Ustawienie materiałów
  useEffect(() => {
    clone.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        
        materials.forEach((mat) => {
          const standardMat = mat as THREE.MeshStandardMaterial;
          standardMat.transparent = true;
          standardMat.opacity = opacity;
          if (color) standardMat.color = new THREE.Color(color);
          standardMat.depthWrite = opacity >= 1.0;
        });
      }
    });
  }, [clone, opacity, color]);

  // Sterowanie Suwakiem
  useEffect(() => {
    const actionName = names[0];
    const action = actions[actionName];

    if (action) {
      action.play();
      action.paused = true;
      const duration = action.getClip().duration;
      // Zabezpieczenie na wypadek NaN
      action.time = duration * (Number.isFinite(animationProgress) ? animationProgress : 0);
    }
  }, [actions, names, animationProgress]);

  return <primitive object={clone} scale={1.5} position={[0, -1, 0]} />;
}

interface DualSyncedModelsProps {
  outerUrl: string;
  innerUrl: string;
  animationProgress: number;
}

export function DualSyncedModels({ outerUrl, innerUrl, animationProgress }: DualSyncedModelsProps) {
  return (
    <group position={[0, 1, 0]} scale={1.5}>
      <SingleAnimatedModel 
        url={innerUrl} 
        animationProgress={animationProgress}
        opacity={0.5}
        color="#df5c5c"
      />
      <SingleAnimatedModel 
        url={outerUrl} 
        animationProgress={animationProgress}
        opacity={0.5}
        color="#305064"
      />
    </group>
  );
}

// Preload jest trudny przy dynamicznych URLach (blob), więc można go pominąć 
// lub używać tylko dla stałych zasobów.