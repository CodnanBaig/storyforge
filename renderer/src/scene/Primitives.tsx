import React from 'react';
import type {CharacterSpec, StyleTokens, Vec3} from '../types';

export const seeded = (seed: number, index: number) => {
  const x = Math.sin(seed * 12.9898 + index * 78.233) * 43758.5453;
  return x - Math.floor(x);
};

export const Box: React.FC<{position?: Vec3; size?: Vec3; color: string; rotation?: Vec3; roughness?: number}> = ({position, size = [1, 1, 1], color, rotation, roughness = 0.85}) => (
  <mesh position={position} rotation={rotation} castShadow receiveShadow>
    <boxGeometry args={size}/><meshStandardMaterial color={color} roughness={roughness}/>
  </mesh>
);
export const Cylinder: React.FC<{position?: Vec3; radius?: number; top?: number; height?: number; color: string; rotation?: Vec3; segments?: number}> = ({position, radius = 1, top, height = 1, color, rotation, segments = 32}) => (
  <mesh position={position} rotation={rotation} castShadow receiveShadow>
    <cylinderGeometry args={[top ?? radius, radius, height, segments]}/><meshStandardMaterial color={color} roughness={0.8}/>
  </mesh>
);
export const Glow: React.FC<{position: Vec3; color: string; radius?: number; intensity?: number}> = ({position, color, radius = 0.16, intensity = 1.5}) => (
  <group position={position}>
    <mesh><sphereGeometry args={[radius, 20, 12]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.5} roughness={0.4}/></mesh>
    <pointLight color={color} intensity={intensity} distance={5} decay={2}/>
  </group>
);
export const Lantern: React.FC<{position?: Vec3; color: string; time?: number}> = ({position, color, time = 0}) => (
  <group position={position}>
    <Cylinder position={[0, 0.02, 0]} radius={0.15} height={0.08} color="#24323A"/>
    <Cylinder position={[0, 0.39, 0]} radius={0.17} top={0.09} height={0.12} color="#24323A"/>
    {[0, 1, 2, 3].map((n) => <Box key={n} position={[Math.cos(n * Math.PI / 2) * 0.12, 0.2, Math.sin(n * Math.PI / 2) * 0.12]} size={[0.025, 0.34, 0.025]} color="#24323A"/>)}
    <Glow position={[0, 0.21, 0]} color={color} radius={0.095} intensity={2.5 + Math.sin(time * 4.1) * 0.1}/>
    <mesh position={[0, 0.51, 0]}><torusGeometry args={[0.10, 0.018, 8, 20]}/><meshStandardMaterial color="#24323A"/></mesh>
  </group>
);

const Limb: React.FC<{position: Vec3; length: number; radius: number; color: string; bend?: number}> = ({position, length, radius, color, bend = 0}) => (
  <group position={position} rotation={[bend, 0, 0]}>
    <mesh position={[0, -length / 2, 0]} castShadow><capsuleGeometry args={[radius, Math.max(0.01, length - radius * 2), 5, 12]}/><meshStandardMaterial color={color} roughness={0.8}/></mesh>
  </group>
);

/** Story participant, not a presenter. All poses derive solely from timeline time. */
export const Mannequin: React.FC<{spec: CharacterSpec; position?: Vec3; rotation?: number; time: number; pose?: 'walk' | 'inspect' | 'listen'; amber: string}> = ({spec, position, rotation = 0, time, pose = 'inspect', amber}) => {
  const stride = pose === 'walk' ? Math.sin(time * 3.2) * 0.33 : Math.sin(time * 0.7) * 0.025;
  const bob = pose === 'walk' ? Math.sin(time * 6.4) * 0.018 : Math.sin(time * 1.1) * 0.008;
  return <group position={position} rotation={[0, rotation, 0]} scale={spec.scale}>
    <group position={[0, bob, 0]}>
      <Limb position={[-0.15, 0.82, 0]} length={0.76} radius={0.105} color={spec.trousers} bend={stride}/>
      <Limb position={[0.15, 0.82, 0]} length={0.76} radius={0.105} color={spec.trousers} bend={-stride}/>
      <Box position={[-0.15, 0.07, 0.065]} size={[0.23, 0.14, 0.39]} color="#15242D"/>
      <Box position={[0.15, 0.07, 0.065]} size={[0.23, 0.14, 0.39]} color="#15242D"/>
      <mesh position={[0, 1.1, 0]} castShadow><capsuleGeometry args={[0.27, 0.36, 6, 16]}/><meshStandardMaterial color={spec.coat} roughness={0.9}/></mesh>
      <Cylinder position={[0, 1.48, 0]} radius={0.085} height={0.14} color={spec.skin}/>
      <group rotation={[pose === 'inspect' ? 0.16 : 0, Math.sin(time * 0.3) * 0.08, 0]} position={[0, 1.67, 0]}>
        <mesh scale={[0.85, 1, 0.9]} castShadow><sphereGeometry args={[0.21, 20, 16]}/><meshStandardMaterial color={spec.skin} roughness={0.85}/></mesh>
        <mesh position={[0, 0.085, -0.02]} rotation={[-0.2, 0, 0]}><sphereGeometry args={[0.205, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2]}/><meshStandardMaterial color="#263C43" roughness={0.95}/></mesh>
      </group>
      <Limb position={[-0.31, 1.32, 0]} length={0.61} radius={0.09} color={spec.coat} bend={-stride}/>
      <Limb position={[0.31, 1.32, 0]} length={0.6} radius={0.09} color={spec.coat} bend={pose === 'listen' ? -1.5 : -0.28 + stride * 0.3}/>
      <mesh position={[-0.31, 0.72, 0]}><sphereGeometry args={[0.095, 12, 10]}/><meshStandardMaterial color={spec.skin}/></mesh>
      <mesh position={[0.31, pose === 'listen' ? 1.27 : 0.74, pose === 'listen' ? 0.57 : 0.17]}><sphereGeometry args={[0.095, 12, 10]}/><meshStandardMaterial color={spec.skin}/></mesh>
      <Box position={[0, 1.11, -0.26]} size={[0.37, 0.45, 0.2]} color="#8B7557"/>
      {pose !== 'listen' && <Lantern position={[0.32, 0.24, 0.2]} color={amber} time={time}/>}
    </group>
  </group>;
};

export const Rock: React.FC<{position: Vec3; scale?: Vec3; color: string; seed: number}> = ({position, scale = [1, 1, 1], color, seed}) => (
  <mesh position={position} scale={scale} rotation={[seed * 0.5, seed * 0.7, seed * 0.11]} castShadow receiveShadow>
    <icosahedronGeometry args={[1, 0]}/><meshStandardMaterial color={color} roughness={1} flatShading/>
  </mesh>
);

export const Pine: React.FC<{position: Vec3; scale: number; tokens: StyleTokens}> = ({position, scale, tokens}) => <group position={position} scale={scale}>
  <Cylinder position={[0, 0.7, 0]} radius={0.12} height={1.4} color={tokens.wood} segments={8}/>
  {[0, 1, 2].map((level) => <mesh key={level} position={[0, 1.1 + level * 0.52, 0]} castShadow><coneGeometry args={[0.77 - level * 0.15, 1.45, 7]}/><meshStandardMaterial color={level % 2 ? tokens.teal : '#254D50'} roughness={1} flatShading/></mesh>)}
</group>;
