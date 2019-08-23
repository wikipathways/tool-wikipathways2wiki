# wikipathways2wiki

## Install

First install [Nix](https://nixos.org/nix/download.html). Then run `nix-shell` from this directory to install dependencies. Now you can start developing and test files like `./gpml2svg/convert.py`.

## Sync mynixpkgs

Sync subtree repo:
```
git subtree pull --prefix mynixpkgs mynixpkgs master --squash
git subtree push --prefix mynixpkgs mynixpkgs master
```
