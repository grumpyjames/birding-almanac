import os

from datetime import datetime
import markdown
import pystache
import shutil
import sys
from bs4 import BeautifulSoup


class TemplateRenderer:
  def __init__(
      self,
      page_template,
      content_template,
      cell_template,
      fpi_template,
      fc_template,
  ):
    self.page_template = page_template
    self.content_template = content_template
    self.cell_template = cell_template
    self.fpi_template = fpi_template
    self.fc_template = fc_template

  def render_page(self, page_html):
    return pystache.render(
      self.page_template,
      {
        'content': page_html
      }
    )

  def render_content(self, content_html, content_nav):
    page_html = pystache.render(
      self.content_template,
      {
        'main-content': content_html,
        'content-nav': content_nav
      }
    )
    return self.render_page(page_html)


  def render_cell(self, title, url, blurb):
    return pystache.render(
      self.cell_template,
      {
        'site_name': title,
        'site_url': url,
        'short_site_description': blurb
      }
    )

  def render_feature(self, name, url, blurb_html):
    return pystache.render(
      self.fc_template,
      {
        'feature_url': url,
        'feature_name': name,
        'feature_description': blurb_html
      }
    )

  def render_front_page_item(self, item):
    return pystache.render(self.fpi_template, item)


def parse_metadata(metadata_dict):
  date_format = "%Y-%m-%dT%H:%M:%S.%fZ"

  return {
    "publish_time": datetime.strptime(metadata_dict["publish_time"][0], date_format),
    "updated_time": datetime.strptime(metadata_dict["updated_time"][0], date_format)
  }

def create_website(output, home, render_at_time):
  with \
      open("page.mustache") as f, \
      open("content.mustache") as c, \
      open("front_page_item.mustache") as fpi, \
      open("feature_cell.mustache") as fc, \
      open('by_name_cell.mustache') as cell:
    templating = TemplateRenderer(
      f.read(),
      c.read(),
      cell.read(),
      fpi.read(),
      fc.read()
    )

  os.makedirs(output, exist_ok=True)
  copy_images(output)
  about_page(templating, output)
  sites_with_blurb = []
  sites(templating, render_at_time, output, sites_with_blurb)
  all_feature_items = []
  features(templating, render_at_time, output, all_feature_items)
  front_page(templating, home, all_feature_items, sites_with_blurb, output)


def copy_images(output):
  for file in os.listdir("."):
    if file.endswith(".png") or file.endswith(".ico"):
      shutil.copyfile(file, os.path.join(output, file))


def about_page(templating, output):
  with open("about.mustache") as about:
    about_html = templating.render_page(about.read())
    with open(os.path.join(output, "about.html"), "w+") as out:
      out.write(about_html)

def front_page(templating, home, all_feature_items, sites_with_blurb, output):
  front_page_items = []
  front_page_items.extend(all_feature_items)
  front_page_items.extend(sites_with_blurb)
  front_page_items = sorted(front_page_items, key=lambda item: item["publish_time"], reverse=True)
  home_items = ""
  for index, item in enumerate(home):
    home_items += templating.render_front_page_item(item)

  def convert(index, item):
    even = index % 2 != 0
    common = {
      'row-class': ('left' if even else 'right'),
      'img-class': ('float-right' if even else 'float-left'),
      'date': datetime.strftime(item["publish_time"], "%B %-d, %Y"),
      'time': datetime.strftime(item["publish_time"], "%H:%M"),
      'blurb': item["blurb"]
    }

    if item["type"] == "site":
      custom = {
        'index-link': '/sites/index.html',
        'index-title': 'Site Guides',
        'item-link': '/sites/' + item["site_path"] + '.html',
        'item-title': item["site_name"],
        'image': '/sites/' + item["site_path"] + '-thumb.png',
      }
    elif item["type"] == "feature":
      custom = {
        'index-link': '/features/' + item["feature_path"] + '/index.html',
        'index-title': item["feature_title"],
        'item-link': '/features/' + item["feature_path"] + '/' + item["feature_item_path"] + '.html',
        'item-title': item["feature_item_title"],
        'image': '/features/' + item["feature_path"] + '/' + item["feature_item_path"] + '-thumb.png',
      }
    else:
      raise ("Unknown item type: " + item["type"])
    return  {**common, **custom}

  for (index, f) in enumerate(front_page_items):
    home_items += "<hr/>"
    front_page_item = convert(index, f)
    home_items += templating.render_front_page_item(front_page_item)
  index_html = templating.render_page(home_items)
  with open(os.path.join(output, "index.html"), "+w") as index_file:
    index_file.write(index_html)


def features(
    templating,
    render_at_time,
    output,
    all_feature_items):

  feature_cells = []

  def as_html(md_file):
    return md_file.rstrip(".md") + ".html"

  def about_feature(path_to_feature):
    with open(path_to_feature + '/about.md') as about_feature:
      md = markdown.Markdown(extensions=['meta'])
      feature_blurb = md.convert(about_feature.read())
      # noinspection PyUnresolvedReferences
      feature_title = md.Meta["feature_title"][0]
      feature_cells.append(templating.render_feature(
        feature_title,
        "/" + path_to_feature,
        feature_blurb
      ))
    return feature_title

  os.makedirs(os.path.join(output, "features"), exist_ok=True)

  feature_dir = os.listdir("features")
  for feature in feature_dir:
    feature_path = 'features/' + feature

    feature_title = about_feature(feature_path)

    feature_items = []
    os.makedirs(os.path.join(output, feature_path), exist_ok=True)
    feature_files = os.listdir(feature_path)
    feature_md_files = []
    for file in feature_files:
      if file.endswith(".png") or file.endswith(".jpg"):
        src = feature_path + '/' + file
        shutil.copyfile(src, os.path.join(output, src))
      elif file.endswith(".md") and file != "about.md":
        feature_md_files.append(file)

    feature_md_files.sort()
    for index, file in enumerate(feature_md_files):
      with open(feature_path + "/" + file) as feature_file:
        md = markdown.Markdown(extensions=['meta'])
        feature_html = md.convert(feature_file.read())
        # noinspection PyUnresolvedReferences
        feature_metadata = parse_metadata(md.Meta)
        if feature_metadata["publish_time"] < render_at_time:
          soup = BeautifulSoup(feature_html, features="html.parser")

          # noinspection PyUnresolvedReferences
          feature_items.append({
            'url': as_html(file),
            'name': (str(index + 1) + ": " + soup.h3.text),
            'blurb': soup.p.text,
            'publish_time': feature_metadata["publish_time"],
            'updated_time': feature_metadata["updated_time"],
            'type': 'feature',
            'feature_path': feature,
            'feature_title': feature_title,
            'feature_item_path': file.rstrip(".md"),
            'feature_item_title': md.Meta["title"][0]
          })

          nav = []
          if index > 0:
            prev_file_link = as_html(feature_md_files[index - 1])
            nav += "<a class='nav-previous' href='" + prev_file_link + "'>Previous</a>"
          if index + 1 < len(feature_md_files):
            next_file_link = as_html(feature_md_files[index + 1])
            nav += "<a class='nav-next' href='" + next_file_link + "'>Next</a>"
          content_nav = "".join(nav)
          full_page_html = templating.render_content(feature_html, content_nav)

          out_path = os.path.join(output, feature_path + "/" + as_html(file))
          with open(out_path, "w+") as file_output:
            file_output.write(full_page_html)

    all_feature_items.extend(feature_items)

    feature_index_html = ""

    for f_w_b in feature_items:
      feature_index_html += templating.render_cell(
        f_w_b["name"],
        f_w_b["url"],
        f_w_b["blurb"]
      )
    with open(os.path.join(output, "features/" + feature + "/index.html"), "w+") as feature_index:
      cells = "<div class=\"row\">" + feature_index_html + "</div>"
      feature_index.write(templating.render_page(cells))
  with open(os.path.join(output, 'features/index.html'), "w+") as features_index:
    feature_rows = ("<div class=\"row\">" + feature_cell + "</div>" for feature_cell in feature_cells)
    features_index.write(templating.render_page("".join(feature_rows)))


def sites(
    templating,
    render_at_time,
    output,
    sites_with_blurb):
  os.makedirs(os.path.join(output, "sites"), exist_ok=True)

  sites_to_convert = []

  for filename in os.listdir("sites"):
    if filename.endswith(".md"):
      sites_to_convert.append((filename, filename.split(".")[0]))
    elif filename.endswith(".png"):
      shutil.copyfile("sites/" + filename, os.path.join(output, "sites/" + filename))
  for (f, site_name) in sites_to_convert:
    with open(os.path.join("sites", f)) as site_file:
      site_markdown = site_file.read()
      md = markdown.Markdown(extensions=['meta'])
      site_html = md.convert(site_markdown)
      # noinspection PyUnresolvedReferences
      metadata = parse_metadata(md.Meta)
      if metadata["publish_time"] < render_at_time:
        soup = BeautifulSoup(site_html, features="html.parser")
        sites_with_blurb.append({
          'name': site_name,
          'blurb': soup.p.text,
          'publish_time': metadata["publish_time"],
          'updated_time': metadata["updated_time"],
          'type': 'site',
          'site_name': site_name.replace("_", " "),
          'site_path': site_name
        })

        full_page_html = templating.render_content(site_html, "")
        with open(os.path.join(output, "sites", site_name + ".html"), "w+") as file_output:
          file_output.write(full_page_html)

  cells = ""
  for (site) in sites_with_blurb:
    cells += templating.render_cell(
      site["name"].replace("_", " "),
      site["name"] + '.html',
      site["blurb"])
  with open(os.path.join(output, 'sites/index.html'), "w+") as list_index:
    cells = "<div class=\"row\">" + cells + "</div>"
    list_index.write(
      templating.render_page(cells)
    )


def welcome_item():
  return {
    'row-class': 'left',
    'img-class': 'float-right',
    'index-link': '#',
    'index-title': 'Announcements',
    'item-link': '#',
    'item-title': 'Welcome to Average Birding',
    'image': '/welcome-thumb.png',
    'blurb': """
      <p>A birding website by average birders, for birders of any feather.</p>
<p>Our <a href="sites/index.html">site guides</a> offer introductions to birding locations. 
Our <a href="features/">features</a>, in particular, <a href="features/a-200-bird-year">a 200 bird year?</a> offer a birding distraction. 
Scroll down for links to our most recently updated pages.</p>    
    """,
    'date': "December 15, 2019",
    'time': "19:48"
  }

home = [
  welcome_item()
]

output = sys.argv[1]
if len(sys.argv) > 2:
  render_at_time = datetime.strptime(sys.argv[2], "%Y-%m-%dT%H:%M:%S.%fZ")
else:
  render_at_time = datetime.now()

create_website(output, home, render_at_time)