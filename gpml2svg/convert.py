#!/usr/bin/env python3

# import xml.etree.ElementTree as ET
import argparse
import csv
import itertools
import json
from lxml import etree as ET
import re
import shlex
import subprocess

from os import path, rename
import requests
import pywikibot
from pywikibot.data import sparql


SCRIPT_DIR = path.dirname(path.realpath(__file__))

SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
parser = ET.XMLParser(strip_cdata=False)

WPID_RE = re.compile(r"WP\d+")
WPID_REV_RE = re.compile(r"(WP\d+)_r?(\d+)")
LEADING_DOT_RE = re.compile(r"^\.")
BARE_BASE_RE = re.compile(r"(.+)\.*")
NON_ALPHANUMERIC_RE = re.compile(r"\W")
LATEST_GPML_VERSION = "2013a"

BRIDGEDB_REPO_BASE = "https://raw.githubusercontent.com/bridgedb/BridgeDb/master"
BRIDGEDB2WD_PROPS_REQUEST = requests.get(
    BRIDGEDB_REPO_BASE + "/org.bridgedb.bio/src/main/resources/org/bridgedb/bio/datasources.tsv"
)
BRIDGEDB2WD_PROPS = dict()
for row in csv.DictReader(BRIDGEDB2WD_PROPS_REQUEST.text.splitlines(), delimiter="\t"):
    BRIDGEDB2WD_PROPS[row["datasource_name"]] = row["wikidata_property"]


# see https://stackoverflow.com/a/8998040
def grouper_it(n, iterable):
    it = iter(iterable)
    while True:
        chunk_it = itertools.islice(it, n)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)


def gpml2json(path_in, path_out, pathway_iri, wp_id, pathway_version, wd_sparql):
    """Convert from GPML to JSON.

    Keyword arguments:
    path_in -- path in, e.g., ./WP4542_103412.gpml
    path_out -- path out, e.g., ./WP4542_103412.json
    pathway_iri -- e.g., http://identifiers.org/wikipathways/WP4542
    wp_id -- e.g., WP4542
    pathway_version -- e.g., 103412
    wd_sparql -- wikidata object for making queries
    """

    dir_out = path.dirname(path_out)
    # example base_out: 'WP4542.json'
    base_out = path.basename(path_out)
    [stub_out, ext_out_with_dot] = path.splitext(base_out)

    gpml2pvjson_cmd = (
        f"gpml2pvjson --id {pathway_iri} --pathway-version {pathway_version}"
    )
    with open(path_in, "r") as f_in:
        with open(path_out, "w") as f_out:
            gpml2pvjson_ps = subprocess.Popen(
                shlex.split(gpml2pvjson_cmd), stdin=f_in, stdout=f_out, shell=False
            )
            gpml2pvjson_ps.communicate()[0]

    organism = None
    with open(path_out, "r") as json_f:
        pathway_data = json.load(json_f)
        pathway = pathway_data["pathway"]
        organism = pathway["organism"]
        entities_by_id = pathway_data["entitiesById"]
        entities_with_valid_xrefs = list()
        for entity in entities_by_id.values():
            datasource_invalid = "xrefDataSource" in entity and (
                entity["xrefDataSource"] in ["undefined"]
                or not entity["xrefDataSource"]
            )
            xref_identifier_invalid = "xrefIdentifier" in entity and (
                entity["xrefIdentifier"] in ["undefined"]
                or not entity["xrefIdentifier"]
            )
            if datasource_invalid or xref_identifier_invalid:
                entity_id = entity["id"]
                print(
                    f"Invalid xref datasource and/or identifier for {wp_id}, entity {entity_id}"
                )
                # bridgedbjs fails when an identifier is something like 'undefined'.
                # Should it ignore datasources/identifiers it doesn't recognize
                # and just keep going?
                del entity["xrefDataSource"]
                del entity["xrefIdentifier"]
            else:
                entities_with_valid_xrefs.append(entity)
        with open(path_out, "w") as f_out:
            json.dump(pathway_data, f_out)

    if not organism:
        print("No organism. Can't call BridgeDb.")
    elif len(entities_with_valid_xrefs) == 0:
        # TODO: bridgedbjs fails when no xrefs are present.
        # Update bridgedbjs to do this check:
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
            pathway = pathway_data["pathway"]
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

            pathway_id_query = (
                '''
SELECT ?item WHERE {
?item wdt:P2410 "'''
                + wp_id
                + """" .
SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}"""
            )
            wd_pathway_id_result = wd_sparql.query(pathway_id_query)

            if len(wd_pathway_id_result["results"]["bindings"]) == 0:
                print(f"Pathway ID {wp_id} not found in Wikidata. Retrying.")
                # retry once
                wd_pathway_id_result = wd_sparql.query(pathway_id_query)
            if len(wd_pathway_id_result["results"]["bindings"]) == 0:
                # if it still doesn't work, skip it
                print(
                    f"Pathway ID {wp_id} still not found in Wikidata. Skipping conversion."
                )
                return False

            wikidata_pathway_iri = wd_pathway_id_result["results"]["bindings"][0][
                "item"
            ]["value"]
            wikidata_pathway_identifier = wikidata_pathway_iri.replace(
                "http://www.wikidata.org/entity/", ""
            )

            # adding Wikidata IRI to sameAs property & ensuring no duplication
            if not "sameAs" in pathway:
                pathway["sameAs"] = wikidata_pathway_identifier
            else:
                same_as = pathway["sameAs"]
                if type(same_as) == str:
                    pathway["sameAs"] = list({wikidata_pathway_identifier, same_as})
                else:
                    same_as.append(wikidata_pathway_identifier)
                    pathway["sameAs"] = list(set(same_as))

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

            # Here we chunk the headings and queries into paired batches and
            # make several smaller requests to WD. This is needed because some
            # of the GET requests become too large to send as a single request.

            batch_size = 10
            for [heading_batch, query_batch] in zip(
                grouper_it(batch_size, headings), grouper_it(batch_size, queries)
            ):
                headings_str = " ".join(heading_batch)
                queries_str = (
                    "WHERE { "
                    + " ".join(query_batch)
                    + ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
                )
                xref_query = f"SELECT {headings_str} {queries_str}"
                xref_result = wd_sparql.query(xref_query)
                xref_query = f"SELECT {headings_str} {queries_str}"
                xref_result = wd_sparql.query(xref_query)

                bridgedb_keys = xref_result["head"]["vars"]
                for binding in xref_result["results"]["bindings"]:
                    for bridgedb_key in bridgedb_keys:
                        # TODO: is this check needed?
                        if type(binding[bridgedb_key]["value"]) == list:
                            raise Exception("Error: expected list and got string")

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


def json2svg(json_f, path_out, pathway_iri, wp_id, pathway_version, theme):
    """Convert from JSON to SVG.

    Keyword arguments:
    json_f -- path of JSON file, e.g., ./WP4542_103412.gpml
    path_out -- path out, e.g., ./WP4542_103412.svg
    pathway_iri -- e.g., http://identifiers.org/wikipathways/WP4542
    wp_id -- e.g., WP4542
    pathway_version -- e.g., 103412
    theme -- theme (plain or dark) to use when converting to SVG (default plain)
    """

    dir_out = path.dirname(path_out)
    # example base_out: 'WP4542.svg'
    base_out = path.basename(path_out)
    [stub_out, ext_out_with_dot] = path.splitext(base_out)

    pvjs_cmd = f"pvjs --theme {theme}"
    with open(json_f, "r") as f_in:
        with open(path_out, "w") as f_out:
            pvjs_ps = subprocess.Popen(
                shlex.split(pvjs_cmd), stdin=f_in, stdout=f_out, shell=False
            )
            pvjs_ps.communicate()[0]

    tree = ET.parse(path_out, parser=parser)
    root = tree.getroot()

    #############################
    # SVG > .svg
    #############################

    # TODO: make the stand-alone SVGs work for upload to WM Commons:
    # https://www.mediawiki.org/wiki/Manual:Coding_conventions/SVG
    # https://commons.wikimedia.org/wiki/Help:SVG
    # https://commons.wikimedia.org/wiki/Commons:Commons_SVG_Checker?withJS=MediaWiki:CommonsSvgChecker.js
    # W3 validator: http://validator.w3.org/#validate_by_upload+with_options

    # WM says: "the recommended image height is around 400–600 pixels. When a
    #           user views the full size image, a width of 600–800 pixels gives
    #           them a good close-up view"
    # https://commons.wikimedia.org/wiki/Help:SVG#Frequently_asked_questions
    root.set("width", "800px")
    root.set("height", "600px")

    # TODO: verify that all of the following cases are now correctly handled in pvjs
    for style_el in root.findall(".//style"):
        if not style_el.text == "":
            raise Exception("Expected empty style sheets.")
    for el in root.findall(".//pattern[@id='PatternQ47512']"):
        raise Exception("Unexpected pattern.")

    edge_warning_sent = False
    for el in root.xpath(
        ".//svg:g/svg:g[contains(@class,'Edge')]/svg:g", namespaces=SVG_NS
    ):
        if not edge_warning_sent:
            print("TODO: update pvjs to avoid having nested g elements for edges.")
            edge_warning_sent = True
        # raise Exception("Unexpected nested g element for edge.")

    for el in root.xpath(
        "/svg:svg/svg:g/svg:g[contains(@class,'Edge')]/svg:path/@style",
        namespaces=SVG_NS,
    ):
        raise Exception(
            "Unexpected style attribute on path element for edge.", namespaces=SVG_NS
        )

    for el in root.xpath(
        "/svg:svg/svg:defs/svg:g[@id='jic-defs']/svg:svg/svg:defs", namespaces=SVG_NS
    ):
        raise Exception("Unexpected nested svg for defs.")

    for el in root.findall(".//defs/g[@id='jic-defs']/svg/defs"):
        raise Exception("Unexpected nested svg for defs.")

    for el in root.xpath(
        ".//svg:g/svg:g[contains(@class,'Edge')]/svg:path/@style", namespaces=SVG_NS
    ):
        raise Exception("Unexpected style attribute on path element for edge.")

    # TODO: should any of this be in pvjs instead?
    style_selector = (
        "[@style='color:inherit;fill:inherit;fill-opacity:inherit;stroke:inherit;stroke-width:inherit']"
    )
    for el_parent in root.findall(f".//*{style_selector}/.."):
        stroke_width = el_parent.attrib.get("stroke-width", 1)
        for el in root.findall(f".//*{style_selector}"):
            el.set(
                "style",
                f"color:inherit;fill:inherit;fill-opacity:inherit;stroke:inherit;stroke-width:{str(stroke_width)}",
            )

    for el in root.findall(".//*[@filter='url(#kaavioblackto000000filter)']"):
        el.attrib.pop("filter", None)

    for image_parent in root.findall(".//*image/.."):
        images = image_parent.findall("image")
        for image in images:
            image_parent.remove(image)

    # TODO: do the attributes "filter" "fill" "fill-opacity" "stroke" "stroke-dasharray" "stroke-width"
    # on the top-level g element apply to the g elements for edges?

    # TODO: do the attributes "color" "fill" "fill-opacity" "stroke" "stroke-dasharray" "stroke-width"
    # on the top-level g element apply to the path elements for edges?

    # TODO: Which of the following is correct?
    # To make the SVG file independent of Arial, change all occurrences of
    #   font-family: Arial to font-family: 'Liberation Sans', Arial, sans-serif
    #   https://commons.wikimedia.org/wiki/Help:SVG#fallback
    # vs.
    # Phab:T64987, Phab:T184369, Gnome #95; font-family="'font name'"
    #   (internally quoted font family name) does not work
    #   (File:Mathematical_implication_diagram-alt.svg, File:T184369.svg)
    #   https://commons.wikimedia.org/wiki/Commons:Commons_SVG_Checker?withJS=MediaWiki:CommonsSvgChecker.js

    # Liberation Sans is the open replacement for Arial, but its kerning
    # has some issues, at least as processed by librsvg.
    # An alternative that is also supported MW is DejaVu Sans. Using
    #   transform="scale(0.92,0.98)"
    # might yield better kerning and take up about the same amount of space.

    # Long-term, should we switch our default font from Arial to something prettier?
    # It would have to be a well-supported font.
    # This page <https://commons.wikimedia.org/wiki/Help:SVG#fallback> says:
    #     On Commons, librsvg has the fonts listed in:
    #     https://meta.wikimedia.org/wiki/SVG_fonts#Latin_(basic)_fonts_comparison
    #     ...
    #     In graphic illustrations metric exact text elements are often important
    #     and Arial can be seen as de-facto standard for such a feature.

    for el in root.xpath(".//*[contains(@font-family,'Arial')]", namespaces=SVG_NS):
        el.set("font-family", "'Liberation Sans', Arial, sans-serif")

    # TODO: do we need to specify fill=currentColor for any elements?

    for el in root.xpath(".//svg:defs//svg:marker//*[not(@fill)]", namespaces=SVG_NS):
        el.set("fill", "currentColor")

    for el in root.xpath(".//svg:text[@stroke-width='0.05px']", namespaces=SVG_NS):
        el.attrib.pop("stroke-width", None)

    for el in root.xpath(".//svg:text[@overflow]", namespaces=SVG_NS):
        el.attrib.pop("overflow", None)

    for el in root.xpath(".//svg:text[@dominant-baseline]", namespaces=SVG_NS):
        el.attrib.pop("dominant-baseline", None)

    for el in root.xpath(".//svg:text[@clip-path]", namespaces=SVG_NS):
        el.attrib.pop("clip-path", None)

    FONT_SIZE_RE = re.compile(r"^([0-9.]*)px$")
    # TRANSLATE_RE = re.compile(r"^translate[(]([0-9.]*),([0-9.]*)[)]$")
    TRANSLATE_RE = re.compile(r"^translate\(([0-9.]*),([0-9.]*)\)$")
    # We are pushing the text down based on font size.
    # This is needed because librsvg doesn't support attribute "alignment-baseline".

    for el in root.xpath(".//svg:text[@font-size]", namespaces=SVG_NS):
        font_size_full = el.attrib.get("font-size")
        font_size_matches = re.search(FONT_SIZE_RE, font_size_full)
        if font_size_matches:
            font_size = float(font_size_matches.group(1))

        if not font_size:
            font_size = 5

        x_translation = None
        y_translation = None
        transform_full = el.attrib.get("transform")
        if transform_full:
            translate_matches = re.search(TRANSLATE_RE, transform_full)
            if translate_matches:
                x_translation = float(translate_matches.group(1))
                y_translation_uncorrected = float(translate_matches.group(2))

        if not x_translation:
            x_translation = 0
            y_translation_uncorrected = 0

        y_translation_corrected = font_size / 3 + y_translation_uncorrected
        el.set("transform", f"translate({x_translation},{y_translation_corrected})")

    # Add link outs
    WIKIDATA_CLASS_RE = re.compile("Wikidata_Q[0-9]+")
    for el in root.xpath(".//*[contains(@class,'DataNode')]", namespaces=SVG_NS):
        wikidata_classes = list(
            filter(WIKIDATA_CLASS_RE.match, el.attrib.get("class").split(" "))
        )
        if len(wikidata_classes) > 0:
            # if there are multiple, we just link out to the first
            wikidata_id = wikidata_classes[0].replace("Wikidata_", "")
            el.tag = "{http://www.w3.org/2000/svg}a"
            # linkout_base = "https://www.wikidata.org/wiki/"
            linkout_base = "https://scholia.toolforge.org/"
            el.set("{http://www.w3.org/1999/xlink}href", linkout_base + wikidata_id)

            # make linkout open in new tab/window
            el.set("target", "_blank")

    ###########
    # Run SVGO
    ###########

    pre_svgo_svg_f = f"{dir_out}/{stub_out}.pre_svgo.svg"
    tree.write(pre_svgo_svg_f)

    tree.write(path_out)
    args = shlex.split(
        f'svgo --multipass --config "{SCRIPT_DIR}/svgo-config.json" {path_out}'
    )
    subprocess.run(args)

    #########################################
    # Future enhancements for pretty version
    #########################################

    # TODO: convert the following bash code into Python

    # Glyphs from reactome
    # TODO: how about using these: https://reactome.org/icon-lib
    # for example, mitochondrion: https://reactome.org/icon-lib?f=cell_elements#Mitochondrion.svg
    # They appear to be CC-4.0, which might mean we can't upload them to WM Commons?

    # Glyphs from SMILES
    #        metabolite_patterns_css_f = (
    #            f"{dir_out}/{bare_stub_out}.metabolite-patterns-uri.css"
    #        )
    #        metabolite_patterns_svg_f = (
    #            f"{dir_out}/{bare_stub_out}.metabolite-patterns-uri.svg"
    #        )
    #
    #        if path.exists(metabolite_patterns_svg_f) and path.exists(
    #            metabolite_patterns_css_f
    #        ):
    #            print(
    #                f"{metabolite_patterns_svg_f} & {metabolite_patterns_css_f} already exist. To overwrite, delete them & try again."
    #            )
    #        else:
    #            # If only one of them exists, we recreate both
    #            if path.exists(metabolite_patterns_svg_f):
    #                os.remove(metabolite_patterns_svg_f)
    #            elif path.exists(metabolite_patterns_css_f):
    #                os.remove(metabolite_patterns_css_f)
    #
    #            metabolite_patterns_svg_tree = ET.parse(
    #                "<svg><defs></defs></svg>", parser=parser
    #            )
    #            metabolite_patterns_svg_root = metabolite_patterns_svg_tree.getroot()
    #
    #            # TODO convert the following sh script to Python
    #            """
    #            jq -r '[.entitiesById[] | select(.type | contains(["Metabolite"]))] | unique_by(.type)[] | [.xrefDataSource, .xrefIdentifier, [.type[] | select(startswith("wikidata:"))][0], [.type[] | select(startswith("hmdb:") and length == 14)][0]] | @tsv' "$json_f" | \
    #             while IFS=$'\t' read -r data_source identifier wikidata_id hmdb_id; do
    #              wikidata_identifier=$(echo "$wikidata_id" | sed 's/wikidata://');
    #              bridgedb_request_uri="http://webservice.bridgedb.org/Human/attributes/$data_source/$identifier?attrName=SMILES"
    #              if [ -z "$data_source" ] || [ -z "$identifier" ]; then
    #                echo "Missing Xref data source and/or identifier in $stub_out";
    #                continue;
    #              fi
    #
    #              smiles=$(curl -Ls "$bridgedb_request_uri")
    #              bridgedb_request_status=$?
    #
    #              if [ "$bridgedb_request_status" != 0 ] || [ -z "$smiles" ] || [[ "$smiles" =~ 'The server has not found anything matching the request URI' ]]; then
    #            #    if [ "$bridgedb_request_status" != 0 ]; then
    #            #      echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from $bridgedb_request_uri (status code: $bridgedb_request_status)";
    #            #    elif [ -z "$smiles" ]; then
    #            #      echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from $bridgedb_request_uri (nothing returned)";
    #            #    elif [[ "$smiles" =~ 'The server has not found anything matching the request URI' ]]; then
    #            #      echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from $bridgedb_request_uri";
    #            #      echo '(The server has not found anything matching the request URI)'
    #            #    fi
    #
    #                # If the DataSource and Identifier specified don't get us a SMILES string,
    #                # it could be because BridgeDb doesn't support queries for that DataSource.
    #                # For example, WP396_97382 has a DataNode with PubChem-compound:3081372,
    #                # http://webservice.bridgedb.org/Human/attributes/PubChem-compound/3081372?attrName=SMILES
    #                # doesn't return anything. However, that DataNode can be mapped to HMDB:HMDB61196, and
    #                # the url http://webservice.bridgedb.org/Human/attributes/HMDB/HMDB61196
    #                # does return a SMILES string.
    #                # Note that BridgeDb currently requires us to use the 5 digit HMDB identifier,
    #                # even though there is another format that uses more digits.
    #
    #                if [ ! -z "$hmdb_id" ]; then
    #                  hmdb_identifier="HMDB"${hmdb_id:(-5)};
    #                  bridgedb_request_uri_orig="$bridgedb_request_uri"
    #                  bridgedb_request_uri="http://webservice.bridgedb.org/Human/attributes/HMDB/$hmdb_identifier?attrName=SMILES"
    #                  #echo "Trying alternate bridgedb_request_uri: $bridgedb_request_uri"
    #                  smiles=$(curl -Ls "$bridgedb_request_uri")
    #                  bridgedb_request_status=$?
    #                  if [ "$bridgedb_request_status" != 0 ]; then
    #                    echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from both $bridgedb_request_uri_orig and alternate $bridgedb_request_uri (status code: $bridgedb_request_status)";
    #                    continue;
    #                  elif [ -z "$smiles" ]; then
    #                    echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from both $bridgedb_request_uri_orig and alternate $bridgedb_request_uri (nothing returned)";
    #                    continue;
    #                  elif [[ "$smiles" =~ 'The server has not found anything matching the request URI' ]]; then
    #                    echo "Failed to get SMILES string for $stub_out:$data_source:$identifier from both $bridgedb_request_uri_orig and alternate $bridgedb_request_uri";
    #                    echo '(The server has not found anything matching the request URI)'
    #                    continue;
    #                  fi
    #                else
    #                  continue;
    #                fi
    #              fi
    #
    #              smiles_url_encoded=$(echo "$smiles" | jq -Rr '@uri')
    #              cdkdepict_url="http://www.simolecule.com/cdkdepict/depict/bow/svg?smi=$smiles_url_encoded&abbr=on&hdisp=bridgehead&showtitle=false&zoom=1.0&annotate=none"
    #
    #              cat >> "$css_out" <<EOF
    #            [typeof~="wikidata:$wikidata_identifier"]:hover > .Icon {
    #              cursor: default;
    #              fill: url(#Pattern$wikidata_identifier);
    #              transform-box: fill-box;
    #              transform: scale(2, 3);
    #              transform-origin: 50% 50%;
    #            }
    #            [typeof~="wikidata:$wikidata_identifier"]:hover > .Text {
    #              font-size: 0px;
    #            }
    #            EOF
    #
    #              # TODO: do we want to disable the clip-path on hover?
    #              #[typeof~=wikidata:$wikidata_identifier]:hover > .Icon {
    #              #  clip-path: unset;
    #              #  rx: unset;
    #              #  ry: unset;
    #              #  cursor: default;
    #              #  fill: url(#Pattern$wikidata_identifier);
    #              #  transform-box: fill-box;
    #              #  transform: scale(2, 3);
    #              #  transform-origin: 50% 50%;
    #              #}
    #
    #              #  "transform-box: fill-box" is needed for FF.
    #              #  https://bugzilla.mozilla.org/show_bug.cgi?id=1209061
    #
    #              xmlstarlet ed -L \
    #                                -s "/svg/defs" -t elem -n "pattern" -v "" \
    #                            --var prevpattern '$prev' \
    #                                -s '$prevpattern' -t elem -n "image" -v "" \
    #                            --var previmage '$prev' \
    #                                -i '$prevpattern' -t attr -n "id" -v "Pattern$wikidata_identifier" \
    #                                -i '$prevpattern' -t attr -n "width" -v "100%" \
    #                                -i '$prevpattern' -t attr -n "height" -v "100%" \
    #                                -i '$prevpattern' -t attr -n "patternContentUnits" -v "objectBoundingBox" \
    #                                -i '$prevpattern' -t attr -n "preserveAspectRatio" -v "none" \
    #                                -i '$prevpattern' -t attr -n "viewBox" -v "0 0 1 1" \
    #                                -i '$previmage' -t attr -n "width" -v "1" \
    #                                -i '$previmage' -t attr -n "height" -v "1" \
    #                                -i '$previmage' -t attr -n "href" -v "$cdkdepict_url" \
    #                                -i '$previmage' -t attr -n "preserveAspectRatio" -v "none" \
    #                      "$svg_out"
    #            done
    #
    #            sed -i '/<style.*>/{
    #        r '"$metabolite_patterns_css_f"'
    #        }' "$path_out"
    #
    #            sed -i '/<g id="jic-defs">/{
    #        r /dev/stdin
    #        }' "$path_out" < <(xmlstarlet sel -t -c '/svg/defs/*' "$metabolite_patterns_svg_f")
    #            """


def convert(
    path_in, path_out, pathway_iri, wp_id, pathway_version, scale=100, theme="plain"
):
    """Convert from GPML to another format like SVG.

    Keyword arguments:
    path_in -- path in, e.g., ./WP4542_103412.gpml
    path_out -- path out, e.g., ./WP4542_103412.svg
    pathway_iri -- e.g., http://identifiers.org/wikipathways/WP4542
    pathway_version -- e.g., 103412
    scale -- scale to use when converting to PNG (default 100)
    theme -- theme (plain or dark) to use when converting to SVG (default plain)"""
    if not path.exists(path_in):
        raise Exception(f"Missing file '{path_in}'")

    if path.exists(path_out):
        print(f"File {path_out} already exists. Skipping.")
        return True

    dir_in = path.dirname(path_in)
    base_in = path.basename(path_in)
    # example base_in: 'WP4542.gpml'
    [stub_in, ext_in_with_dot] = path.splitext(base_in)
    # gettting rid of the leading dot, e.g., '.gpml' to 'gpml'
    ext_in = LEADING_DOT_RE.sub("", ext_in_with_dot)

    if ext_in != "gpml":
        # TODO: how about *.gpml.xml?
        raise Exception(f"Currently only accepting *.gpml for path_in")
    gpml_f = path_in

    dir_out = path.dirname(path_out)
    # example base_out: 'WP4542.svg'
    base_out = path.basename(path_out)
    [stub_out, ext_out_with_dot] = path.splitext(base_out)
    # getting rid of the leading dot, e.g., '.svg' to 'svg'
    ext_out = LEADING_DOT_RE.sub("", ext_out_with_dot)

    tree = ET.parse(gpml_f, parser=parser)
    root = tree.getroot()

    if root is None:
        raise Exception("no root element")
    if root.tag is None:
        raise Exception("no root tag")

    gpml_version = re.sub(r"{http://pathvisio.org/GPML/(\w+)}Pathway", r"\1", root.tag)
    if ext_out != "gpml" and gpml_version != LATEST_GPML_VERSION:
        old_f = f"{dir_in}/{stub_in}.{gpml_version}.gpml"
        rename(gpml_f, old_f)
        convert(old_f, gpml_f, pathway_iri, wp_id, pathway_version, scale)

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
        gpml2json(path_in, path_out, pathway_iri, wp_id, pathway_version, wd_sparql)
    elif ext_out in ["svg", "pvjssvg"]:
        #############################
        # SVG
        #############################

        json_f = f"{dir_out}/{stub_in}.json"
        if not path.isfile(json_f):
            gpml2json(path_in, json_f, pathway_iri, wp_id, pathway_version, wd_sparql)

        json2svg(json_f, path_out, pathway_iri, wp_id, pathway_version, theme)
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

    group.add_argument(
        "--theme",
        type=str,
        help="Default: plain. Options: plain or dark. Only valid for conversions to SVG format.",
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
            theme=args.theme,
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        # do something
        print("")
