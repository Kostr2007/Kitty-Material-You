#language slang 2026
// Copyright (C) 2026 Kitty Material You contributors
// Distributed under terms of the GPLv3 license.
//
// Material You cursor trail: the trail is drawn as a soft, rounded blob of
// the cursor color (the primary color of a Material You scheme) that thins
// out towards its tail. Pair it with cursor_trail_spring in kitty.conf, for
// example `cursor_trail_spring m3-expressive-fast`, so the blob stretches and
// wobbles like jelly as it follows the cursor.

import kitty_custom_shader_types;

// Corner radius of the blob, in pixels.
static const float CORNER_RADIUS = 6.0;
// Width of the anti-aliased edge, in pixels.
static const float EDGE_SOFTNESS = 1.5;
// Opacity at the tail end of the trail, relative to the head (which is fully opaque).
static const float TAIL_OPACITY = 0.15;
// Overall opacity of the trail.
static const float OPACITY = 0.85;

// Signed distance (negative inside) from p to the polygon v0..v3. Works for
// the convex and the slightly concave quads a stretching trail produces.
float
quad_sdf(float2 p, float2 v0, float2 v1, float2 v2, float2 v3) {
    float2 v[4] = { v0, v1, v2, v3 };
    float d = dot(p - v[0], p - v[0]);
    float s = 1.0;
    for (int i = 0, j = 3; i < 4; j = i, i++) {
        float2 e = v[j] - v[i];
        float2 w = p - v[i];
        float2 b = w - e * clamp(dot(w, e) / max(dot(e, e), 1e-6), 0.0, 1.0);
        d = min(d, dot(b, b));
        bool3 c = bool3(p.y >= v[i].y, p.y < v[j].y, e.x * w.y > e.y * w.x);
        if (all(c) || all(!c)) s = -s;
    }
    return s * sqrt(d);
}

public float4
fragment_main(float4 color, KittyTextures t, KittyCustomShaderData d) {
    float opacity = d.cursor_trail_color.a * OPACITY;
    if (opacity <= 0.0) return color;

    // Work in pixels so that the shape is not distorted by the aspect ratio
    float2 px = float2(d.viewport_size_pixels);
    float2 p = t.pos * px;
    float2 c0 = float2(d.cursor_trail_corners_x.x, d.cursor_trail_corners_y.x) * px; // top-right
    float2 c1 = float2(d.cursor_trail_corners_x.y, d.cursor_trail_corners_y.y) * px; // bottom-right
    float2 c2 = float2(d.cursor_trail_corners_x.z, d.cursor_trail_corners_y.z) * px; // bottom-left
    float2 c3 = float2(d.cursor_trail_corners_x.w, d.cursor_trail_corners_y.w) * px; // top-left

    // Shrink the polygon by the radius and grow it back, rounding its corners
    float2 center = (c0 + c1 + c2 + c3) * 0.25;
    float radius = min(CORNER_RADIUS, 0.5 * min(length(c0 - c3), length(c0 - c1)));
    float2 inset[4] = { c0, c1, c2, c3 };
    for (int i = 0; i < 4; i++) {
        float2 v = center - inset[i];
        float l = length(v);
        inset[i] += v / max(l, 1e-4) * min(radius, l);
    }
    float dist = quad_sdf(p, inset[0], inset[1], inset[2], inset[3]) - radius;
    float coverage = 1.0 - smoothstep(-EDGE_SOFTNESS, EDGE_SOFTNESS, dist);
    if (coverage <= 0.0) return color;

    // Fade towards the tail: the head is the cursor itself
    float4 e = d.cursor_trail_edge * float4(px.x, px.x, px.y, px.y);
    float2 head = float2((e.x + e.y) * 0.5, (e.z + e.w) * 0.5);
    float far = 1.0;
    for (int i = 0; i < 4; i++) far = max(far, length(float2(inset[i]) - head));
    float along = clamp(length(p - head) / far, 0.0, 1.0);
    opacity *= coverage * lerp(1.0, TAIL_OPACITY, smoothstep(0.0, 1.0, along));

    // Leave the cursor itself alone so it renders cleanly on top
    float inside_cursor = step(e.x, p.x) * step(p.x, e.y) * step(e.w, p.y) * step(p.y, e.z);
    opacity *= 1.0 - inside_cursor;

    return float4(lerp(color.rgb, d.cursor_trail_color.rgb, opacity), color.a);
}
