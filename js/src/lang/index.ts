/**
 * Language pack registry.
 */

import type { LangPack } from '../types';
import { en } from './en';
import { ru } from './ru';

const registry: Record<string, LangPack> = {
  en,
  ru,
};

/**
 * Get language pack by code.
 */
export function getLangPack(code: string): LangPack | undefined {
  return registry[code];
}

/**
 * Check if language has deep support (full dictionary).
 */
export function hasDeepSupport(code: string): boolean {
  return code in registry;
}

/**
 * List all supported languages.
 */
export function supportedLanguages(): string[] {
  return Object.keys(registry);
}
