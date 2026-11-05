import React from 'react';
import {Composition, type CalculateMetadataFunction} from 'remotion';
import {StoryVideo} from './StoryVideo';
import {demoManifest, longDemoManifest} from './demo';
import {assertManifest} from './validate.mjs';
import type {VideoProps} from './types';

const calculateMetadata: CalculateMetadataFunction<VideoProps> = ({props}) => {
  assertManifest(props.manifest);
  return {
    width: props.manifest.format.width,
    height: props.manifest.format.height,
    fps: props.manifest.format.fps,
    durationInFrames: props.manifest.scenes.reduce((sum, scene) => sum + scene.duration_in_frames, 0),
  };
};

export const RemotionRoot: React.FC = () => <>
  <Composition id="StoryShort" component={StoryVideo} defaultProps={{manifest: demoManifest}} width={1080} height={1920} fps={30} durationInFrames={1350} calculateMetadata={calculateMetadata}/>
  <Composition id="StoryLong" component={StoryVideo} defaultProps={{manifest: longDemoManifest}} width={1920} height={1080} fps={30} durationInFrames={1350} calculateMetadata={calculateMetadata}/>
</>;
