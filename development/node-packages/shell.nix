{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [
    pkgs.nodePackages.node2nix

    # node-gyp dependencies (node-gyp compiles C/C++ Addons)
    #   see https://github.com/nodejs/node-gyp#on-unix
    pkgs.python2
  ] ++ (if pkgs.stdenv.isDarwin then [
    # more node-gyp dependencies
    # XCode Command Line Tools
    # TODO: do we need cctools?
    #pkgs.darwin.cctools
  ] else [
    # more node-gyp dependencies
    pkgs.gnumake

    # gcc and binutils disagree on the version of a
    # dependency, so we need to binutils-unwrapped.
    pkgs.gcc # also provides cc
    pkgs.binutils-unwrapped # provides ar
  ]);
  shellHook = ''
    if [ ! -f "$SSL_CERT_FILE" ]; then
      candidate_ssl_cert_file="/etc/ssl/certs/ca-bundle.crt"
      if [ -f "$candidate_ssl_cert_file" ]; then
        export SSL_CERT_FILE="$candidate_ssl_cert_file"
      else
        echo "Cannot find a valid SSL certificate file. curl will not work." 1>&2
      fi
    fi
  '';
}
