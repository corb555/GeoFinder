#!/bin/bash
export PYTHONPATH=$PWD

packages="geodata ancestry geofinder util"
index_file="docs/index.html"

rm $index_file
cat docs/head.html >> $index_file

for pkg in $packages; do
	echo $pkg
	echo "<li><a href='$pkg/index.html' target='container'>$pkg</a></li>" >> $index_file
	pdoc --all-submodules --html --overwrite --html-no-source --html-dir docs $pkg
done

echo "</ul></div></nav><iframe class="container" name="container" src="geodata/index.html"></iframe></body></html>" >> $index_file
