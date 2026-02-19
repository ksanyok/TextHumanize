/**
 * Core types for TextHumanize.
 */

/** Options for text humanization. */
export interface HumanizeOptions {
  /** Language code: 'auto', 'en', 'ru', 'uk', 'de', 'fr', 'es', etc. */
  lang?: string;
  /** Processing profile. */
  profile?: Profile;
  /** Processing intensity 0-100. */
  intensity?: number;
  /** Preservation settings. */
  preserve?: PreserveConfig;
  /** Processing constraints. */
  constraints?: ConstraintConfig;
  /** Random seed for reproducibility. */
  seed?: number;
}

export type Profile =
  | 'chat' | 'web' | 'seo' | 'docs' | 'formal'
  | 'academic' | 'marketing' | 'social' | 'email';

export interface PreserveConfig {
  codeBlocks?: boolean;
  urls?: boolean;
  emails?: boolean;
  hashtags?: boolean;
  mentions?: boolean;
  markdown?: boolean;
  html?: boolean;
  numbers?: boolean;
  brandTerms?: string[];
}

export interface ConstraintConfig {
  maxChangeRatio?: number;
  minSentenceLength?: number;
  keepKeywords?: string[];
}

/** Result of text humanization. */
export interface HumanizeResult {
  /** Original input text. */
  original: string;
  /** Processed text. */
  text: string;
  /** Detected language. */
  lang: string;
  /** Profile used. */
  profile: string;
  /** Intensity used. */
  intensity: number;
  /** List of changes applied. */
  changes: ChangeEntry[];
  /** Metrics before processing. */
  metricsBefore: Record<string, number>;
  /** Metrics after processing. */
  metricsAfter: Record<string, number>;
}

export interface ChangeEntry {
  type: string;
  description: string;
  [key: string]: unknown;
}

/** Text analysis report. */
export interface AnalysisReport {
  lang: string;
  totalChars: number;
  totalWords: number;
  totalSentences: number;
  avgSentenceLength: number;
  sentenceLengthVariance: number;
  bureaucraticRatio: number;
  connectorRatio: number;
  repetitionScore: number;
  typographyScore: number;
  burstinessScore: number;
  artificialityScore: number;
  fleschKincaidGrade: number;
  colemanLiauIndex: number;
  avgWordLength: number;
  avgSyllablesPerWord: number;
  predictabilityScore: number;
  charPerplexity: number;
  vocabularyRichness: number;
}

/** Language pack interface. */
export interface LangPack {
  code: string;
  name: string;
  bureaucratic: Record<string, string[]>;
  synonyms: Record<string, string[]>;
  connectors: string[];
  fillers: string[];
}
