{ pkgs ? import <nixpkgs> {} }:
with pkgs.lib.strings;
let
  deps = import ./deps.nix;
  shellHookBase = fileContents ./shell-hook-base.sh;
in
  pkgs.mkShell {
    buildInputs = deps ++ [ pkgs.python3Packages.pycodestyle pkgs.python3Packages.rope ];
    shellHook = concatStringsSep "\n" [
      shellHookBase
      ''
      # this is needed in order that tools like curl and git can work with SSL
      if [ ! -f "$SSL_CERT_FILE" ] || [ ! -f "$NIX_SSL_CERT_FILE" ]; then
        candidate_ssl_cert_file=""
        if [ -f "$SSL_CERT_FILE" ]; then
          candidate_ssl_cert_file="$SSL_CERT_FILE"
        elif [ -f "$NIX_SSL_CERT_FILE" ]; then
          candidate_ssl_cert_file="$NIX_SSL_CERT_FILE"
        else
          candidate_ssl_cert_file="/etc/ssl/certs/ca-bundle.crt"
        fi
        if [ -f "$candidate_ssl_cert_file" ]; then
            export SSL_CERT_FILE="$candidate_ssl_cert_file"
            export NIX_SSL_CERT_FILE="$candidate_ssl_cert_file"
        else
          echo "Cannot find a valid SSL certificate file. curl will not work." 1>&2
        fi
      fi
      ''
    ];
}
