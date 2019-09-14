#! /usr/bin/env bash

set -e

# see https://stackoverflow.com/a/246128/5354298
get_script_dir() { cd "$( dirname "${BASH_SOURCE[0]}" )"; echo "$( pwd )"; }

# see https://stackoverflow.com/questions/592620/check-if-a-program-exists-from-a-bash-script
is_installed() { hash $1 2>/dev/null || { false; } }
exit_if_not_installed() { is_installed $1 || { echo >&2 "I require $1 but it's not installed. Aborting. See https://nixos.org/nix/manual/#sec-prerequisites-source."; exit 1; } }
function ensure_installed() {
	if ! is_installed $1 ; then
		echo "Installing missing dependency $1...";
		$2;
	fi
}

SCRIPT_DIR="$(get_script_dir)"

echo "installing/updating node packages"

echo "ensuring nix is installed and up to date...";
exit_if_not_installed nix-channel;
exit_if_not_installed nix-env;
nix-channel --update

ensure_installed node "nix-env -f <nixpkgs> -i nodejs";
ensure_installed node2nix "nix-env -f <nixpkgs> -iA nodePackages.node2nix";
ensure_installed jq "nix-env -f <nixpkgs> -i jq";

cd "$SCRIPT_DIR";

rm -f node-env.nix;

node2nix --nodejs-10 -i node-packages-v10.json -o node-packages-v10.nix -c composition-v10.nix
# not working for node 12 at present. see https://github.com/svanderburg/node2nix/issues/153
node2nix --nodejs-12 -i node-packages-v12.json -o node-packages-v12.nix -c composition-v12.nix

# TODO: look at whether to use a lock file somehow.
