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
