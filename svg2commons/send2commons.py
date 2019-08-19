# -*- coding: utf-8  -*-

# python3 send2commons.py WP4150 Q50400662 "23:18, 15 August 2019" "signaling pathways,kidney diseases"
# python3 send2commons.py WP4542 Q66104607 "23:55, 14 June 2019" "Signaling pathways,Immune response,Leukocyte disorders,T cells,Cancers"

import sys

import json
import shlex, subprocess

import pywikibot
from pywikibot.specialbots import UploadRobot

import xml.etree.ElementTree as ET


def complete_desc_and_upload(
    filename, pagetitle, desc, date, categories, source, author, wpid, qid
):
    description = (
        u"""
== [https://tools.wmflabs.org/pathway-viewer?id="""
        + wpid
        + """ Interactive View] ==
Link above goes to an interactive viewer that allows pan and zoom.

=={{int:filedesc}}==
{{Information
|Description    = {{en|1="""
        + desc
        + """}}
|Source         = """
        + source
        + """
|Author         = """
        + author
        + """
|Date           = """
        + date
        + """
|Permission     = CC0
|other_versions = 
}}
=={{int:license-header}}==
{{cc-zero}}

==More Information==
{{On Wikidata|"""
        + qid
        + """}}
{{current}}

"""
        + categories
    )

    print("")
    print(description)
    print("")

    url = [filename]
    keepFilename = (
        True
    )  # set to True to skip double-checking/editing destination filename
    verifyDescription = (
        False
    )  # set to False to skip double-checking/editing description => change to bot-mode
    targetSite = pywikibot.getSite("commons", "commons")

    bot = UploadRobot(
        url,
        description=description,
        useFilename=pagetitle,
        keepFilename=keepFilename,
        verifyDescription=verifyDescription,
        targetSite=targetSite,
    )
    bot.run()


def main(args):
    wpid = args[0]
    qid = args[1]
    date = args[2]
    additional_categories = [x.strip() for x in args[3].split(",")]

    pathway_content = dict()
    with open(
        "/data/project/wikipathways2wiki/www/js/public/{}.json".format(wpid)
    ) as pathway_f:
        pathway_content = json.load(pathway_f)
    pathway_name = pathway_content["pathway"]["name"]
    organism = pathway_content["pathway"]["organism"]
    pathwayVersion = pathway_content["pathway"]["pathwayVersion"]
    description = "\n".join(
        [
            x["content"]
            for x in pathway_content["pathway"]["comments"]
            if x["source"] == "WikiPathways-description"
        ]
    )

    filename = "{}.svg".format(wpid)
    pagetitle = "{} ({}).svg".format(pathway_name, organism)
    desc = description
    date = "23:18, 15 August 2019"
    source = "Published as {0}, revision {1}, at https://www.wikipathways.org/index.php/Pathway:{0}?oldid={1}".format(
        wpid, pathwayVersion
    )
    author = "WikiPathways community"

    categories = """[[Category:WikiPathways]]
[[Category:Images with annotations]]
""" + "[[Category:{}]]".format(
        organism
    )

    for additional_category in additional_categories:
        categories += "[[Category:{}]]".format(additional_category)

    ns = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}

    ET.register_namespace("", "http://www.w3.org/2000/svg")

    tree = ET.parse(filename)
    root = tree.getroot()

    style_selector = (
        "[@style='color:inherit;fill:inherit;fill-opacity:inherit;stroke:inherit;stroke-width:inherit']"
    )
    for el_parent in root.findall(".//*{}/..".format(style_selector), ns):
        stroke_width = el_parent.attrib.get("stroke-width", 1)
        for el in root.findall(".//*{}".format(style_selector), ns):
            el.set(
                "style",
                "color:inherit;fill:inherit;fill-opacity:inherit;stroke:inherit;stroke-width:{}".format(
                    str(stroke_width)
                ),
            )

    for el in root.findall(".//*[@filter='url(#kaavioblackto000000filter)']", ns):
        el.attrib.pop("filter", None)

    for image_parent in root.findall(".//*svg:image/..", ns):
        images = image_parent.findall("svg:image", ns)
        for image in images:
            image_parent.remove(image)

    processed_filename = filename + ".processed.svg"
    tree.write(processed_filename)

    args = shlex.split(
        "/data/project/wikipathways2wiki/.npm-global/bin/svgo --multipass --config svgo-config.json {}".format(
            processed_filename
        )
    )
    subprocess.run(args)

    complete_desc_and_upload(
        filename=processed_filename,
        pagetitle=pagetitle,
        desc=desc,
        date=date,
        categories=categories,
        source=source,
        author=author,
        wpid=wpid,
        qid=qid,
    )


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        pywikibot.stopme()
