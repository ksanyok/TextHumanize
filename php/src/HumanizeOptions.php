<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * HumanizeOptions — configuration for text humanization.
 */
class HumanizeOptions
{
    public ?string $lang;
    public string $profile;
    public int $intensity;
    public array $preserve;
    public array $constraints;
    public ?int $seed;

    private const VALID_PROFILES = ['chat', 'web', 'seo', 'docs', 'formal'];

    public function __construct(
        ?string $lang = null,
        string $profile = 'web',
        int $intensity = 60,
        array $preserve = [],
        array $constraints = [],
        ?int $seed = null,
    ) {
        $this->lang = $lang;

        if (!in_array($profile, self::VALID_PROFILES, true)) {
            throw new \InvalidArgumentException(
                "Invalid profile '$profile'. Must be one of: " . implode(', ', self::VALID_PROFILES)
            );
        }
        $this->profile = $profile;
        $this->intensity = max(0, min(100, $intensity));

        $this->preserve = array_merge([
            'code_blocks' => true,
            'urls' => true,
            'emails' => true,
            'hashtags' => true,
            'mentions' => true,
            'markdown' => true,
            'html' => true,
            'numbers' => false,
            'brand_terms' => [],
        ], $preserve);

        $this->constraints = array_merge([
            'max_change_ratio' => 0.4,
            'min_sentence_length' => 3,
            'keep_keywords' => [],
        ], $constraints);

        $this->seed = $seed;
    }
}
