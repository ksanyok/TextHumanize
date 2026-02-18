<?php

declare(strict_types=1);

namespace TextHumanize;

use TextHumanize\Lang\Registry;

/**
 * Smart sentence splitter — correct segmentation considering abbreviations.
 *
 * Handles problems of naive regex approach:
 * - Abbreviations (т.д., Mr., Inc.)
 * - Decimal numbers (3.14)
 * - Initials (А.С. Пушкин)
 * - Direct speech ("Hello!" — he said.)
 * - URLs and emails inside sentences
 * - Ellipsis (...)
 * - Nested quotes and parentheses
 */
class SentenceSplitter
{
    /** Universal abbreviations (all languages). */
    private const UNIVERSAL_ABBREVS = [
        'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'inc', 'ltd',
        'corp', 'etc', 'vs', 'approx', 'dept', 'est', 'govt',
        'intl', 'no', 'nos', 'vol', 'vols', 'rev', 'fig', 'misc',
        'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep',
        'oct', 'nov', 'dec',
        'www', 'http', 'https', 'ftp',
    ];

    /** @var array<string, true> Combined abbreviation set (lowercased, dot-stripped). */
    private array $abbreviations;

    private string $lang;

    public function __construct(string $lang = 'en')
    {
        $this->lang = $lang;
        $langPack = Registry::get($lang);

        $packAbbrevs = $langPack['abbreviations'] ?? [];

        $this->abbreviations = [];
        foreach ($packAbbrevs as $a) {
            $key = mb_strtolower(rtrim($a, '.'));
            $this->abbreviations[$key] = true;
        }
        foreach (self::UNIVERSAL_ABBREVS as $a) {
            $this->abbreviations[$a] = true;
        }
    }

    /**
     * Split text into sentences.
     *
     * @return list<string>
     */
    public function split(string $text): array
    {
        if (trim($text) === '') {
            return [];
        }

        $spans = $this->splitSpans($text);
        return array_map(fn(array $s): string => $s['text'], $spans);
    }

    /**
     * Split text into sentence spans with positions.
     *
     * Each span is an associative array with keys:
     *   text  — sentence text
     *   start — start offset in the original text
     *   end   — end offset in the original text
     *   index — 0-based sentence index
     *
     * @return list<array{text: string, start: int, end: int, index: int}>
     */
    public function splitSpans(string $text): array
    {
        if (trim($text) === '') {
            return [];
        }

        $breaks = $this->findBreaks($text);

        $sentences = [];
        $start = 0;

        foreach ($breaks as $brk) {
            $sentText = trim(mb_substr($text, $start, $brk - $start));
            if ($sentText !== '') {
                $sentences[] = [
                    'text'  => $sentText,
                    'start' => $start,
                    'end'   => $brk,
                    'index' => count($sentences),
                ];
            }
            $start = $brk;
        }

        // Last sentence
        $last = trim(mb_substr($text, $start));
        if ($last !== '') {
            $sentences[] = [
                'text'  => $last,
                'start' => $start,
                'end'   => mb_strlen($text),
                'index' => count($sentences),
            ];
        }

        return $sentences;
    }

    /**
     * Repair incorrectly split sentences.
     *
     * Merges sentences when:
     * - The previous one does not end with .!?
     * - The current one starts with a lowercase letter
     * - The previous one is too short (1-2 words) and doesn't end with .!?
     *
     * @param list<string> $sentences
     * @return list<string>
     */
    public function repair(array $sentences): array
    {
        if (count($sentences) < 2) {
            return $sentences;
        }

        $result = [$sentences[0]];

        for ($i = 1; $i < count($sentences); $i++) {
            $prev = $result[count($result) - 1];
            $curr = $sentences[$i];

            $shouldMerge = false;

            // If previous doesn't end with .!?…
            if ($prev !== '' && !$this->endsWithTerminator($prev)) {
                $shouldMerge = true;
            }

            // If current starts with lowercase
            if ($curr !== '' && $this->startsWithLower($curr)) {
                $shouldMerge = true;
            }

            // If previous is too short (1-2 words) and not ending with punctuation
            if ($prev !== '' && str_word_count($prev) <= 2 && !$this->endsWithTerminator($prev)) {
                $shouldMerge = true;
            }

            if ($shouldMerge) {
                $result[count($result) - 1] = $prev . ' ' . $curr;
            } else {
                $result[] = $curr;
            }
        }

        return $result;
    }

    // ---------------------------------------------------------------
    // Internal helpers
    // ---------------------------------------------------------------

    /**
     * Find sentence break positions in text.
     *
     * @return list<int>
     */
    private function findBreaks(string $text): array
    {
        $breaks = [];

        // Build protected zones (regions where we must not break)
        $protected = $this->buildProtectedZones($text);

        // Find all potential sentence-ending punctuation followed by whitespace
        // Pattern: .!?… + optional closing quotes/brackets + whitespace
        if (preg_match_all('/([.!?…]["\'\x{00BB}\x{201D}\)\]]*)\s+/u', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $match) {
                $fullMatchStart = (int) $match[1];
                $fullMatch      = $match[0];
                $pos            = $fullMatchStart + strlen($fullMatch); // byte position after whitespace

                // Byte offset of the punctuation mark
                $dotPos = $fullMatchStart;

                // Check if inside a protected zone
                if ($this->inProtected($dotPos, $protected)) {
                    continue;
                }

                // Check that the next character is uppercase or opening quote/dash
                if ($pos < strlen($text)) {
                    $nextChar = mb_substr(substr($text, $pos, 6), 0, 1);
                    $isUpper  = mb_strtoupper($nextChar) === $nextChar && mb_strtolower($nextChar) !== $nextChar;
                    if (!$isUpper && !in_array($nextChar, ['"', "'", '«', "\u{201C}", '(', '—'], true)) {
                        continue;
                    }
                }

                // Check if the punctuation is a dot — may be abbreviation
                if ($text[$dotPos] === '.') {
                    $wordBefore = $this->getWordBeforeDot($text, $dotPos);

                    if ($wordBefore !== '' && isset($this->abbreviations[mb_strtolower($wordBefore)])) {
                        continue;
                    }

                    // Single-letter initial
                    if ($wordBefore !== '' && mb_strlen($wordBefore) === 1 && ctype_alpha($wordBefore)) {
                        continue;
                    }

                    // Decimal number
                    if ($dotPos > 0 && ctype_digit($text[$dotPos - 1])) {
                        if ($dotPos + 1 < strlen($text) && ctype_digit($text[$dotPos + 1])) {
                            continue;
                        }
                    }
                }

                $breaks[] = $pos;
            }
        }

        $breaks = array_unique($breaks);
        sort($breaks);

        return $breaks;
    }

    /**
     * Build a list of protected zones (byte ranges where splitting is forbidden).
     *
     * @return list<array{int, int}>
     */
    private function buildProtectedZones(string $text): array
    {
        $zones = [];

        // Placeholders from segmenter (\x00THZ_...\x00)
        if (preg_match_all('/\x00THZ_[A-Z_]+_\d+\x00/', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $zones[] = [$m[1], $m[1] + strlen($m[0])];
            }
        }

        // Quoted blocks (direct speech) — double quotes
        if (preg_match_all('/"[^"]*"/u', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                if (strlen($m[0]) < 500) {
                    $zones[] = [$m[1], $m[1] + strlen($m[0])];
                }
            }
        }

        // Guillemets «»
        if (preg_match_all('/\x{00AB}[^\x{00BB}]*\x{00BB}/u', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                if (strlen($m[0]) < 500) {
                    $zones[] = [$m[1], $m[1] + strlen($m[0])];
                }
            }
        }

        // Parentheses
        if (preg_match_all('/\([^)]*\)/', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                if (strlen($m[0]) < 300) {
                    $zones[] = [$m[1], $m[1] + strlen($m[0])];
                }
            }
        }

        // Ellipsis not followed by uppercase letter (not a sentence boundary)
        if (preg_match_all('/\.\.\.(?!\s+[A-Z\x{0410}-\x{042F}\x{0401}\x{0406}\x{0407}\x{0404}\x{0490}])/u', $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $zones[] = [$m[1], $m[1] + strlen($m[0])];
            }
        }

        // Multi-dot abbreviations: т.д., т.п., т.е., e.g., etc.
        $abbrPattern = '/(?:'
            . 'т\.д|т\.п|т\.е|и т\.д|и т\.п|т\.к|т\.н'
            . '|e\.g|i\.e|a\.m|p\.m|vs|p\.s'
            . '|к\.т\.н|д\.т\.н|Ph\.D|M\.D|B\.A|M\.A'
            . ')\./ui';

        if (preg_match_all($abbrPattern, $text, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $zones[] = [$m[1], $m[1] + strlen($m[0])];
            }
        }

        return $zones;
    }

    /**
     * Check whether a byte position falls inside a protected zone.
     *
     * @param list<array{int, int}> $zones
     */
    private function inProtected(int $pos, array $zones): bool
    {
        foreach ($zones as [$start, $end]) {
            if ($pos >= $start && $pos < $end) {
                return true;
            }
        }
        return false;
    }

    /**
     * Extract the word immediately before the dot at the given byte position.
     */
    private function getWordBeforeDot(string $text, int $dotPos): string
    {
        if ($dotPos <= 0) {
            return '';
        }

        $end   = $dotPos;
        $start = $end - 1;

        while ($start > 0 && ctype_alpha($text[$start - 1])) {
            $start--;
        }

        $word = substr($text, $start, $end - $start);

        // Check for multi-dot abbreviation (e.g. т.д.)
        if ($start > 1 && $text[$start - 1] === '.' && $start > 2 && ctype_alpha($text[$start - 2])) {
            $widerStart = $start - 2;
            while ($widerStart > 0 && (ctype_alpha($text[$widerStart - 1]) || $text[$widerStart - 1] === '.')) {
                $widerStart--;
            }
            $wider = substr($text, $widerStart, $end - $widerStart);
            if (substr_count($wider, '.') >= 1) {
                return str_replace('.', '', $wider);
            }
        }

        return $word;
    }

    /**
     * Check whether the string ends with a sentence terminator (.!?…).
     */
    private function endsWithTerminator(string $s): bool
    {
        $last = mb_substr($s, -1);
        return in_array($last, ['.', '!', '?', '…'], true);
    }

    /**
     * Check whether the string starts with a lowercase letter.
     */
    private function startsWithLower(string $s): bool
    {
        $first = mb_substr($s, 0, 1);
        return mb_strtolower($first) === $first && mb_strtoupper($first) !== $first;
    }
}

/**
 * Convenience function: split text into sentences.
 *
 * @return list<string>
 */
function split_sentences(string $text, string $lang = 'en'): array
{
    return (new SentenceSplitter($lang))->split($text);
}
