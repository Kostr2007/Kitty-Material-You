#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kitty Material You contributors

# Animated color scheme changes (the color_transition option): instead of
# switching colors instantly, morph every animatable color in OKLab space,
# one frame at a time, then apply the requested change exactly as it would
# have been applied without animation.

from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Optional

from .fast_data_types import add_timer, evaluate_easing_function, get_options, monotonic, remove_timer
from .options.types import special_colors
from .options.utils import EasingFunction

if TYPE_CHECKING:
    from .colors import BackgroundImageOptions, ColorsSpec, TransparentBackgroundColors
    from .typing_compat import WindowType

FRAME_INTERVAL = 1 / 60
Lab = tuple[float, float, float]


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def int_to_oklab(color: int) -> Lab:
    r, g, b = (srgb_to_linear(((color >> shift) & 0xFF) / 255) for shift in (16, 8, 0))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_int(lab: Lab) -> int:
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186124 * m_ + 1.7076147010 * s_,
    )
    r, g, b = (max(0, min(255, round(linear_to_srgb(max(0.0, min(1.0, c))) * 255))) for c in rgb)
    return (r << 16) | (g << 8) | b


def mix_colors(start: int, end: int, t: float) -> int:
    if t <= 0:
        return start
    if t >= 1 and t - 1 < 1e-9:
        return end
    a, b = int_to_oklab(start), int_to_oklab(end)
    return oklab_to_int((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))


def animatable_keys(spec: 'ColorsSpec') -> tuple[str, ...]:
    return tuple(k for k, v in spec.items() if isinstance(v, int) and k not in special_colors)


class ColorTransition:
    """Morph a group of windows (and the global colors) from their current colors to spec."""

    def __init__(
        self,
        groups: Sequence[tuple[tuple['WindowType', ...], dict[str, int]]],
        target: dict[str, int],
        duration: float,
        easing: EasingFunction,
        apply_frame: Callable[[tuple['WindowType', ...], 'ColorsSpec'], None],
        finish: Callable[[frozenset[str]], None],
    ):
        self.groups, self.target, self.duration, self.easing = groups, target, duration, easing
        self.apply_frame, self.finish = apply_frame, finish
        self.started_at = monotonic()
        self.timer_id: int | None = None

    def progress(self, elapsed: float) -> float:
        t = elapsed / self.duration if self.duration > 0 else 1
        if t >= 1:
            return 1
        if not self.easing:
            return t
        return evaluate_easing_function(self.easing, t, self.duration)

    def start(self) -> None:
        self.tick()
        if self.timer_id is None and not self.done:
            self.timer_id = add_timer(self.tick, FRAME_INTERVAL, True)

    done = False

    def tick(self, timer_id: Optional[int] = None) -> None:
        if self.done:
            return
        elapsed = monotonic() - self.started_at
        if elapsed >= self.duration:
            self.stop(apply_final=True)
            return
        t = self.progress(elapsed)
        for windows, start in self.groups:
            self.apply_frame(windows, {k: mix_colors(v, self.target[k], t) for k, v in start.items()})

    def stop(self, apply_final: bool = False, except_keys: frozenset[str] = frozenset()) -> None:
        if self.done:
            return
        self.done = True
        if self.timer_id is not None:
            remove_timer(self.timer_id)
            self.timer_id = None
        if apply_final:
            self.finish(except_keys)


current_transition: ColorTransition | None = None


def cancel_color_transition(retargeted_keys: Iterable[str] = ()) -> None:
    """Stop the running transition. Colors that are not being retargeted by a
    new transition jump to their final values, the others continue from where
    they are now."""
    global current_transition
    if current_transition is not None:
        ct, current_transition = current_transition, None
        ct.stop(apply_final=True, except_keys=frozenset(retargeted_keys))


def global_start_colors(keys: Iterable[str]) -> dict[str, int]:
    from .fast_data_types import get_boss

    opts = get_options()
    keys = frozenset(keys)
    ans: dict[str, int] = {}
    for k in keys:
        v = getattr(opts, k, None)
        if v is not None and k not in special_colors:
            try:
                ans[k] = int(v)
            except TypeError:
                pass
    for tm in get_boss().all_tab_managers:
        for k, cv in tm.tab_bar.current_colors.items():
            if k in keys and cv is not None:
                ans[k] = int(cv)
        break
    return ans


def start_color_transition(
    spec: 'ColorsSpec',
    transparent_background_colors: 'TransparentBackgroundColors',
    configured: bool,
    windows: Sequence['WindowType'],
    notify_on_bg_change: bool,
    background_image_options: Optional['BackgroundImageOptions'],
) -> bool:
    """Start animating towards spec, returns False if no animation is needed and the colors should be applied directly."""
    global current_transition
    duration, easing, _ = get_options().color_transition
    keys = animatable_keys(spec)
    cancel_color_transition(keys)
    if duration <= 0 or not keys:
        return False
    from .colors import patch_colors

    target = {k: v for k in keys if isinstance(v := spec[k], int)}
    gstart = global_start_colors(keys)
    groups: dict[tuple[tuple[str, int], ...], list[WindowType]] = {}
    for w in windows:
        if not w:
            continue
        current: dict[str, Any] = w.current_colors
        start = dict(gstart)
        for k in keys:
            if isinstance(current.get(k), int):
                start[k] = current[k]
        start = {k: v for k, v in start.items() if v != target[k]}
        groups.setdefault(tuple(sorted(start.items())), []).append(w)
    if not windows:
        start = {k: v for k, v in gstart.items() if v != target[k]}
        groups[tuple(sorted(start.items()))] = []
    final_groups = tuple((tuple(ws), dict(start)) for start, ws in groups.items() if start)
    if not final_groups:
        return False

    def apply_frame(group: tuple['WindowType', ...], frame: 'ColorsSpec') -> None:
        from .fast_data_types import get_boss

        boss = get_boss()
        alive = tuple(w for w in group if w.id in boss.window_id_map)
        if group and not alive:
            return
        patch_colors(frame, transparent_background_colors, False, windows=alive, notify_on_bg_change=False, animate=False)

    def finish(except_keys: frozenset[str]) -> None:
        global current_transition
        if current_transition is not None and current_transition.done:
            current_transition = None
        from .fast_data_types import get_boss

        boss = get_boss()
        alive = [w for w in windows if w and w.id in boss.window_id_map]
        final_spec = {k: v for k, v in spec.items() if k not in except_keys} if except_keys else spec
        patch_colors(
            final_spec,
            transparent_background_colors,
            configured,
            windows=alive,
            notify_on_bg_change=notify_on_bg_change,
            background_image_options=background_image_options,
            animate=False,
        )

    current_transition = ColorTransition(final_groups, target, duration, easing, apply_frame, finish)
    current_transition.start()
    return True
