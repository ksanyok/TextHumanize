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

    /**
     * Jaccard similarity between original and processed text (0..1).
     *
     * 1.0 = identical, 0.0 = completely different.
     */
    public function getSimilarity(): float
    {
        if ($this->original === '' && $this->processed === '') {
            return 1.0;
        }
        if ($this->original === '' || $this->processed === '') {
            return 0.0;
        }

        $origWords = array_unique(preg_split('/\s+/', mb_strtolower(trim($this->original))));
        $newWords = array_unique(preg_split('/\s+/', mb_strtolower(trim($this->processed))));

        $origSet = array_flip($origWords);
        $newSet = array_flip($newWords);

        $intersection = count(array_intersect_key($origSet, $newSet));
        $union = count($origSet) + count($newSet) - $intersection;

        return $union > 0 ? $intersection / $union : 1.0;
    }

    /**
     * Overall quality score (0..1).
     *
     * Balances sufficient change with preservation of meaning.
     * Ideal range: ~0.75-0.90.
     */
    public function getQualityScore(): float
    {
        $sim = $this->getSimilarity();
        $change = $this->getChangeRatio();

        if ($change < 0.01) {
            return 0.3;
        }
        if ($sim < 0.3) {
            return 0.2;
        }

        $changeScore = 1.0 - abs($change - 0.2) / 0.4;
        $changeScore = max(0.0, min(1.0, $changeScore));

        return $sim * 0.6 + $changeScore * 0.4;
    }
}
