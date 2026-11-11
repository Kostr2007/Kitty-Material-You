#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kitty Material You contributors

from collections.abc import Mapping

# Paired text and surface roles. ANSI colors are application-controlled and
# cannot all be treated as normal text on the default background.
TEXT_PAIRS = (
    ('foreground', 'background'),
    ('selection_foreground', 'selection_background'),
    ('cursor_text_color', 'cursor'),
    ('active_tab_foreground', 'active_tab_background'),
    ('inactive_tab_foreground', 'inactive_tab_background'),
    ('mark1_foreground', 'mark1_background'),
    ('mark2_foreground', 'mark2_background'),
    ('mark3_foreground', 'mark3_background'),
)


def relative_luminance(color: int) -> float:
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return sum(linear(((color >> shift) & 255) / 255) * weight for shift, weight in ((16, 0.2126), (8, 0.7152), (0, 0.0722)))


def contrast_ratio(a: int, b: int) -> float:
    x, y = sorted((relative_luminance(a), relative_luminance(b)))
    return (y + 0.05) / (x + 0.05)


def reverses_polarity(start: Mapping[str, int], target: Mapping[str, int]) -> bool:
    """Opposite text/surface ordering cannot be continuously mixed legibly."""
    for fg, bg in TEXT_PAIRS:
        if fg in start and bg in start:
            before = relative_luminance(start[fg]) - relative_luminance(start[bg])
            after = relative_luminance(target.get(fg, start[fg])) - relative_luminance(target.get(bg, start[bg]))
            if before * after < 0:
                return True
    return False


def main() -> None:
    """Audit effective kitty configs, using kitty's own include/color parser."""
    import argparse
    import json

    from .config import load_config

    parser = argparse.ArgumentParser(description='Check Material You text/surface pairs (opaque sRGB, 4.5:1 minimum).')
    parser.add_argument('configs', nargs='+', help='kitty config files, applied in order (includes supported)')
    parser.add_argument('--json', action='store_true', help='machine readable report')
    args = parser.parse_args()
    bad = []
    opts = load_config(*args.configs, accumulate_bad_lines=bad)
    if bad:
        parser.error('; '.join(f'{b.number}: {b.line}: {b.exception}' for b in bad))
    colors: dict[str, int] = {}
    for pair in TEXT_PAIRS:
        for key in pair:
            value = getattr(opts, key)
            if value is not None and int(value) >= 0:
                colors[key] = int(value)
    # kitty's automatic selection defaults are an inversion of terminal text.
    colors.setdefault('selection_foreground', colors['background'])
    colors.setdefault('selection_background', colors['foreground'])
    colors.setdefault('cursor', colors['foreground'])
    colors.setdefault('cursor_text_color', colors['background'])
    results = [
        {'foreground': fg, 'background': bg, 'ratio': contrast_ratio(colors[fg], colors[bg]), 'pass': contrast_ratio(colors[fg], colors[bg]) >= 4.5}
        for fg, bg in TEXT_PAIRS
    ]
    report = {'opaque_srgb_only': True, 'background_opacity': opts.background_opacity, 'pairs': results, 'pass': all(r['pass'] for r in results)}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for result in results:
            print(f'{"PASS" if result["pass"] else "FAIL"} {result["foreground"]}/{result["background"]}: {result["ratio"]:.2f}:1')
        print('Opaque sRGB pairs only; compositor opacity, ANSI application colors and shader overlays require visual review.')
    raise SystemExit(0 if report['pass'] else 1)
