#language slang 2026
// Copyright (C) 2026 Kitty Material You contributors
// Distributed under terms of the GPLv3 license.
//
// Material You focus indicator: when a window gains focus a rounded outline in
// the cursor color (the primary color of a Material You scheme) springs into
// place around it with a little bounce, glows for a moment and fades away,
// while the other windows briefly recede.
//
// The pipeline uses a linear animation_curve, the spring is computed here.

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

// Thickness of the focus outline, in pixels (M3 uses 3dp)
static const float OUTLINE_WIDTH = 3.0;
// Gap between the edge of the space the window occupies (including its margin) and the outline, in pixels
static const float OUTLINE_INSET = 2.0;
// How far outside its final position the outline starts, in pixels
static const float SPRING_TRAVEL = 18.0;
// Corner radius of the outline, in pixels
static const float CORNER_RADIUS = 14.0;
// Damping ratio of the spring that moves the outline into place (below 1 bounces)
static const float SPRING_DAMPING = 0.55;
// Number of natural periods of the spring that fit in the animation
static const float SPRING_SPEED = 9.0;
// Peak opacity of the outline
static const float OUTLINE_OPACITY = 0.9;
// How much other windows are dimmed at the start of the animation (0 = not at all)
static const float INACTIVE_DIM = 0.25;
// Use this color instead of the cursor color when its alpha is non-zero (linear RGB)
static const float4 OUTLINE_COLOR = float4(0.0);

float
spring(float damping, float t) {
    if (damping < 1.0) {
        float wd = sqrt(1.0 - damping * damping);
        return 1.0 - exp(-damping * t) * (cos(wd * t) + (damping / wd) * sin(wd * t));
    }
    return 1.0 - exp(-t) * (1.0 + t);
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
    float4 g = d.active_window_geometry;
    if (g.z <= 0.0 || g.w <= 0.0) return color;
    // Only interesting when there is more than one window
    if (all(abs(g - d.central_area) < 1e-4)) return color;

    // Include the padding, border and margin of the window
    g.xy -= d.active_window_padding.xy;
    g.zw += d.active_window_padding.xy + d.active_window_padding.zw;

    float2 px = float2(d.viewport_size_pixels);
    float2 p = t.pos * px;
    float2 lo = g.xy * px, size = g.zw * px;
    float2 center = lo + size * 0.5;

    // The outline springs in from outside its final position
    float settle = spring(SPRING_DAMPING, progress * SPRING_SPEED * 6.2831853);
    float offset = OUTLINE_INSET + (1.0 - settle) * SPRING_TRAVEL;
    float2 half_size = size * 0.5 - OUTLINE_INSET + (offset - OUTLINE_INSET);
    float dist = rounded_rect_sdf(p, center, max(half_size, float2(1.0)), CORNER_RADIUS);
    float ring = 1.0 - smoothstep(OUTLINE_WIDTH * 0.5 - 0.75, OUTLINE_WIDTH * 0.5 + 0.75, abs(dist + OUTLINE_WIDTH * 0.5));
    float fade = smoothstep(0.0, 0.05, progress) * (1.0 - smoothstep(0.55, 1.0, progress));
    float3 tint = OUTLINE_COLOR.a > 0.0 ? OUTLINE_COLOR.rgb : (d.cursor_color.a > 0.0 ? d.cursor_color.rgb : d.foreground.rgb);

    float inside = rounded_rect_sdf(p, center, size * 0.5, CORNER_RADIUS);
    float3 rgb = color.rgb;
    if (inside > 0.0 && all(t.pos >= d.central_area.xy) && all(t.pos <= d.central_area.xy + d.central_area.zw)) {
        rgb = state_layer(rgb, float3(0.0), INACTIVE_DIM * (1.0 - smoothstep(0.0, 1.0, progress)));
    }
    return float4(state_layer(rgb, tint, ring * fade * OUTLINE_OPACITY), color.a);
}
