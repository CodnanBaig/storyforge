import type {StyleId, StyleTokens} from './types';

export const styles: Record<StyleId, StyleTokens> = {
  'midnight-dossier': {
    background: '#08151F', paper: '#EFE8D9', muted: '#91A3AD',
    teal: '#609B92', amber: '#E6AB5D', stone: '#425765',
    wood: '#725A42', dark: '#122938',
  },
  'coastal-archive': {
    background: '#132832', paper: '#F4ECD9', muted: '#A1B5B8',
    teal: '#8AB6A4', amber: '#E3BE78', stone: '#5C7580',
    wood: '#8C775C', dark: '#203C47',
  },
  'ember-noir': {
    background: '#191922', paper: '#EFE3CD', muted: '#AAA3A0',
    teal: '#7E9891', amber: '#E6A163', stone: '#585765',
    wood: '#765449', dark: '#302735',
  },
};
