import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

/** Deterministic code-driven 2D character for small reusable actions.
 * This is a first rig, not a full multi-bone animator or a character generator.
 * Every pose is a function of the requested frame, not wall-clock state.
 */
export type ActorAction = 'idle' | 'walk' | 'run' | 'point' | 'look' | 'react' | 'crouch';
export type Actor2DPlan = {
  action: ActorAction;
  x_from: number;
  x_to: number;
  y: number;
  scale: number;
  facing?: -1 | 1;
};
type Props = {
  plan: Actor2DPlan;
  durationInFrames: number;
  coat: string;
  skin: string;
  trousers: string;
  width: number;
  height: number;
};
const clamp = (v: number, low: number, high: number) => Math.max(low, Math.min(high, v));

export const Actor2D: React.FC<Props> = ({plan, durationInFrames, coat, skin, trousers, width, height}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = clamp(frame / Math.max(1, durationInFrames - 1), 0, 1);
  const x = interpolate(progress, [0, 1], [plan.x_from, plan.x_to]);
  const action = plan.action;
  const travelling = action === 'walk' || action === 'run';
  const phase = frame / fps * (action === 'run' ? 16 : 9);
  const stride = travelling ? Math.sin(phase) : 0;
  const magnitude = action === 'run' ? 31 : action === 'walk' ? 18 : 0;
  const bob = travelling ? Math.abs(Math.sin(phase)) * (action === 'run' ? 10 : 5) : 0;
  const armA = action === 'point' ? -85 : travelling ? -stride * magnitude * 0.8 : action === 'react' ? -42 : 8;
  const armB = action === 'react' ? -60 : travelling ? stride * magnitude * 0.8 : 12;
  const lean = action === 'run' ? 9 : action === 'react' ? -11 : 0;
  const bend = action === 'crouch' ? 36 : 0;
  const look = action === 'look' ? Math.sin(frame / fps * 2.5) * 10 : action === 'react' ? -13 : 0;
  const flip = plan.facing === -1 ? -1 : 1;
  const size = 300 * plan.scale * width / 1080;
  return <div aria-label={'Animated '+action+' character'} style={{
    position: 'absolute', width: size, height: size * 1.35, pointerEvents: 'none',
    left: x * width - size / 2, top: height * (1 - plan.y) - size * 1.35,
    transform: 'scaleX('+flip+')', transformOrigin: 'center bottom',
  }}>
    <svg viewBox="0 0 240 330" width="100%" height="100%" style={{overflow: 'visible'}}>
      <ellipse cx="120" cy="315" rx="53" ry="9" fill="#080E19" opacity="0.3"/>
      <g transform={'translate(0 '+(-bob + bend)+')'} strokeLinecap="round" strokeLinejoin="round">
        <g transform={'translate(119 230) rotate('+(-stride * magnitude)+')'}>
          <path d="M0 0 L0 61" stroke={trousers} strokeWidth="24"/>
          <path d="M0 60 L-10 84" stroke={trousers} strokeWidth="19"/>
          <path d="M-19 88 L14 88" stroke="#20212A" strokeWidth="17"/>
        </g>
        <g transform={'translate(120 230) rotate('+(stride * magnitude)+')'}>
          <path d="M0 0 L0 61" stroke={trousers} strokeWidth="24"/>
          <path d="M0 60 L12 84" stroke={trousers} strokeWidth="19"/>
          <path d="M-4 88 L26 88" stroke="#343443" strokeWidth="17"/>
        </g>
        <g transform={'translate(120 152) rotate('+lean+')'}>
          <g transform={'translate(-28 11) rotate('+armB+')'}>
            <path d="M0 0 L-9 63" stroke={coat} strokeWidth="20"/>
            <circle cx="-9" cy="65" r="10" fill={skin}/>
          </g>
          <rect x="-32" y="0" width="64" height="88" rx="18" fill={coat}/>
          <path d="M0 3 L0 84" stroke="#FFFFFF" strokeOpacity="0.24" strokeWidth="3"/>
          <g transform={'translate(28 11) rotate('+armA+')'}>
            <path d="M0 0 L10 63" stroke={coat} strokeWidth="21"/>
            <circle cx="10" cy="66" r="10" fill={skin}/>
          </g>
          <rect x="-12" y="-13" width="24" height="18" rx="6" fill={skin}/>
          <g transform={'translate(0 -35) rotate('+look+')'}>
            <ellipse cx="0" cy="0" rx="36" ry="40" fill={skin}/>
            <path d="M-35 -2 Q-43 -48 0 -44 Q40 -44 37 -9 Q15 -19 -4 -14 Q-24 -21 -35 -2Z" fill="#1B2430"/>
            <circle cx="16" cy="1" r="3.5" fill="#1C1C23"/>
            {action === 'react' && <ellipse cx="23" cy="20" rx="5" ry="8" fill="#302128"/>}
          </g>
        </g>
      </g>
    </svg>
  </div>;
};
