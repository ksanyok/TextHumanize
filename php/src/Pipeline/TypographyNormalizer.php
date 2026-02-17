<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Profiles;

/**
 * Typography normalizer — removes AI-characteristic "perfect" typography.
 */
class TypographyNormalizer
{
    private array $profile;
    public array $changes = [];

    public function __construct(string $profileName = 'web')
    {
        $this->profile = Profiles::get($profileName);
    }

    /**
     * Normalize typography in text.
     *
     * @return array{0: string, 1: array} [normalized_text, changes]
     */
    public function normalize(string $text, string $lang = 'en'): array
    {
        $this->changes = [];

        $text = $this->normalizeDashes($text);
        $text = $this->normalizeQuotes($text);
        $text = $this->normalizeEllipsis($text);
        $text = $this->normalizeSpaces($text);
        $text = $this->normalizePunctuationSpacing($text);
        $text = $this->collapseMultipleSpaces($text);

        return [$text, $this->changes];
    }

    private function normalizeDashes(string $text): string
    {
        $target = $this->profile['typography']['dash'];

        // Em dash → target
        if ($target !== '—') {
            $before = $text;
            $text = str_replace('—', $target, $text);
            if ($text !== $before) {
                $this->changes[] = ['type' => 'typography', 'what' => "em_dash → $target"];
            }
        }

        // Ensure spaces around dashes (in sentence context)
        $text = preg_replace('/(\S)([–—])(\S)/u', '$1 $2 $3', $text);

        return $text;
    }

    private function normalizeQuotes(string $text): string
    {
        $target = $this->profile['typography']['quotes'];

        if ($target === '«»') {
            return $text; // Keep typographic quotes for formal
        }

        $before = $text;
        // Replace French/Russian quotes
        $text = str_replace(['«', '»', '„', '"', '"', '"', '‹', '›'], '"', $text);
        if ($text !== $before) {
            $this->changes[] = ['type' => 'typography', 'what' => 'typographic_quotes → "'];
        }

        return $text;
    }

    private function normalizeEllipsis(string $text): string
    {
        $target = $this->profile['typography']['ellipsis'];

        if ($target === '...') {
            $before = $text;
            $text = str_replace('…', '...', $text);
            if ($text !== $before) {
                $this->changes[] = ['type' => 'typography', 'what' => '… → ...'];
            }
        }

        return $text;
    }

    private function normalizeSpaces(string $text): string
    {
        $before = $text;

        // Remove special Unicode spaces (except for formal profile)
        $specialSpaces = ["\xC2\xA0", "\xE2\x80\xAF", "\xE2\x80\x89",
            "\xE2\x80\x83", "\xE2\x80\x82"];

        foreach ($specialSpaces as $sp) {
            $text = str_replace($sp, ' ', $text);
        }

        // Remove zero-width chars
        $text = str_replace(["\xE2\x80\x8B", "\xE2\x80\x8C", "\xE2\x80\x8D", "\xEF\xBB\xBF"], '', $text);

        if ($text !== $before) {
            $this->changes[] = ['type' => 'typography', 'what' => 'special_spaces normalized'];
        }

        return $text;
    }

    private function normalizePunctuationSpacing(string $text): string
    {
        // Remove space before punctuation
        $text = preg_replace('/\s+([,.;:!?])/u', '$1', $text);
        // Ensure space after punctuation (if followed by a letter)
        $text = preg_replace('/([,.;:!?])(\p{L})/u', '$1 $2', $text);

        return $text;
    }

    private function collapseMultipleSpaces(string $text): string
    {
        // Collapse multiple spaces but preserve indentation
        $lines = explode("\n", $text);
        $result = [];
        foreach ($lines as $line) {
            // Preserve leading whitespace
            if (preg_match('/^(\s*)(.*)$/', $line, $m)) {
                $result[] = $m[1] . preg_replace('/  +/', ' ', $m[2]);
            } else {
                $result[] = $line;
            }
        }
        return implode("\n", $result);
    }
}
