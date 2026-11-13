<?php

declare(strict_types=1);

namespace TextHumanize\Safe;

/** Small seeded PRNG (xorshift32) — deterministic, no global state. */
final class Rng
{
    private int $s;

    public function __construct(int $seed = 0)
    {
        $s = ($seed ^ 0x9E3779B9) & 0xFFFFFFFF;
        $this->s = $s === 0 ? 0x6D2B79F5 : $s;
    }

    /** @return float in [0, 1) */
    public function random(): float
    {
        $x = $this->s;
        $x ^= ($x << 13) & 0xFFFFFFFF;
        $x ^= $x >> 17;
        $x ^= ($x << 5) & 0xFFFFFFFF;
        $this->s = $x & 0xFFFFFFFF;
        return $this->s / 4294967296.0;
    }

    public function choice(array $items): mixed
    {
        $items = array_values($items);
        return $items[(int) floor($this->random() * count($items))];
    }
}
