<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Lang\Registry;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * StructureDiversifier — varies sentence structure, replaces AI connectors.
 */
class StructureDiversifier
{
    private array $langPack = [];
    private array $profile = [];
    private int $intensity = 60;
    private RandomHelper $rng;
    public array $changes = [];

    /**
     * Process text — diversify structure.
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
            $this->profile['structure_intensity']
        );

        if ($prob < 0.05) {
            return $text;
        }

        $text = $this->replaceAiConnectors($text, $prob);
        $text = $this->diversifySentenceStarts($text, $prob);
        $text = $this->splitLongSentences($text, $prob);
        $text = $this->joinShortSentences($text, $prob);

        return $text;
    }

    /**
     * Replace AI-characteristic connectors.
     */
    private function replaceAiConnectors(string $text, float $prob): string
    {
        $connectors = $this->langPack['ai_connectors'] ?? [];
        if (empty($connectors)) {
            return $text;
        }

        $maxReplacements = max(3, intdiv(count($connectors), 2));
        $replaced = 0;

        foreach ($connectors as $connector => $alternatives) {
            if ($replaced >= $maxReplacements) {
                break;
            }

            if (!Profiles::coinFlip($prob, $this->rng)) {
                continue;
            }

            // Try sentence-start pattern first
            $pattern = '/(?<=^|[.!?]\s)' . preg_quote($connector, '/') . '\b/um';
            if (preg_match($pattern, $text)) {
                $replacement = $this->rng->choice($alternatives);
                $text = preg_replace($pattern, $replacement, $text, 1);
                $this->changes[] = [
                    'type' => 'structure_connector',
                    'from' => $connector,
                    'to' => $replacement,
                ];
                $replaced++;
            }
        }

        return $text;
    }

    /**
     * Diversify sentence starts — vary if 2+ consecutive sentences start the same.
     */
    private function diversifySentenceStarts(string $text, float $prob): string
    {
        $starters = $this->langPack['sentence_starters'] ?? [];
        if (empty($starters)) {
            return $text;
        }

        $sentences = self::splitSentences($text);
        if (count($sentences) < 2) {
            return $text;
        }

        $changed = false;
        for ($i = 1; $i < count($sentences); $i++) {
            $prev = self::firstWord($sentences[$i - 1]);
            $curr = self::firstWord($sentences[$i]);

            if ($prev !== '' && mb_strtolower($prev) === mb_strtolower($curr)) {
                if (!Profiles::coinFlip($prob, $this->rng)) {
                    continue;
                }

                if (isset($starters[$curr])) {
                    $alt = $this->rng->choice($starters[$curr]);
                    $sentences[$i] = preg_replace(
                        '/^' . preg_quote($curr, '/') . '/u',
                        $alt,
                        $sentences[$i],
                        1
                    );
                    $changed = true;
                    $this->changes[] = [
                        'type' => 'structure_starter',
                        'from' => $curr,
                        'to' => $alt,
                    ];
                }
            }
        }

        return $changed ? implode(' ', $sentences) : $text;
    }

    /**
     * Split sentences that are too long.
     */
    private function splitLongSentences(string $text, float $prob): string
    {
        $targets = $this->langPack['profile_targets'][$this->profile['description'] === 'Lively conversational style' ? 'chat' : 'web'] ?? ['min' => 10, 'max' => 22];
        $maxTarget = $targets['max'] ?? 22;
        $splitAt = $maxTarget * 2;

        $sentences = self::splitSentences($text);
        $result = [];

        foreach ($sentences as $sentence) {
            $wordCount = count(preg_split('/\s+/', trim($sentence)));

            if ($wordCount > $splitAt && Profiles::coinFlip($prob, $this->rng)) {
                $parts = $this->trySplitSentence($sentence);
                if ($parts !== null) {
                    $result = array_merge($result, $parts);
                    $this->changes[] = ['type' => 'structure_split', 'sentence' => mb_substr($sentence, 0, 50)];
                    continue;
                }
            }

            $result[] = $sentence;
        }

        return implode(' ', $result);
    }

    /**
     * Join very short consecutive sentences.
     */
    private function joinShortSentences(string $text, float $prob): string
    {
        $targets = $this->langPack['profile_targets']['web'] ?? ['min' => 10, 'max' => 22];
        $minTarget = $targets['min'] ?? 10;
        $conjunctions = array_slice($this->langPack['conjunctions'] ?? ['and', 'but'], 0, 4);

        if (empty($conjunctions)) {
            return $text;
        }

        $sentences = self::splitSentences($text);
        if (count($sentences) < 2) {
            return $text;
        }

        $result = [];
        $i = 0;

        while ($i < count($sentences)) {
            $wordCount = count(preg_split('/\s+/', trim($sentences[$i])));

            if ($wordCount <= $minTarget
                && $i + 1 < count($sentences)
                && count(preg_split('/\s+/', trim($sentences[$i + 1]))) <= $minTarget
                && Profiles::coinFlip($prob, $this->rng)
            ) {
                $conj = $this->rng->choice($conjunctions);
                $first = rtrim($sentences[$i]);
                // Remove ending punctuation
                $first = preg_replace('/[.!?]+$/', '', $first);
                $second = $sentences[$i + 1];
                // Lowercase first letter of second
                $second = mb_strtolower(mb_substr($second, 0, 1)) . mb_substr($second, 1);

                $result[] = "$first, $conj $second";
                $this->changes[] = ['type' => 'structure_join'];
                $i += 2;
            } else {
                $result[] = $sentences[$i];
                $i++;
            }
        }

        return implode(' ', $result);
    }

    /**
     * Try to split a sentence at a conjunction near the middle.
     * @return string[]|null
     */
    private function trySplitSentence(string $sentence): ?array
    {
        $splitConj = $this->langPack['split_conjunctions'] ?? [];
        $words = preg_split('/\s+/', trim($sentence));
        $mid = intdiv(count($words), 2);
        $bestPos = null;
        $bestDist = PHP_INT_MAX;

        foreach ($splitConj as $conj) {
            $pattern = '/\b' . preg_quote($conj, '/') . '\b/ui';
            if (preg_match_all($pattern, $sentence, $matches, PREG_OFFSET_CAPTURE)) {
                foreach ($matches[0] as $m) {
                    // Count words before this position
                    $before = mb_substr($sentence, 0, $m[1]);
                    $wordsBefore = count(preg_split('/\s+/', trim($before)));
                    $wordsAfter = count($words) - $wordsBefore;
                    $dist = abs($wordsBefore - $mid);

                    if ($wordsBefore >= 5 && $wordsAfter >= 5 && $dist < $bestDist) {
                        $bestDist = $dist;
                        $bestPos = $m[1];
                    }
                }
            }
        }

        if ($bestPos === null) {
            return null;
        }

        $first = trim(mb_substr($sentence, 0, $bestPos));
        $second = trim(mb_substr($sentence, $bestPos));

        // Add period to first part if it doesn't end with punctuation
        if (!preg_match('/[.!?]$/', $first)) {
            $first .= '.';
        }

        // Capitalize second part
        $second = mb_strtoupper(mb_substr($second, 0, 1)) . mb_substr($second, 1);

        return [$first, $second];
    }

    /**
     * Split text into sentences.
     * @return string[]
     */
    private static function splitSentences(string $text): array
    {
        $parts = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        return array_filter($parts, fn(string $s): bool => trim($s) !== '');
    }

    /**
     * Get first word of a sentence.
     */
    private static function firstWord(string $sentence): string
    {
        $words = preg_split('/\s+/', trim($sentence), 2);
        return $words[0] ?? '';
    }
}
