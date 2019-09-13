# Nix Definitions for Selected Node.js Packages

## How to Update

You can update the Nix definitions for these Node.js packages.

Install [`node2nix`](https://github.com/svanderburg/node2nix).

(Optional) Update the list of package names in each `node-packages-<v#>.json`
file and/or set or update the version number for any of the packages.

Run the update script:
```
./update.sh
```

As of 13 September 2019, here are the Node.js versions:
* node2nix default: 8
* `nixos`: 8, 10 and 11
* `nixpkgs`: 10, 11 and 12

We'll keep this in sync with `nixpkgs`.

## Test

```sh
nix-build -E 'with import <nixpkgs> { }; (import ./node-packages.nix).pvjs'
./result/bin/pvjs --help
```

Or for a specific version of Node.js:

```
nix-build -E 'with import <nixpkgs> { }; (import ./node-packages.nix).nodePackages_10_x."@wikipathways/pvjs"'
./result/bin/pvjs --help
```
