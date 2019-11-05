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

```
python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./hey.json
```

```
python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./WP4542_103412.json
```

```
python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./WP4542_103412.svg
```

```
./gpml2svg/batch_process_daily_human_approved.sh | tee -a gpml2svg_out.log 2> >(tee -a gpml2svg_err.log >&2)
```

## TODO

Compare `svgo-config.json` vs. `kaavio-svgo-config.json` to determine the best settings for SVGO.

Address this error:
```
Processing WP466
err
Error: malformed path data
    at /nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/parse-svg-path/index.js:45:42
    at String.replace (<anonymous>)
    at parse (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/parse-svg-path/index.js:29:7)
    at new Points (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/point-at-length/index.js:9:41)
    at Object.Points [as createSVGPathCalculator] (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/point-at-length/index.js:8:43)
    at CurvedLine.SVGPath (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/kaavio/src/drawers/edges/index.ts:91:27)
    at new CurvedLine (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/kaavio/src/drawers/edges/index.ts:235:5)
    at Edge.render (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/kaavio/src/components/Edge.tsx:75:11)
    at processChild (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/react-dom/cjs/react-dom-server.node.development.js:3295:18)
    at resolve (/nix/store/fma79c4cqavpnxlp87zipw3vpjbn9lsn-node__at_wikipathways_slash_pvjs-5.0.0/lib/node_modules/@wikipathways/pvjs/node_modules/react-dom/cjs/react-dom-server.node.development.js:3126:5)
Traceback (most recent call last):
  File "gpml2svg/convert.py", line 806, in <module>

    main()
  File "gpml2svg/convert.py", line 800, in main
    theme=args.theme,
  File "gpml2svg/convert.py", line 710, in convert
    json2svg(json_f, path_out, pathway_iri, wp_id, pathway_version, theme)
  File "gpml2svg/convert.py", line 284, in json2svg
    tree = ET.parse(path_out, parser=parser)
  File "src/lxml/etree.pyx", line 3467, in lxml.etree.parse
  File "src/lxml/parser.pxi", line 1839, in lxml.etree._parseDocument
  File "src/lxml/parser.pxi", line 1865, in lxml.etree._parseDocumentFromURL
  File "src/lxml/parser.pxi", line 1769, in lxml.etree._parseDocFromFile
  File "src/lxml/parser.pxi", line 1163, in lxml.etree._BaseParser._parseDocFromFile
  File "src/lxml/parser.pxi", line 601, in lxml.etree._ParserContext._handleParseResultDoc
  File "src/lxml/parser.pxi", line 711, in lxml.etree._handleParseResult
  File "src/lxml/parser.pxi", line 640, in lxml.etree._raiseParseError
  File "daily_human_approved_gpml_2019-11-05/WP466.svg", line 1
lxml.etree.XMLSyntaxError: Document is empty, line 1, column 1
CRITICAL: Exiting due to uncaught exception <class 'lxml.etree.XMLSyntaxError'>
```

## Sync mynixpkgs

The following is safe to ignore. To sync the `mynixpkgs` subtree repo, run:

```
git remote add mynixpkgs git@github.com:ariutta/mynixpkgs.git # if not done already
git subtree pull --prefix mynixpkgs mynixpkgs master --squash
git subtree push --prefix mynixpkgs mynixpkgs master
```
