<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Lang\Registry;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * RepetitionReducer — reduces word and bigram repetitions using synonyms.
 */
class RepetitionReducer
{
    private array $langPack = [];
    private array $profile = [];
    private int $intensity = 60;
    private RandomHelper $rng;
    public array $changes = [];

    /**
     * Process text — reduce repetitions.
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
            $this->profile['repetition_intensity']
        );

        if ($prob < 0.05) {
            return $text;
        }

        $text = $this->reduceWordRepetitions($text, $prob);

        return $text;
    }

    /**
     * Reduce word repetitions in sliding window.
     */
    private function reduceWordRepetitions(string $text, float $prob): string
    {
        $synonyms = $this->langPack['synonyms'] ?? [];
        $stopWords = array_flip($this->langPack['stop_words'] ?? []);

        if (empty($synonyms)) {
            return $text;
        }

        $sentences = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        if (count($sentences) < 3) {
            return $text;
        }

        $windowSize = 3;
        $changed = false;

        for ($i = 0; $i < count($sentences); $i++) {
            // Build window
            $windowStart = max(0, $i - $windowSize + 1);
            $windowSentences = array_slice($sentences, $windowStart, $windowSize);

            // Count content words in window
            $wordCounts = [];
            foreach ($windowSentences as $s) {
                foreach ($this->extractContentWords($s, $stopWords) as $word) {
                    $lower = mb_strtolower($word);
                    $wordCounts[$lower] = ($wordCounts[$lower] ?? 0) + 1;
                }
            }

            // Find repeated words with synonyms
            foreach ($wordCounts as $word => $count) {
                if ($count >= 2 && isset($synonyms[$word]) && Profiles::coinFlip($prob, $this->rng)) {
                    $syn = $this->rng->choice($synonyms[$word]);

                    // Replace last occurrence in current sentence
                    $pattern = '/\b' . preg_quote($word, '/') . '\b/ui';
                    if (preg_match($pattern, $sentences[$i])) {
                        $sentences[$i] = preg_replace($pattern, $syn, $sentences[$i], 1);
                        $this->changes[] = [
                            'type' => 'repetition_word',
                            'from' => $word,
                            'to' => $syn,
                        ];
                        $changed = true;
                        break; // One replacement per sentence
                    }
                }
            }
        }

        return $changed ? implode(' ', $sentences) : $text;
    }

    /**
     * Extract content words (excluding stop words and short words).
     * @return string[]
     */
    private function extractContentWords(string $text, array $stopWords): array
    {
        preg_match_all('/[\p{L}]+/u', $text, $matches);
        $words = [];
        foreach ($matches[0] as $word) {
            $lower = mb_strtolower($word);
            if (mb_strlen($lower) > 2 && !isset($stopWords[$lower])) {
                $words[] = $word;
            }
        }
        return $words;
    }
}
