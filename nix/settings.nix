# The Material You look and feel of Kitty Material You as kitty.conf settings.
# The home-manager module uses these, extras/material-you.conf has the same
# settings for people who do not use Nix (`nix flake check` keeps them in sync).
{
  shapes = {
    # Rounded block/hollow cursors, capsule shaped beam and underline cursors
    cursor_corner_radius = "0.3";
    # Windows are rounded cards with a little space around them
    window_border_radius = "12pt";
    window_border_width = "1pt";
    window_margin_width = "3";
    draw_minimal_borders = "no";
    # Pill shaped tabs
    tab_bar_style = "material";
    tab_bar_margin_width = "6";
    tab_bar_margin_height = "6 4";
    tab_title_template = "{index}  {title}";
    active_tab_font_style = "bold";
    inactive_tab_font_style = "normal";
    # A slim, rounded scrollbar
    scrollbar = "scrolled";
    scrollbar_radius = "0.5";
  };

  motion = {
    # A jelly like cursor trail driven by an M3 Expressive spring
    cursor_trail = "1";
    cursor_trail_decay = "0.1 0.35";
    cursor_trail_spring = "m3-expressive-fast";
    cursor_trail_start_threshold = "2";
    # The cursor fades in and out with an M3 effects spring
    cursor_blink_interval = "0.6 m3-spring-effects";
    cursor_stop_blinking_after = "15";
    visual_bell_duration = "0.3 m3-emphasized-decelerate";
    # Color scheme changes (myt apply, light/dark switches) morph in OKLab
    color_transition = "0.5 m3-spring-effects";
  };

  shaders = {
    # Jelly cursor trail, touch ripples and a springy focus indicator
    custom_shaders = "material-you";
  };
}
