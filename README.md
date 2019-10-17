# wikipathways2wiki

## Install

1) Install [Nix](https://nixos.org/nix/download.html). 
2) Run `nix-shell` from this directory to install dependencies and enter the dev environment.
3) Configure Pywikibot: `pwb.py generate_user_files` (respond to the prompts)

Now you can start developing and testing files like `./gpml2svg/convert.py`.

## Sync mynixpkgs

The following is safe to ignore. To sync the `mynixpkgs` subtree repo, run:
```
git remote add mynixpkgs git@github.com:ariutta/mynixpkgs.git # if not done already
git subtree pull --prefix mynixpkgs mynixpkgs master --squash
git subtree push --prefix mynixpkgs mynixpkgs master
```
