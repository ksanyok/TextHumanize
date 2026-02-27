# WordPress Plugin

PHP-based WordPress plugin using the TextHumanize PHP SDK.

## Installation

1. Copy the `texthumanize-wp/` folder to `wp-content/plugins/`
2. Run `composer install` inside the plugin folder
3. Activate via WordPress admin → Plugins

## Plugin Code

Create `wp-content/plugins/texthumanize-wp/texthumanize-wp.php`:

```php
<?php
/**
 * Plugin Name: TextHumanize
 * Description: Humanize text content and detect AI-generated text
 * Version: 1.0.0
 * Author: TextHumanize Contributors
 */

defined('ABSPATH') || exit;

require_once __DIR__ . '/vendor/autoload.php';

use TextHumanize\TextHumanize;

class TextHumanize_WP {
    private TextHumanize $th;
    private string $lang;

    public function __construct() {
        $this->th = new TextHumanize();
        $this->lang = get_option('texthumanize_lang', 'en');

        // Admin settings
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);

        // Content filters (opt-in)
        if (get_option('texthumanize_auto_humanize', false)) {
            add_filter('the_content', [$this, 'humanize_content'], 20);
        }

        // Meta box for post editor
        add_action('add_meta_boxes', [$this, 'add_meta_box']);
        add_action('wp_ajax_texthumanize_check', [$this, 'ajax_check']);
        add_action('wp_ajax_texthumanize_humanize', [$this, 'ajax_humanize']);
    }

    /**
     * Humanize content filter.
     */
    public function humanize_content(string $content): string {
        if (empty($content) || is_admin()) {
            return $content;
        }

        $result = $this->th->humanize($content, $this->lang, [
            'profile' => get_option('texthumanize_profile', 'web'),
            'intensity' => (int) get_option('texthumanize_intensity', 60),
        ]);

        return $result['text'] ?? $content;
    }

    /**
     * AI detection AJAX handler.
     */
    public function ajax_check(): void {
        check_ajax_referer('texthumanize_nonce', 'nonce');

        $text = sanitize_textarea_field($_POST['text'] ?? '');
        if (empty($text)) {
            wp_send_json_error('No text provided');
        }

        $result = $this->th->detectAi($text, $this->lang);
        wp_send_json_success([
            'score' => $result['score'],
            'verdict' => $result['verdict'],
            'confidence' => $result['confidence'],
        ]);
    }

    /**
     * Humanize AJAX handler.
     */
    public function ajax_humanize(): void {
        check_ajax_referer('texthumanize_nonce', 'nonce');

        $text = sanitize_textarea_field($_POST['text'] ?? '');
        if (empty($text)) {
            wp_send_json_error('No text provided');
        }

        $result = $this->th->humanize($text, $this->lang, [
            'profile' => sanitize_text_field($_POST['profile'] ?? 'web'),
            'intensity' => (int) ($_POST['intensity'] ?? 60),
        ]);

        wp_send_json_success([
            'text' => $result['text'],
            'change_ratio' => $result['change_ratio'],
        ]);
    }

    /**
     * Meta box in post editor.
     */
    public function add_meta_box(): void {
        add_meta_box(
            'texthumanize_box',
            'TextHumanize',
            [$this, 'render_meta_box'],
            ['post', 'page'],
            'side',
            'high'
        );
    }

    public function render_meta_box($post): void {
        wp_nonce_field('texthumanize_nonce', 'texthumanize_nonce');
        ?>
        <div id="texthumanize-panel">
            <p>
                <button type="button" class="button" id="th-check-ai">
                    🔍 Check AI Score
                </button>
            </p>
            <p>
                <button type="button" class="button button-primary" id="th-humanize">
                    ✨ Humanize Content
                </button>
            </p>
            <div id="th-result" style="margin-top: 10px;"></div>
        </div>
        <script>
        jQuery(function($) {
            $('#th-check-ai').on('click', function() {
                var content = wp.data.select('core/editor').getEditedPostContent();
                $.post(ajaxurl, {
                    action: 'texthumanize_check',
                    nonce: $('#texthumanize_nonce').val(),
                    text: content
                }, function(res) {
                    if (res.success) {
                        var d = res.data;
                        $('#th-result').html(
                            '<strong>AI Score:</strong> ' + (d.score * 100).toFixed(0) + '%<br>' +
                            '<strong>Verdict:</strong> ' + d.verdict
                        );
                    }
                });
            });

            $('#th-humanize').on('click', function() {
                var content = wp.data.select('core/editor').getEditedPostContent();
                $.post(ajaxurl, {
                    action: 'texthumanize_humanize',
                    nonce: $('#texthumanize_nonce').val(),
                    text: content
                }, function(res) {
                    if (res.success) {
                        wp.data.dispatch('core/editor').editPost({
                            content: res.data.text
                        });
                        $('#th-result').html(
                            '<strong>Humanized!</strong> Change: ' +
                            (res.data.change_ratio * 100).toFixed(0) + '%'
                        );
                    }
                });
            });
        });
        </script>
        <?php
    }

    /**
     * Admin menu.
     */
    public function add_admin_menu(): void {
        add_options_page(
            'TextHumanize Settings',
            'TextHumanize',
            'manage_options',
            'texthumanize',
            [$this, 'render_settings_page']
        );
    }

    public function register_settings(): void {
        register_setting('texthumanize', 'texthumanize_lang');
        register_setting('texthumanize', 'texthumanize_profile');
        register_setting('texthumanize', 'texthumanize_intensity');
        register_setting('texthumanize', 'texthumanize_auto_humanize');
    }

    public function render_settings_page(): void {
        ?>
        <div class="wrap">
            <h1>TextHumanize Settings</h1>
            <form method="post" action="options.php">
                <?php settings_fields('texthumanize'); ?>
                <table class="form-table">
                    <tr>
                        <th>Language</th>
                        <td>
                            <select name="texthumanize_lang">
                                <?php foreach (['en','ru','uk','de','fr','es','pl','pt','it'] as $l): ?>
                                <option value="<?= $l ?>" <?php selected(get_option('texthumanize_lang'), $l); ?>><?= strtoupper($l) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th>Profile</th>
                        <td>
                            <select name="texthumanize_profile">
                                <?php foreach (['web','chat','seo','docs','formal','marketing','social','email'] as $p): ?>
                                <option value="<?= $p ?>" <?php selected(get_option('texthumanize_profile'), $p); ?>><?= ucfirst($p) ?></option>
                                <?php endforeach; ?>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th>Intensity (0-100)</th>
                        <td><input type="number" name="texthumanize_intensity" value="<?= esc_attr(get_option('texthumanize_intensity', 60)) ?>" min="0" max="100"></td>
                    </tr>
                    <tr>
                        <th>Auto-humanize posts</th>
                        <td><input type="checkbox" name="texthumanize_auto_humanize" value="1" <?php checked(get_option('texthumanize_auto_humanize')); ?>></td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }
}

new TextHumanize_WP();
```

## composer.json

Create `wp-content/plugins/texthumanize-wp/composer.json`:

```json
{
    "require": {
        "ksanyok/texthumanize-php": "^0.15"
    }
}
```

## Features

- **Meta box** in Gutenberg editor with "Check AI Score" and "Humanize Content" buttons
- **AJAX-powered** — no page reloads
- **Settings page** — language, profile, intensity, auto-humanize toggle
- **Content filter** — optional auto-humanize on `the_content`
- **Nonce verification** — WordPress security standards
