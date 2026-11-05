import short from '../examples/demo-short.json';
import long from '../examples/demo-long.json';
import type {Manifest} from './types';

export const demoManifest = short.manifest as Manifest;
export const longDemoManifest = long.manifest as Manifest;
