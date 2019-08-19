#rsync -rIl --delete --exclude "./*" --include "./{svg2commons,gpml2svg}/*.{py,json}" tools-login.wmflabs.org:~/tool-wikipathways2wiki/
rsync -rRIl --delete ./{gpml2svg,svg2commons}/*.{py,json} tools-login.wmflabs.org:~/tool-wikipathways2wiki/

ssh tools-login.wmflabs.org 'cd tool-wikipathways2wiki; rsync -rRIl --delete ./{svg2commons,gpml2svg}/*.{py,json} /data/project/wikipathways2wiki/tool-wikipathways2wiki-tmp/; become wikipathways2wiki "/data/project/wikipathways2wiki/update.sh"; rm -rf /data/project/wikipathways2wiki/tool-wikipathways2wiki-tmp'
