import React from 'react';
import type {CharacterSpec, SceneSpec, StyleTokens} from '../types';
import {Box, Cylinder, Glow, Lantern, Mannequin, Pine, Rock, seeded} from './Primitives';

export interface EnvironmentProps {scene: SceneSpec; tokens: StyleTokens; time: number; character?: CharacterSpec}

export const LighthouseCoast: React.FC<EnvironmentProps> = ({tokens: t, time, scene, character}) => <group>
  <Cylinder position={[0, -0.6, 0]} radius={4.6} top={4.4} height={0.24} color="#123A4A" segments={80}/>
  {[0, 1, 2, 3, 4].map((i) => <mesh key={i} position={[0, -0.465, 0]} rotation={[-Math.PI / 2, 0, 0]}>
    <ringGeometry args={[3.15 + i * 0.3 + Math.sin(time * 0.5 + i) * 0.025, 3.18 + i * 0.3, 96]}/>
    <meshStandardMaterial color={t.teal} transparent opacity={0.14 + i * 0.015} roughness={0.3}/>
  </mesh>)}
  <Cylinder position={[0, -0.22, 0]} radius={3.15} top={2.9} height={0.55} color={t.stone} segments={12}/>
  <Cylinder position={[0, 0.08, 0]} radius={2.9} top={2.85} height={0.12} color="#49635F" segments={12}/>
  {Array.from({length: 16}, (_, i) => {
    const a = i / 16 * Math.PI * 2;
    return <Rock key={i} seed={i} position={[Math.cos(a) * 3.05, -0.13, Math.sin(a) * 3.05]} scale={[0.45 + seeded(scene.seed, i) * 0.45, 0.32, 0.6]} color={i % 2 ? t.stone : '#344955'}/>;
  })}
  <group position={[-0.65, 0.14, -0.7]}>
    <Cylinder position={[0, 0.12, 0]} radius={1.04} height={0.25} color={t.stone}/>
    <Cylinder position={[0, 2.24, 0]} radius={0.82} top={0.55} height={4.25} color="#DDD5BF"/>
    <Cylinder position={[0, 2.1, 0]} radius={0.703} top={0.68} height={0.35} color={t.teal}/>
    {[0.85, 2.9, 3.7].map((y, i) => <Box key={y} position={[0.22, y, 0.56 + (3.7 - y) * 0.03]} size={[0.17, 0.31, 0.07]} color={i === 2 ? t.amber : t.dark}/>)}
    <Box position={[0, 0.54, 0.79]} size={[0.42, 0.85, 0.07]} color={t.dark}/>
    <Cylinder position={[0, 4.45, 0]} radius={0.9} height={0.18} color={t.dark}/>
    <mesh position={[0, 4.95, 0]}><cylinderGeometry args={[0.56, 0.56, 0.9, 24]}/><meshStandardMaterial color="#83AFA8" transparent opacity={0.13} depthWrite={false} roughness={0.25}/></mesh>
    <Glow position={[0, 5, 0]} radius={0.31} color={t.amber} intensity={12}/>
    {[0, 1, 2, 3, 4, 5].map((i) => <Box key={i} position={[Math.cos(i * Math.PI / 3) * 0.57, 4.95, Math.sin(i * Math.PI / 3) * 0.57]} size={[0.045, 0.9, 0.045]} color={t.dark}/>)}
    <Cylinder position={[0, 5.46, 0]} radius={0.82} top={0.08} height={0.46} color={t.dark}/>
    <Cylinder position={[0, 5.81, 0]} radius={0.035} height={0.35} color={t.amber}/>
    <group rotation={[0, time * 0.13, 0]}>
      <mesh position={[2.4, 4.98, 0]} rotation={[0, 0, Math.PI / 2]}><coneGeometry args={[0.85, 4.8, 32, 1, true]}/><meshBasicMaterial color={t.amber} transparent opacity={0.045} depthWrite={false}/></mesh>
    </group>
  </group>
  <group position={[1.3, 0.2, -0.55]}>
    <Box position={[0, 0.58, 0]} size={[1.35, 1.1, 1.25]} color="#B7B49F"/>
    <mesh position={[0, 1.4, 0]} rotation={[0, Math.PI / 4, 0]} castShadow><coneGeometry args={[1.1, 0.6, 4]}/><meshStandardMaterial color={t.dark} flatShading/></mesh>
    <Box position={[0, 0.55, 0.64]} size={[0.34, 0.6, 0.03]} color={t.dark}/>
    <Box position={[0.45, 0.75, 0.64]} size={[0.22, 0.28, 0.03]} color={t.amber}/>
  </group>
  {[-1, 0, 1].map((i) => <Box key={i} position={[1.1 + i * 0.25, 0.19, 1.1 + i * 0.4]} size={[0.6, 0.05, 0.3]} rotation={[0, -0.4, 0]} color="#A49F88"/>)}
  {character && <Mannequin spec={character} position={[0.8, 0.2, 1.7]} rotation={-0.55} time={time} pose="inspect" amber={t.amber}/>}
</group>;

export const ArchiveRoom: React.FC<EnvironmentProps> = ({tokens: t, time, scene, character}) => <group>
  <Box position={[0, -0.2, 0]} size={[7, 0.4, 5.4]} color={t.dark}/>
  {Array.from({length: 12}, (_, i) => <Box key={i} position={[-3.2 + i * 0.58, 0.025, 0]} size={[0.55, 0.06, 5.15]} color={i % 2 ? '#5E6158' : '#535B55'}/>)}
  <Box position={[0, 2.2, -2.5]} size={[7, 4.4, 0.22]} color="#304A52"/>
  <Box position={[-3.4, 1.1, 0]} size={[0.2, 2.2, 5]} color="#273F47"/>
  <group position={[-1.7, 2.8, -2.35]}>
    <Box size={[1.7, 2.2, 0.12]} color={t.teal}/>
    <Box position={[0, 0, 0.1]} size={[0.07, 2.25, 0.1]} color={t.dark}/>
    <Box position={[0, 0, 0.1]} size={[1.75, 0.07, 0.1]} color={t.dark}/>
    <Box position={[0, -1.15, 0.12]} size={[2, 0.12, 0.3]} color={t.wood}/>
  </group>
  <group position={[1.65, 0, -2.05]}>
    {[0.25, 1.25, 2.25, 3.25].map((y) => <Box key={y} position={[0, y, 0]} size={[2.1, 0.11, 0.7]} color={t.wood}/>)}
    {[-1, 1].map((x) => <Box key={x} position={[x, 1.7, 0]} size={[0.1, 3.5, 0.7]} color={t.wood}/>)}
    {Array.from({length: 15}, (_, i) => <Box key={i} position={[-0.78 + (i % 5) * 0.35, 0.7 + Math.floor(i / 5), 0]} size={[0.23, 0.75 - seeded(scene.seed, i) * 0.22, 0.46]} rotation={[0, 0, (seeded(scene.seed, i + 30) - 0.5) * 0.13]} color={[t.teal, t.stone, '#A99470', '#685346'][i % 4]}/>)}
  </group>
  <group position={[-0.4, 0, 0.2]}>
    <Box position={[0, 1.22, 0]} size={[3.25, 0.14, 1.6]} color={t.wood}/>
    {[-1.35, 1.35].flatMap((x) => [-0.6, 0.6].map((z) => <Box key={`${x}-${z}`} position={[x, 0.59, z]} size={[0.12, 1.18, 0.12]} color={t.dark}/>))}
    {[0, 1, 2].map((i) => <Box key={i} position={[-0.4 + i * 0.16, 1.31 + i * 0.008, 0.1]} size={[0.85, 0.012, 0.6]} rotation={[0, -0.2 + i * 0.16, 0]} color={t.paper}/>)}
    <Box position={[0.65, 1.43, -0.25]} size={[0.72, 0.28, 0.45]} color={t.dark}/>
    <Box position={[0.68, 1.45, -0.01]} size={[0.48, 0.13, 0.02]} color={t.teal}/>
    <Lantern position={[-1.1, 1.31, -0.3]} color={t.amber} time={time}/>
    <pointLight position={[-1, 2.1, -0.4]} color={t.amber} intensity={8} distance={5}/>
  </group>
  {character && <Mannequin spec={character} position={[1.45, 0.1, 1.2]} rotation={-1.7} time={time} pose="inspect" amber={t.amber}/>}
</group>;

export const SignalChamber: React.FC<EnvironmentProps> = ({tokens: t, time, character}) => <group>
  <Cylinder position={[0, -0.18, 0]} radius={3.7} height={0.36} color={t.dark} segments={48}/>
  <Cylinder position={[0, 0.025, 0]} radius={3.45} height={0.05} color={t.stone} segments={48}/>
  {[0, 1, 2, 3, 4, 5].map((i) => {
    const x = -2.5 + i;
    const length = 2 * Math.sqrt(3.45 ** 2 - x ** 2) - 0.08;
    return <Box key={i} position={[x, 0.07, 0]} size={[0.018, 0.02, length]} color="#748C90"/>;
  })}
  <group position={[-0.8, 0, -0.75]}>
    <Cylinder position={[0, 0.28, 0]} radius={1.3} top={1.1} height={0.5} color={t.dark}/>
    <Box position={[0, 1.6, 0]} size={[0.38, 2.4, 0.4]} color={t.stone}/>
    <group position={[0, 3.2, 0]} rotation={[0.15, Math.sin(time * 0.16) * 0.12, -0.08]}>
      {[0.85, 1.2, 1.55].map((r, i) => <mesh key={r} rotation={[0, 0, time * (i % 2 ? 0.025 : -0.025)]} castShadow><torusGeometry args={[r, 0.05, 10, 64]}/><meshStandardMaterial color={i === 1 ? t.amber : t.teal} metalness={0.25} roughness={0.5}/></mesh>)}
      <Box size={[3.4, 0.075, 0.075]} color={t.teal}/><Box size={[0.075, 3.4, 0.075]} color={t.teal}/>
      <Glow position={[0, 0, 0.08]} color={t.amber} radius={0.25} intensity={5}/>
    </group>
  </group>
  <group position={[1.3, 0, 0.7]}>
    <Box position={[0, 0.8, 0]} size={[1.7, 1.5, 0.95]} color={t.dark}/>
    <Box position={[0, 1.58, 0]} size={[1.85, 0.14, 1.05]} color={t.wood}/>
    <Box position={[-0.3, 1.76, -0.17]} size={[0.8, 0.35, 0.5]} color={t.stone}/>
    <Box position={[-0.3, 1.79, 0.09]} size={[0.58, 0.16, 0.025]} color={t.teal}/>
    {[0, 1, 2].map((i) => <Glow key={i} position={[0.38 + i * 0.14, 1.68, 0.26]} radius={0.035} color={i === 0 ? t.amber : t.teal} intensity={0.08}/>)}
  </group>
  {[-2.7, 2.7].map((x) => <group key={x} position={[x, 0, -1.8]}><Cylinder position={[0, 1.2, 0]} radius={0.12} height={2.4} color={t.stone}/><Glow position={[0, 2.45, 0]} color={t.teal} radius={0.1}/></group>)}
  {character && <Mannequin spec={character} position={[1.1, 0.1, 2.1]} rotation={-2.7} time={time} pose="listen" amber={t.amber}/>}
</group>;

export const ForestPath: React.FC<EnvironmentProps> = ({tokens: t, time, scene, character}) => <group>
  <Cylinder position={[0, -0.27, 0]} radius={3.8} top={3.65} height={0.55} color={t.stone} segments={12}/>
  <Cylinder position={[0, 0.03, 0]} radius={3.65} height={0.08} color="#334F4A" segments={12}/>
  {Array.from({length: 13}, (_, i) => <Box key={i} position={[Math.sin(i * 0.26) * 0.65 - 0.4, 0.09, -3 + i * 0.48]} size={[1.1, 0.03, 0.6]} rotation={[0, Math.cos(i * 0.26) * 0.24, 0]} color="#8B8B70"/>)}
  {Array.from({length: 10}, (_, i) => {
    const side = i % 2 ? 1 : -1;
    return <Pine key={i} position={[side * (1.55 + seeded(scene.seed, i) * 1.05), 0.12, -2.45 + Math.floor(i / 2) * 1.15]} scale={0.75 + seeded(scene.seed, i + 20) * 0.4} tokens={t}/>;
  })}
  {Array.from({length: 7}, (_, i) => <Rock key={i} position={[-2.3 + seeded(scene.seed, i + 50) * 4.6, 0.17, -2.6 + seeded(scene.seed, i + 80) * 5.2]} scale={[0.25, 0.16, 0.3]} color={t.stone} seed={i}/>)}
  <group position={[-0.45, 0.1, -2.8]}><Cylinder position={[0, 0.95, 0]} radius={0.09} height={1.9} color={t.wood}/><Lantern position={[0, 1.93, 0]} color={t.amber} time={time}/></group>
  {character && <Mannequin spec={character} position={[0.1 + Math.sin(time * 0.3) * 0.06, 0.13, 1.3 - Math.sin(time * 0.15) * 0.2]} rotation={-2.75} time={time} pose="walk" amber={t.amber}/>}
</group>;

export const environmentRegistry = {
  'lighthouse-coast': LighthouseCoast,
  'archive-room': ArchiveRoom,
  'signal-chamber': SignalChamber,
  'forest-path': ForestPath,
};
