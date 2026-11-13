<?php

declare(strict_types=1);

namespace TextHumanize\Safe;

/**
 * Lightweight AI-style score (PHP port of js/src/detector.ts): cliche and
 * officialese density, stock connector openings, sentence-length burstiness
 * and average sentence length. A heuristic, not a forensic detector.
 */
final class Detector
{
    /** @return array{words:int,sentences:int,avgSentenceLength:float,sentenceLengthCV:float,clichePer100:float,officialesePer100:float,connectorStartShare:float} */
    public static function features(string $text, string $lang): array
    {
        $words = preg_match_all('/[\p{L}\p{N}]+/u', $text);
        $sentences = array_values(array_filter(
            array_map('trim', preg_split('/(?<=[.!?…])\s+|\n+/u', $text) ?: []),
            static fn ($s) => preg_match_all('/[\p{L}\p{N}]+/u', $s) > 1,
        ));
        $lens = array_map(static fn ($s) => preg_match_all('/[\p{L}\p{N}]+/u', $s), $sentences);
        $n = count($lens);
        $avg = $n ? array_sum($lens) / $n : 0.0;
        $sd = $n ? sqrt(array_sum(array_map(static fn ($l) => ($l - $avg) ** 2, $lens)) / $n) : 0.0;
        $pack = LangData::get($lang);
        $cl = $of = $cs = 0;
        if ($pack) {
            $cl = $pack['re']['phrases'] ? preg_match_all($pack['re']['phrases'], $text) : 0;
            $of = $pack['re']['bureaucratic'] ? preg_match_all($pack['re']['bureaucratic'], $text) : 0;
            if ($pack['re']['connectors'] && preg_match_all($pack['re']['connectors'], $text, $m, PREG_OFFSET_CAPTURE)) {
                foreach ($m[0] as [, $off]) {
                    if (Engine::isSentenceStart($text, $off)) {
                        $cs++;
                    }
                }
            }
        }
        return [
            'words' => $words,
            'sentences' => $n,
            'avgSentenceLength' => $avg,
            'sentenceLengthCV' => $avg > 0 ? $sd / $avg : 0.0,
            'clichePer100' => $words ? $cl / $words * 100 : 0.0,
            'officialesePer100' => $words ? $of / $words * 100 : 0.0,
            'connectorStartShare' => $n ? $cs / $n : 0.0,
        ];
    }

    /** 0–100 AI-style score. */
    public static function score(string $text, string $lang): int
    {
        $f = self::features($text, $lang);
        if ($f['words'] < 8) {
            return 0;
        }
        $s = min(40, ($f['clichePer100'] + 0.5 * $f['officialesePer100']) * 9);
        $s += min(25, $f['connectorStartShare'] * 70);
        if ($f['sentences'] >= 3) {
            $cv = $f['sentenceLengthCV'];
            $s += $cv < 0.25 ? 20 : ($cv < 0.35 ? 14 : ($cv < 0.45 ? 7 : 0));
        }
        $s += $f['avgSentenceLength'] > 22 ? 15 : ($f['avgSentenceLength'] > 17 ? 8 : 0);
        $conf = min(1, $f['words'] / 40);
        return (int) max(0, min(100, round($s * $conf)));
    }

    /** Effective intensity for a text with the given score (same gate as the JS port). */
    public static function adapt(int $intensity, int $score): int
    {
        if ($score <= 5) {
            return 0;
        }
        if ($score <= 15) {
            return max(8, intdiv($intensity * 35, 100));
        }
        if ($score <= 25) {
            return max(10, intdiv($intensity, 2));
        }
        if ($score >= 70) {
            return min(100, intdiv($intensity * 12, 10));
        }
        return $intensity;
    }
}
