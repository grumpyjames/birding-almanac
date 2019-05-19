import os

import markdown
import pystache
import shutil
from bs4 import BeautifulSoup


def as_html(md_file):
  return md_file.split(".md")[0] + ".html"


def site_guide_item(
    even,
    site_name,
    site_path,
    blurb
):
  row_class = 'left' if even else 'right'
  img_class = 'float-right' if even else 'float-left'
  return {
    'row-class': row_class,
    'img-class': img_class,
    'index-link': '/sites/index.html',
    'index-title': 'Site Guides',
    'item-link': '/sites/' + site_path + '.html',
    'item-title': site_name,
    'image': '/sites/' + site_path + '-thumb.png',
    'blurb': blurb,
  }


def feature_item(
    even,
    feature_name,
    feature_path,
    feature_item_title,
    feature_item_path,
    blurb,
):
  row_class = 'left' if even else 'right'
  img_class = 'float-right' if even else 'float-left'
  return {
    'row-class': row_class,
    'img-class': img_class,
    'index-link': '/features/' + feature_path + '/index.html',
    'index-title': feature_name,
    'item-link': '/features/' + feature_path + '/' + feature_item_path + '.html',
    'item-title': feature_item_title,
    'image': '/features/' + feature_path + '/' + feature_item_path + '-thumb.png',
    'blurb': blurb,
  }


home = [
  feature_item(
    True,
    "A 200 Bird Year",
    "a-200-bird-year",
    "Part 2: A false start",
    "part-02-a-false-start",
    """
    <p>Many birders are up bright and early on New Year's Day, eager to make
a start on a new list.</p>
    <p>The best laid plans of mice and men, however...</p>
    """
  ),
  feature_item(
    False,
    "A 200 Bird Year",
    "a-200-bird-year",
    "Part 1: Prologue",
    "part-01-prologue",
    """
    <p>Where does this idea of a big year come from?</p>
    <p>Why is 200 such a popular number to go for?</p>
    <p>Let's try for a 200 bird year, and find out!</p>
    """
  ),
  site_guide_item(
    True,
    "Barnes WWT",
    "Barnes_WWT",
    """
    <p>A WWT reserve in TfL Zone 2.</p>
    <p>That can't possible work, can it?</p>
    <p>Spoiler alert: it very much can.</p>
    """
  )
]

with \
    open("page.mustache") as f, \
    open("content.mustache") as c, \
    open("front_page_item.mustache") as fpi, \
    open("feature_cell.mustache") as fc, \
    open('by_name_cell.mustache') as cell:
  page_template = f.read()
  content_template = c.read()
  cell_template = cell.read()
  fpi_template = fpi.read()
  fc_template = fc.read()

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

  def render_feature(name, url, blurb_html):
    return pystache.render(
      fc_template,
      {
        'feature_url': url,
        'feature_name': name,
        'feature_description': blurb_html
      }
    )

  for filename in os.listdir("sites"):
    if filename.endswith(".md"):
      sites_to_convert.append((filename, filename.split(".")[0]))
    elif filename.endswith(".png"):
      shutil.copyfile("sites/" + filename, "out/sites/" + filename)

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
      sites_with_blurb.append({'name': site_name, 'blurb': soup.p.text})

      full_page_html = render_content(site_html, "")
      with open(os.path.join("out/sites", site_name + ".html"), "w+") as output:
        output.write(full_page_html)

  cells = ""
  for (site) in sites_with_blurb:
    cells += render_cell(
      site["name"].replace("_", " "),
      site["name"] + '.html',
      site["blurb"])

  with open('out/sites/index.html', "w+") as list_index:
    cells = "<div class=\"row\">" + cells + "</div>"
    list_index.write(
      render_page(cells)
    )

  feature_cells = render_feature(
    "A 200 Bird Year",
    "/features/a-200-bird-year",
    """
    <p>A journal of an attempt at a 200 bird year</p>
    """
  )

  with open('out/features/index.html', "w+") as features_index:
    feature_cells = "<div class=\"row\">" + feature_cells + "</div>"
    features_index.write(render_page(feature_cells))

  features = os.listdir("features")
  for feature in features:
    features_with_blurb = []
    os.makedirs("out/features/" + feature, exist_ok=True)
    feature_files = os.listdir("features/" + feature)
    feature_md_files = []
    for file in feature_files:
      if file.endswith(".png"):
        src = 'features/' + feature + '/' + file
        shutil.copyfile(src, 'out/' + src)
      elif file.endswith(".md"):
        feature_md_files.append(file)

    feature_md_files.sort()
    for index, file in enumerate(feature_md_files):
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
          prev_file_link = as_html(feature_md_files[index - 1])
          nav += "<a class='nav-previous' href='" + prev_file_link + "'>Previous</a>"
        if index + 1 < len(feature_md_files):
          next_file_link = as_html(feature_md_files[index + 1])
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

  home_items = ""
  for index, item in enumerate(home):
    if index > 0:
      home_items += "<hr/>"
    home_items += pystache.render(fpi_template, item)

  index_html = render_page(home_items)
  with open("out/index.html", "+w") as index_file:
    index_file.write(index_html)
