<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * HumanizeResult — result of text humanization.
 */
class HumanizeResult
{
    public readonly string $original;
    public readonly string $processed;
    public readonly string $lang;
    public readonly string $profile;
    public readonly array $changes;

    public function __construct(
        string $original,
        string $processed,
        string $lang,
        string $profile,
        array $changes = [],
    ) {
        $this->original = $original;
        $this->processed = $processed;
        $this->lang = $lang;
        $this->profile = $profile;
        $this->changes = $changes;
    }

    /**
     * Calculate word-level change ratio (0..1).
     */
    public function getChangeRatio(): float
    {
        $origWords = preg_split('/\s+/', trim($this->original));
        $newWords = preg_split('/\s+/', trim($this->processed));

        if (empty($origWords) || $origWords === ['']) {
            return 0.0;
        }

        $total = max(count($origWords), count($newWords));
        $diffs = 0;

        for ($i = 0; $i < $total; $i++) {
            $a = $origWords[$i] ?? '';
            $b = $newWords[$i] ?? '';
            if ($a !== $b) {
                $diffs++;
            }
        }

        return $diffs / $total;
    }
}
