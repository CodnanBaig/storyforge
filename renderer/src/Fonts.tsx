import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';

let fontsReady: Promise<void> | undefined;

const loadLocalFont = async (family: string, filename: string) => {
  const url = staticFile(`fonts/${filename}`);
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not load ${filename}: HTTP ${response.status}`);
  // Register stable faces once per document. Component-owned @font-face styles
  // can be detached while an asynchronous render changes the composition.
  const face = new FontFace(family, await response.arrayBuffer(), {weight: '400', style: 'normal'});
  await face.load();
  // TypeScript's DOM snapshot omits FontFaceSet's standard mutable-set method.
  (document.fonts as FontFaceSet & {add(font: FontFace): FontFaceSet}).add(face);
};

const ensureFonts = () => {
  if (!fontsReady) fontsReady = Promise.all([
    loadLocalFont('Story Sans', 'DejaVuSans.ttf'),
    loadLocalFont('Story Serif', 'DejaVuSerif.ttf'),
  ]).then(() => undefined);
  return fontsReady;
};

/** Vendored fonts make composition metrics reproducible on macOS and Linux. */
export const Fonts: React.FC = () => {
  const [handle] = useState(() => delayRender('Load local StoryForge fonts'));
  useEffect(() => {
    let active = true;
    ensureFonts()
      .then(() => {if (active) continueRender(handle);})
      .catch((error) => {if (active) cancelRender(error);});
    return () => {active = false;};
  }, [handle]);
  return null;
};
