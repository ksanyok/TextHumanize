<?php

declare(strict_types=1);

namespace TextHumanize\Pipeline;

/**
 * Protected segment info.
 */
class ProtectedSegment
{
    public function __construct(
        public readonly string $placeholder,
        public readonly string $original,
        public readonly string $kind,
    ) {
    }
}

/**
 * Text with protected segments replaced by placeholders.
 */
class SegmentedText
{
    /** @var ProtectedSegment[] */
    public readonly array $segments;
    public readonly string $text;

    /**
     * @param ProtectedSegment[] $segments
     */
    public function __construct(string $text, array $segments)
    {
        $this->text = $text;
        $this->segments = $segments;
    }

    /**
     * Restore protected segments into processed text.
     */
    public function restore(string $processedText): string
    {
        // Restore in reverse order
        $segments = array_reverse($this->segments);
        foreach ($segments as $seg) {
            $processedText = str_replace($seg->placeholder, $seg->original, $processedText);
        }
        return $processedText;
    }
}

/**
 * Segmenter — protects code blocks, URLs, emails, etc. from modification.
 */
class Segmenter
{
    private array $preserve;
    private int $counter = 0;

    public function __construct(array $preserve = [])
    {
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
    }

    /**
     * Segment text, replacing protected elements with placeholders.
     */
    public function segment(string $text): SegmentedText
    {
        $segments = [];
        $this->counter = 0;

        // Code blocks
        if ($this->preserve['code_blocks']) {
            $text = $this->protect($text, '/```[\s\S]*?```|~~~[\s\S]*?~~~/u', 'code_block', $segments);
            $text = $this->protect($text, '/`[^`\n]+`/u', 'inline_code', $segments);
        }

        // Markdown images (before links)
        if ($this->preserve['markdown']) {
            $text = $this->protect($text, '/!\[[^\]]*\]\([^)]+\)/u', 'md_image', $segments);
            $text = $this->protect($text, '/\[[^\]]*\]\([^)]+\)/u', 'md_link', $segments);
        }

        // URLs
        if ($this->preserve['urls']) {
            $text = $this->protect($text, '#https?://[^\s<>\])"\']+#u', 'url', $segments);
        }

        // Emails
        if ($this->preserve['emails']) {
            $text = $this->protect($text, '/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/u', 'email', $segments);
        }

        // HTML tags
        if ($this->preserve['html']) {
            $text = $this->protect($text, '/<[^>]+>/u', 'html', $segments);
        }

        // Hashtags
        if ($this->preserve['hashtags']) {
            $text = $this->protect($text, '/#[a-zA-Z0-9_\p{L}]+/u', 'hashtag', $segments);
        }

        // Mentions
        if ($this->preserve['mentions']) {
            $text = $this->protect($text, '/@[a-zA-Z0-9_]+/u', 'mention', $segments);
        }

        // Brand terms
        if (!empty($this->preserve['brand_terms'])) {
            foreach ($this->preserve['brand_terms'] as $term) {
                $pattern = '/\b' . preg_quote($term, '/') . '\b/ui';
                $text = $this->protect($text, $pattern, 'brand', $segments);
            }
        }

        // Keep keywords (for SEO)
        $keepKeywords = $this->preserve['keep_keywords'] ?? [];
        if (!empty($keepKeywords)) {
            foreach ($keepKeywords as $kw) {
                $pattern = '/' . preg_quote($kw, '/') . '/ui';
                $text = $this->protect($text, $pattern, 'keyword', $segments);
            }
        }

        return new SegmentedText($text, $segments);
    }

    /**
     * Replace matches with placeholders.
     * @param ProtectedSegment[] $segments
     */
    private function protect(string $text, string $pattern, string $kind, array &$segments): string
    {
        return preg_replace_callback($pattern, function (array $m) use ($kind, &$segments): string {
            $this->counter++;
            $placeholder = "\x00THZ_{$kind}_{$this->counter}\x00";
            $segments[] = new ProtectedSegment($placeholder, $m[0], $kind);
            return $placeholder;
        }, $text) ?? $text;
    }
}
