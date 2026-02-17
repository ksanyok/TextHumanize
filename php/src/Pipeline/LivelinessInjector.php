<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

use TextHumanize\Lang\Registry;
use TextHumanize\Profiles;
use TextHumanize\RandomHelper;

/**
 * LivelinessInjector — adds conversational markers for chat/web profiles.
 */
class LivelinessInjector
{
    private array $langPack = [];
    private array $profile = [];
    private int $intensity = 60;
    private RandomHelper $rng;
    public array $changes = [];

    /**
     * Process text — inject liveliness markers.
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
            $this->profile['liveliness_intensity']
        );

        if ($prob < 0.1) {
            return $text;
        }

        $text = $this->injectMarkers($text, $prob);
        $text = $this->varyPunctuation($text, $prob);

        return $text;
    }

    /**
     * Insert colloquial markers into some sentences.
     */
    private function injectMarkers(string $text, float $prob): string
    {
        $markers = $this->langPack['colloquial_markers'] ?? [];
        if (empty($markers)) {
            return $text;
        }

        $sentences = preg_split('/(?<=[.!?…])\s+/u', trim($text));
        if (count($sentences) < 4) {
            return $text;
        }

        $usedMarkers = [];
        $maxInserts = max(1, intdiv(count($sentences), 8));
        $inserts = 0;

        for ($i = 2; $i < count($sentences) && $inserts < $maxInserts; $i++) {
            if (!Profiles::coinFlip($prob * 0.3, $this->rng)) {
                continue;
            }

            // Pick unused marker
            $available = array_diff($markers, $usedMarkers);
            if (empty($available)) {
                break;
            }

            $marker = $this->rng->choice(array_values($available));
            $usedMarkers[] = $marker;

            // Insert after first word
            $words = preg_split('/\s+/', trim($sentences[$i]), 2);
            if (count($words) >= 2) {
                $sentences[$i] = $words[0] . ', ' . $marker . ', ' . $words[1];
                $this->changes[] = [
                    'type' => 'liveliness_marker',
                    'marker' => $marker,
                ];
                $inserts++;
            }
        }

        return implode(' ', $sentences);
    }

    /**
     * Vary punctuation — replace first semicolon with period.
     */
    private function varyPunctuation(string $text, float $prob): string
    {
        if (!Profiles::coinFlip($prob * 0.3, $this->rng)) {
            return $text;
        }

        $pos = mb_strpos($text, ';');
        if ($pos === false) {
            return $text;
        }

        // Replace ; with . and capitalize next letter
        $before = mb_substr($text, 0, $pos);
        $after = mb_substr($text, $pos + 1);
        $after = ltrim($after);

        if (mb_strlen($after) > 0) {
            $after = mb_strtoupper(mb_substr($after, 0, 1)) . mb_substr($after, 1);
        }

        $this->changes[] = ['type' => 'liveliness_punctuation', 'what' => '; → .'];
        return $before . '. ' . $after;
    }
}
