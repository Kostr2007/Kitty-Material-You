# home-manager module: Kitty Material You, integrated with Material-You-Terminal
# (https://github.com/Kostr2007/Material-You-Terminal) when its module is loaded.
{ self, material-you-terminal }:

{ config, lib, pkgs, options, ... }:

let
  inherit (lib) mkOption mkEnableOption mkIf mkMerge mkDefault mkOverride types literalExpression;

  cfg = config.programs.kitty-material-you;
  material = import ./settings.nix;
  system = pkgs.stdenv.hostPlatform.system;

  # Material-You-Terminal's home-manager module is loaded (homeManagerModules.default does that)
  hasMyt = options ? programs && options.programs ? material-you-terminal;
  mytEnabled = hasMyt && cfg.materialYouTerminal.enable && config.programs.material-you-terminal.enable;

  # Above the mkDefault of Material-You-Terminal, below plain user settings
  mkMaterial = mkOverride 900;

  settings =
    lib.optionalAttrs cfg.shapes.enable (material.shapes // {
      cursor_corner_radius = toString cfg.shapes.cursorCornerRadius;
      window_border_radius = cfg.shapes.windowCornerRadius;
    })
    // lib.optionalAttrs cfg.motion.enable (material.motion // {
      cursor_trail_spring = cfg.motion.cursorTrailSpring;
      color_transition = cfg.motion.colorTransition;
    })
    // lib.optionalAttrs (cfg.shaders != [ ]) {
      custom_shaders = lib.concatStringsSep " " cfg.shaders;
    };
in
{
  options.programs.kitty-material-you = {
    enable = mkEnableOption "Kitty Material You, kitty with Material Design 3 shapes, spring motion and dynamic color";

    package = mkOption {
      type = types.package;
      default = self.packages.${system}.default;
      defaultText = literalExpression "kitty-material-you.packages.\${system}.default";
      description = "The Kitty Material You package, used as `programs.kitty.package`.";
    };

    shapes = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Rounded cursors, rounded window cards, pill shaped tabs and a rounded scrollbar.";
      };
      cursorCornerRadius = mkOption {
        type = types.numbers.between 0 0.5;
        default = 0.3;
        description = "Corner radius of the cursor in units of the cell width, 0.5 makes a pill.";
      };
      windowCornerRadius = mkOption {
        type = types.str;
        default = "12pt";
        description = "Corner radius of window borders (`window_border_radius`).";
      };
    };

    motion = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = ''
          Spring physics: a jelly like cursor trail, spring eased cursor blinking
          and animated color scheme changes.
        '';
      };
      cursorTrailSpring = mkOption {
        type = types.str;
        default = "m3-expressive-fast";
        example = "700 0.7";
        description = ''
          Spring of the cursor trail: an M3 spring token (`m3-spring-fast`,
          `m3-expressive-default`, ...) or a stiffness and damping ratio.
          `none` uses kitty's classic exponential trail.
        '';
      };
      colorTransition = mkOption {
        type = types.str;
        default = "0.5 m3-spring-effects";
        example = "0.45 m3-emphasized-decelerate";
        description = ''
          Duration in seconds and easing of the color morph when the color
          scheme changes, `0` to switch instantly. With Material-You-Terminal
          this replaces the morphing done by `myt`, kitty animates the colors
          itself at the full frame rate.
        '';
      };
    };

    shaders = mkOption {
      type = types.listOf types.str;
      default = [ "material-you" ];
      example = [ "m3-cursor-trail" "m3-ripple" ];
      description = ''
        Custom shaders (`custom_shaders`): `material-you` combines the jelly
        cursor trail (`m3-cursor-trail`), touch ripples (`m3-ripple`) and the
        focus indicator (`m3-focus`). An empty list disables custom shaders.
      '';
    };

    theme = mkOption {
      type = types.enum [ "dark" "light" "none" ];
      default = "dark";
      description = ''
        The bundled M3 baseline color scheme, used only when the colors do not
        come from Material-You-Terminal.
      '';
    };

    materialYouTerminal.enable = mkOption {
      type = types.bool;
      default = true;
      description = ''
        Theme kitty, fish, starship and fastfetch with Material-You-Terminal
        (colors from your wallpaper, `myt apply`). Requires its home-manager
        module, which `homeManagerModules.default` of this flake includes.
      '';
    };
  };

  config = mkIf cfg.enable (mkMerge [
    {
      programs.kitty = {
        enable = true;
        package = mkDefault cfg.package;
        settings = lib.mapAttrs (_: mkMaterial) settings;
        extraConfig = mkIf (!mytEnabled && cfg.theme != "none") ''
          # kitty-material-you
          include ${../extras/themes}/material-you-${cfg.theme}.conf
        '';
      };
    }

    (lib.optionalAttrs hasMyt (mkIf cfg.materialYouTerminal.enable {
      programs.material-you-terminal = {
        enable = mkDefault true;
        # kitty morphs the colors itself, so myt only has to send the new palette once
        animations.transitionMs = mkIf (cfg.motion.enable && cfg.motion.colorTransition != "0") (mkDefault 0);
      };
    }))
  ]);
}
