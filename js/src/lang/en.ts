/**
 * English language pack.
 */

import type { LangPack } from '../types';

export const en: LangPack = {
  code: 'en',
  name: 'English',
  bureaucratic: {
    'utilize': ['use'],
    'implement': ['do', 'apply', 'set up'],
    'facilitate': ['help', 'ease', 'make easier'],
    'demonstrate': ['show'],
    'subsequently': ['then', 'later'],
    'consequently': ['so', 'as a result'],
    'nevertheless': ['still', 'yet'],
    'furthermore': ['also', 'plus'],
    'additionally': ['also', 'on top of that'],
    'comprehensive': ['full', 'complete', 'thorough'],
    'significant': ['big', 'major', 'notable'],
    'approximately': ['about', 'roughly', 'around'],
    'fundamental': ['basic', 'core', 'key'],
    'methodology': ['method', 'approach'],
    'optimization': ['improvement', 'tuning'],
    'functionality': ['feature', 'capability'],
    'perspective': ['view', 'angle', 'take'],
    'paradigm': ['model', 'framework'],
    'leverage': ['use', 'take advantage of'],
    'streamline': ['simplify', 'speed up'],
  },
  synonyms: {
    'important': ['key', 'vital', 'crucial', 'essential'],
    'good': ['great', 'solid', 'strong', 'fine'],
    'bad': ['poor', 'weak', 'flawed'],
    'help': ['assist', 'support', 'aid'],
    'make': ['create', 'build', 'produce'],
    'use': ['employ', 'apply', 'rely on'],
    'show': ['reveal', 'highlight', 'display'],
    'big': ['large', 'major', 'substantial'],
    'small': ['minor', 'tiny', 'slight'],
    'fast': ['quick', 'rapid', 'swift'],
  },
  connectors: [
    'however', 'moreover', 'furthermore', 'additionally',
    'consequently', 'therefore', 'nevertheless', 'in addition',
    'as a result', 'on the other hand', 'in conclusion',
    'for instance', 'specifically', 'notably',
  ],
  fillers: [
    'well', 'actually', 'basically', 'honestly',
    'you know', 'I mean', 'so to speak',
  ],
};
