import os

import markdown
import pystache
from bs4 import BeautifulSoup


def as_html(md_file):
  return md_file.split(".md")[0] + ".html"

with open("page.mustache") as f, open("content.mustache") as c, open('by_name_cell.mustache') as cell:
  page_template = f.read()
  content_template = c.read()
  cell_template = cell.read()

  sites_to_convert = []

  def render_page(page_html):
    return pystache.render(
      page_template,
      {
        'content': page_html
      }
    )


  def render_content(content_html, content_nav):
    page_html = pystache.render(
      content_template,
      {
        'main-content': content_html,
        'content-nav': content_nav
      }
    )
    return render_page(page_html)


  def render_cell(title, url, blurb):
    return pystache.render(
      cell_template,
      {
        'site_name': title,
        'site_url': url,
        'short_site_description': blurb
      }
    )


  for filename in os.listdir("sites"):
    if filename.endswith(".md"):
      sites_to_convert.append((filename, filename.split(".")[0]))  
      
  with open("front.mustache") as front:
    front_html = render_page(front.read())
    with open(os.path.join("out", "index.html"), "w+") as out:
      out.write(front_html)

  with open("about.mustache") as about:
    about_html = render_page(about.read())
    with open(os.path.join("out", "about.html"), "w+") as out:
      out.write(about_html)

  sites_with_blurb = []
  for (f, site_name) in sites_to_convert:
    with open(os.path.join("sites", f)) as site_file:
      site_markdown = site_file.read()
      site_html = markdown.markdown(site_markdown)
      soup = BeautifulSoup(site_html, features="html.parser")
      sites_with_blurb.append({ 'name': site_name, 'blurb': soup.p.text })

      full_page_html = render_content(site_html, "")
      with open(os.path.join("out/sites", site_name + ".html"), "w+") as output:
        output.write(full_page_html)

  cells = ""
  for (site) in sites_with_blurb:
    cells += render_cell(
      site["name"].replace("_", " "),
      site["name"] + '.html',
      site["blurb"])

  with open('out/sites/on_a_list.html', "w+") as list_index:
    cells = "<div class=\"row\">" + cells + "</div>"
    list_index.write(
      render_page(cells)
    )

  features = os.listdir("features")
  for feature in features:
    features_with_blurb = []
    os.makedirs("out/features/" + feature, exist_ok=True)
    feature_files = os.listdir("features/" + feature)
    for index, file in enumerate(feature_files):
      with open("features/" + feature + "/" + file) as feature_file:
        feature_html = markdown.markdown(feature_file.read())

        soup = BeautifulSoup(feature_html, features="html.parser")

        features_with_blurb.append({
          'url': as_html(file),
          'name': (str(index + 1) + ": " + soup.h3.text),
          'blurb': soup.p.text
        })

        nav = []
        if index > 0:
          prev_file_link = as_html(feature_files[index - 1])
          nav += "<a class='nav-previous' href='" + prev_file_link + "'>Previous</a>"
        if index + 1 < len(feature_files):
          next_file_link = as_html(feature_files[index + 1])
          nav += "<a class='nav-next' href='" + next_file_link + "'>Next</a>"
        content_nav = "".join(nav)
        full_page_html = render_content(feature_html, content_nav)

        out_path = "out/features/" + feature + "/" + as_html(file)
        with open(out_path, "w+") as output:
          output.write(full_page_html)
    feature_index_html = ""
    for f_w_b in features_with_blurb:
      feature_index_html += render_cell(
        f_w_b["name"],
        f_w_b["url"],
        f_w_b["blurb"]
      )
    with open("out/features/" + feature + "/index.html", "w+") as feature_index:
      cells = "<div class=\"row\">" + feature_index_html + "</div>"
      feature_index.write(render_page(cells))