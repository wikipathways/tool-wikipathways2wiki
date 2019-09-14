# Nix Definitions for Selected Node.js Packages

Based on [`node2nix`](https://github.com/svanderburg/node2nix).

As of 13 September 2019, here are the Node.js versions:
* node2nix default: 8
* `nixos`: 8, 10 and 11
* `nixpkgs`: 10, 11 and 12

We'll keep this in sync with `nixpkgs`.

## How to Update

Steps for updating the Nix definitions for these Node.js packages:

1) `cd` to this directory.

2) If you have not setup `direnv` to [work with](https://github.com/direnv/direnv/wiki/Nix) `nix-shell`,
enter the development environment by running `nix-shell`.

3) (*Optional*) Update the list of package names in each `node-packages-<v#>.json`
file and/or set or update the version number for any of the packages.

4) Run the update script:
```
./update.sh
```

## Test

Build a package using default version of Node.js:

```sh
nix-build -E 'with import <nixpkgs> { }; (import ./node-packages.nix).svgo'
./result/bin/svgo --help
```

Or build for a specific version of Node.js:

```
nix-build -E 'with import <nixpkgs> { }; (import ./node-packages.nix).nodePackages_12_x.svgo'
./result/bin/svgo --help
```
