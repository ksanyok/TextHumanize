<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * UniversalProcessor — language-agnostic text processing.
 * Works for any language using statistical/structural methods.
 */
class UniversalProcessor
{
    private array $profile = [];
    private int $intensity = 60;
    private RandomHelper $rng;
    public array $changes = [];

    /**
     * Process text with language-agnostic methods.
     */
    public function process(string $text, array $profile, int $intensity, RandomHelper $rng): string
    {
        $this->profile = $profile;
        $this->intensity = $intensity;
        $this->rng = $rng;
        $this->changes = [];

        $prob = $this->intensity / 100.0;

        $text = $this->normalizeUnicode($text, $prob);
        $text = $this->varySentenceLengths($text, $prob);
        $text = $this->varyPunctuation($text, $prob);
        $text = $this->breakParagraphRhythm($text, $prob);

        return $text;
    }

    /**
     * Normalize Unicode characters.
     */
    private function normalizeUnicode(string $text, float $prob): string
    {
        $dash = $this->profile['typography']['dash'];

        // Em dash → target (if not formal)
        if ($dash !== '—') {
            $before = $text;
            $text = str_replace('—', $dash, $text);
            if ($text !== $before) {
                $this->changes[] = ['type' => 'universal_unicode', 'what' => 'em_dash → ' . $dash];
            }
        }

        $quotes = $this->profile['typography']['quotes'];
        if ($quotes !== '«»') {
            $before = $text;
            $text = str_replace(['«', '»', '„', "\u{201C}", "\u{201D}", "\u{201E}"], '"', $text);
            $text = str_replace(["\u{2018}", "\u{2019}", "\u{201A}"], "'", $text);
            if ($text !== $before) {
                $this->changes[] = ['type' => 'universal_unicode', 'what' => 'smart_quotes normalized'];
            }
        }

        // Ellipsis
        $ellipsis = $this->profile['typography']['ellipsis'];
        if ($ellipsis === '...') {
            $text = str_replace('…', '...', $text);
        }

        // Special spaces → regular
        $specialSpaces = ["\xC2\xA0", "\xE2\x80\xAF", "\xE2\x80\x89",
            "\xE2\x80\x83", "\xE2\x80\x82"];
        foreach ($specialSpaces as $sp) {
            $text = str_replace($sp, ' ', $text);
        }

        // Zero-width chars
        $text = str_replace(["\xE2\x80\x8B", "\xE2\x80\x8C", "\xE2\x80\x8D", "\xEF\xBB\xBF"], '', $text);

        // Hyphen variants → ASCII
        $text = str_replace(['‐', '‑', '⁃'], '-', $text);

        // Bullet chars → dash
        $text = str_replace(['•', '◦', '▪', '▸', '▹'], '-', $text);

        return $text;
    }

    /**
     * Vary sentence lengths to increase burstiness.
     */
    private function varySentenceLengths(string $text, float $prob): string
    {
        $sentences = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        if (count($sentences) < 3) {
            return $text;
        }

        $lengths = array_map(fn(string $s): int => count(preg_split('/\s+/', trim($s))), $sentences);
        $avg = array_sum($lengths) / count($lengths);

        if ($avg <= 0) {
            return $text;
        }

        // Calculate coefficient of variation
        $variance = 0;
        foreach ($lengths as $len) {
            $variance += ($len - $avg) ** 2;
        }
        $variance /= count($lengths);
        $cv = sqrt($variance) / $avg;

        // If sentences are too uniform (low burstiness), try splitting long ones
        if ($cv < 0.5 && Profiles::coinFlip($prob, $this->rng)) {
            $threshold = $avg * 1.8;
            $result = [];

            foreach ($sentences as $sentence) {
                $wc = count(preg_split('/\s+/', trim($sentence)));
                if ($wc > $threshold) {
                    $parts = $this->universalSplitSentence($sentence);
                    if ($parts !== null) {
                        $result = array_merge($result, $parts);
                        $this->changes[] = ['type' => 'universal_split'];
                        continue;
                    }
                }
                $result[] = $sentence;
            }

            return implode(' ', $result);
        }

        return $text;
    }

    /**
     * Split sentence at comma or semicolon nearest to middle.
     * @return string[]|null
     */
    private function universalSplitSentence(string $sentence): ?array
    {
        $words = preg_split('/\s+/', trim($sentence));
        $mid = intdiv(count($words), 2);

        // Find comma or semicolon nearest to middle
        $bestPos = null;
        $bestDist = PHP_INT_MAX;

        if (preg_match_all('/[;,]/u', $sentence, $matches, PREG_OFFSET_CAPTURE)) {
            foreach ($matches[0] as $m) {
                $beforeText = mb_substr($sentence, 0, (int) $m[1]);
                $wordsBefore = count(preg_split('/\s+/', trim($beforeText)));
                $wordsAfter = count($words) - $wordsBefore;
                $dist = abs($wordsBefore - $mid);

                if ($wordsBefore >= 4 && $wordsAfter >= 4 && $dist < $bestDist) {
                    $bestDist = $dist;
                    $bestPos = $m[1];
                }
            }
        }

        if ($bestPos === null) {
            return null;
        }

        $first = trim(mb_substr($sentence, 0, (int) $bestPos));
        $second = trim(mb_substr($sentence, $bestPos + 1));

        if (!preg_match('/[.!?]$/', $first)) {
            $first .= '.';
        }

        $second = mb_strtoupper(mb_substr($second, 0, 1)) . mb_substr($second, 1);

        return [$first, $second];
    }

    /**
     * Vary punctuation — replace semicolons and excessive colons.
     */
    private function varyPunctuation(string $text, float $prob): string
    {
        if (!Profiles::coinFlip($prob * 0.4, $this->rng)) {
            return $text;
        }

        // Replace first semicolon with period
        $pos = mb_strpos($text, ';');
        if ($pos !== false) {
            $before = mb_substr($text, 0, $pos);
            $after = ltrim(mb_substr($text, $pos + 1));
            if (mb_strlen($after) > 0) {
                $after = mb_strtoupper(mb_substr($after, 0, 1)) . mb_substr($after, 1);
            }
            $text = $before . '. ' . $after;
            $this->changes[] = ['type' => 'universal_punctuation', 'what' => '; → .'];
        }

        return $text;
    }

    /**
     * Break paragraph rhythm — merge tiny adjacent paragraphs if sizes are too uniform.
     */
    private function breakParagraphRhythm(string $text, float $prob): string
    {
        $paragraphs = preg_split('/\n\s*\n/', $text);
        if (count($paragraphs) < 3) {
            return $text;
        }

        $sizes = array_map(fn(string $p): int => mb_strlen(trim($p)), $paragraphs);
        $avg = array_sum($sizes) / count($sizes);

        if ($avg <= 0) {
            return $text;
        }

        $variance = 0;
        foreach ($sizes as $s) {
            $variance += ($s - $avg) ** 2;
        }
        $variance /= count($sizes);
        $cv = sqrt($variance) / $avg;

        // Only if paragraphs are too uniform
        if ($cv < 0.4 && Profiles::coinFlip($prob, $this->rng)) {
            // Find two smallest adjacent paragraphs and merge them
            $minSum = PHP_INT_MAX;
            $mergeIdx = null;

            for ($i = 0; $i < count($paragraphs) - 1; $i++) {
                $sum = $sizes[$i] + $sizes[$i + 1];
                if ($sum < $minSum) {
                    $minSum = $sum;
                    $mergeIdx = $i;
                }
            }

            if ($mergeIdx !== null) {
                $paragraphs[$mergeIdx] = trim($paragraphs[$mergeIdx]) . ' ' . trim($paragraphs[$mergeIdx + 1]);
                array_splice($paragraphs, $mergeIdx + 1, 1);
                $this->changes[] = ['type' => 'universal_paragraph_merge'];
            }
        }

        return implode("\n\n", $paragraphs);
    }
}
