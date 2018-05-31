mkdir -p out/sites
for file in `ls sites/*.md`; do
    outfile="${file%.*}"
    cp site-header.html out/$outfile.html
    pandoc -f markdown -t html $file >> out/$outfile.html
    cat site-footer.html >> out/$outfile.html
done

cp index-header.html out/index.html
for file in `ls out/sites/*html`; do
    site_name="$(basename "${file%.*}")"
    human_site_name="$(echo $site_name | tr '_' ' ')"
    echo "<li><a href=\"sites/$site_name.html\">$human_site_name</a>" >> out/index.html
done
cat index-footer.html >> out/index.html
