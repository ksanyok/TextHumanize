<?php

declare(strict_types=1);

namespace TextHumanize;

use TextHumanize\Lang\Registry;

/**
 * Language detector — detects text language from content.
 */
class LangDetector
{
    /**
     * Detect the language of the text.
     */
    public static function detect(string $text): string
    {
        $text = trim($text);
        if (mb_strlen($text) < 10) {
            return 'en';
        }

        $cyrillicRatio = self::cyrillicRatio($text);

        if ($cyrillicRatio > 0.5) {
            return self::detectCyrillicLanguage($text);
        }

        if ($cyrillicRatio > 0.1) {
            // Mixed — check Ukrainian markers first
            if (self::hasUkrainianMarkers($text)) {
                return 'uk';
            }
            return 'ru';
        }

        return self::detectLatinLanguage($text);
    }

    /**
     * Calculate ratio of Cyrillic characters.
     */
    private static function cyrillicRatio(string $text): float
    {
        $letters = preg_replace('/[^\\p{L}]/u', '', $text);
        if (mb_strlen($letters) === 0) {
            return 0.0;
        }

        preg_match_all('/[\\p{Cyrillic}]/u', $letters, $matches);
        return count($matches[0]) / mb_strlen($letters);
    }

    /**
     * Detect specific Cyrillic language (ru/uk).
     */
    private static function detectCyrillicLanguage(string $text): string
    {
        if (self::hasUkrainianMarkers($text)) {
            return 'uk';
        }
        if (self::hasRussianMarkers($text)) {
            return 'ru';
        }
        return 'ru'; // Default for Cyrillic
    }

    /**
     * Check for Ukrainian-specific characters and words.
     */
    private static function hasUkrainianMarkers(string $text): bool
    {
        // Ukrainian-unique letters: і, ї, є, ґ
        if (preg_match('/[іїєґІЇЄҐ]/u', $text)) {
            return true;
        }

        $ukWords = ['це', 'або', 'також', 'проте', 'щоб', 'якщо', 'інший',
            'тому', 'але', 'який', 'яка', 'яке', 'які'];
        $lower = mb_strtolower($text);
        foreach ($ukWords as $word) {
            if (preg_match('/\\b' . preg_quote($word, '/') . '\\b/u', $lower)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Check for Russian-specific characters and words.
     */
    private static function hasRussianMarkers(string $text): bool
    {
        // Russian-unique letters: ё, ы, э, ъ
        if (preg_match('/[ёыэъЁЫЭЪ]/u', $text)) {
            return true;
        }

        $ruWords = ['который', 'также', 'однако', 'ещё', 'чтобы', 'если',
            'потому', 'когда', 'очень', 'только', 'между'];
        $lower = mb_strtolower($text);
        foreach ($ruWords as $word) {
            if (preg_match('/\\b' . preg_quote($word, '/') . '\\b/u', $lower)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Detect Latin-script language.
     */
    private static function detectLatinLanguage(string $text): string
    {
        $lower = mb_strtolower($text);
        $scores = [];

        // German markers
        $scores['de'] = 0;
        if (preg_match('/[äöüßÄÖÜ]/u', $text)) {
            $scores['de'] += 5;
        }
        foreach (['der', 'die', 'das', 'und', 'ist', 'ein', 'nicht', 'ich', 'mit', 'auf'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['de'] += 2;
            }
        }

        // French markers
        $scores['fr'] = 0;
        if (preg_match('/[àâçéèêëîïôùûüÿœæ]/u', $lower)) {
            $scores['fr'] += 5;
        }
        foreach (['les', 'des', 'une', 'est', 'dans', 'pas', 'pour', 'que', 'sur', 'avec'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['fr'] += 2;
            }
        }

        // Spanish markers
        $scores['es'] = 0;
        if (preg_match('/[ñ¿¡áéíóú]/u', $lower)) {
            $scores['es'] += 5;
        }
        foreach (['los', 'las', 'una', 'del', 'por', 'para', 'como', 'más', 'pero', 'con'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['es'] += 2;
            }
        }

        // Polish markers
        $scores['pl'] = 0;
        if (preg_match('/[ąęśźżłńćó]/u', $lower)) {
            $scores['pl'] += 5;
        }
        foreach (['nie', 'jest', 'się', 'jak', 'ale', 'dla', 'jest', 'lub', 'tak', 'już'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['pl'] += 2;
            }
        }

        // Portuguese markers
        $scores['pt'] = 0;
        if (preg_match('/[ãõç]/u', $lower)) {
            $scores['pt'] += 5;
        }
        foreach (['uma', 'são', 'como', 'mais', 'dos', 'das', 'para', 'pelo', 'pela', 'com'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['pt'] += 2;
            }
        }

        // Italian markers
        $scores['it'] = 0;
        if (preg_match('/[àèéìòù]/u', $lower)) {
            $scores['it'] += 3;
        }
        foreach (['della', 'delle', 'degli', 'sono', 'anche', 'come', 'questo', 'quello', 'molto', 'perché'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['it'] += 2;
            }
        }

        // English markers
        $scores['en'] = 0;
        foreach (['the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 'but'] as $w) {
            if (preg_match('/\\b' . $w . '\\b/u', $lower)) {
                $scores['en'] += 2;
            }
        }

        arsort($scores);
        $best = array_key_first($scores);
        $bestScore = $scores[$best];

        if ($bestScore < 4) {
            return 'en'; // Fallback
        }

        return $best;
    }
}
