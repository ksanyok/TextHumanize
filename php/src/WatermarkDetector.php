<?php

declare(strict_types=1);

namespace TextHumanize;

/**
 * Detection and removal of text watermarks.
 *
 * Detects hidden markers:
 * - Unicode steganography (zero-width characters, homoglyphs)
 * - AI watermarks (statistical patterns)
 * - Hidden metadata (invisible characters)
 */

// ═══════════════════════════════════════════════════════════════
//  WATERMARK REPORT
// ═══════════════════════════════════════════════════════════════

/**
 * WatermarkReport — result of watermark detection.
 */
class WatermarkReport
{
    public bool $hasWatermarks = false;

    /** @var list<string> */
    public array $watermarkTypes = [];

    /** @var list<string> */
    public array $details = [];

    public string $cleanedText = '';

    public int $charactersRemoved = 0;

    /**
     * List of homoglyph substitutions found.
     * Each entry: [originalChar, expectedChar, position].
     *
     * @var list<array{string, string, int}>
     */
    public array $homoglyphsFound = [];

    public int $zeroWidthCount = 0;

    public float $confidence = 0.0;
}

// ═══════════════════════════════════════════════════════════════
//  WATERMARK DETECTOR
// ═══════════════════════════════════════════════════════════════

/**
 * WatermarkDetector — detection and removal of text watermarks.
 */
class WatermarkDetector
{
    // ═══════════════════════════════════════════════════════════
    //  ZERO-WIDTH CHARACTERS
    // ═══════════════════════════════════════════════════════════

    /** All zero-width and invisible Unicode characters */
    private const ZERO_WIDTH_CHARS = [
        "\u{200b}" => true, // Zero Width Space
        "\u{200c}" => true, // Zero Width Non-Joiner
        "\u{200d}" => true, // Zero Width Joiner
        "\u{200e}" => true, // Left-to-Right Mark
        "\u{200f}" => true, // Right-to-Left Mark
        "\u{2060}" => true, // Word Joiner
        "\u{2061}" => true, // Function Application
        "\u{2062}" => true, // Invisible Times
        "\u{2063}" => true, // Invisible Separator
        "\u{2064}" => true, // Invisible Plus
        "\u{feff}" => true, // Zero Width No-Break Space (BOM)
        "\u{00ad}" => true, // Soft Hyphen
        "\u{034f}" => true, // Combining Grapheme Joiner
        "\u{061c}" => true, // Arabic Letter Mark
        "\u{180e}" => true, // Mongolian Vowel Separator
    ];

    // ═══════════════════════════════════════════════════════════
    //  HOMOGLYPH DETECTION
    // ═══════════════════════════════════════════════════════════

    /** Cyrillic → Latin (visually identical) */
    private const CYRILLIC_TO_LATIN = [
        'а' => 'a', 'с' => 'c', 'е' => 'e', 'о' => 'o', 'р' => 'p',
        'х' => 'x', 'у' => 'y', 'А' => 'A', 'В' => 'B', 'С' => 'C',
        'Е' => 'E', 'Н' => 'H', 'К' => 'K', 'М' => 'M', 'О' => 'O',
        'Р' => 'P', 'Т' => 'T', 'Х' => 'X',
    ];

    /** Latin → Cyrillic (reverse mapping) */
    private const LATIN_TO_CYRILLIC = [
        'a' => 'а', 'c' => 'с', 'e' => 'е', 'o' => 'о', 'p' => 'р',
        'x' => 'х', 'y' => 'у', 'A' => 'А', 'B' => 'В', 'C' => 'С',
        'E' => 'Е', 'H' => 'Н', 'K' => 'К', 'M' => 'М', 'O' => 'О',
        'P' => 'Р', 'T' => 'Т', 'X' => 'Х',
    ];

    /** Special homoglyphs (look like normal chars but from other code blocks) */
    private const SPECIAL_HOMOGLYPHS = [
        // Fullwidth Latin
        "\u{ff41}" => 'a', "\u{ff42}" => 'b', "\u{ff43}" => 'c', "\u{ff44}" => 'd',
        "\u{ff45}" => 'e', "\u{ff46}" => 'f', "\u{ff47}" => 'g',
        // Mathematical / confusable letters
        "\u{2202}" => 'd', // Partial Differential → d
        "\u{0435}" => 'e', // Cyrillic е → Latin e
        "\u{03b1}" => 'a', // Greek alpha → a
        "\u{03bf}" => 'o', // Greek omicron → o
        "\u{0456}" => 'i', // Ukrainian і → Latin i
        "\u{0430}" => 'a', // Cyrillic а → Latin a
        // Subscript / superscript numbers
        "\u{00b2}" => '2', "\u{00b3}" => '3', "\u{00b9}" => '1',
        "\u{2070}" => '0', "\u{2071}" => 'i',
        // Confusable punctuation
        "\u{2018}" => "'", "\u{2019}" => "'", "\u{201c}" => '"', "\u{201d}" => '"',
        "\u{2012}" => '-', "\u{2013}" => '-', "\u{2014}" => '-',
        "\u{2212}" => '-', // minus sign vs hyphen
        "\u{00a0}" => ' ', // Non-breaking space
        "\u{2003}" => ' ', // Em space
        "\u{2002}" => ' ', // En space
        "\u{2009}" => ' ', // Thin space
        "\u{200a}" => ' ', // Hair space
        "\u{205f}" => ' ', // Medium Mathematical Space
        "\u{3000}" => ' ', // Ideographic Space
    ];

    /** Allowed endings that are not considered suspicious */
    private const ALLOWED_ENDINGS = [
        'ed', 'ly', 'ng', 'er', 'on', 'al', 'le', 'es', 'ts',
        'ть', 'ий', 'ый', 'ет', 'на',
    ];

    private string $lang;

    public function __construct(string $lang = 'en')
    {
        $this->lang = $lang;
    }

    // ─── Convenience static methods ─────────────────────────

    /**
     * Detect watermarks in text (convenience static method).
     */
    public static function detectWatermarks(string $text, string $lang = 'en'): WatermarkReport
    {
        return (new self($lang))->detect($text);
    }

    /**
     * Clean text from watermarks (convenience static method).
     */
    public static function cleanWatermarks(string $text, string $lang = 'en'): string
    {
        return (new self($lang))->clean($text);
    }

    // ─── Main detection ─────────────────────────────────────

    /**
     * Detect watermarks in text.
     */
    public function detect(string $text): WatermarkReport
    {
        $report = new WatermarkReport();
        $report->cleanedText = $text;

        // 1. Zero-width characters
        $this->detectZeroWidth($text, $report);

        // 2. Homoglyphs
        $this->detectHomoglyphs($text, $report);

        // 3. Invisible Unicode characters
        $this->detectInvisible($text, $report);

        // 4. Unusual spacing patterns
        $this->detectSpacingAnomalies($text, $report);

        // 5. Statistical watermark patterns
        $this->detectStatisticalWatermarks($text, $report);

        // 6. C2PA / IPTC metadata markers
        $this->detectMetadataMarkers($text, $report);

        // Determine overall result
        $report->hasWatermarks = count($report->watermarkTypes) > 0;
        if ($report->hasWatermarks) {
            $report->confidence = min(
                0.3
                + 0.15 * count($report->watermarkTypes)
                + 0.01 * $report->charactersRemoved
                + 0.05 * count($report->homoglyphsFound),
                1.0
            );
        }

        return $report;
    }

    /**
     * Remove all detected watermarks.
     */
    public function clean(string $text): string
    {
        $report = $this->detect($text);
        return $report->cleanedText;
    }

    // ───────────────────────────────────────────────────────────
    //  ZERO-WIDTH
    // ───────────────────────────────────────────────────────────

    private function detectZeroWidth(string $text, WatermarkReport $report): void
    {
        $count = 0;
        $cleaned = [];
        $length = mb_strlen($text, 'UTF-8');

        for ($i = 0; $i < $length; $i++) {
            $ch = mb_substr($text, $i, 1, 'UTF-8');
            if (isset(self::ZERO_WIDTH_CHARS[$ch])) {
                $count++;
            } else {
                $cleaned[] = $ch;
            }
        }

        if ($count > 0) {
            $report->watermarkTypes[] = 'zero_width_characters';
            $report->details[] = "Found {$count} zero-width/invisible characters";
            $report->zeroWidthCount = $count;
            $report->charactersRemoved += $count;
            $report->cleanedText = implode('', $cleaned);
        }
    }

    // ───────────────────────────────────────────────────────────
    //  HOMOGLYPHS
    // ───────────────────────────────────────────────────────────

    private function detectHomoglyphs(string $text, WatermarkReport $report): void
    {
        $isCyrillic = in_array($this->lang, ['ru', 'uk'], true);

        /** @var list<array{string, string, int}> $homoglyphs */
        $homoglyphs = [];

        $chars = $this->mbStrSplit($report->cleanedText);
        $len = count($chars);

        for ($i = 0; $i < $len; $i++) {
            $ch = $chars[$i];

            if ($isCyrillic) {
                // In Cyrillic text, look for Latin substitutions
                if (isset(self::LATIN_TO_CYRILLIC[$ch])) {
                    $left = $i > 0 ? $chars[$i - 1] : ' ';
                    $right = $i < $len - 1 ? $chars[$i + 1] : ' ';
                    if (self::isCyrillicChar($left) || self::isCyrillicChar($right)) {
                        $expected = self::LATIN_TO_CYRILLIC[$ch];
                        $homoglyphs[] = [$ch, $expected, $i];
                        $chars[$i] = $expected;
                    }
                }
            } else {
                // In Latin text, look for Cyrillic substitutions
                if (isset(self::CYRILLIC_TO_LATIN[$ch])) {
                    $left = $i > 0 ? $chars[$i - 1] : ' ';
                    $right = $i < $len - 1 ? $chars[$i + 1] : ' ';
                    if (self::isLatinChar($left) || self::isLatinChar($right)) {
                        $expected = self::CYRILLIC_TO_LATIN[$ch];
                        $homoglyphs[] = [$ch, $expected, $i];
                        $chars[$i] = $expected;
                    }
                }
            }

            // Check special homoglyphs
            if (isset(self::SPECIAL_HOMOGLYPHS[$ch])) {
                $expected = self::SPECIAL_HOMOGLYPHS[$ch];
                if ($ch !== $expected) {
                    $homoglyphs[] = [$ch, $expected, $i];
                    $chars[$i] = $expected;
                }
            }
        }

        if ($homoglyphs !== []) {
            $report->watermarkTypes[] = 'homoglyph_substitution';
            $report->homoglyphsFound = $homoglyphs;
            $count = count($homoglyphs);
            $report->details[] = "Found {$count} homoglyph substitutions";
            $report->charactersRemoved += $count;
            $report->cleanedText = implode('', $chars);
        }
    }

    // ───────────────────────────────────────────────────────────
    //  INVISIBLE UNICODE
    // ───────────────────────────────────────────────────────────

    /**
     * Detect invisible Unicode characters by category (Cf — format characters).
     */
    private function detectInvisible(string $text, WatermarkReport $report): void
    {
        $count = 0;
        $cleaned = [];
        $length = mb_strlen($report->cleanedText, 'UTF-8');

        for ($i = 0; $i < $length; $i++) {
            $ch = mb_substr($report->cleanedText, $i, 1, 'UTF-8');

            // Allow normal whitespace and newlines
            if ($ch === "\n" || $ch === "\r" || $ch === "\t" || $ch === ' ') {
                $cleaned[] = $ch;
                continue;
            }

            // Detect format characters (Cf) that aren't zero-width (already handled)
            if (self::isUnicodeCategoryFormat($ch) && !isset(self::ZERO_WIDTH_CHARS[$ch])) {
                $count++;
            } else {
                $cleaned[] = $ch;
            }
        }

        if ($count > 0) {
            $report->watermarkTypes[] = 'invisible_unicode';
            $report->details[] = "Found {$count} invisible Unicode format characters";
            $report->charactersRemoved += $count;
            $report->cleanedText = implode('', $cleaned);
        }
    }

    // ───────────────────────────────────────────────────────────
    //  SPACING ANOMALIES
    // ───────────────────────────────────────────────────────────

    /**
     * Detect unusual spacing patterns that could encode information.
     */
    private function detectSpacingAnomalies(string $text, WatermarkReport $report): void
    {
        $cleaned = $report->cleanedText;

        // Multiple consecutive spaces (could encode binary data)
        if (preg_match_all('/ {2,}/', $cleaned, $matches)) {
            $multiSpaceCount = count($matches[0]);
            if ($multiSpaceCount > 5) {
                $report->watermarkTypes[] = 'spacing_steganography';
                $report->details[] = "Found {$multiSpaceCount} unusual multi-space sequences";
                // Normalize to single spaces
                $cleaned = (string) preg_replace('/ {2,}/', ' ', $cleaned);
                $report->cleanedText = $cleaned;
            }
        }

        // Trailing spaces on lines (could encode bits)
        $lines = explode("\n", $cleaned);
        $trailingCount = 0;
        foreach ($lines as $line) {
            if ($line !== rtrim($line, ' ')) {
                $trailingCount++;
            }
        }
        if ($trailingCount > 3) {
            $report->watermarkTypes[] = 'trailing_space_steganography';
            $report->details[] = "Found {$trailingCount} lines with trailing spaces";
            $cleaned = implode(
                "\n",
                array_map(static fn(string $line): string => rtrim($line, ' '), $lines)
            );
            $report->cleanedText = $cleaned;
        }
    }

    // ───────────────────────────────────────────────────────────
    //  STATISTICAL WATERMARKS
    // ───────────────────────────────────────────────────────────

    /**
     * Detect statistical watermark patterns used by AI systems.
     *
     * Some AI watermarking schemes bias token selection toward
     * "green list" tokens. This manifests as unusual bigram distributions.
     */
    private function detectStatisticalWatermarks(string $text, WatermarkReport $report): void
    {
        if (preg_match_all('/\b\w+\b/u', mb_strtolower($text, 'UTF-8'), $matches)) {
            $words = $matches[0];
        } else {
            return;
        }

        if (count($words) < 50) {
            return;
        }

        // Check if word endings are suspiciously uniform
        $endings2 = [];
        foreach ($words as $w) {
            if (mb_strlen($w, 'UTF-8') > 3) {
                $endings2[] = mb_substr($w, -2, 2, 'UTF-8');
            }
        }

        if ($endings2 === []) {
            return;
        }

        $endingCounts = array_count_values($endings2);
        arsort($endingCounts);
        $total = count($endings2);

        // If any 2-char ending appears in >15% of words (unusual)
        $top3 = array_slice($endingCounts, 0, 3, true);
        foreach ($top3 as $ending => $count) {
            $ratio = $count / $total;
            if ($ratio > 0.15 && !in_array($ending, self::ALLOWED_ENDINGS, true)) {
                $pct = sprintf('%.1f%%', $ratio * 100);
                $report->watermarkTypes[] = 'statistical_bias';
                $report->details[] = "Suspicious word ending bias: '{$ending}' appears in {$pct} of words";
                break;
            }
        }
    }

    // ───────────────────────────────────────────────────────────
    //  C2PA / IPTC METADATA MARKERS
    // ───────────────────────────────────────────────────────────

    /** Regex patterns for content provenance metadata embedded in text */
    private const METADATA_PATTERNS = [
        // C2PA content credential markers
        ['pattern' => '/(?:c2pa|smpte|cr|cai):[a-zA-Z0-9_.\\/\\-]+/iu', 'kind' => 'c2pa_manifest'],
        // IPTC / XMP metadata namespace prefixes
        ['pattern' => '/(?:iptc|dc|xmp|exif|photoshop|rdf):[a-zA-Z][a-zA-Z0-9_]+/iu', 'kind' => 'iptc_metadata'],
        // Content Credentials / Content Authenticity Initiative strings
        ['pattern' => '/Content\s+Credentials?|Content\s+Authenticity|AI[\s\-]?Generated|Machine[\s\-]?Generated|Generative[\s\-]?AI/iu', 'kind' => 'content_provenance'],
        // Embedded base64 provenance blobs (≥ 40 chars of base64)
        ['pattern' => '/(?:^|[\s;,])([A-Za-z0-9+\\/]{40,}={0,2})(?:$|[\s;,])/mu', 'kind' => 'embedded_blob'],
        // UUID-style provenance identifiers
        ['pattern' => '/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/iu', 'kind' => 'provenance_uuid'],
    ];

    /**
     * Detect C2PA / IPTC content-provenance markers embedded in text.
     *
     * Looks for namespace prefixes (c2pa:, iptc:, dc:, xmp:, etc.),
     * Content Credentials strings, base64 provenance blobs and UUIDs
     * that AI systems or pipelines may inject.
     */
    private function detectMetadataMarkers(string $text, WatermarkReport $report): void
    {
        $foundTypes = [];
        $foundDetails = [];
        $cleaned = $report->cleanedText;

        foreach (self::METADATA_PATTERNS as $entry) {
            $pattern = $entry['pattern'];
            $kind = $entry['kind'];

            if (preg_match_all($pattern, $cleaned, $matches)) {
                $allMatches = $matches[0];
                $count = count($allMatches);
                $foundTypes[] = $kind;

                // Show at most 3 samples per kind
                $samples = array_slice($allMatches, 0, 3);
                $sampleStrs = array_map(
                    static fn(string $s): string => "'" . mb_substr($s, 0, 40, 'UTF-8') . "'",
                    $samples
                );
                $foundDetails[] = "{$kind}: {$count} occurrence(s) (e.g. " . implode(', ', $sampleStrs) . ")";

                // Remove detected markers from cleaned text
                $cleaned = (string) preg_replace($pattern, '', $cleaned);
            }
        }

        if ($foundTypes !== []) {
            $report->watermarkTypes[] = 'metadata_markers';
            array_push($report->details, ...$foundDetails);
            // Clean up leftover whitespace after removal
            $cleaned = trim((string) preg_replace('/ {2,}/', ' ', $cleaned));
            $report->cleanedText = $cleaned;
        }
    }

    // ───────────────────────────────────────────────────────────
    //  HELPERS
    // ───────────────────────────────────────────────────────────

    /**
     * Check if a character is Cyrillic.
     */
    private static function isCyrillicChar(string $ch): bool
    {
        if ($ch === '' || ctype_space($ch)) {
            return false;
        }
        // Cyrillic Unicode block: U+0400–U+04FF (basic), U+0500–U+052F (supplement)
        $code = mb_ord($ch, 'UTF-8');
        return $code !== false && $code >= 0x0400 && $code <= 0x052F;
    }

    /**
     * Check if a character is Latin.
     */
    private static function isLatinChar(string $ch): bool
    {
        if ($ch === '' || ctype_space($ch)) {
            return false;
        }
        $code = mb_ord($ch, 'UTF-8');
        if ($code === false) {
            return false;
        }
        // Basic Latin letters: A–Z (0x41–0x5A), a–z (0x61–0x7A)
        // Latin Extended-A: 0x0100–0x017F, Latin Extended-B: 0x0180–0x024F
        return ($code >= 0x41 && $code <= 0x5A)
            || ($code >= 0x61 && $code <= 0x7A)
            || ($code >= 0x00C0 && $code <= 0x024F);
    }

    /**
     * Check if a character belongs to Unicode "Cf" (Format) category.
     *
     * Uses IntlChar when available, otherwise falls back to a code-point range check.
     */
    private static function isUnicodeCategoryFormat(string $ch): bool
    {
        if (class_exists(\IntlChar::class)) {
            $code = mb_ord($ch, 'UTF-8');
            if ($code === false) {
                return false;
            }
            return \IntlChar::charType($code) === \IntlChar::CHAR_CATEGORY_FORMAT_CHAR;
        }

        // Fallback: rough check for the most common Cf code-point ranges
        $code = mb_ord($ch, 'UTF-8');
        if ($code === false) {
            return false;
        }

        // Common Cf ranges
        return ($code >= 0x00AD && $code <= 0x00AD) // Soft hyphen
            || ($code >= 0x0600 && $code <= 0x0605)
            || ($code === 0x061C)
            || ($code === 0x06DD)
            || ($code === 0x070F)
            || ($code === 0x08E2)
            || ($code >= 0x180E && $code <= 0x180E)
            || ($code >= 0x200B && $code <= 0x200F)
            || ($code >= 0x202A && $code <= 0x202E)
            || ($code >= 0x2060 && $code <= 0x2064)
            || ($code >= 0x2066 && $code <= 0x206F)
            || ($code === 0xFEFF)
            || ($code >= 0xFFF9 && $code <= 0xFFFB);
    }

    /**
     * Split a UTF-8 string into an array of single characters.
     *
     * @return list<string>
     */
    private function mbStrSplit(string $string): array
    {
        if ($string === '') {
            return [];
        }
        return mb_str_split($string, 1, 'UTF-8');
    }
}
