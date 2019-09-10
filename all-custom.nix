with import <nixpkgs> { config.allowUnfree = true; };

let
  python3Packages = import ./development/python-modules/python-packages.nix;
  nodePackages_10_x = callPackage ./development/node-packages/default-v10.nix {
    nodejs = pkgs.nodejs-10_x;
  };
  nodePackages = nodePackages_10_x;
in
{
  python3Packages = python3Packages;
  nodePackages = nodePackages;
  depcheck = nodePackages.depcheck;
  gpml2pvjson = nodePackages.gpml2pvjson;
  bridgedb = nodePackages.bridgedb;
  pvjs = nodePackages."@wikipathways/pvjs";

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
