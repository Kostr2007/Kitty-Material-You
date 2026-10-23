{
  description = "Kitty Material You: the kitty terminal with Material Design 3 motion, shapes and dynamic color";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # Palette generation (matugen), fish/starship/fastfetch theming and the `myt` tool.
    material-you-terminal.url = "git+https://github.com/Kostr2007/Material-You-Terminal";
    material-you-terminal.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, material-you-terminal }:
    let
      inherit (nixpkgs) lib;
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # The kitty version this fork is based on (see kitty/constants.py).
      upstreamVersion =
        let
          re = "version: Version = Version\\(([0-9]+), ([0-9]+), ([0-9]+)\\)";
          line = lib.findFirst (l: builtins.match re l != null) null
            (lib.splitString "\n" (builtins.readFile ./kitty/constants.py));
        in
        lib.concatStringsSep "." (builtins.match re line);

      # Everything except the Nix packaging, so editing nix/ does not rebuild kitty.
      src = lib.fileset.toSource {
        root = ./.;
        fileset = lib.fileset.difference ./. (lib.fileset.unions [
          ./nix
          ./flake.nix
          (lib.fileset.maybeMissing ./flake.lock)
          (lib.fileset.maybeMissing ./result)
        ]);
      };

      mkKitty = pkgs: args: pkgs.callPackage ./nix/package.nix ({
        inherit src;
        version = upstreamVersion;
      } // args);
    in
    {
      overlays.default = final: _prev: {
        kitty-material-you = mkKitty final { };
      };

      packages = forAllSystems (pkgs:
        let kitty = mkKitty pkgs { }; in {
          default = kitty;
          kitty-material-you = kitty;
          # Same build without running kitty's test suite (much faster).
          kitty-material-you-no-tests = kitty.overrideAttrs { doCheck = false; doInstallCheck = false; };
          # The `myt` tool of Material-You-Terminal
          myt = material-you-terminal.packages.${pkgs.stdenv.hostPlatform.system}.default;
        });

      apps = forAllSystems (pkgs: {
        # `nix run github:Kostr2007/Kitty-Material-You`
        default = {
          type = "app";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.default}/bin/kitty";
          meta.description = "Run Kitty Material You";
        };
      });

      homeManagerModules = {
        # Kitty Material You together with the Material-You-Terminal module
        default = {
          imports = [
            self.homeManagerModules.kitty-material-you
            material-you-terminal.homeManagerModules.default
          ];
        };
        # Only Kitty Material You, it integrates with Material-You-Terminal when
        # you import that module yourself
        kitty-material-you = import ./nix/home-manager.nix { inherit self material-you-terminal; };
      };

      nixosModules = {
        default = self.nixosModules.kitty-material-you;
        kitty-material-you = import ./nix/nixos.nix { inherit self material-you-terminal; };
      };

      checks = forAllSystems (pkgs: import ./nix/checks.nix { inherit pkgs self material-you-terminal; });

      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);

      devShells = forAllSystems (pkgs: {
        # `nix develop` then `python3 setup.py build && python3 test.py`
        default = pkgs.mkShell {
          inputsFrom = [ self.packages.${pkgs.stdenv.hostPlatform.system}.default ];
          packages = with pkgs; [ python3Packages.pillow nixpkgs-fmt matugen ];
          shellHook = ''
            export GOTOOLCHAIN=local
          '';
        };
      });
    };
}
