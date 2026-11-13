<?php

declare(strict_types=1);

namespace TextHumanize\Safe;

/**
 * Publication-safe edit engine (PHP port of js/src/engine.ts).
 *
 * Candidate edits (AI cliches, stock sentence-initial connectors, officialese)
 * are collected on the original text, de-overlapped, ranked and budgeted, then
 * applied in one right-to-left pass. Private-use characters (U+E000–U+F8FF)
 * are opaque boundaries so callers can embed placeholders for markup.
 * All offsets are byte offsets into UTF-8 strings.
 */
final class Engine
{
    /** Conjunctions/adverbs that take no comma when opening a sentence. */
    private const BARE = [
        'and', 'but', 'yet', 'и', 'но', 'а', 'да', 'і', 'але', 'та', 'ale', 'i', 'a', 'y', 'pero',
        'e', 'mas', 'und', 'aber', 'et', 'mais', 'ma', 'і ще', 'и ещё', 'and also',
        'также', 'ещё', 'еще', 'плюс', 'тоже', 'також', 'ще', 'теж', 'także', 'również', 'też',
        'también', 'também', 'auch', 'aussi', 'anche',
    ];

    /**
     * @param array{intensity:int|float, seed?:int, keep?:string[], connectors?:bool, words?:bool,
     *              phrases?:bool, split?:bool, lang?:string} $opts
     * @return array{text:string, changes:array<int, array<string, string>>}
     */
    public static function rewrite(string $text, array $pack, array $opts, ?Rng $rng = null): array
    {
        $changes = [];
        $intensity = max(0, min(100, (float) $opts['intensity']));
        if (trim($text) === '' || $intensity < 5) {
            return ['text' => $text, 'changes' => []];
        }
        $rng ??= new Rng($opts['seed'] ?? crc32($text));
        $p = $intensity / 100;

        $protected = self::findProtected($text, $opts['keep'] ?? []);
        $cands = [];
        if (($opts['phrases'] ?? true) !== false) {
            self::collect($text, $pack, 'phrases', 'phrase', 3, min(1.0, 0.35 + $p), $cands);
        }
        if (($opts['connectors'] ?? true) !== false && $pack['re']['connectors']) {
            preg_match_all($pack['re']['connectors'], $text, $m, PREG_OFFSET_CAPTURE);
            foreach ($m[0] as [$frag, $off]) {
                $alts = $pack['idx']['connectors'][LangData::key($frag)] ?? null;
                if ($alts && self::isSentenceStart($text, $off)) {
                    $cands[] = self::cand($off, $frag, $alts, 'connector', 2, min(1.0, 0.3 + $p));
                }
            }
        }
        if (($opts['words'] ?? true) !== false) {
            self::collect($text, $pack, 'bureaucratic', 'word', 1, $p * 0.9, $cands);
        }

        $words = preg_match_all('/[\p{L}\p{N}]+/u', $text);
        $budget = max(1, (int) round($words * (0.03 + $p * 0.15)));

        usort($cands, static fn ($a, $b) => [$b['priority'], $b['end'] - $b['start'], $a['start']]
            <=> [$a['priority'], $a['end'] - $a['start'], $b['start']]);
        $accepted = [];
        foreach ($cands as $c) {
            if (count($accepted) >= $budget) {
                break;
            }
            if (self::overlaps($c, $protected) || self::overlaps($c, $accepted)) {
                continue;
            }
            if ($rng->random() > $c['prob']) {
                continue;
            }
            $accepted[] = $c;
        }
        if (!$accepted && empty($opts['split'])) {
            return ['text' => $text, 'changes' => []];
        }

        // "Moreover, it is worth noting that X": drop the connector instead of rewriting both.
        $forceDrop = [];
        foreach ($accepted as $i => $c) {
            if ($c['type'] !== 'connector') {
                continue;
            }
            foreach ($accepted as $j => $o) {
                if ($i !== $j && $o['start'] >= $c['end']
                    && preg_match('/^[\s,:]*$/u', substr($text, $c['end'], $o['start'] - $c['end']))) {
                    $forceDrop[$i] = true;
                }
            }
        }

        uasort($accepted, static fn ($a, $b) => $b['start'] <=> $a['start']);
        $used = [];
        $out = $text;
        foreach ($accepted as $i => $c) {
            $start = $c['start'];
            $end = $c['end'];
            $atStart = self::isSentenceStart($out, $start);
            $before = $start > 0 ? self::lastChar(substr($out, 0, $start)) : '';
            $afterTrim = ltrim(substr($out, $end), " \t\n,:");
            $nextToTag = self::isPlaceholder($before) || self::isPlaceholder(mb_substr($afterTrim, 0, 1));
            $noDrop = $nextToTag || isset($pack['contrast'][mb_strtolower($c['original'])]);
            $repl = isset($forceDrop[$i]) && !$noDrop ? '' : self::pick($c, $atStart, $used, $rng, $noDrop);
            if ($repl === null) {
                continue;
            }
            if ($repl === '') {
                preg_match('/^\s*[,:]?\s*/u', substr($out, $end), $tail);
                $end += strlen($tail[0]);
                if (!$atStart && !preg_match('/\s$/u', substr($out, 0, $start))) {
                    $repl = ' ';
                }
                $after = substr($out, $end);
                if ($atStart && preg_match('/^\p{L}/u', $after)) {
                    $after = self::ucfirst($after);
                }
                $out = substr($out, 0, $start) . $repl . $after;
            } else {
                if (self::isAllCaps($c['original'])) {
                    $repl = mb_strtoupper($repl);
                } elseif ($atStart || self::isUpperInitial($c['original'])) {
                    $repl = self::ucfirst($repl);
                }
                $rest = substr($out, $end);
                if (preg_match('/[,:]$/u', $repl) && preg_match('/^\s*[,:]/u', $rest, $mm)) {
                    $end += strlen($mm[0]);
                } elseif ($atStart && in_array(LangData::key($repl), self::BARE, true) && str_starts_with($rest, ',')) {
                    $end += 1;
                }
                $out = substr($out, 0, $start) . $repl . substr($out, $end);
            }
            $k = LangData::key($repl);
            $used[$k] = ($used[$k] ?? 0) + 1;
            $r = trim($repl);
            $changes[] = [
                'type' => $c['type'] === 'word' ? 'decancel_word' : $c['type'],
                'description' => $r !== '' ? "{$c['original']} → {$r}" : "Dropped \"{$c['original']}\"",
                'original' => $c['original'],
                'replacement' => $r,
            ];
        }
        $changes = array_reverse($changes);

        if (!empty($opts['split']) && $rng->random() < $p * 0.6) {
            $split = self::splitLongSentence($out, $pack);
            if ($split) {
                $out = $split[0];
                $changes[] = ['type' => 'split', 'description' => $split[1]];
            }
        }
        return ['text' => self::tidy($out, $opts['lang'] ?? $pack['code']), 'changes' => $changes];
    }

    public static function isSentenceStart(string $text, int $offset): bool
    {
        if ($offset <= 0) {
            return true;
        }
        $from = max(0, $offset - 240);
        $window = mb_strcut($text, $from, $offset - $from, 'UTF-8');
        $anchor = $from === 0 ? '(?:^|[.!?…]|\n)' : '(?:[.!?…]|\n)';
        return (bool) preg_match('/' . $anchor . '[\s\x{E000}-\x{F8FF}"\'«“„‘(\[¿¡]*$/u', $window);
    }

    /** Repair spacing/punctuation artefacts. Linear patterns only (see CodeQL js/polynomial-redos). */
    public static function tidy(string $text, string $lang): string
    {
        $t = (string) preg_replace('/[ \t]{2,}/u', ' ', $text);
        $t = (string) preg_replace($lang === 'fr' ? '/(?<! ) +(?=[,.…])/u' : '/(?<! ) +(?=[,.;:!?…])/u', '', $t);
        $t = (string) preg_replace('/,\s*([,.;:!?])/u', '$1', $t);
        return (string) preg_replace('/([.!?])\s+,/u', '$1', $t);
    }

    private static function collect(string $text, array $pack, string $dict, string $type, int $prio, float $prob, array &$out): void
    {
        $re = $pack['re'][$dict] ?? null;
        if (!$re) {
            return;
        }
        preg_match_all($re, $text, $m, PREG_OFFSET_CAPTURE);
        foreach ($m[0] as [$frag, $off]) {
            $alts = $pack['idx'][$dict][LangData::key($frag)] ?? null;
            if ($alts) {
                $out[] = self::cand($off, $frag, $alts, $type, $prio, $prob);
            }
        }
    }

    private static function cand(int $off, string $frag, array $alts, string $type, int $prio, float $prob): array
    {
        return ['start' => $off, 'end' => $off + strlen($frag), 'original' => $frag, 'options' => $alts,
            'type' => $type, 'priority' => $prio, 'prob' => $prob];
    }

    private static function findProtected(string $text, array $keep): array
    {
        $ranges = [];
        foreach ($keep as $term) {
            $term = trim((string) $term);
            if ($term === '') {
                continue;
            }
            preg_match_all('/' . preg_quote($term, '/') . '/iu', $text, $m, PREG_OFFSET_CAPTURE);
            foreach ($m[0] as [$frag, $off]) {
                $ranges[] = ['start' => $off, 'end' => $off + strlen($frag)];
            }
        }
        return $ranges;
    }

    private static function overlaps(array $c, array $list): bool
    {
        foreach ($list as $r) {
            if ($c['start'] < $r['end'] && $r['start'] < $c['end']) {
                return true;
            }
        }
        return false;
    }

    private static function pick(array $c, bool $atStart, array $used, Rng $rng, bool $noDrop): ?string
    {
        $opts = array_values(array_map('strval', $c['options']));
        if ($noDrop) {
            $opts = array_values(array_filter($opts, static fn ($o) => $o !== ''));
        }
        if ($atStart) {
            $opts = array_values(array_filter($opts, static fn ($o) => $o === ''
                || preg_match('/^[' . LangData::WORD . ']/u', $o)));
        }
        if ($c['type'] === 'connector' && !$noDrop && $rng->random() < 0.33) {
            return '';
        }
        if (!$opts) {
            return null;
        }
        if (!$atStart) {
            $dashed = array_values(array_filter($opts, static fn ($o) => (bool) preg_match('/^[—–]\s/u', $o)));
            if ($dashed) {
                foreach ($opts as $o) {
                    if (in_array('— ' . $o, $dashed, true) || in_array('– ' . $o, $dashed, true)) {
                        $opts = $dashed;
                        break;
                    }
                }
            }
        }
        $fresh = array_values(array_filter($opts, static fn ($o) => !isset($used[LangData::key($o)])));
        return $rng->choice($fresh ?: $opts);
    }

    /** "X, and Y" → "X. And Y" for the longest sentence of 28+ words; both halves keep 8+ words. */
    private static function splitLongSentence(string $text, array $pack): ?array
    {
        if (!preg_match_all('/(?:^|(?<=[.!?…]))[^.!?…]+[.!?…]+/u', $text, $m, PREG_OFFSET_CAPTURE)) {
            return null;
        }
        $best = null;
        foreach ($m[0] as [$s, $off]) {
            $w = preg_match_all('/[\p{L}\p{N}]+/u', $s);
            if ($w >= 28 && (!$best || $w > $best[2])) {
                $best = [$off, $s, $w];
            }
        }
        if (!$best) {
            return null;
        }
        [$off, $sentence] = $best;
        $mid = strlen($sentence) / 2;
        $pick = null;
        foreach ($pack['splitJoints'] as $joint) {
            $from = 0;
            while (($at = strpos($sentence, $joint, $from)) !== false) {
                $from = $at + 1;
                $left = preg_match_all('/[\p{L}\p{N}]+/u', substr($sentence, 0, $at));
                $right = preg_match_all('/[\p{L}\p{N}]+/u', substr($sentence, $at + strlen($joint)));
                if ($left < 8 || $right < 8) {
                    continue;
                }
                if (!$pick || abs($at - $mid) < abs($pick[0] - $mid)) {
                    $pick = [$at, $joint];
                }
            }
        }
        if (!$pick) {
            return null;
        }
        [$at, $joint] = $pick;
        $conj = trim((string) preg_replace('/^[,;]\s*/u', '', $joint));
        $rest = substr($sentence, $at + strlen($joint));
        $glued = $conj !== '' ? self::ucfirst($conj) . ' ' . $rest : self::ucfirst($rest);
        $new = rtrim(substr($sentence, 0, $at)) . '. ' . $glued;
        return [substr($text, 0, $off) . $new . substr($text, $off + strlen($sentence)), 'Split long sentence at "' . trim($joint) . '"'];
    }

    public static function ucfirst(string $s): string
    {
        if (!preg_match('/\p{L}/u', $s, $m, PREG_OFFSET_CAPTURE)) {
            return $s;
        }
        [$ch, $off] = $m[0];
        return substr($s, 0, $off) . mb_strtoupper($ch) . substr($s, $off + strlen($ch));
    }

    private static function isUpperInitial(string $s): bool
    {
        return preg_match('/\p{L}/u', $s, $m) === 1 && $m[0] !== mb_strtolower($m[0]);
    }

    private static function isAllCaps(string $s): bool
    {
        $l = (string) preg_replace('/[^\p{L}]/u', '', $s);
        return mb_strlen($l) > 1 && $l === mb_strtoupper($l) && $l !== mb_strtolower($l);
    }

    private static function lastChar(string $s): string
    {
        return $s === '' ? '' : mb_substr($s, -1);
    }

    private static function isPlaceholder(string $ch): bool
    {
        return $ch !== '' && preg_match('/^[\x{E000}-\x{F8FF}]$/u', $ch) === 1;
    }
}
