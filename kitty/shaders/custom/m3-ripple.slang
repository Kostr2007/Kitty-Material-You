#language slang 2026
// Copyright (C) 2026 Kitty Material You contributors
// Distributed under terms of the GPLv3 license.
//
// Material You touch ripple: clicking spreads a soft circle of the state
// layer color (the cursor color, the primary color of a Material You scheme)
// from the click position across the window, which then fades away, like
// pressing a button on Android.
//
// The pipeline uses a linear animation_curve, the M3 motion is computed here.

import kitty_custom_shader_types;

// Material state layers are composited in sRGB space, like Android does, so
// that a 12% overlay looks like 12% and not much stronger on dark themes
float3
to_srgb(float3 c) {
    return lerp(12.92 * c, 1.055 * pow(max(c, float3(0.0)), float3(1.0 / 2.4)) - 0.055, step(float3(0.0031308), c));
}

float3
to_linear(float3 c) {
    return lerp(c / 12.92, pow((max(c, float3(0.0)) + 0.055) / 1.055, float3(2.4)), step(float3(0.04045), c));
}

float3
state_layer(float3 color, float3 tint, float opacity) {
    return to_linear(lerp(to_srgb(color), to_srgb(tint), opacity));
}

// Opacity of the pressed state layer (M3 uses 10%)
static const float STATE_LAYER_OPACITY = 0.12;
// Fraction of the animation spent expanding, the rest is spent fading out
static const float EXPAND_FRACTION = 0.6;
// Width of the soft edge of the ripple, in pixels
static const float EDGE_SOFTNESS = 24.0;
// Clip the ripple to the window that was clicked, with rounded corners of this radius in pixels
static const float WINDOW_CORNER_RADIUS = 12.0;
// Use this color instead of the cursor color when its alpha is non-zero (linear RGB)
static const float4 RIPPLE_COLOR = float4(0.0);

// M3 emphasized decelerate easing, cubic-bezier(0.05, 0.7, 0.1, 1)
float
emphasized_decelerate(float x) {
    // solve the bezier for t with a few Newton iterations
    float t = x;
    for (int i = 0; i < 6; i++) {
        float mt = 1.0 - t;
        float bx = 3.0 * mt * mt * t * 0.05 + 3.0 * mt * t * t * 0.1 + t * t * t;
        float dx = 3.0 * mt * mt * 0.05 + 6.0 * mt * t * (0.1 - 0.05) + 3.0 * t * t * (1.0 - 0.1);
        t = clamp(t - (bx - x) / max(dx, 1e-4), 0.0, 1.0);
    }
    float mt = 1.0 - t;
    return 3.0 * mt * mt * t * 0.7 + 3.0 * mt * t * t * 1.0 + t * t * t;
}

float
rounded_rect_sdf(float2 p, float2 center, float2 half_size, float radius) {
    float2 q = abs(p - center) - (half_size - radius);
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}

public float4
fragment_main(float4 color, KittyTextures t, KittyCustomShaderData d) {
    float progress = t.animation_progress;
    if (progress <= 0.0 || progress >= 1.0) return color;
    float2 px = float2(d.viewport_size_pixels);
    float2 p = t.pos * px;
    float2 click = d.mouse_pos.zw * px;

    // The area the ripple is confined to: the window that was clicked
    float4 g = d.active_window_geometry;
    if (g.z <= 0.0 || g.w <= 0.0) g = d.central_area;
    float2 lo = g.xy * px, size = g.zw * px;
    float clip = rounded_rect_sdf(p, lo + size * 0.5, size * 0.5, WINDOW_CORNER_RADIUS);
    if (clip > 0.0) return color;
    if (any(click < lo) || any(click > lo + size)) return color;

    // Expand to the farthest corner with emphasized decelerate motion
    float2 far = max(abs(click - lo), abs(click - (lo + size)));
    float max_radius = length(far);
    float expand = emphasized_decelerate(clamp(progress / EXPAND_FRACTION, 0.0, 1.0));
    float radius = max(1.0, expand * max_radius);
    float coverage = 1.0 - smoothstep(radius - EDGE_SOFTNESS, radius, length(p - click));
    // fade in quickly, fade out after expanding
    float fade_in = smoothstep(0.0, 0.08, progress);
    float fade_out = 1.0 - smoothstep(EXPAND_FRACTION, 1.0, progress);
    float alpha = STATE_LAYER_OPACITY * coverage * fade_in * fade_out * (1.0 - smoothstep(-1.0, 0.0, clip));

    float3 tint = RIPPLE_COLOR.a > 0.0 ? RIPPLE_COLOR.rgb : (d.cursor_color.a > 0.0 ? d.cursor_color.rgb : d.foreground.rgb);
    return float4(state_layer(color.rgb, tint, alpha), color.a);
}
