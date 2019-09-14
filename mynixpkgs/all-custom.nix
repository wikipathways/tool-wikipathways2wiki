with import <nixpkgs> { config.allowUnfree = true; };
with lib.trivial;
let
  python3Packages = import ./development/python-modules/python-packages.nix;
  nodePackages = import ./development/node-packages/node-packages.nix;
in
mergeAttrs nodePackages {
  python3Packages = python3Packages;

  bash-it = callPackage ./bash-it/default.nix {}; 
  black = callPackage ./black/default.nix {}; 
  composer2nix = import (fetchTarball https://api.github.com/repos/svanderburg/composer2nix/tarball/8453940d79a45ab3e11f36720b878554fe31489f) {}; 
  java-buildpack-memory-calculator = callPackage ./java-buildpack-memory-calculator/default.nix {};
  mediawiki-codesniffer = callPackage ./mediawiki-codesniffer/default.nix {};
  pathvisio = callPackage ./pathvisio/default.nix {};
  perlPackages = callPackage ./perl-packages.nix {}; 
  pgsanity = callPackage ./pgsanity/default.nix {};
  privoxy = callPackage ./privoxy/darwin-service.nix {}; 

  pywikibot = callPackage ./pywikibot/default.nix {
    buildPythonPackage = python37Packages.buildPythonPackage;
  };

  sqlint = callPackage ./sqlint/default.nix {};
  tosheets = callPackage ./tosheets/default.nix {};
  vim = callPackage ./vim/default.nix {};
}
