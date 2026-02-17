<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Lang\Registry;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * Debureaucratizer — replaces bureaucratic words and phrases with simpler alternatives.
 */
class Debureaucratizer
{
    private array $langPack = [];
    private array $profile = [];
    private int $intensity = 60;
    private RandomHelper $rng;
    public array $changes = [];

    /**
     * Process text — replace bureaucratic words and phrases.
     */
    public function process(string $text, array $langPack, array $profile, int $intensity, RandomHelper $rng): string
    {
        $this->langPack = $langPack;
        $this->profile = $profile;
        $this->intensity = $intensity;
        $this->rng = $rng;
        $this->changes = [];

        $prob = Profiles::intensityProbability(
            $this->intensity,
            $this->profile['decancel_intensity']
        );

        if ($prob < 0.05) {
            return $text;
        }

        $text = $this->replacePhrases($text, $prob);
        $text = $this->replaceWords($text, $prob);

        return $text;
    }

    /**
     * Replace bureaucratic phrases (longest first).
     */
    private function replacePhrases(string $text, float $prob): string
    {
        $phrases = $this->langPack['bureaucratic_phrases'] ?? [];
        if (empty($phrases)) {
            return $text;
        }

        // Sort by length (longest first)
        uksort($phrases, fn(string $a, string $b): int => mb_strlen($b) - mb_strlen($a));

        foreach ($phrases as $phrase => $replacements) {
            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            $pattern = '/\b' . preg_quote($phrase, '/') . '\b/ui';
            if (preg_match($pattern, $text, $match, PREG_OFFSET_CAPTURE)) {
                $replacement = $this->rng->choice($replacements);
                // Preserve case of first letter
                $replacement = self::matchCase($match[0][0], $replacement);
                $text = substr_replace($text, $replacement, (int) $match[0][1], strlen($match[0][0]));

                $this->changes[] = [
                    'type' => 'decancel_phrase',
                    'from' => $match[0][0],
                    'to' => $replacement,
                ];
            }
        }

        return $text;
    }

    /**
     * Replace bureaucratic words.
     */
    private function replaceWords(string $text, float $prob): string
    {
        $words = $this->langPack['bureaucratic'] ?? [];
        if (empty($words)) {
            return $text;
        }

        foreach ($words as $word => $replacements) {
            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            $pattern = '/\b' . preg_quote($word, '/') . '\b/ui';
            if (preg_match($pattern, $text, $match, PREG_OFFSET_CAPTURE)) {
                if (!Profiles::coinFlip($prob, $this->rng)) {
                    continue;
                }

                $replacement = $this->rng->choice($replacements);
                $replacement = self::matchCase($match[0][0], $replacement);
                $text = substr_replace($text, $replacement, (int) $match[0][1], strlen($match[0][0]));

                $this->changes[] = [
                    'type' => 'decancel_word',
                    'from' => $match[0][0],
                    'to' => $replacement,
                ];
            }
        }

        return $text;
    }

    /**
     * Match case of original text (first letter).
     */
    private static function matchCase(string $original, string $replacement): string
    {
        if (mb_strlen($original) === 0 || mb_strlen($replacement) === 0) {
            return $replacement;
        }

        $firstChar = mb_substr($original, 0, 1);
        if ($firstChar === mb_strtoupper($firstChar)) {
            return mb_strtoupper(mb_substr($replacement, 0, 1)) . mb_substr($replacement, 1);
        }

        return $replacement;
    }
}
