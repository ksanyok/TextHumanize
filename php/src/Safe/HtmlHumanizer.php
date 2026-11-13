<?php

declare(strict_types=1);

namespace TextHumanize\Safe;

use TextHumanize\LangDetector;

/**
 * HTML-aware humanization (PHP port of js/src/html.ts).
 *
 * Inline tags, entities and protected elements (<a>…</a>, <code>, <pre>,
 * <script>, data-humanize="off", translate="no") become private-use
 * placeholders, so links, anchors and attributes stay byte-identical. A block
 * whose placeholders do not come back in order is left untouched.
 */
final class HtmlHumanizer
{
    private const BLOCK = ['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'blockquote', 'div', 'section',
        'article', 'header', 'footer', 'main', 'aside', 'nav', 'dd', 'dt', 'dl', 'figcaption', 'caption', 'summary',
        'details', 'ul', 'ol', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'figure', 'form', 'fieldset', 'address',
        'body', 'html', 'hr'];
    private const PROTECTED = ['a', 'code', 'pre', 'script', 'style', 'kbd', 'samp', 'var', 'textarea', 'svg', 'math',
        'button', 'select', 'option', 'noscript', 'template', 'iframe', 'object', 'title', 'head', 'tt'];
    private const VOID = ['br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'col', 'embed', 'param', 'track'];
    private const HEADINGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
    private const LISTISH = ['li', 'td', 'th', 'dt', 'dd', 'caption', 'figcaption', 'summary'];
    private const SPLITTABLE = ['p', 'div', 'blockquote', 'section', 'article', 'main', 'body', ''];
    private const ENTITY_RE = '/&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#\d{1,7}|#[xX][0-9a-fA-F]{1,6});/';
    private const PROTECT_RE = '/\b(?:https?:\/\/|www\.)[^\s<>"\']+|(?<![\w.+-])[\w.+-]+@[\w-]+\.[\w.-]+|(?<![\p{L}\p{N}])[@#][\p{L}\p{N}_]+/u';
    private const PH_BASE = 0xE000;
    private const PH_MAX = 0xF8FF - 0xE000;

    /**
     * @param array{lang?:string, profile?:string, intensity?:int, seed?:int, keep_keywords?:string[],
     *              brand_terms?:string[], heading_factor?:float, list_factor?:float, max_link_share?:float,
     *              score?:bool} $o
     * @return array{html:string, lang:string, changes:array, stats:array, ai_score_before:int, ai_score_after:int,
     *               warnings:array}
     */
    public static function humanize(string $html, array $o = []): array
    {
        $lang = LangData::normalize(!empty($o['lang']) && $o['lang'] !== 'auto'
            ? $o['lang'] : LangDetector::detect(self::stripTags($html)));
        $pack = LangData::get($lang);
        $stats = ['blocks' => 0, 'changed' => 0, 'reverted' => 0, 'skipped' => 0];
        $changes = [];
        $wantScore = ($o['score'] ?? true) !== false;

        // ---- group segments into blocks ----
        $segments = self::tokenize($html);
        $units = [];
        $stack = [];
        $cur = ['tag' => '', 'parts' => []];
        $flush = static function () use (&$cur, &$units, &$stack): void {
            if ($cur['parts']) {
                $units[] = $cur;
            }
            $cur = ['tag' => $stack ? end($stack) : '', 'parts' => []];
        };
        $n = count($segments);
        for ($i = 0; $i < $n; $i++) {
            $seg = $segments[$i];
            if (isset($seg['text'])) {
                self::pushText($cur['parts'], $seg['text']);
                continue;
            }
            $tag = $seg['tag'];
            $name = self::tagName($tag);
            if ($name === '') {
                $cur['parts'][] = ['atom', $tag, ''];
                continue;
            }
            $closing = str_starts_with($tag, '</');
            $self = str_ends_with($tag, '/>');
            if (!$closing && !$self && !in_array($name, self::VOID, true)
                && (in_array($name, self::PROTECTED, true) || self::optedOut($tag))) {
                $depth = 1;
                $raw = $tag;
                for ($j = $i + 1; $j < $n && $depth > 0; $j++) {
                    $s = $segments[$j];
                    if (isset($s['tag'])) {
                        if (self::tagName($s['tag']) === $name && !str_ends_with($s['tag'], '/>')) {
                            $depth += str_starts_with($s['tag'], '</') ? -1 : 1;
                        }
                        $raw .= $s['tag'];
                    } else {
                        $raw .= $s['text'];
                    }
                }
                $i = $j - 1;
                if (in_array($name, self::BLOCK, true)) {
                    $flush();
                    $units[] = $raw;
                } else {
                    $cur['parts'][] = ['atom', $raw, self::stripTags($raw)];
                }
                continue;
            }
            if (in_array($name, self::BLOCK, true)) {
                $flush();
                $units[] = $tag;
                if (!in_array($name, self::VOID, true) && !$self) {
                    if ($closing) {
                        $at = array_search($name, array_reverse($stack, true), true);
                        if ($at !== false) {
                            $stack = array_slice($stack, 0, $at);
                        }
                    } else {
                        $stack[] = $name;
                    }
                }
                $cur['tag'] = $stack ? end($stack) : '';
                continue;
            }
            $cur['parts'][] = ['atom', $tag, $name === 'br' ? ' ' : ''];
        }
        $flush();

        // ---- score & intensity ----
        $visibleOf = static fn (array $b) => implode('', array_map(static fn ($p) => $p[2], $b['parts']));
        $blocks = array_values(array_filter($units, 'is_array'));
        $base = (int) ($o['intensity'] ?? 60);
        $scoreBefore = $wantScore || !isset($o['intensity'])
            ? Detector::score(implode("\n", array_map($visibleOf, $blocks)), $lang) : -1;
        $effective = $scoreBefore >= 0 ? Detector::adapt($base, $scoreBefore) : $base;
        if ($effective !== $base) {
            $changes[] = ['type' => 'adaptive_intensity', 'description' => "Adapted intensity: AI={$scoreBefore}%, {$base}→{$effective}"];
        }
        $rng = new Rng((int) ($o['seed'] ?? crc32($html)));
        $keepBase = array_merge($o['brand_terms'] ?? [], $o['keep_keywords'] ?? []);
        $hf = (float) ($o['heading_factor'] ?? 0);
        $lf = (float) ($o['list_factor'] ?? 0.75);
        $maxLink = (float) ($o['max_link_share'] ?? 0.6);
        $noSplit = in_array($o['profile'] ?? 'web', ['formal', 'academic', 'docs'], true);

        // ---- rewrite block by block ----
        $out = '';
        $after = [];
        foreach ($units as $u) {
            if (is_string($u)) {
                $out .= $u;
                continue;
            }
            $original = implode('', array_map(static fn ($p) => $p[1], $u['parts']));
            $visible = $visibleOf($u);
            $words = preg_match_all('/[\p{L}\p{N}]+/u', $visible);
            if ($words === 0) {
                $out .= $original;
                $after[] = $visible;
                continue;
            }
            $stats['blocks']++;
            $atoms = array_values(array_filter($u['parts'], static fn ($p) => $p[0] === 'atom'));
            $linkChars = 0;
            foreach ($atoms as $p) {
                if (preg_match('/^<a\b/i', $p[1])) {
                    $linkChars += mb_strlen(trim($p[2]));
                }
            }
            $factor = in_array($u['tag'], self::HEADINGS, true) ? $hf : (in_array($u['tag'], self::LISTISH, true) ? $lf : 1.0);
            $visChars = max(1, mb_strlen(trim($visible)));
            if (!$pack || $effective === 0 || $factor <= 0 || $words < 4 || $linkChars / $visChars > $maxLink
                || count($atoms) > self::PH_MAX) {
                $stats['skipped']++;
                $out .= $original;
                $after[] = $visible;
                continue;
            }

            $list = [];
            $encoded = '';
            foreach ($u['parts'] as $p) {
                if ($p[0] === 'text') {
                    $encoded .= $p[1];
                } else {
                    $encoded .= mb_chr(self::PH_BASE + count($list), 'UTF-8');
                    $list[] = $p;
                }
            }
            $keep = $keepBase;
            if (preg_match_all(self::PROTECT_RE, $encoded, $pm)) {
                array_push($keep, ...$pm[0]);
            }
            $text = self::typography($encoded, $lang);
            $r = Engine::rewrite($text, $pack, [
                'intensity' => (int) round($effective * $factor),
                'keep' => $keep,
                'lang' => $lang,
                'split' => !$noSplit && in_array($u['tag'], self::SPLITTABLE, true),
            ], $rng);
            $text = $r['text'];

            if (self::placeholders($encoded) !== self::placeholders($text) || trim($text) === '') {
                $stats['reverted']++;
                $out .= $original;
                $after[] = $visible;
                continue;
            }
            if ($text === $encoded) {
                $out .= $original;
                $after[] = $visible;
                continue;
            }
            $stats['changed']++;
            $out .= self::restore($text, $list, 1);
            $after[] = self::restore($text, $list, 2);
            foreach ($r['changes'] as $c) {
                $changes[] = $c + ['block' => $u['tag'] ?: 'text'];
            }
        }

        $afterText = implode("\n", $after);
        return [
            'html' => $out,
            'lang' => $lang,
            'changes' => $changes,
            'stats' => $stats,
            'ai_score_before' => $wantScore ? $scoreBefore : -1,
            'ai_score_after' => $wantScore ? Detector::score($afterText, $lang) : -1,
            'warnings' => self::mixedScript($afterText),
        ];
    }

    /** Words mixing Cyrillic and Latin letters ("манning"): reported, never auto-fixed. */
    public static function mixedScript(string $text): array
    {
        $out = [];
        if (preg_match_all('/[\p{L}\p{M}]+/u', $text, $m)) {
            foreach (array_unique($m[0]) as $w) {
                if (preg_match('/\p{Cyrillic}/u', $w) && preg_match('/\p{Latin}/u', $w)) {
                    $out[] = ['type' => 'mixed_script', 'token' => $w];
                    if (count($out) >= 20) {
                        break;
                    }
                }
            }
        }
        return $out;
    }

    /** Linear single-pass tokenizer (no backtracking over the whole document). */
    private static function tokenize(string $html): array
    {
        $segs = [];
        $last = 0;
        $len = strlen($html);
        $i = strpos($html, '<');
        $commentsClosed = true;
        while ($i !== false && $i < $len) {
            $end = -1;
            if (substr_compare($html, '<!--', $i, 4) === 0) {
                $close = $commentsClosed ? strpos($html, '-->', $i + 4) : false;
                if ($close !== false) {
                    $end = $close + 3;
                } else {
                    $commentsClosed = false;
                }
            } else {
                $gt = strpos($html, '>', $i + 1);
                $lt = strpos($html, '<', $i + 1);
                if ($gt !== false && ($lt === false || $gt < $lt)
                    && preg_match('/^(?:<![^<>]*>|<\/?[a-zA-Z][^<>]*>)$/', substr($html, $i, $gt - $i + 1))) {
                    $end = $gt + 1;
                }
            }
            if ($end > 0) {
                if ($i > $last) {
                    $segs[] = ['text' => substr($html, $last, $i - $last)];
                }
                $segs[] = ['tag' => substr($html, $i, $end - $i)];
                $last = $end;
                $i = strpos($html, '<', $end);
            } else {
                $i = strpos($html, '<', $i + 1);
            }
        }
        if ($last < $len) {
            $segs[] = ['text' => substr($html, $last)];
        }
        return $segs;
    }

    private static function pushText(array &$parts, string $text): void
    {
        $last = 0;
        if (preg_match_all(self::ENTITY_RE, $text, $m, PREG_OFFSET_CAPTURE)) {
            foreach ($m[0] as [$ent, $off]) {
                if ($off > $last) {
                    $t = substr($text, $last, $off - $last);
                    $parts[] = ['text', $t, $t];
                }
                $vis = preg_match('/^(&nbsp;|&#160;|&#xa0;)$/i', $ent) ? ' ' : ($ent === '&amp;' ? '&' : '');
                $parts[] = ['atom', $ent, $vis];
                $last = $off + strlen($ent);
            }
        }
        if ($last < strlen($text)) {
            $t = substr($text, $last);
            $parts[] = ['text', $t, $t];
        }
    }

    /** Minimal typography (same rules as the JS normalizer). */
    private static function typography(string $t, string $lang): string
    {
        $t = (string) preg_replace('/ {2,}/u', ' ', $t);
        $t = (string) preg_replace($lang === 'fr' ? '/(?<! ) +(?=[.,])/u' : '/(?<! ) +(?=[.,;:!?])/u', '', $t);
        $t = (string) preg_replace('/(\p{Ll}{2})([.!?])(\p{Lu}\p{Ll})/u', '$1$2 $3', $t);
        $t = str_replace(' -- ', ' — ', $t);
        if ($lang === 'ru' || $lang === 'uk') {
            $t = str_replace(' - ', ' — ', $t);
            if (substr_count($t, '"') % 2 === 0 && str_contains($t, '"')) {
                $open = true;
                $t = (string) preg_replace_callback('/"/', static function () use (&$open) {
                    $q = $open ? '«' : '»';
                    $open = !$open;
                    return $q;
                }, $t);
            }
        } elseif ($lang === 'pl') {
            $t = str_replace(' - ', ' – ', $t);
        }
        return (string) preg_replace('/\.{3,}/u', '…', $t);
    }

    private static function placeholders(string $s): string
    {
        return preg_match_all('/[\x{E000}-\x{F8FF}]/u', $s, $m) ? implode('', $m[0]) : '';
    }

    private static function restore(string $text, array $list, int $field): string
    {
        return (string) preg_replace_callback(
            '/[\x{E000}-\x{F8FF}]/u',
            static fn ($m) => $list[mb_ord($m[0], 'UTF-8') - self::PH_BASE][$field] ?? '',
            $text,
        );
    }

    private static function tagName(string $tag): string
    {
        return preg_match('/^<\/?\s*([a-zA-Z][a-zA-Z0-9-]*)/', $tag, $m) ? strtolower($m[1]) : '';
    }

    private static function optedOut(string $tag): bool
    {
        return (bool) preg_match('/\sdata-humanize\s*=\s*["\']?(?:off|false|0)|\stranslate\s*=\s*["\']?no|\sclass\s*=\s*["\'][^"\']*\bnotranslate\b/i', $tag);
    }

    private static function stripTags(string $s): string
    {
        return (string) preg_replace(self::ENTITY_RE, ' ', (string) preg_replace('/<[^<>]*>/', ' ', $s));
    }
}
