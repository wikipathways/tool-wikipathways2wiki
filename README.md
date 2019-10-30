# wikipathways2wiki

## Install

1. Install [Nix](https://nixos.org/nix/download.html).
2. Run `nix-shell` from this directory to install dependencies and enter the dev environment.
3. Configure Pywikibot: `pwb.py generate_user_files` (respond to the prompts)

Now you can start developing and testing files like `./gpml2svg/convert.py`.

## Usage

Sample commands:

```
rm WP4542_*.* && python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_104788.gpml ./WP4542_104788.svg && xmllint --pretty 1 WP4542_104788.svg > WP4542_104788.pretty1.svg && xmllint --pretty 2 WP4542_104788.svg > WP4542_104788.pretty2.svg
```

## Sync mynixpkgs

The following is safe to ignore. To sync the `mynixpkgs` subtree repo, run:

```
git remote add mynixpkgs git@github.com:ariutta/mynixpkgs.git # if not done already
git subtree pull --prefix mynixpkgs mynixpkgs master --squash
git subtree push --prefix mynixpkgs mynixpkgs master
```
