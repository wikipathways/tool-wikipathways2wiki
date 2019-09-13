with import <nixpkgs> { config.allowUnfree = true; };
let
  nodePackages_8_x = callPackage ./default-v8.nix {
    nodejs = pkgs.nodejs-8_x;
  };
  nodePackages_10_x = callPackage ./default-v10.nix {
    nodejs = pkgs.nodejs-10_x;
  };
  nodePackages_12_x = callPackage ./default-v12.nix {
    nodejs = pkgs.nodejs-12_x;
  };
  nodePackages = nodePackages_10_x;
in
{
  nodePackages = nodePackages;
  nodePackages_8_x = nodePackages_8_x;
  nodePackages_10_x = nodePackages_10_x;
  nodePackages_12_x = nodePackages_12_x;

  depcheck = nodePackages.depcheck;
  typescript = nodePackages.typescript;
  gpml2pvjson = nodePackages.gpml2pvjson;
  bridgedb = nodePackages.bridgedb;
  pvjs = nodePackages."@wikipathways/pvjs";
  svgo = nodePackages.svgo;
}
