with import <nixpkgs> { config.allowUnfree = true; };
let
  deps = import ./deps.nix;
in deps
