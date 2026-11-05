import React, {useLayoutEffect} from 'react';
import {useThree} from '@react-three/fiber';
import {ThreeCanvas} from '@remotion/three';
import {PerspectiveCamera} from 'three';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {CharacterSpec, SceneSpec, StyleTokens} from '../types';
import {environmentRegistry} from './Environments';

const CameraRig: React.FC<{scene: SceneSpec; time: number; progress: number}> = ({scene, time, progress}) => {
  const {camera} = useThree();
  useLayoutEffect(() => {
    const lighthouse = scene.template === 'lighthouse-coast';
    const base = lighthouse ? 17.9 : 13.6;
    const distance = base * ({wide: 1, medium: 0.95, detail: 0.87}[scene.camera]);
    const angle = (scene.template === 'archive-room' ? 0.48 : 0.67) + Math.sin(time * 0.06) * 0.035;
    const dolly = 1 - progress * 0.025;
    camera.position.set(Math.sin(angle) * distance * dolly, (lighthouse ? 8.8 : 8) * dolly, Math.cos(angle) * distance * dolly);
    camera.lookAt(0, lighthouse ? 2.2 : 1.6, 0);
    if (camera instanceof PerspectiveCamera) {
      camera.fov = 38;
      camera.updateProjectionMatrix();
    }
    camera.updateMatrixWorld();
  }, [camera, scene.template, scene.camera, time, progress]);
  return null;
};

export const Diorama: React.FC<{scene: SceneSpec; tokens: StyleTokens; character?: CharacterSpec; width: number; height: number}> = ({scene, tokens, character, width, height}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const Environment = environmentRegistry[scene.template];
  return <ThreeCanvas
    width={width} height={height}
    shadows camera={{position: [10, 9, 14], fov: 38, near: 0.1, far: 80}}
    gl={{antialias: true, alpha: true, preserveDrawingBuffer: true}}
    style={{width, height}}
  >
    <color attach="background" args={[tokens.background]}/>
    <fog attach="fog" args={[tokens.background, 23, 48]}/>
    <ambientLight intensity={0.7} color="#BDD5D8"/>
    <hemisphereLight args={['#BED8DC', tokens.dark, 1.3]}/>
    <directionalLight position={[-4, 10, 7]} intensity={2.6} color="#DFE8E3" castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-left={-8} shadow-camera-right={8} shadow-camera-top={9} shadow-camera-bottom={-8} shadow-normalBias={0.04}/>
    <directionalLight position={[5, 5, -6]} intensity={3.2} color={tokens.teal}/>
    <directionalLight position={[-5, 3, -3]} intensity={1.2} color={tokens.amber}/>
    <CameraRig scene={scene} time={time} progress={frame / Math.max(1, scene.duration_in_frames - 1)}/>
    <Environment scene={scene} tokens={tokens} time={time} character={character}/>
  </ThreeCanvas>;
};
