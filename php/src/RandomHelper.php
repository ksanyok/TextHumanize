<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Seeded random number generator for reproducibility.
 */
class RandomHelper
{
    private int $state;

    public function __construct(?int $seed = null)
    {
        $this->state = $seed ?? random_int(0, PHP_INT_MAX);
    }

    /**
     * Generate a random float between 0 and 1.
     */
    public function random(): float
    {
        // Linear congruential generator
        // Use fmod to avoid float-to-int precision loss on 64-bit PHP
        $next = fmod($this->state * 1103515245.0 + 12345.0, 2147483648.0);
        $this->state = (int) $next;
        return abs($this->state) / 2147483647.0;
    }

    /**
     * Generate a random integer between min and max (inclusive).
     */
    public function randInt(int $min, int $max): int
    {
        return $min + (int) floor($this->random() * ($max - $min + 1));
    }

    /**
     * Choose a random element from an array.
     */
    public function choice(array $items): mixed
    {
        if (empty($items)) {
            return null;
        }
        $items = array_values($items);
        return $items[$this->randInt(0, count($items) - 1)];
    }

    /**
     * Shuffle array in place (Fisher-Yates).
     */
    public function shuffle(array &$items): void
    {
        $n = count($items);
        for ($i = $n - 1; $i > 0; $i--) {
            $j = $this->randInt(0, $i);
            [$items[$i], $items[$j]] = [$items[$j], $items[$i]];
        }
    }
}
