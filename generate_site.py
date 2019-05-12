import os

import markdown
import pystache
from bs4 import BeautifulSoup

with open("page.mustache") as f, open("content.mustache") as c:
  page_template = f.read()
  content_template = c.read()
  sites_to_convert = []
  features = []

  for filename in os.listdir("sites"):
    if filename.endswith(".md"):
      sites_to_convert.append((filename, filename.split(".")[0]))  
      
  with open("front.mustache") as front:
    front_html = pystache.render(page_template, { 'content': front.read() })
    with open(os.path.join("out", "index.html"), "w+") as out:
      out.write(front_html)

  with open("about.mustache") as about:
    about_html = pystache.render(page_template, { 'content': about.read() })
    with open(os.path.join("out", "about.html"), "w+") as out:
      out.write(about_html)

  sites_with_blurb = []
  for (f, site_name) in sites_to_convert:
    with open(os.path.join("sites", f)) as site_file:
      site_markdown = site_file.read()
      site_html = markdown.markdown(site_markdown)
      soup = BeautifulSoup(site_html, features="html.parser")
      sites_with_blurb.append({ 'name': site_name, 'blurb': soup.p.text })
      content_html = pystache.render(
        content_template,
        { 
          'main-content': site_html 
        })
      full_page_html = pystache.render(
        page_template, { 'content': content_html })
      with open(os.path.join("out/sites", site_name + ".html"), "w+") as output:
        output.write(full_page_html)
  
  with open('by_name_cell.mustache') as cell:
    cell_template = cell.read()
    cells = ""
    for (site) in sites_with_blurb:
      cells += pystache.render(cell_template,
        { 'site_name': site["name"].replace("_", " ")
        , 'site_url': site["name"] + '.html'
        , 'short_site_description': site["blurb"]
        })
    with open('out/sites/on_a_list.html', "w+") as list_index:
      cells = "<div class=\"row\">" + cells + "</div>"   
      list_index.write(pystache.render(page_template, {'content': cells}))

  features = os.listdir("features")
  for feature in features:    
    print(os.listdir("features/" + feature))

