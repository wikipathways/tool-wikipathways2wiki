{ pkgs ? import <nixpkgs> {} }:
let
  deps = import ./deps.nix;
in
  pkgs.mkShell {
    buildInputs = deps;
    shellHook = ''
      #export PATH="$HOME/Documents/safer-npm:$PATH"
    '';
}
