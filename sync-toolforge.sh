rsync -rIl --delete --exclude "./*" --include "./{svg2commons}/*.{py,json}" tools-login.wmflabs.org:~/tool-wikipathways2wiki/

ssh tools-login.wmflabs.org 'rsync -rIl --delete --exclude "./*" --include "tool-wikipathways2wiki/{svg2commons}/*.{py,json}" ./tool-wikipathways2wiki/ /data/project/wikipathways2wiki/tool-wikipathways2wiki-tmp/; become wikipathways2wiki "/data/project/wikipathways2wiki/update.sh"; rm -rf /data/project/wikipathways2wiki/tool-wikipathways2wiki-tmp'
