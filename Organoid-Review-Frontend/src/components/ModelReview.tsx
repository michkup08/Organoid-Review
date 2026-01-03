import { useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { GLTF } from 'three-stdlib'; 

interface AnimatedModelProps {
  url: string;
  animationProgress: number; // 0.0 do 1.0
  opacity?: number;
  color?: string;
}

type GLTFResult = GLTF & {
  nodes: Record<string, THREE.Mesh>;
  materials: Record<string, THREE.MeshStandardMaterial>;
};

export function ModelReview({ url, animationProgress, opacity = 0.6, color = '#888888' }: AnimatedModelProps) {
  const { scene } = useGLTF(url) as unknown as GLTFResult;
  
  const [morphMesh, setMorphMesh] = useState<THREE.Mesh | null>(null);

  // 1. Znajdź Mesha i ustaw materiały (tylko raz)
  useEffect(() => {
    if (!scene) return;

    let foundMesh: THREE.Mesh | null = null;

    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        
        // Ustawienia materiału (przezroczystość)
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        materials.forEach((mat) => {
          const standardMat = mat as THREE.MeshStandardMaterial;
          standardMat.transparent = true;
          standardMat.opacity = opacity;
          standardMat.color = new THREE.Color(color);
          standardMat.depthWrite = false;
          standardMat.needsUpdate = true;
        });

        // Szukamy mesha, który ma Morph Targets (kształty)
        // To jest kluczowe - szukamy obiektu zdolnego do zmiany kształtu
        if (mesh.morphTargetInfluences && mesh.morphTargetInfluences.length > 0) {
          foundMesh = mesh;
        }
      }
    });

    setMorphMesh(foundMesh);
  }, [scene, opacity]);

  // 2. Pętla sterująca (Manual Morphing)
  useFrame(() => {
    if (!morphMesh || !morphMesh.morphTargetInfluences) return;

    const influences = morphMesh.morphTargetInfluences;
    const count = influences.length;

    // WAŻNE: W Blenderze index 0 to zazwyczaj "Basis" (kształt bazowy).
    // Jeśli tak jest, nasze animowane klatki to indexy od 1 do końca.
    // Musimy sprawdzić, czy mamy co najmniej 2 kształty (Basis + Frame_1).
    if (count < 2) return;

    // Resetujemy wszystkie wagi do 0 (czyszczenie poprzedniej klatki)
    morphMesh.morphTargetInfluences.fill(0);

    // --- MATEMATYKA INTERPOLACJI ---
    
    // Zakładamy, że klatki animacji to indexy od 1 do (count - 1)
    // Dostępna ilość klatek do animowania:
    const framesCount = count - 1; 

    // Obliczamy, w którym miejscu "wirtualnie" jesteśmy
    // Np. progress 0.5 przy 100 klatkach to wartość 50.0
    const virtualFrame = animationProgress * (framesCount - 1);
    
    // Index dolny (np. 50)
    const lowerIndex = Math.floor(virtualFrame) + 1; // +1 bo pomijamy Basis (index 0)
    // Index górny (np. 51)
    const upperIndex = lowerIndex + 1;
    
    // Ułamek (np. 0.5 - ile brakuje do następnej klatki)
    const alpha = virtualFrame % 1;

    // Ustawiamy wagi:
    // Jeśli jesteśmy w połowie między klatką 50 a 51:
    // Klatka 50 dostaje 50% wagi, Klatka 51 dostaje 50% wagi.
    
    if (lowerIndex < count) {
      influences[lowerIndex] = 1 - alpha;
    }
    
    if (upperIndex < count) {
      influences[upperIndex] = alpha;
    }

    // Jeśli morphTargets są indexowane po nazwie, Three.js i tak trzyma je w tablicy values,
    // więc ten kod zadziała bezpośrednio na GPU.
  });

  return <primitive object={scene} scale={1.5} position={[0, -1, 0]} />;
}

export default ModelReview;