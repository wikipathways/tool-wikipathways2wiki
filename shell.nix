{ pkgs ? import <nixpkgs> {} }:
with pkgs.lib.strings;
let
  deps = import ./deps.nix;
  shellHookBase = fileContents ./shell-hook.sh;
in
  pkgs.mkShell {
    buildInputs = deps ++ [ pkgs.python3Packages.pycodestyle pkgs.python3Packages.rope ];
    shellHook = concatStringsSep "\n" [
      shellHookBase
      ''
        # To open as a jupyter notebook:
        # jupyter notebook --port=8888 --notebook-dir ./
      ''
    ];
}
