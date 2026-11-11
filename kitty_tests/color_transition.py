#!/usr/bin/env python
# License: GPLv3 Copyright: 2026, Kitty Material You contributors

from unittest.mock import patch

from kitty.color_transition import ColorTransition, animatable_keys, int_to_oklab, mix_colors, oklab_to_int
from kitty.options.utils import EasingFunction

from .base import BaseTest


class TestColorTransition(BaseTest):
    def test_oklab(self):
        for c in (0, 0xFFFFFF, 0x6750A4, 0xD0BCFF, 0x1D1B20, 0xFF0000, 0x00FF00, 0x0000FF):
            self.ae(oklab_to_int(int_to_oklab(c)), c)
        self.ae(mix_colors(0x000000, 0xFFFFFF, 0), 0)
        self.ae(mix_colors(0x000000, 0xFFFFFF, 1), 0xFFFFFF)
        mid = mix_colors(0x000000, 0xFFFFFF, 0.5)
        # perceptual midpoint of black and white is a mid gray, much lighter than linear 50%
        self.assertTrue(0x50 < (mid & 0xFF) < 0x70, hex(mid))
        self.ae(len({(mid >> s) & 0xFF for s in (0, 8, 16)}), 1)
        # overshoot is clamped to valid colors
        self.ae(mix_colors(0x000000, 0xFFFFFF, 1.3), 0xFFFFFF)

    def test_animatable_keys(self):
        self.ae(animatable_keys({'background': 1, 'color3': 2, 'cursor': None, 'macos_titlebar_color': 0}), ('background', 'color3'))

    def test_transition(self):
        now = [10.0]
        frames, finished = [], []

        def run(easing=EasingFunction()):
            del frames[:], finished[:]
            ct = ColorTransition(
                (((), {'background': 0x000000}),),
                {'background': 0xFFFFFF},
                1.0,
                easing,
                lambda windows, spec: frames.append(spec['background']),
                lambda except_keys: finished.append(except_keys),
            )
            with (
                patch('kitty.color_transition.monotonic', lambda: now[0]),
                patch('kitty.color_transition.add_timer', lambda *a: 1),
                patch('kitty.color_transition.remove_timer', lambda *a: None),
            ):
                now[0] = 10.0
                ct.started_at = now[0]
                ct.start()
                for t in (0.25, 0.5, 0.75, 1.0, 1.5):
                    now[0] = 10.0 + t
                    ct.tick()
            return ct

        ct = run()
        self.assertTrue(ct.done)
        self.ae(len(frames), 4)  # t=0, .25, .5, .75 then the final change is applied as is
        self.ae(finished, [frozenset()])
        self.ae(frames[0], 0)
        self.assertTrue(all(b > a for a, b in zip(frames, frames[1:])))

        run(EasingFunction.spring('0.6'))
        self.ae(len(frames), 4)
        self.ae(finished, [frozenset()])

        # stopping without applying the final colors
        ct = ColorTransition((((), {'background': 0}),), {'background': 1}, 1, EasingFunction(), lambda *a: None, finished.append)
        del finished[:]
        ct.stop()
        self.ae(finished, [])
        ct = ColorTransition((((), {'background': 0}),), {'background': 1}, 1, EasingFunction(), lambda *a: None, finished.append)
        ct.stop(apply_final=True, except_keys=frozenset({'background'}))
        self.ae(finished, [frozenset({'background'})])

    def test_color_contrast(self):
        from kitty.color_contrast import contrast_ratio, reverses_polarity

        self.ae(contrast_ratio(0, 0xFFFFFF), 21)
        self.ae(contrast_ratio(0x6750A4, 0x6750A4), 1)
        dark = {'foreground': 0xE6E0E9, 'background': 0x141218}
        light = {'foreground': 0x1D1B20, 'background': 0xFEF7FF}
        self.assertTrue(reverses_polarity(dark, light))
        self.assertTrue(reverses_polarity(light, dark))
        self.assertFalse(reverses_polarity(dark, {'background': 0x211F24}))
        self.assertTrue(reverses_polarity(dark, {'background': 0xFFFFFF}))
        self.assertFalse(reverses_polarity({'background': 0}, light))
        self.assertTrue(
            reverses_polarity(
                {'active_tab_foreground': 0xFFFFFF, 'active_tab_background': 0},
                {'active_tab_foreground': 0, 'active_tab_background': 0xFFFFFF},
            )
        )

    def test_color_effects_do_not_overshoot(self):
        ct = ColorTransition((), {}, 1, EasingFunction.spring('0.6'), lambda *a: None, lambda *a: None)
        values = [ct.progress(t / 1000) for t in range(1001)]
        self.assertTrue(all(0 <= t <= 1 for t in values))

    def test_polarity_transition_is_instant(self):
        from types import SimpleNamespace

        from kitty.color_transition import start_color_transition

        dark = {'foreground': 0xE6E0E9, 'background': 0x141218}
        light = {'foreground': 0x1D1B20, 'background': 0xFEF7FF}
        window = SimpleNamespace(current_colors=dark)
        with (
            patch('kitty.color_transition.get_options', lambda: SimpleNamespace(color_transition=(0.5, EasingFunction(), None))),
            patch('kitty.color_transition.global_start_colors', lambda keys: dark),
            patch('kitty.color_transition.cancel_color_transition'),
            patch('kitty.color_transition.ColorTransition') as transition,
        ):
            self.assertFalse(start_color_transition(light, (), False, [window], False, None))
            transition.assert_not_called()
            # Also catch polarity changes when just one member of the pair is sent.
            self.assertFalse(start_color_transition({'background': 0xFFFFFF}, (), False, [window], False, None))
            self.assertTrue(start_color_transition({'background': 0x211F24}, (), False, [window], False, None))
            transition.assert_called_once()
