#!/usr/bin/env python3

# python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./hey.json
# python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./WP4542_103412.json
# python3 gpml2svg/convert.py ~/Documents/WP4542/WP4542_103412.gpml ./WP4542_103412.svg

import xml.etree.ElementTree as ET
import argparse
import csv
import json
import re
import shlex
import subprocess

from os import path, rename
import requests
import pywikibot
from pywikibot.data import sparql

WPID_RE = re.compile(r"WP\d+")
WPID_REV_RE = re.compile(r"(WP\d+)_(\d+)")
LEADING_DOT_RE = re.compile(r"^\.")
NON_ALPHANUMERIC_RE = re.compile(r"\W")
LATEST_GPML_VERSION = "2013a"

BRIDGEDB_REPO_BASE = "https://raw.githubusercontent.com/bridgedb/BridgeDb/master"
BRIDGEDB2WD_PROPS_REQUEST = requests.get(
    BRIDGEDB_REPO_BASE + "/org.bridgedb.bio/resources/org/bridgedb/bio/datasources.tsv"
)
BRIDGEDB2WD_PROPS = dict()
for row in csv.DictReader(BRIDGEDB2WD_PROPS_REQUEST.text.splitlines(), delimiter="\t"):
    BRIDGEDB2WD_PROPS[row["datasource_name"]] = row["wikidata_property"]


def convert2json(
    path_in,
    path_out,
    pathway_iri,
    wp_id,
    pathway_version,
    root,
    ns,
    dir_out,
    stub_out,
    wd_sparql,
):
    """Convert from GPML to JSON.

    Keyword arguments:
    path_in -- path in, e.g., ./WP4542_103412.gpml
    path_out -- path out, e.g., ./WP4542_103412.svg
    pathway_iri -- e.g., http://identifiers.org/wikipathways/WP4542
    wp_id -- e.g., WP4542
    pathway_version -- e.g., 103412
    root -- parsed GPML
    ns -- namespaces used when parsing GPML
    dir_out -- directory out
    stub_out -- filename w/out extension
    wd_sparql -- wikidata object for making queries
    """
    organism = root.attrib.get("Organism")
    # TODO: bridgedbjs fails when no xrefs are present.
    # Update bridgedbjs to do this check:
    xref_identifiers = root.findall("./gpml:DataNode/gpml:Xref[@ID]", ns)
    # bridgedbjs also fails when an identifier is something like
    # 'undefined'. Should it ignore datasources/identifiers it doesn't
    # recognize and just keep going?

    gpml2pvjson_cmd = (
        f"gpml2pvjson --id {pathway_iri} --pathway-version {pathway_version}"
    )
    with open(path_in, "r") as f_in:
        with open(path_out, "w") as f_out:
            gpml2pvjson_ps = subprocess.Popen(
                shlex.split(gpml2pvjson_cmd), stdin=f_in, stdout=f_out, shell=False
            )
            gpml2pvjson_ps.communicate()[0]

    if (not organism) or (not xref_identifiers):
        print("No xrefs to process.")
    else:
        pre_bridgedb_json_f = f"{dir_out}/{stub_out}.pre_bridgedb.json"
        rename(path_out, pre_bridgedb_json_f)

        bridgedb_cmd = f"""bridgedb xrefs -f json \
            -i '.entitiesById[].type' "{organism}" \
            '.entitiesById[].xrefDataSource' \
            '.entitiesById[].xrefIdentifier' \
            ChEBI P683 Ensembl P594 "Entrez Gene" P351 HGNC P353 HMDB P2057 Wikidata
        """
        with open(pre_bridgedb_json_f, "r") as f_in:
            with open(path_out, "w") as f_out:
                bridgedb_ps = subprocess.Popen(
                    shlex.split(bridgedb_cmd), stdin=f_in, stdout=f_out, shell=False
                )
                bridgedb_ps.communicate()[0]

        no_wikidata_xrefs_by_bridgedb_key = dict()
        entity_ids_by_bridgedb_key = dict()
        with open(path_out, "r") as json_f:
            pathway_data = json.load(json_f)
            entities_by_id = pathway_data["entitiesById"]
            for entity in entities_by_id.values():
                if (
                    "xrefIdentifier" in entity
                    and "xrefDataSource" in entity
                    and entity["xrefDataSource"] in BRIDGEDB2WD_PROPS
                    and len(
                        [
                            entity_type
                            for entity_type in entity["type"]
                            if entity_type.startswith("Wikidata:")
                        ]
                    )
                    == 0
                ):
                    entity_id = entity["id"]
                    datasource = entity["xrefDataSource"]
                    xref_identifier = entity["xrefIdentifier"]
                    bridgedb_key = NON_ALPHANUMERIC_RE.sub(
                        "", datasource + xref_identifier
                    )
                    no_wikidata_xrefs_by_bridgedb_key[bridgedb_key] = [
                        datasource,
                        xref_identifier,
                    ]
                    if bridgedb_key not in entity_ids_by_bridgedb_key:
                        entity_ids_by_bridgedb_key[bridgedb_key] = [entity_id]
                    else:
                        entity_ids_by_bridgedb_key[bridgedb_key].append(entity_id)

            # Add Wikidata ids
            # TODO rewrite JavaScript file ./other/js/add_wd_ids as a Python script
            # will require using a Python Wikidata client library.
            # add_wd_ids_cmd = f"add_wd_ids {path_out}"
            # subprocess.run(shlex.split(add_wd_ids_cmd))

            wd_pathway_id_result = wd_sparql.query(
                '''
SELECT ?item WHERE {
?item wdt:P2410 "'''
                + wp_id
                + """" .
SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}"""
            )

            wikidata_pathway_iri = wd_pathway_id_result["results"]["bindings"][0][
                "item"
            ]["value"]
            wikidata_pathway_identifier = wikidata_pathway_iri.replace(
                "http://www.wikidata.org/entity/", ""
            )
            print(f"wikidata_pathway_iri: {wikidata_pathway_iri}")
            print(f"wikidata_pathway_identifier: {wikidata_pathway_identifier}")

            # TODO: get xrefs from JSON.
            # convert datasource to a wikidata property
            # query wikidata via sparql to get qurls

            headings = []
            queries = []
            for i, xref in enumerate(no_wikidata_xrefs_by_bridgedb_key.values()):
                [datasource, xref_identifier] = xref
                heading = "?" + NON_ALPHANUMERIC_RE.sub(
                    "", datasource + xref_identifier
                )
                headings.append(heading)
                wd_prop = BRIDGEDB2WD_PROPS[datasource]
                queries.append(f'{heading} wdt:{wd_prop} "{xref_identifier}" .')
            headings_str = " ".join(headings)
            queries_str = (
                "WHERE { "
                + " ".join(queries)
                + ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
            )
            xref_query = f"SELECT {headings_str} {queries_str}"
            xref_result = wd_sparql.query(xref_query)

            bridgedb_keys = xref_result["head"]["vars"]
            for binding in xref_result["results"]["bindings"]:
                for bridgedb_key in bridgedb_keys:
                    # TODO: are any of the values lists, not strings?
                    wd_xref_identifier = binding[bridgedb_key]["value"].replace(
                        "http://www.wikidata.org/entity/", ""
                    )
                    for entity_id in entity_ids_by_bridgedb_key[bridgedb_key]:
                        entities_by_id[entity_id]["type"].append(
                            f"Wikidata:{wd_xref_identifier}"
                        )
            pre_wd_json_f = f"{dir_out}/{stub_out}.pre_wd.json"
            rename(path_out, pre_wd_json_f)
            with open(path_out, "w") as f_out:
                json.dump(pathway_data, f_out)


def convert(path_in, path_out, pathway_iri, wp_id, pathway_version, scale=100):
    """Convert from GPML to another format like SVG.

    Keyword arguments:
    path_in -- path in, e.g., ./WP4542_103412.gpml
    path_out -- path out, e.g., ./WP4542_103412.svg
    pathway_iri -- e.g., http://identifiers.org/wikipathways/WP4542
    pathway_version -- e.g., 103412
    scale -- scale to use when converting to PNG (default 100)"""
    if not path.exists(path_in):
        raise Exception(f"Missing file '{path_in}'")

    if path.exists(path_out):
        print(f"File {path_out} already exists. Skipping.")
        return True

    dir_in = path.dirname(path_in)
    base_in = path.basename(path_in)
    [stub_in, ext_in_with_dot] = path.splitext(base_in)
    # get rid of the leading dot
    # ext_in = LEADING_DOT_RE.sub("", ext_in_with_dot)

    dir_out = path.dirname(path_out)
    base_out = path.basename(path_out)
    [stub_out, ext_out_with_dot] = path.splitext(base_out)
    # get rid of the leading dot
    ext_out = LEADING_DOT_RE.sub("", ext_out_with_dot)

    gpml_f = f"{dir_in}/{stub_in}.gpml"

    ns = {"gpml": "http://pathvisio.org/GPML/2013a"}

    ET.register_namespace("", "http://pathvisio.org/GPML/2013a")

    tree = ET.parse(gpml_f)
    root = tree.getroot()

    if not root:
        raise Exception("no root element")
    if not root.tag:
        raise Exception("no root tag")

    gpml_version = re.sub(r"{http://pathvisio.org/GPML/(\w+)}Pathway", r"\1", root.tag)
    if gpml_version != LATEST_GPML_VERSION:
        old_f = f"{dir_in}/{stub_in}.{gpml_version}.gpml"
        rename(gpml_f, old_f)
        subprocess.run(shlex.split(f"pathvisio convert {old_f} {gpml_f}"))

    # trying to get wd ids via sparql via pywikibot
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()  # this is a DataSite object
    wd_sparql = sparql.SparqlQuery(
        endpoint="https://query.wikidata.org/sparql", repo=repo
    )
    # (self, endpoint=None, entity_url=None, repo=None, 2 max_retries=None, retry_wait=None)

    if ext_out in ["gpml", "owl", "pdf", "pwf", "txt"]:
        subprocess.run(shlex.split(f"pathvisio convert {path_in} {path_out}"))
    elif ext_out == "png":
        # TODO: look at using --scale as an option (instead of an argument),
        #       for both pathvisio and gpmlconverter.
        # TODO: move the setting of a default value for scale into
        # pathvisio instead of here.
        subprocess.run(shlex.split(f"pathvisio convert {path_in} {path_out} {scale}"))
        # Use interlacing? See https://github.com/PathVisio/pathvisio/issues/78
        # It's probably not worthwhile. If we did it, we would need to install
        # imagemagick and then run this:
        #     mv "$path_out" "$path_out.noninterlaced.png"
        #     convert -interlace PNG "$path_out.noninterlaced.png" "$path_out"
    elif ext_out in ["json", "jsonld"]:
        convert2json(
            path_in,
            path_out,
            pathway_iri,
            wp_id,
            pathway_version,
            root,
            ns,
            dir_out,
            stub_out,
            wd_sparql,
        )
    elif ext_out in ["svg", "pvjssvg"]:
        #############################
        # SVG
        #############################
        # TODO convert the following sh script to Python
        """
          bare_stub_out="${base_out%%.*}"
        #  # For now, assume no inputs specify plain or dark
        #  all_exts_out="${base_out#*.}"
        #  second_ext_out="${all_exts_out%.*}"
        #  third_extension_out="${second_ext_out%.*}"

          json_f="$dir_out/$bare_stub_out.json"
          "$SCRIPT_DIR/gpmlconverter" --id "$pathway_id" --pathway-version "$PATHWAY_VERSION" "$path_in" "$json_f"

          metabolite_patterns_css_f="$dir_out/$bare_stub_out.metabolite-patterns-uri.css"
          metabolite_patterns_svg_f="$dir_out/$bare_stub_out.metabolite-patterns-uri.svg"
          "$SCRIPT_DIR/metabolite-patterns-uri" "$json_f"

          if [[ "$base_out" =~ (pvjssvg)$ ]]; then
            #############################
            # SVG > .pvjssvg
            #############################
            pvjs --react --theme "plain" < "$json_f" | xmlstarlet fo | tail -n +2 > "$path_out"
            # TODO: I should be able to use "xmlstarlet fo -o" instead of "tail -n +2"
            # to omit the xml declaration <?xml version="1.0"?>, but "xmlstarlet fo -o"
            # is giving an error. Strangely, "xmlstarlet fo" does not error.
            #pvjs --react --theme "plain" < "$json_f" | xmlstarlet fo -o > "$path_out"

            fix_pvjs_bugs "$path_out"

        #    sed -i '/<style.*>/{
        #r '"$metabolite_patterns_css_f"'
        #}' "$path_out"

            sed -i '/<g id="jic-defs">/{
        r /dev/stdin
        }' "$path_out" < <(xmlstarlet sel -t -c '/svg/defs/*' "$metabolite_patterns_svg_f")

            # We overwrite the stylesheet, getting rid of the hover effects
            # for metabolites, but that's desired for now.
            # We have the patterns in case we want to do anything with
            # them later on, but we don't have the busy hover effects.
            xmlstarlet ed -L -O -N svg='http://www.w3.org/2000/svg' \
                    -u "/svg:svg/svg:style/text()" \
                    -v "
        " \
                "$path_out"

            sed -i '/<style.*>/{
        r '"$SCRIPT_DIR/../plain.css"'
        }' "$path_out"

            #############################
            # SVG > .dark.pvjssvg
            #############################
            path_out_dark_pvjssvg="$dir_out/$bare_stub_out.dark.pvjssvg"
            cat "$path_out" | xmlstarlet ed -O -N svg='http://www.w3.org/2000/svg' \
                    -u "/svg:svg/svg:style/text()" \
                    -v "
        " > \
                "$path_out_dark_pvjssvg"

            sed -i '/<style.*>/{
        r '"$SCRIPT_DIR/../dark.css"'
        }' "$path_out_dark_pvjssvg"

          else
            #############################
            # SVG > .svg
            #############################

            # TODO: make the stand-alone SVGs work for upload to WM Commons:
            # https://www.mediawiki.org/wiki/Manual:Coding_conventions/SVG
            # https://commons.wikimedia.org/wiki/Help:SVG
            # https://commons.wikimedia.org/wiki/Commons:Commons_SVG_Checker?withJS=MediaWiki:CommonsSvgChecker.js
            # The W3 validator might be outdated. It doesn't allow for RDFa attributes.
            # http://validator.w3.org/#validate_by_upload+with_options


            # WM says: "the recommended image height is around 400–600 pixels. When a
            #           user views the full size image, a width of 600–800 pixels gives
            #           them a good close-up view"
            # https://commons.wikimedia.org/wiki/Help:SVG#Frequently_asked_questions

            pvjs < "$json_f" | \
              xmlstarlet ed -N svg='http://www.w3.org/2000/svg' \
                            -i '/svg:svg' --type attr -n width -v '800px' \
                            -i '/svg:svg' --type attr -n height -v '600px' \
                            -u "/svg:svg/svg:style/text()" \
                            -v "
        " \
              > "$path_out"

            fix_pvjs_bugs "$path_out"

            sed -i '/<style.*>/{
        r '"$metabolite_patterns_css_f"'
        }' "$path_out"

            sed -i '/<g id="jic-defs">/{
        r /dev/stdin
        }' "$path_out" < <(xmlstarlet sel -t -c '/svg/defs/*' "$metabolite_patterns_svg_f")

            edge_count=$(cat "$path_out" | xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v 'count(/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')])')
            for i in $(seq $edge_count); do
              xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                      -m "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')][$i]/svg:g/svg:path" \
                      "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')][$i]" \
                      "$path_out";
            done

            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -m "/svg:svg/svg:defs/svg:g[@id='jic-defs']/svg:svg/svg:defs/*" \
                    "/svg:svg/svg:defs/svg:g[@id='jic-defs']" \
                    -d "/svg:svg/svg:defs/svg:g[@id='jic-defs']/svg:svg" \
                    "$path_out";

            for attr in "filter" "fill" "fill-opacity" "stroke" "stroke-dasharray" "stroke-width"; do
              xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                      -i "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]" -t attr -n "$attr" -v "REPLACE_ME" \
                      -u "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]/@$attr" \
                      -x "string(../svg:g/@$attr)" \
                      "$path_out"
            done

            for attr in "color" "fill" "fill-opacity" "stroke" "stroke-dasharray" "stroke-width"; do
              xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                            -i "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]/svg:path" -t attr -n "$attr" -v "REPLACE_ME" \
                            -u "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]/svg:path/@$attr" \
                            -x "string(../../svg:g/@$attr)" \
                            "$path_out"
            done

            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                          -d "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]/svg:g" \
                          -d "/svg:svg/svg:g/svg:g[contains(@typeof,'Edge')]/svg:path/@style" \
                          "$path_out"

            # Which of the following is correct?
            # To make the SVG file independent of Arial, change all occurrences of
            #   font-family: Arial to font-family: 'Liberation Sans', Arial, sans-serif
            #   https://commons.wikimedia.org/wiki/Help:SVG#fallback
            # vs.
            # Phab:T64987, Phab:T184369, Gnome #95; font-family="'font name'"
            #   (internally quoted font family name) does not work
            #   (File:Mathematical_implication_diagram-alt.svg, File:T184369.svg)
            #   https://commons.wikimedia.org/wiki/Commons:Commons_SVG_Checker?withJS=MediaWiki:CommonsSvgChecker.js

            # The kerning for Liberation Sans has some issues, at least when run through librsvg.
            # Liberation Sans is the open replacement for Arial, but DejaVu Sans with transform="scale(0.92,0.98)"
            # might have better kerning while taking up about the same amount of space.

            # Long-term, should we switch our default font from Arial to something prettier?
            # It would have to be a well-supported font.
            # This page <https://commons.wikimedia.org/wiki/Help:SVG#fallback> says:
            #     On Commons, librsvg has the fonts listed in:
            #     https://meta.wikimedia.org/wiki/SVG_fonts#Latin_(basic)_fonts_comparison
            #     ...
            #     In graphic illustrations metric exact text elements are often important
            #     and Arial can be seen as de-facto standard for such a feature.
            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -u "//*[contains(@font-family,'Arial')]/@font-family" \
                    -v "'Liberation Sans', Arial, sans-serif" \
                    "$path_out"
            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -u "//*[contains(@font-family,'arial')]/@font-family" \
                    -v "'Liberation Sans', Arial, sans-serif" \
                    "$path_out"

            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -i "/svg:svg/svg:defs/svg:g/svg:marker/svg:path[not(@fill)]" -t attr -n "fill" -v "REPLACE_ME" \
                    -u "/svg:svg/svg:defs/svg:g/svg:marker/svg:path[@fill='REPLACE_ME']/@fill" \
                    -v "currentColor" \
                    "$path_out"

        #  		  -u "/svg:svg/@color" \
        #		  -v "black" \
        #		  -u "/svg:svg/svg:g/@color" \
        #		  -v "black" \
            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
            -u "/svg:svg/svg:g//svg:text[@stroke-width='0.05px']/@stroke-width" \
            -v "0px" \
            -d "/svg:svg/svg:g//*/svg:text/@overflow" \
            -d "/svg:svg/svg:g//*/svg:text/@dominant-baseline" \
            -d "/svg:svg/svg:g//*/svg:text/@clip-path" \
            -d "/svg:svg/svg:g//svg:defs" \
            -d "/svg:svg/svg:g//svg:text[@stroke-width='0.05px']/@stroke-width" \
            "$path_out";

            # We are pushing the text down based on font size.
            # This is needed because librsvg doesn't support attribute "alignment-baseline".
            el_count=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "count(/svg:svg/svg:g//svg:text)" "$path_out")
            for i in $(seq $el_count); do
                font_size=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "(/svg:svg/svg:g//svg:text)[$i]/@font-size" "$path_out" | sed 's/^\([0-9.]*\)px$/\1/g');
              font_size=${font_size:-5}
              x_translation=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "(/svg:svg/svg:g//svg:text)[$i]/@transform" "$path_out" | sed 's/^translate[(]\([0-9.]*\),\([0-9.]*\)[)]$/\1/g');
              y_translation=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "(/svg:svg/svg:g//svg:text)[$i]/@transform" "$path_out" | sed 's/^translate[(]\([0-9.]*\),\([0-9.]*\)[)]$/\2/g');
              updated_y_translation=$(echo "$font_size / 3 + $y_translation" | bc)
              xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -u "(/svg:svg/svg:g//svg:text)[$i]/@transform" \
                    -v "translate($x_translation,$updated_y_translation)" \
                    "$path_out";
            done
          
            # TODO: how about using these: https://reactome.org/icon-lib
            # for example, mitochondrion: https://reactome.org/icon-lib?f=cell_elements#Mitochondrion.svg
            # They appear to be CC-4.0, which might mean we can't upload them to WM Commons?

            # Linkify
            path_out_tmp="$path_out.tmp.svg"
            cp "$path_out" "$path_out_tmp"
            el_count=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "count(/svg:svg/svg:g//*[@class])" "$path_out_tmp")
            for i in $(seq $el_count); do
                readarray -t wditems <<<$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t \
                        -v "(/svg:svg/svg:g//*[@class])[$i]/@class" "$path_out_tmp" | \
                    awk '/Wikidata_Q[0-9]+/' | tr ' ' '\n' | awk '/Wikidata_Q[0-9]+/');
            wditems_len="${#wditems[@]}"
                if [[ wditems_len -eq 1 ]]; then
                wditem=${wditems[0]}
                if [ ! -z $wditem ]; then

                    #wikidata_iri=$(echo "$wditem" | awk -F'_' '{print "https://www.wikidata.org/wiki/"$NF}')
                    scholia_iri=$(echo "$wditem" | awk -F'_' '{print "https://tools.wmflabs.org/scholia/"$NF}')

                    xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                                -i "(/svg:svg/svg:g//*[@class])[$i]" \
                                -t attr -n "xlink:href" \
                                -v "$scholia_iri" \
                                "$path_out_tmp";
                
                    xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                                -i "(/svg:svg/svg:g//*[@class])[$i]" \
                                -t attr -n "target" \
                                -v "_blank" \
                                "$path_out_tmp";
                
                    xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                                -r "(/svg:svg/svg:g//*[@class])[$i]" \
                                -v "a" \
                                "$path_out_tmp";
                fi
                fi
                
            done
            
            mv "$path_out_tmp" "$path_out"

            #############################
            # SVG > .dark.svg
            #############################
            path_out_dark_svg="$dir_out/$bare_stub_out.dark.svg"

            # Invert colors and filters
          
            cat "$path_out" | xmlstarlet ed -N svg='http://www.w3.org/2000/svg' \
                  -u "/svg:svg/@color" \
                  -v "white" \
                  -u "/svg:svg/svg:g/@color" \
                  -v "white" > \
                  "$path_out_dark_svg"

            for attr in "color" "fill" "stroke"; do
              el_count=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "count(/svg:svg/svg:g//*[@$attr])" "$path_out_dark_svg")
              for i in $(seq $el_count); do
                color=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "(/svg:svg/svg:g//*[@$attr])[$i]/@$attr" "$path_out_dark_svg");
                inverted_color=$(invert_color $color)
                xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                          -u "(/svg:svg/svg:g//*[@$attr])[$i]/@$attr" \
                      -v "$inverted_color" \
                      "$path_out_dark_svg";
              done
            done

            el_count=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "count(/svg:svg/svg:g//*[@filter])" "$path_out_dark_svg")
            for i in $(seq $el_count); do
              filter_value=$(xmlstarlet sel -N svg='http://www.w3.org/2000/svg' -t -v "(/svg:svg/svg:g//*[@filter])[$i]/@filter" "$path_out_dark_svg");
              inverted_filter_value=$(invert_filter $filter_value)
              xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                    -u "(/svg:svg/svg:g//*[@filter])[$i]/@filter" \
                    -v "$inverted_filter_value" \
                    "$path_out_dark_svg";
            done
          
            # clip-path needed because rx and ry don't work in FF or Safari
            xmlstarlet ed -L -N svg='http://www.w3.org/2000/svg' \
                  -u "/svg:svg/svg:g/svg:rect[contains(@class,'Icon')]/@fill" \
                  -v "#3d3d3d" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'Edge')]/svg:path/@stroke-width" \
                  -v "1.1px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupGroup')]/*[contains(@class,'Icon')]/@fill" \
                  -v "transparent" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupGroup')]/*[contains(@class,'Icon')]/@stroke-width" \
                  -v "0px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupComplex')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#B4B464" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupComplex')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "0.1" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupComplex')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "#808080" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupNone')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#B4B464" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupNone')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "0.1" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupNone')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "#808080" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupPathway')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#008000" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupPathway')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "0.05" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'GroupPathway')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "#808080" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'CellularComponent')]/*[contains(@class,'Icon')]/@color" \
                  -v "red" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'CellularComponent')]/*[contains(@class,'Icon')]/@fill" \
                  -v "pink" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'CellularComponent')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "0.05" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'CellularComponent')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "orange" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'Label')]/*[contains(@class,'Icon')]/@color" \
                  -v "transparent" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'Label')]/*[contains(@class,'Icon')]/@fill" \
                  -v "none" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'Label')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "0" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'Label')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "none" \
                  -i "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/*[contains(@class,'Icon')]" -t attr -n "clip-path" -v "url(#ClipPathRoundedRectangle)" \
                          -i "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/*[contains(@class,'Icon')]" -t attr -n "rx" -v "15px" \
                          -i "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/*[contains(@class,'Icon')]" -t attr -n "ry" -v "15px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/*[contains(@class,'Icon')]/@stroke-width" \
                  -v "0px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/*[contains(@class,'Text')]/@font-weight" \
                  -v "bold" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'GeneProduct')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#f4d03f" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'GeneProduct')]/*[contains(@class,'Text')]/@fill" \
                  -v "#333" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Protein')]/*[contains(@class,'Icon')]/@fill" \
                  -v "brown" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Protein')]/*[contains(@class,'Text')]/@fill" \
                  -v "#FEFEFE" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Rna')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#9453A7" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Rna')]/*[contains(@class,'Text')]/@fill" \
                  -v "#ECF0F1" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Icon')]/@xlink:href" \
                  -v "#Rectangle" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#75C95C" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Icon')]/@fill-opacity" \
                  -v "1" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Text')]/@stroke" \
                  -v "transparent" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Text')]/@stroke-width" \
                  -v "0px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Pathway')]/*[contains(@class,'Text')]/@fill" \
                  -v "#1C2833" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Metabolite')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#0000EE" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode') and contains(@typeof, 'Metabolite')]/*[contains(@class,'Text')]/@fill" \
                  -v "#FEFEFE" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/svg:g[contains(@typeof, 'State')]/*[contains(@class,'Icon')]/@fill" \
                  -v "#fefefe" \
                  -i "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/svg:g[contains(@typeof, 'State')]/*[contains(@class,'Icon')]" \
                  -t attr -n "color" \
                  -v "gray" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/svg:g[contains(@typeof, 'State')]/*[contains(@class,'Icon')]/@stroke" \
                  -v "gray" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/svg:g[contains(@typeof, 'State')]/*[contains(@class,'Icon')]/@stroke-width" \
                  -v "1px" \
                  -u "/svg:svg/svg:g//svg:g[contains(@class,'DataNode')]/svg:g[contains(@typeof, 'State')]/*[contains(@class,'Text')]/@fill" \
                  -v "black" \
                  "$path_out_dark_svg"
      fi
      """
    else:
        raise Exception(f"Invalid output extension: '{ext_out}'")


def main():
    """main."""

    version = "0.0.0"

    parser = argparse.ArgumentParser(description="Convert GPML to SVG")
    parser.add_argument("path_in")
    parser.add_argument("path_out")

    group_version = parser.add_mutually_exclusive_group()
    group_version.add_argument(
        "-V", "--version", action="store_true", help="Display version of this program"
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pathway-id", type=str, help="WikiPathways ID, e.g., WP1243")
    # In the future, this could change, e.g., maybe we'll starting using
    # a Wikidata ID like Q66104607 or
    # a WM Commons IRI.

    group.add_argument(
        "--pathway-version", type=str, help="WikiPathways revision (oldid), e.g., 69897"
    )
    # In the future, this could change, e.g., maybe we'll start using
    # a SHA256 hash of the GPML or
    # a Wikidata revision or
    # a WM Commons image edit date

    group.add_argument(
        "--scale",
        type=int,
        help="Default: 100. Only valid for conversions to PNG format.",
    )

    args = parser.parse_args()

    if args.version:
        print(version)
    else:
        pathway_id = args.pathway_id
        path_in = args.path_in
        pathway_version = args.pathway_version

        pathway_iri = None
        wp_id = None

        if pathway_id is None:
            pathway_id = path_in

        pathway_id_path_in = f"{pathway_id} {path_in}"
        wp_id_rev_match = WPID_REV_RE.search(pathway_id_path_in)
        if wp_id_rev_match:
            wp_id = wp_id_rev_match.group(1)
            if pathway_version is None:
                pathway_version = wp_id_rev_match.group(2)
            else:
                pathway_version = 0
        else:
            wp_id_match = WPID_RE.search(pathway_id_path_in)
            if wp_id_match:
                wp_id = wp_id_match.group(0)

        if wp_id is None:
            raise Exception(
                f"Specify a WikiPathways ID in pathway_id or path_in, e.g., '--pathway_id WP4542'"
            )
        else:
            if pathway_id.startswith("http"):
                pathway_iri = pathway_id
            else:
                pathway_iri = f"http://identifiers.org/wikipathways/{wp_id}"

        convert(
            args.path_in,
            args.path_out,
            pathway_iri=pathway_iri,
            wp_id=wp_id,
            pathway_version=pathway_version,
            scale=args.scale,
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        print("done")
