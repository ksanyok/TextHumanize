/**
 * TextHumanize for WordPress — Editor Panel Scripts.
 *
 * @package TextHumanize
 */
/* global jQuery, ajaxurl, wp, thData */

(function ($) {
    'use strict';

    /**
     * Get current post content from Gutenberg or Classic editor.
     * @returns {string}
     */
    function getEditorContent() {
        if (typeof wp !== 'undefined' && wp.data) {
            return wp.data.select('core/editor').getEditedPostContent();
        }
        var el = document.getElementById('content');
        return el ? el.value : '';
    }

    /**
     * Display result in the meta-box panel.
     * @param {string} html
     */
    function showResult(html) {
        var el = document.getElementById('th-result');
        if (el) {
            el.style.display = 'block';
            el.innerHTML = html;
        }
    }

    /**
     * Check AI score via AJAX.
     */
    window.thCheckAI = function () {
        var content = getEditorContent();
        if (!content) {
            showResult('<b>' + thData.i18n.error + ':</b> ' + thData.i18n.noContent);
            return;
        }

        showResult('<em>' + thData.i18n.checking + '</em>');

        $.post(ajaxurl, {
            action: 'th_check_ai',
            nonce: thData.nonce,
            text: content
        }, function (res) {
            if (res.success) {
                var pct = (res.data.score * 100).toFixed(0);
                showResult(
                    '<b>' + thData.i18n.aiScore + ':</b> ' + pct + '% — ' + res.data.verdict
                );
            } else {
                showResult('<b>' + thData.i18n.error + ':</b> ' + res.data);
            }
        }).fail(function () {
            showResult('<b>' + thData.i18n.error + ':</b> ' + thData.i18n.networkError);
        });
    };

    /**
     * Humanize content via AJAX.
     */
    window.thHumanize = function () {
        var content = getEditorContent();
        if (!content) {
            showResult('<b>' + thData.i18n.error + ':</b> ' + thData.i18n.noContent);
            return;
        }

        showResult('<em>' + thData.i18n.processing + '</em>');

        $.post(ajaxurl, {
            action: 'th_humanize',
            nonce: thData.nonce,
            text: content
        }, function (res) {
            if (res.success) {
                // Update editor content
                if (typeof wp !== 'undefined' && wp.data) {
                    wp.data.dispatch('core/editor').editPost({
                        content: res.data.text
                    });
                } else {
                    var ed = document.getElementById('content');
                    if (ed) {
                        ed.value = res.data.text;
                    }
                }
                var pct = (res.data.change_ratio * 100).toFixed(0);
                showResult(
                    '<b>✅ ' + thData.i18n.humanized + '</b> ' +
                    thData.i18n.changed + ': ' + pct + '%'
                );
            } else {
                showResult('<b>' + thData.i18n.error + ':</b> ' + res.data);
            }
        }).fail(function () {
            showResult('<b>' + thData.i18n.error + ':</b> ' + thData.i18n.networkError);
        });
    };

})(jQuery);
