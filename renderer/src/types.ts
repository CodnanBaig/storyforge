import type {Actor2DPlan} from './scene/Actor2D';
export type Vec3 = [number, number, number];
export type Template = 'lighthouse-coast' | 'archive-room' | 'signal-chamber' | 'forest-path';
export type CameraSize = 'wide' | 'medium' | 'detail';
export type StyleId = 'midnight-dossier' | 'coastal-archive' | 'ember-noir';

export interface CharacterSpec {
  id: string;
  name: string;
  coat: string;
  skin: string;
  trousers: string;
  scale: number;
}
export interface AssetSpec {
  id: string;
  kind: 'image' | 'audio';
  /** Local path relative to renderer/public. */
  src: string;
  provenance?: string;
}
export interface SceneSpec {
  id: string;
  template: Template;
  duration_in_frames: number;
  eyebrow: string;
  headline: string;
  body: string;
  character_id?: string;
  camera: CameraSize;
  seed: number;
  image_asset_id?: string;
  /** Optional frame-deterministic 2D puppet, independent of the 3D scene. */
  actor_2d?: Actor2DPlan;
}
export interface Caption {
  text: string;
  start: number;
  end: number;
}
export interface Manifest {
  schema_version: '1.0';
  project_id: string;
  title: string;
  demo: boolean;
  format: {width: number; height: number; fps: number};
  style_id: StyleId;
  characters: CharacterSpec[];
  assets: AssetSpec[];
  scenes: SceneSpec[];
  narration: null | {asset_id: string; duration_seconds: number; measured: true};
  music: null | {asset_id: string; volume: number};
  captions: Caption[];
}
export type VideoProps = {manifest: Manifest};

export interface StyleTokens {
  background: string;
  paper: string;
  muted: string;
  teal: string;
  amber: string;
  stone: string;
  wood: string;
  dark: string;
}
