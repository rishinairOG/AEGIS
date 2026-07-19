import React, { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { useFrame } from '@react-three/fiber';

const BASE_RADIUS = 0.8;
const PULSE_AMPLITUDE = 0.15;
const IDLE_BREATH_SPEED = 1.2;

function Sphere({ intensityRef, isListeningRef }) {
  const meshRef = useRef(null);

  useFrame((_, delta) => {
    if (!meshRef.current) return;
    const intensity = intensityRef.current ?? 0;
    const isListening = isListeningRef.current ?? false;

    if (isListening) {
      const scale = 1 + intensity * PULSE_AMPLITUDE * 2;
      meshRef.current.scale.lerp({ x: scale, y: scale, z: scale }, 0.15);
      const emissive = 0.2 + intensity * 0.6;
      meshRef.current.material.emissiveIntensity = Math.min(1, emissive);
    } else {
      const breath = Math.sin(performance.now() * 0.001 * IDLE_BREATH_SPEED) * 0.04;
      meshRef.current.scale.lerp({ x: 1 + breath, y: 1 + breath, z: 1 + breath }, 0.08);
      meshRef.current.material.emissiveIntensity = 0.15 + breath * 2;
    }
  });

  return (
    <mesh ref={meshRef} scale={1}>
      <sphereGeometry args={[BASE_RADIUS, 64, 64]} />
      <meshStandardMaterial
        color="#0a0a0f"
        emissive="#06b6d4"
        emissiveIntensity={0.2}
        metalness={0.6}
        roughness={0.3}
        wireframe={false}
      />
    </mesh>
  );
}

function Scene({ intensityRef, isListeningRef }) {
  return (
    <>
      <ambientLight intensity={0.15} />
      <pointLight position={[4, 4, 4]} intensity={0.8} color="#22d3ee" />
      <pointLight position={[-3, -2, 2]} intensity={0.3} color="#06b6d4" />
      <Sphere intensityRef={intensityRef} isListeningRef={isListeningRef} />
    </>
  );
}

export default function Visualizer3D({ audioData, isListening, intensity = 0, width = 600, height = 400 }) {
  const intensityRef = useRef(intensity);
  const isListeningRef = useRef(isListening);
  intensityRef.current = intensity;
  isListeningRef.current = isListening;

  return (
    <div className="relative w-full h-full min-h-[200px]" style={{ width, height }}>
      <Canvas
        camera={{ position: [0, 0, 2.5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <Scene intensityRef={intensityRef} isListeningRef={isListeningRef} />
      </Canvas>
      {/* Overlay label */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
        <span
          className="font-display text-cyan-400/90 font-semibold tracking-[0.35em] drop-shadow-[0_0_20px_rgba(34,211,238,0.6)]"
          style={{ fontSize: Math.min(width, height) * 0.08 }}
        >
          A.T.L.A.S.
        </span>
      </div>
    </div>
  );
}
