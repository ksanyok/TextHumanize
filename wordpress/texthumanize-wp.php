<?php
/**
 * Plugin Name: TextHumanize for WordPress
 * Plugin URI:  https://github.com/ksanyok/TextHumanize
 * Description: Humanize text content and detect AI-generated text using TextHumanize PHP SDK.
 * Version:     1.0.0
 * Author:      TextHumanize Contributors
 * License:     Dual License
 * Text Domain: texthumanize
 * Requires PHP: 8.1
 *
 * Setup:
 *   1. Copy this folder to wp-content/plugins/texthumanize-wp/
 *   2. Run: cd wp-content/plugins/texthumanize-wp && composer install
 *   3. Activate in WordPress admin → Plugins
 *
 * Requires the TextHumanize PHP SDK. Add to composer.json:
 *   { "require": { "ksanyok/texthumanize-php": "^0.15" } }
 */

defined('ABSPATH') || exit;

// Load SDK — adjust path if using Composer autoload from main project
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require_once __DIR__ . '/vendor/autoload.php';
} elseif (file_exists(ABSPATH . '../../php/src/TextHumanize.php')) {
    // Development fallback: direct load from repo
    require_once ABSPATH . '../../php/src/TextHumanize.php';
}

/**
 * Main plugin class.
 */
class TextHumanize_WP_Plugin {

    /** @var \TextHumanize\TextHumanize|null */
    private $th = null;

    public function __construct() {
        // Admin
        add_action('admin_menu', [$this, 'add_settings_page']);
        add_action('admin_init', [$this, 'register_settings']);

        // Meta box
        add_action('add_meta_boxes', [$this, 'add_meta_box']);

        // AJAX handlers
        add_action('wp_ajax_th_check_ai', [$this, 'ajax_check_ai']);
        add_action('wp_ajax_th_humanize', [$this, 'ajax_humanize']);

        // Auto-humanize (opt-in)
        if (get_option('th_auto_humanize', false)) {
            add_filter('the_content', [$this, 'auto_humanize'], 20);
        }
    }

    /**
     * Get or create TextHumanize instance.
     */
    private function get_th() {
        if ($this->th === null) {
            if (class_exists('\\TextHumanize\\TextHumanize')) {
                $this->th = new \TextHumanize\TextHumanize();
            }
        }
        return $this->th;
    }

    /**
     * Auto-humanize content filter.
     */
    public function auto_humanize(string $content): string {
        $th = $this->get_th();
        if (!$th || empty($content) || is_admin()) {
            return $content;
        }

        try {
            $lang = get_option('th_lang', 'en');
            $profile = get_option('th_profile', 'web');
            $intensity = (int) get_option('th_intensity', 60);

            $result = $th->humanize($content, $lang, [
                'profile' => $profile,
                'intensity' => $intensity,
            ]);

            return $result['text'] ?? $content;
        } catch (\Exception $e) {
            return $content;
        }
    }

    /**
     * AJAX: Check AI score.
     */
    public function ajax_check_ai(): void {
        check_ajax_referer('th_nonce', 'nonce');

        $th = $this->get_th();
        if (!$th) {
            wp_send_json_error('TextHumanize SDK not available');
        }

        $text = sanitize_textarea_field(wp_unslash($_POST['text'] ?? ''));
        if (empty($text)) {
            wp_send_json_error('No text provided');
        }

        try {
            $lang = get_option('th_lang', 'en');
            $result = $th->detectAi($text, $lang);
            wp_send_json_success([
                'score' => $result['score'] ?? 0,
                'verdict' => $result['verdict'] ?? 'unknown',
            ]);
        } catch (\Exception $e) {
            wp_send_json_error($e->getMessage());
        }
    }

    /**
     * AJAX: Humanize text.
     */
    public function ajax_humanize(): void {
        check_ajax_referer('th_nonce', 'nonce');

        $th = $this->get_th();
        if (!$th) {
            wp_send_json_error('TextHumanize SDK not available');
        }

        $text = sanitize_textarea_field(wp_unslash($_POST['text'] ?? ''));
        if (empty($text)) {
            wp_send_json_error('No text provided');
        }

        try {
            $lang = get_option('th_lang', 'en');
            $profile = sanitize_text_field($_POST['profile'] ?? 'web');
            $intensity = (int) ($_POST['intensity'] ?? 60);

            $result = $th->humanize($text, $lang, [
                'profile' => $profile,
                'intensity' => $intensity,
            ]);

            wp_send_json_success([
                'text' => $result['text'] ?? $text,
                'change_ratio' => $result['change_ratio'] ?? 0,
            ]);
        } catch (\Exception $e) {
            wp_send_json_error($e->getMessage());
        }
    }

    /**
     * Meta box in post editor.
     */
    public function add_meta_box(): void {
        add_meta_box(
            'texthumanize_box',
            '✨ TextHumanize',
            [$this, 'render_meta_box'],
            ['post', 'page'],
            'side',
            'high'
        );
    }

    public function render_meta_box($post): void {
        wp_nonce_field('th_nonce', 'th_nonce_field');
        $nonce = wp_create_nonce('th_nonce');
        ?>
        <div id="th-panel">
            <p>
                <button type="button" class="button" onclick="thCheckAI()">
                    🔍 Check AI Score
                </button>
            </p>
            <p>
                <button type="button" class="button button-primary"
                        onclick="thHumanize()">
                    ✨ Humanize Content
                </button>
            </p>
            <div id="th-result"
                 style="margin-top:10px; padding:8px;
                        background:#f0f0f1; display:none;">
            </div>
        </div>
        <script>
        function thCheckAI() {
            var content = '';
            if (typeof wp !== 'undefined' && wp.data) {
                content = wp.data.select('core/editor')
                              .getEditedPostContent();
            } else {
                var el = document.getElementById('content');
                content = el ? el.value : '';
            }

            jQuery.post(ajaxurl, {
                action: 'th_check_ai',
                nonce: '<?php echo esc_js($nonce); ?>',
                text: content
            }, function(res) {
                var el = document.getElementById('th-result');
                el.style.display = 'block';
                if (res.success) {
                    var pct = (res.data.score * 100).toFixed(0);
                    el.innerHTML = '<b>AI Score:</b> ' + pct +
                                   '% — ' + res.data.verdict;
                } else {
                    el.innerHTML = '<b>Error:</b> ' + res.data;
                }
            });
        }

        function thHumanize() {
            var content = '';
            if (typeof wp !== 'undefined' && wp.data) {
                content = wp.data.select('core/editor')
                              .getEditedPostContent();
            } else {
                var el = document.getElementById('content');
                content = el ? el.value : '';
            }

            jQuery.post(ajaxurl, {
                action: 'th_humanize',
                nonce: '<?php echo esc_js($nonce); ?>',
                text: content
            }, function(res) {
                var el = document.getElementById('th-result');
                el.style.display = 'block';
                if (res.success) {
                    // Update editor content
                    if (typeof wp !== 'undefined' && wp.data) {
                        wp.data.dispatch('core/editor').editPost({
                            content: res.data.text
                        });
                    } else {
                        var ed = document.getElementById('content');
                        if (ed) ed.value = res.data.text;
                    }
                    var pct = (res.data.change_ratio * 100).toFixed(0);
                    el.innerHTML = '<b>✅ Humanized!</b> Changed: ' +
                                   pct + '%';
                } else {
                    el.innerHTML = '<b>Error:</b> ' + res.data;
                }
            });
        }
        </script>
        <?php
    }

    /**
     * Settings page.
     */
    public function add_settings_page(): void {
        add_options_page(
            'TextHumanize',
            'TextHumanize',
            'manage_options',
            'texthumanize',
            [$this, 'render_settings']
        );
    }

    public function register_settings(): void {
        register_setting('texthumanize_settings', 'th_lang');
        register_setting('texthumanize_settings', 'th_profile');
        register_setting('texthumanize_settings', 'th_intensity');
        register_setting('texthumanize_settings', 'th_auto_humanize');
    }

    public function render_settings(): void {
        $langs = ['en','ru','uk','de','fr','es','pl','pt','it'];
        $profiles = [
            'web', 'chat', 'seo', 'docs', 'formal',
            'marketing', 'social', 'email',
        ];
        ?>
        <div class="wrap">
            <h1>TextHumanize Settings</h1>
            <form method="post" action="options.php">
                <?php settings_fields('texthumanize_settings'); ?>
                <table class="form-table">
                    <tr>
                        <th>Language</th>
                        <td>
                            <select name="th_lang">
                            <?php foreach ($langs as $l): ?>
                                <option value="<?php echo $l; ?>"
                                    <?php selected(get_option('th_lang', 'en'), $l); ?>>
                                    <?php echo strtoupper($l); ?>
                                </option>
                            <?php endforeach; ?>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th>Profile</th>
                        <td>
                            <select name="th_profile">
                            <?php foreach ($profiles as $p): ?>
                                <option value="<?php echo $p; ?>"
                                    <?php selected(get_option('th_profile', 'web'), $p); ?>>
                                    <?php echo ucfirst($p); ?>
                                </option>
                            <?php endforeach; ?>
                            </select>
                        </td>
                    </tr>
                    <tr>
                        <th>Intensity (0-100)</th>
                        <td>
                            <input type="number" name="th_intensity"
                                value="<?php echo esc_attr(get_option('th_intensity', 60)); ?>"
                                min="0" max="100">
                        </td>
                    </tr>
                    <tr>
                        <th>Auto-humanize posts</th>
                        <td>
                            <input type="checkbox" name="th_auto_humanize"
                                value="1"
                                <?php checked(get_option('th_auto_humanize')); ?>>
                            <span class="description">
                                Automatically humanize content on display
                            </span>
                        </td>
                    </tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }
}

// Initialize plugin
new TextHumanize_WP_Plugin();
