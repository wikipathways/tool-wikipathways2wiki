#!/usr/bin/env bash

# see https://stackoverflow.com/a/246128/5354298
get_script_dir() { echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; }
SCRIPT_DIR=$(get_script_dir)

batch_name="daily_human_approved_gpml_$(printf '%(%Y-%m-%d)T\n' -1)"
echo "Batch processing results to $SCRIPT_DIR/$batch_name"
if [ ! -d "$batch_name" ]; then
  wget -O "$batch_name.zip" \
    'https://www.wikipathways.org//wpi/batchDownload.php?species=Homo%20sapiens&fileType=gpml&tag=Curation:AnalysisCollection'
  unzip -d "$batch_name" "$batch_name.zip"
  rm -rf "$batch_name.zip"
else
  echo "Using previously downloaded $batch_name"
fi

gpml2svg() {
  gpmlfile="$1"
  wpid=$(echo $gpmlfile | awk -F_ '{print $(NF-1)}')
  echo "Processing $wpid"
  python3 gpml2svg/convert.py --theme plain "$gpmlfile" "$batch_name/$wpid.svg" || return
  python3 gpml2svg/convert.py --theme dark "$gpmlfile" "$batch_name/$wpid.dark.svg" || return
}

# TODO: look at using gnu parallel instead of for loop. Example:
# https://github.com/ariutta/allene/blob/3ad257effa85426511504d7862f65b9241f7dd31/src/update#L216
for gpmlfile in $batch_name/*.gpml; do
  gpml2svg "$gpmlfile" || break
done

# just for testing purposes:
#for gpmlfile in $(ls -1 $batch_name/*.gpml | grep WP106); do done
#for gpmlfile in $(ls -1 $batch_name/*.gpml | head -n 2); do done

# TODO: get the log processing steps below working again
#cp "$batch_name/*" "public/"
#mv "$HOME/logs/$batch_name.log"
#
#ISSUES_F="$SCRIPT_DIR/public/issues.log"
#echo $'"error"\t"wpid"\t"notes"' > "$ISSUES_F"
#
#grep 'wikidata_property_missing' "$HOME/logs/$batch_name.log" | sort -u >> "$ISSUES_F"
#grep 'wikidata_mapping_failed' "$HOME/logs/$batch_name.log" | sort -u >> "$ISSUES_F"
#grep 'wikidata_ambiguous_mapping' "$HOME/logs/$batch_name.log" | sort -u >> "$ISSUES_F"
#
#grep 'Missing Xref data source and/or identifier in WP' "$HOME/logs/$batch_name.log" |\
#  sed -E 's#Missing Xref data source and/or identifier in (WP[0-9]+)#"xref_missing_datasource_or_identifier"\t"\1"\t""#' |\
#  sort >> "$ISSUES_F"
