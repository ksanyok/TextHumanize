<?php

declare(strict_types=1);

namespace TextHumanize\Safe;

/**
 * Publication-safe dictionaries (officialese, AI cliches, stock connectors),
 * generated from the Python packs by scripts/export_js_langs.py — the same
 * data the JS port uses.
 */
final class LangData
{
    /** Word characters for boundary checks; hyphen/apostrophe are word-internal. */
    public const WORD = "\\p{L}\\p{N}\\p{M}_'’\\-";

    private const ALIASES = ['ua' => 'uk', 'br' => 'pt', 'pt-br' => 'pt', 'pt-pt' => 'pt'];

    /** Coordinating joints where a long sentence may be split in two. */
    private const SPLIT_JOINTS = [
        'en' => ['; ', ', but '],
        'ru' => ['; ', ', но ', ', а ', ', и '],
        'uk' => ['; ', ', але ', ', а ', ', і '],
        'de' => ['; ', ', aber '],
        'fr' => ['; ', ', mais '],
        'es' => ['; ', ', pero '],
        'pl' => ['; ', ', ale ', ', a '],
        'pt' => ['; ', ', mas '],
        'it' => ['; ', ', ma '],
    ];

    /** @var array<string, array|null> */
    private static array $cache = [];

    public static function normalize(?string $code): string
    {
        $c = strtolower(trim((string) $code));
        return self::ALIASES[$c] ?? explode('-', str_replace('_', '-', $c))[0];
    }

    public static function has(?string $code): bool
    {
        return self::get($code) !== null;
    }

    /** @return string[] */
    public static function languages(): array
    {
        return array_map(
            static fn (string $f) => basename($f, '.json'),
            glob(__DIR__ . '/data/*.json') ?: [],
        );
    }

    /**
     * @return array{code:string,bureaucratic:array,phrases:array,connectors:array,contrast:array,splitJoints:string[],
     *               idx:array<string,array>,re:array<string,?string>}|null
     */
    public static function get(?string $code): ?array
    {
        $code = self::normalize($code);
        if (array_key_exists($code, self::$cache)) {
            return self::$cache[$code];
        }
        $file = __DIR__ . '/data/' . basename($code) . '.json';
        if ($code === '' || !is_file($file)) {
            return self::$cache[$code] = null;
        }
        $data = json_decode((string) file_get_contents($file), true);
        if (!is_array($data)) {
            return self::$cache[$code] = null;
        }
        $pack = [
            'code' => $code,
            'bureaucratic' => $data['bureaucratic'] ?? [],
            'phrases' => $data['phrases'] ?? [],
            'connectors' => $data['connectors'] ?? [],
            'contrast' => array_fill_keys(array_map(static fn ($k) => mb_strtolower($k), $data['contrast'] ?? []), true),
            'splitJoints' => self::SPLIT_JOINTS[$code] ?? ['; '],
            'idx' => [],
            're' => [],
        ];
        foreach (['bureaucratic', 'phrases', 'connectors'] as $dict) {
            $idx = [];
            foreach ($pack[$dict] as $k => $v) {
                $idx[self::key((string) $k)] = $v;
            }
            $pack['idx'][$dict] = $idx;
            $pack['re'][$dict] = self::matcher(array_keys($pack[$dict]));
        }
        return self::$cache[$code] = $pack;
    }

    public static function key(string $s): string
    {
        return trim((string) preg_replace('/\s+/u', ' ', mb_strtolower($s)));
    }

    /** One alternation regex per dictionary, longest key first. */
    private static function matcher(array $keys): ?string
    {
        $keys = array_values(array_filter(array_map('strval', $keys), static fn ($k) => trim($k) !== ''));
        if (!$keys) {
            return null;
        }
        usort($keys, static fn ($a, $b) => mb_strlen($b) <=> mb_strlen($a));
        $parts = array_map(
            static fn ($k) => preg_replace('/\\\\?\s+/u', '\\s+', preg_quote(trim($k), '/')),
            $keys,
        );
        return '/(?<![' . self::WORD . '])(?:' . implode('|', $parts) . ')(?![' . self::WORD . '])/iu';
    }
}
