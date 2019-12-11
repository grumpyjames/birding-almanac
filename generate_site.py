import os

from datetime import datetime
import markdown
import pystache
import shutil
import sys
from bs4 import BeautifulSoup


def create_website(output, home, render_at_time):
  os.makedirs(output, exist_ok=True)

  for file in os.listdir("."):
    if file.endswith(".png") or file.endswith(".ico"):
      shutil.copyfile(file, os.path.join(output, file))

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

    def as_html(md_file):
      return md_file.split(".md")[0] + ".html"

    def parse_metadata(metadata_dict):
      format = "%Y-%m-%dT%H:%M:%S.%fZ"

      return {
        "publish_time": datetime.strptime(metadata_dict["publish_time"][0], format),
        "updated_time": datetime.strptime(metadata_dict["updated_time"][0], format)
      }

    os.makedirs(os.path.join(output, "sites"), exist_ok=True)
    for filename in os.listdir("sites"):
      if filename.endswith(".md"):
        sites_to_convert.append((filename, filename.split(".")[0]))
      elif filename.endswith(".png"):
        shutil.copyfile("sites/" + filename, os.path.join(output, "sites/" + filename))

    with open("about.mustache") as about:
      about_html = render_page(about.read())
      with open(os.path.join(output, "about.html"), "w+") as out:
        out.write(about_html)

    sites_with_blurb = []
    for (f, site_name) in sites_to_convert:
      with open(os.path.join("sites", f)) as site_file:
        site_markdown = site_file.read()
        md = markdown.Markdown(extensions = ['meta'])
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

          full_page_html = render_content(site_html, "")
          with open(os.path.join(output, "sites", site_name + ".html"), "w+") as file_output:
            file_output.write(full_page_html)

    cells = ""
    for (site) in sites_with_blurb:
      cells += render_cell(
        site["name"].replace("_", " "),
        site["name"] + '.html',
        site["blurb"])

    with open(os.path.join(output, 'sites/index.html'), "w+") as list_index:
      cells = "<div class=\"row\">" + cells + "</div>"
      list_index.write(
        render_page(cells)
      )

    feature_cells = render_feature(
      "A 200 Bird Year?",
      "/features/a-200-bird-year",
      """
      <p>A journal of an attempt at a 200 bird year</p>
      """
    )

    os.makedirs(os.path.join(output, "features"), exist_ok=True)
    with open(os.path.join(output, 'features/index.html'), "w+") as features_index:
      feature_cells = "<div class=\"row\">" + feature_cells + "</div>"
      features_index.write(render_page(feature_cells))

    features = os.listdir("features")
    all_features_with_blurb = []
    for feature in features:
      features_with_blurb = []
      os.makedirs(os.path.join(output, "features/" + feature), exist_ok=True)
      feature_files = os.listdir("features/" + feature)
      feature_md_files = []
      for file in feature_files:
        if file.endswith(".png") or file.endswith(".jpg"):
          src = 'features/' + feature + '/' + file
          shutil.copyfile(src, os.path.join(output, src))
        elif file.endswith(".md") and file != "about.md":
          feature_md_files.append(file)

      feature_title = None
      with open('features/' + feature + '/about.md') as about_feature:
        md = markdown.Markdown(extensions = ['meta'])
        md.convert(about_feature.read())
        feature_title = md.Meta["feature_title"][0]

      feature_md_files.sort()
      for index, file in enumerate(feature_md_files):
        with open("features/" + feature + "/" + file) as feature_file:
          md = markdown.Markdown(extensions = ['meta'])
          feature_html = md.convert(feature_file.read())
          # noinspection PyUnresolvedReferences
          feature_metadata = parse_metadata(md.Meta)
          if feature_metadata["publish_time"] < render_at_time:
            soup = BeautifulSoup(feature_html, features="html.parser")

            features_with_blurb.append({
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
            full_page_html = render_content(feature_html, content_nav)

            out_path = os.path.join(output, "features/" + feature + "/" + as_html(file))
            with open(out_path, "w+") as file_output:
              file_output.write(full_page_html)
      all_features_with_blurb.extend(features_with_blurb)

      feature_index_html = ""

      for f_w_b in features_with_blurb:
        feature_index_html += render_cell(
          f_w_b["name"],
          f_w_b["url"],
          f_w_b["blurb"]
        )
      with open(os.path.join(output, "features/" + feature + "/index.html"), "w+") as feature_index:
        cells = "<div class=\"row\">" + feature_index_html + "</div>"
        feature_index.write(render_page(cells))

    front_page = []
    front_page.extend(all_features_with_blurb)
    front_page.extend(sites_with_blurb)
    front_page = sorted(front_page, key=lambda item: item["publish_time"], reverse=True)

    home_items = ""
    for index, item in enumerate(home):
      home_items += pystache.render(fpi_template, item)

    def convert(index, item):
      def feature_item(
          even,
          publish_time,
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
          'date': datetime.strftime(publish_time, "%B %-d, %Y"),
          'time': datetime.strftime(publish_time, "%H:%M")
        }

      def site_guide_item(
          even,
          publish_time,
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
          'date': datetime.strftime(publish_time, "%B %-d, %Y"),
          'time': datetime.strftime(publish_time, "%H:%M")
        }

      even = index % 2 != 0
      if item["type"] == "site":
        return site_guide_item(
          even,
          item["publish_time"],
          item["site_name"],
          item["site_path"],
          item["blurb"])
      elif item["type"] == "feature":
        return feature_item(
          even,
          item["publish_time"],
          item["feature_title"],
          item["feature_path"],
          item["feature_item_title"],
          item["feature_item_path"],
          item["blurb"]
        )
      else:
        raise("Unknown item type: " + item["type"])

    for (index, f) in enumerate(front_page):
      home_items += "<hr/>"
      front_page_item = convert(index, f)
      home_items += pystache.render(fpi_template, front_page_item)

    index_html = render_page(home_items)
    with open(os.path.join(output, "index.html"), "+w") as index_file:
      index_file.write(index_html)


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