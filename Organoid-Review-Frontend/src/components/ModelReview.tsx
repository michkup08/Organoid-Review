import { useEffect } from 'react';
import { useAnimations, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { GLTF } from 'three-stdlib'; 
import React from 'react';

interface AnimatedModelProps {
  url: string;
  animationProgress: number; // 0.0 do 1.0
  opacity?: number;
  color?: string;
}

export function SingleAnimatedModel({ 
  url, 
  animationProgress, 
  opacity = 1.0,
  color
}: AnimatedModelProps) {
  // 1. Ładujemy GLTF
  const { scene, animations } = useGLTF(url) as GLTF;
  
  // 2. Klonujemy scenę, aby móc używać tego samego modelu dwa razy (inner/outer) bez konfliktów
  // useGraph tworzy unikalną instancję materiałów i geometrii dla tego wywołania
  const clone = React.useMemo(() => scene.clone(), [scene]);

  // 3. Hook do obsługi animacji (uniwersalny: Morph i Skeletal)
  const { actions, names } = useAnimations(animations, clone);

  // 4. Ustawienie materiałów (Kolor/Przezroczystość)
  useEffect(() => {
    clone.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        
        materials.forEach((mat) => {
          const standardMat = mat as THREE.MeshStandardMaterial;
          standardMat.transparent = true; // Zawsze true, żeby opacity działało
          standardMat.opacity = opacity;
          if (color) standardMat.color = new THREE.Color(color);
          standardMat.depthWrite = opacity >= 1.0; // Wyłącz depthWrite dla przezroczystych, żeby nie migały
        });
      }
    });
  }, [clone, opacity, color]);

  // 5. Sterowanie Animacją Suwakiem (Scrubbing)
  useEffect(() => {
    // Bierzemy pierwszą dostępną animację
    const actionName = names[0];
    const action = actions[actionName];

    if (action) {
      // Przygotuj animację, ale jej nie puszczaj (paused)
      action.play();
      action.paused = true; // Kluczowe dla suwaka!
      
      // Oblicz czas na podstawie progressu (0.0 - 1.0)
      const duration = action.getClip().duration;
      action.time = duration * animationProgress;
      
      // Wymuś aktualizację mixera (czasami potrzebne przy pauzie)
      // action.getMixer().update(0); 
    }
  }, [actions, names, animationProgress]);

  return <primitive object={clone} scale={1.5} position={[0, -1, 0]} />;
}

// Komponent DualSyncedModels pozostaje bez zmian (korzysta z powyższego)
export function DualSyncedModels({ outerUrl, innerUrl, animationProgress }: any) {
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

export default SingleAnimatedModel;