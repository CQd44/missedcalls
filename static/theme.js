/* ============================================================
   DHR Theme — dark/light mode toggle (shared across all pages)

   - Persists the user's choice in localStorage ("dhr-theme").
   - Falls back to the OS "prefers-color-scheme" preference.
   - Exposes window.DHRTheme with: get, set, toggle, onThemeChange, colors
   - Dispatches a "dhr:themechange" event so JS/SVG/Chart.js can react.
   ============================================================ */
(function () {
    'use strict';

    var KEY = 'dhr-theme';

    function systemPrefersDark() {
        try {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        } catch (e) {
            return false;
        }
    }

    function getPreferred() {
        try {
            var stored = localStorage.getItem(KEY);
            if (stored === 'light' || stored === 'dark') return stored;
        } catch (e) { /* ignore */ }
        return systemPrefersDark() ? 'dark' : 'light';
    }

    function get() {
        var t = document.documentElement.getAttribute('data-theme');
        return t === 'dark' ? 'dark' : 'light';
    }

    function apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        try { document.documentElement.style.colorScheme = theme; } catch (e) { /* ignore */ }
        var btn = document.querySelector('.theme-toggle');
        if (btn) btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    }

    function dispatch() {
        var ev;
        try {
            ev = new CustomEvent('dhr:themechange', { detail: { theme: get() } });
        } catch (e) {
            ev = document.createEvent('Event');
            ev.initEvent('dhr:themechange', true, true);
        }
        document.dispatchEvent(ev);
    }

    function set(theme) {
        theme = theme === 'dark' ? 'dark' : 'light';
        apply(theme);
        try { localStorage.setItem(KEY, theme); } catch (e) { /* ignore */ }
        dispatch();
    }

    function toggle() {
        set(get() === 'dark' ? 'light' : 'dark');
    }

    function onThemeChange(fn) {
        document.addEventListener('dhr:themechange', fn);
    }

    /* Palette for JS-driven visuals (Chart.js, inline SVG).
       Mirrors the CSS variables so charts match the active theme. */
    function colors() {
        var map = {
            light: {
                bg: '#f8fafc', card: '#ffffff', text: '#334155',
                muted: '#64748b', faint: '#94a3b8', border: '#e2e8f0',
                track: '#e2e8f0', grid: 'rgba(0, 0, 0, 0.08)',
                chartText: '#64748b',
                success: '#28a745', warning: '#f0ad4e', danger: '#dc3545',
                brand: '#00A9A7', brandDark: '#008f8d'
            },
            dark: {
                bg: '#16162b', card: '#23233d', text: '#e6e8f0',
                muted: '#9aa3b8', faint: '#767f96', border: '#34345a',
                track: '#34345a', grid: 'rgba(255, 255, 255, 0.08)',
                chartText: '#9aa3b8',
                success: '#28a745', warning: '#f0ad4e', danger: '#dc3545',
                brand: '#00A9A7', brandDark: '#00c2c0'
            }
        };
        return map[get()];
    }

    var api = {
        get: get,
        set: set,
        toggle: toggle,
        apply: apply,
        onThemeChange: onThemeChange,
        colors: colors
    };
    window.DHRTheme = api;

    function init() {
        apply(get());

        var btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.addEventListener('click', function () { api.toggle(); });
            btn.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    api.toggle();
                }
            });
            btn.setAttribute('aria-pressed', get() === 'dark' ? 'true' : 'false');
        }

        /* Follow OS changes only while the user hasn't chosen explicitly. */
        if (window.matchMedia) {
            var mq = window.matchMedia('(prefers-color-scheme: dark)');
            var handler = function (e) {
                try {
                    if (!localStorage.getItem(KEY)) apply(e.matches ? 'dark' : 'light');
                } catch (err) { /* ignore */ }
            };
            if (mq.addEventListener) mq.addEventListener('change', handler);
            else if (mq.addListener) mq.addListener(handler);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();