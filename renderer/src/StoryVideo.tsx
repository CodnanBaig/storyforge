import React from 'react';
import {Audio} from '@remotion/media';
import {AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Manifest, SceneSpec, StyleTokens, VideoProps} from './types';
import {styles} from './styles';
import {Diorama} from './scene/Diorama';
import {Actor2D} from './scene/Actor2D';
import {Fonts} from './Fonts';

const fontFamily = '"Story Sans", Arial, sans-serif';
const serif = '"Story Serif", Georgia, serif';

const Scene: React.FC<{scene: SceneSpec; manifest: Manifest; index: number; tokens: StyleTokens}> = ({scene, manifest, index, tokens: t}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const portrait = height > width;
  const unit = width / (portrait ? 1080 : 1920);
  const enter = interpolate(frame, [0, 18], [0, 1], {extrapolateRight: 'clamp'});
  const character = manifest.characters.find((c) => c.id === scene.character_id);
  const image = manifest.assets.find((a) => a.id === scene.image_asset_id);
  const canvasWidth = Math.round(width * (portrait ? 1 : 0.72));
  const canvasHeight = Math.round(height * (portrait ? 0.73 : 1));
  const headlineSize = portrait ? (scene.headline.length > 55 ? 69 : scene.headline.length > 38 ? 79 : 91) : (scene.headline.length > 55 ? 66 : 82);
  return <AbsoluteFill style={{backgroundColor: t.background, color: t.paper, fontFamily, overflow: 'hidden'}}>
    <div style={{position: 'absolute', left: portrait ? 0 : width * 0.28, top: portrait ? height * 0.2 : 0, width: canvasWidth, height: canvasHeight}}>
      <Diorama scene={scene} tokens={t} character={character} width={canvasWidth} height={canvasHeight}/>
      {scene.actor_2d && <Actor2D plan={scene.actor_2d} durationInFrames={scene.duration_in_frames}
        coat={character?.coat ?? t.teal} skin={character?.skin ?? t.paper}
        trousers={character?.trousers ?? t.dark} width={canvasWidth} height={canvasHeight}/>
    </div>
    <AbsoluteFill style={{pointerEvents: 'none', background: portrait
      ? `linear-gradient(180deg, ${t.background} 5%, transparent 35%, transparent 73%, ${t.background} 94%)`
      : `linear-gradient(90deg, ${t.background} 24%, transparent 52%)`}}/>
    {manifest.demo && <div style={{position: 'absolute', left: 76 * unit, top: portrait ? 86 * unit : 70 * unit, display: 'flex', alignItems: 'center', gap: 16 * unit}}>
      <div style={{width: 15 * unit, height: 15 * unit, borderRadius: '50%', border: `${2 * unit}px solid ${t.amber}`, boxShadow: `0 0 ${12 * unit}px ${t.amber}44`}}/>
      <div style={{fontSize: 18 * unit, letterSpacing: 5 * unit, fontWeight: 600}}>STORYFORGE <span style={{color: t.muted, fontWeight: 400}}> / FIELD NOTES</span></div>
    </div>}
    <div style={{position: 'absolute', left: 76 * unit, top: portrait ? 213 * unit : 242 * unit, width: portrait ? 925 * unit : 650 * unit, opacity: enter, transform: `translateY(${(1 - enter) * 18 * unit}px)`}}>
      <div style={{color: t.amber, fontSize: 20 * unit, letterSpacing: 4 * unit, fontWeight: 600, marginBottom: 25 * unit}}>{scene.eyebrow}</div>
      <div style={{fontFamily: serif, fontWeight: 400, fontSize: headlineSize * unit, lineHeight: 1.12, letterSpacing: -2.5 * unit, whiteSpace: 'pre-line'}}>{scene.headline}</div>
      {!portrait && <><div style={{width: 72 * unit, height: 2 * unit, background: t.amber, marginTop: 40 * unit, marginBottom: 32 * unit}}/><div style={{fontSize: 27 * unit, lineHeight: 1.6, color: t.muted, maxWidth: 560 * unit}}>{scene.body}</div></>}
    </div>
    {image && <div style={{position: 'absolute', right: 80 * unit, top: portrait ? 650 * unit : 110 * unit, width: (portrait ? 240 : 290) * unit, padding: 10 * unit, backgroundColor: t.paper, transform: 'rotate(3deg)', boxShadow: `0 ${8 * unit}px ${30 * unit}px #0008`}}><Img src={staticFile(image.src)} style={{display: 'block', width: '100%', height: 200 * unit, objectFit: 'cover'}}/></div>}
    {portrait && <div style={{position: 'absolute', left: 80 * unit, right: 110 * unit, bottom: 232 * unit, opacity: enter}}>
      <div style={{width: 68 * unit, height: 2 * unit, background: t.amber, marginBottom: 24 * unit}}/>
      <div style={{fontSize: 29 * unit, lineHeight: 1.6, color: t.muted, maxWidth: 850 * unit}}>{scene.body}</div>
    </div>}
    <div style={{position: 'absolute', right: (portrait ? 90 : 75) * unit, bottom: (portrait ? 117 : 70) * unit, display: 'flex', gap: 11 * unit}}>
      {manifest.scenes.map((s, i) => <div key={s.id} style={{height: 3 * unit, width: (i === index ? 44 : 18) * unit, backgroundColor: i === index ? t.amber : `${t.muted}55`}}/>)}
    </div>
  </AbsoluteFill>;
};

const Captions: React.FC<{manifest: Manifest; tokens: StyleTokens}> = ({manifest, tokens}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const cue = manifest.captions.find((c) => frame / fps >= c.start && frame / fps < c.end);
  if (!cue) return null;
  const portrait = height > width;
  return <div style={{position: 'absolute', bottom: height * (portrait ? 0.21 : 0.11), left: width * 0.075, right: width * 0.13, display: 'flex', justifyContent: 'center', fontFamily, textAlign: 'center'}}>
    <div style={{background: '#06121BEF', color: tokens.paper, fontWeight: 600, fontSize: width * (portrait ? 0.045 : 0.025), lineHeight: 1.35, padding: '0.34em 0.65em', borderRadius: 8, borderBottom: `3px solid ${tokens.amber}`, maxWidth: '100%'}}>{cue.text}</div>
  </div>;
};

export const StoryVideo: React.FC<VideoProps> = ({manifest}) => {
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const tokens = styles[manifest.style_id];
  let offset = 0;
  const assetSrc = (id: string) => staticFile(manifest.assets.find((a) => a.id === id)!.src);
  const portrait = height > width;
  return <AbsoluteFill style={{background: tokens.background}}>
    <Fonts/>
    {manifest.scenes.map((scene, index) => {
      const from = offset; offset += scene.duration_in_frames;
      return <Sequence key={scene.id} from={from} durationInFrames={scene.duration_in_frames} premountFor={fps} name={scene.eyebrow || scene.id}>
        <Scene scene={scene} manifest={manifest} index={index} tokens={tokens}/>
      </Sequence>;
    })}
    {manifest.narration && <Audio src={assetSrc(manifest.narration.asset_id)} volume={1}/>}
    {manifest.music && <Audio src={assetSrc(manifest.music.asset_id)} loop volume={(f) => {
      const fade = Math.min(1, f / (fps * 0.6), (durationInFrames - f) / (fps * 1.5));
      const duck = manifest.narration && f < manifest.narration.duration_seconds * fps ? 0.45 : 1;
      return manifest.music!.volume * Math.max(0, fade) * duck;
    }}/>}
    <Captions manifest={manifest} tokens={tokens}/>
    {manifest.demo && <div style={{position: 'absolute', bottom: height * (portrait ? 0.058 : 0.061), left: width * (portrait ? 0.074 : 0.04), color: tokens.muted, fontFamily, fontSize: width * (portrait ? 0.0145 : 0.0085), letterSpacing: width * 0.0016}}>
      {manifest.narration ? 'DRAFT TECHNICAL PREVIEW' : 'SILENT TECHNICAL PREVIEW'} · {manifest.project_id.includes('technical-demo') ? 'FICTIONAL STORY' : 'UNVERIFIED DRAFT'}
    </div>}
  </AbsoluteFill>;
};
