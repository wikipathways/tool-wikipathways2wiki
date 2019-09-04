with import <nixpkgs> { config.allowUnfree = true; };
let
  pythonEnv = import ./mynixpkgs/environments/python.nix;
  custom = import ./mynixpkgs/all-custom.nix;
  pathvisio = callPackage ./mynixpkgs/pathvisio/default.nix {
    organism="Homo sapiens";
    headless=true;
    genes=false;
    interactions=false;
    metabolites=false;
    # NOTE: this seems high, but I got an error
    #       regarding memory when it was lower.
    memory="2048m";
  };
in
  pythonEnv ++ [
    (pkgs.python3.withPackages (p: [
      p.requests
      p.ipython
      p.jupyter
      p.matplotlib
      custom.pywikibot
    ]))

    pathvisio
    custom.bridgedb
    custom.gpml2pvjson
    custom.pvjs

    pkgs.coreutils
    pkgs.xmlstarlet
    pkgs.bc
  ] ++ (if stdenv.isDarwin then [

  ] else [

  ])
