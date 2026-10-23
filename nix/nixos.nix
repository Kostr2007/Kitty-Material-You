# NixOS module: installs Kitty Material You and Material-You-Terminal system
# wide and, with home-manager as a NixOS module, makes the home-manager module
# available to every user (`home-manager.users.<name>.programs.kitty-material-you`).
{ self, material-you-terminal }:

{ config, lib, pkgs, options, ... }:

let
  cfg = config.programs.kitty-material-you;
in
{
  # Also provides the Material-You-Terminal home-manager module to all users
  imports = [ material-you-terminal.nixosModules.default ];

  options.programs.kitty-material-you = {
    enable = lib.mkEnableOption ''
      Kitty Material You system wide, together with Material-You-Terminal (fish
      as an available shell, the `myt` tool and a Nerd Font). Per user settings
      live in home-manager: `home-manager.users.<name>.programs.kitty-material-you`'';

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "kitty-material-you.packages.\${system}.default";
      description = "The Kitty Material You package.";
    };
  };

  config = lib.mkMerge [
    (lib.optionalAttrs (options ? home-manager) {
      home-manager.sharedModules = [ self.homeManagerModules.kitty-material-you ];
    })

    (lib.mkIf cfg.enable {
      environment.systemPackages = [ cfg.package ];
      programs.material-you-terminal.enable = lib.mkDefault true;
    })
  ];
}
