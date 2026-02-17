<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Profile definitions and utility helpers.
 */
class Profiles
{
    /**
     * All profile definitions.
     */
    public const PROFILES = [
        'chat' => [
            'description' => 'Lively conversational style',
            'typography' => ['dash' => '-', 'quotes' => '"', 'ellipsis' => '...'],
            'decancel_intensity' => 1.0,
            'structure_intensity' => 1.0,
            'repetition_intensity' => 0.8,
            'liveliness_intensity' => 0.7,
            'target_sentence_len' => [8, 18],
        ],
        'web' => [
            'description' => 'Neutral web content',
            'typography' => ['dash' => '–', 'quotes' => '"', 'ellipsis' => '...'],
            'decancel_intensity' => 0.8,
            'structure_intensity' => 0.8,
            'repetition_intensity' => 0.7,
            'liveliness_intensity' => 0.3,
            'target_sentence_len' => [10, 22],
        ],
        'seo' => [
            'description' => 'SEO-safe mode',
            'typography' => ['dash' => '–', 'quotes' => '"', 'ellipsis' => '...'],
            'decancel_intensity' => 0.4,
            'structure_intensity' => 0.5,
            'repetition_intensity' => 0.3,
            'liveliness_intensity' => 0.0,
            'target_sentence_len' => [12, 25],
        ],
        'docs' => [
            'description' => 'Technical documentation',
            'typography' => ['dash' => '—', 'quotes' => '"', 'ellipsis' => '…'],
            'decancel_intensity' => 0.3,
            'structure_intensity' => 0.4,
            'repetition_intensity' => 0.5,
            'liveliness_intensity' => 0.0,
            'target_sentence_len' => [12, 28],
        ],
        'formal' => [
            'description' => 'Formal style',
            'typography' => ['dash' => '—', 'quotes' => '«»', 'ellipsis' => '…'],
            'decancel_intensity' => 0.2,
            'structure_intensity' => 0.3,
            'repetition_intensity' => 0.4,
            'liveliness_intensity' => 0.0,
            'target_sentence_len' => [15, 30],
        ],
    ];

    /**
     * Get profile configuration.
     */
    public static function get(string $name): array
    {
        return self::PROFILES[$name] ?? self::PROFILES['web'];
    }

    /**
     * Mapping from stage names to profile intensity keys.
     */
    private const STAGE_MAP = [
        'debureaucratize' => 'decancel_intensity',
        'diversify_structure' => 'structure_intensity',
        'reduce_repetitions' => 'repetition_intensity',
        'inject_liveliness' => 'liveliness_intensity',
    ];

    /**
     * Whether a transformation should be applied given stage name, profile, and intensity.
     */
    public static function shouldApply(string $stage, array $profile, int $intensity, float $threshold = 0.3): bool
    {
        $key = self::STAGE_MAP[$stage] ?? null;
        if ($key === null) {
            return true;
        }
        $profileFactor = $profile[$key] ?? 0.0;
        if ($profileFactor <= 0.0) {
            return false;
        }
        return ($intensity / 100.0) * $profileFactor >= $threshold;
    }

    /**
     * Calculate probability of application.
     */
    public static function intensityProbability(int $intensity, float $profileFactor): float
    {
        return min(($intensity / 100.0) * $profileFactor, 1.0);
    }

    /**
     * Coin flip with given probability using a seeded RNG.
     */
    public static function coinFlip(float $probability, ?RandomHelper $rng = null): bool
    {
        if ($rng !== null) {
            return $rng->random() < $probability;
        }
        return mt_rand() / mt_getrandmax() < $probability;
    }
}
