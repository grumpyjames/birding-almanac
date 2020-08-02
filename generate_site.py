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
    self.md = markdown.Markdown(extensions=['meta'])

  def render_page(self, page_html):
    return pystache.render(
      self.page_template,
      {
        'content': page_html
      }
    )

  def render_content(
      self,
      metadata: dict,
      content_html,
      content_nav = None):
    publish_time = metadata["publish_time"]

    return pystache.render(
      self.content_template,
      {
        'date': datetime.strftime(publish_time, "%B %-d, %Y"),
        'time': datetime.strftime(publish_time, "%H:%M"),
        'main-content': content_html,
        'content-nav': "" if content_nav is None else content_nav
      }
    )

  def render_content_page(
      self,
      metadata,
      content_html,
      content_nav = None):
    page_html = self.render_content(metadata, content_html, content_nav)
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

  def markdown(self, file):
    html = self.md.convert(file.read())
    # noinspection PyUnresolvedReferences
    metadata = self.parse_metadata(self.md.Meta)
    return html, metadata

  @staticmethod
  def parse_metadata(metadata_dict):
    date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    result = {}
    for k in metadata_dict:
      v = metadata_dict[k][0]
      if k in ["publish_time", "updated_time"]:
        result[k] = datetime.strptime(v, date_format)
      else:
        result[k] = v

    return result

def create_website(output, render_at_time):
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
  blogs_with_blurb = {}
  blog(templating, render_at_time, output, blogs_with_blurb)
  all_feature_items = []
  features(templating, render_at_time, output, all_feature_items)
  front_page(templating, all_feature_items, sites_with_blurb, blogs_with_blurb, output)


# copy only if different, to preserve timestamps and prevent resync.
def lazy_image_copy(src, target):
  import filecmp
  if not os.path.exists(target):
    shutil.copyfile(src, target)
  elif not filecmp.cmp(src, target):
    shutil.copyfile(src, target)

def is_image(file):
  return file.endswith(".png") \
      or file.endswith(".ico") \
      or file.endswith(".mp4")

def copy_images(output):
  for file in os.listdir("."):
    if is_image(file):
      lazy_image_copy(
        file,
        os.path.join(output, file)
      )


def about_page(templating, output):
  with open("about.mustache") as about:
    about_html = templating.render_page(about.read())
    with open(os.path.join(output, "about.html"), "w+") as out:
      out.write(about_html)

def front_page(templating, all_feature_items, sites_with_blurb, blogs_with_blurb, output):
  front_page_items = []
  front_page_items.extend(all_feature_items)
  front_page_items.extend(sites_with_blurb)
  front_page_items.extend(blogs_with_blurb["other_posts"])
  front_page_items = sorted(front_page_items, key=lambda item: item["publish_time"], reverse=True)

  def convert(index, item):
    even = index % 2 != 0
    common = {
      'row-class': ('left' if even else 'right'),
      'img-class': ('float-right' if even else 'float-left'),
      'date': datetime.strftime(item["publish_time"], "%B %-d, %Y"),
      'time': datetime.strftime(item["publish_time"], "%H:%M"),
      'blurb': item["blurb"],
    }

    if item["type"] == "site":
      custom = {
        'index-link': '/sites/index.html',
        'index-title': 'Site Guides',
        'item-link': '/sites/' + item["site_path"] + '.html',
        'item-title': item["site_name"],
        'image': '/sites/' + item["site_path"] + '-thumb.png',
      }
    elif item["type"] == "blog":
      custom = {
        'index-link': '/blog/index.html',
        'index-title': 'Blog',
        'item-link': '/blog/' + item["blog_path"] + '/index.html',
        'item-title': item["title"],
        'image': '/blog/' + item["blog_path"] + '/' + item["blog_path"] +
                 '-thumb.png',
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
      raise Exception("Unknown item type: " + item["type"])
    return  {**common, **custom}

  home_items = ""
  first = True
  if len(front_page_items) > 50:
    raise Exception("Time to implement pagination, Jimbo")

  for (index, f) in enumerate(front_page_items):
    if not first:
      home_items += "<hr/>"
    first = False
    front_page_item = convert(index + 1, f)
    home_items += templating.render_front_page_item(front_page_item)
  index_html = templating.render_page(home_items)
  with open(os.path.join(output, "index.html"), "+w") as index_file:
    index_file.write(index_html)


def features(
    templating: TemplateRenderer,
    render_at_time,
    output,
    all_feature_items):

  feature_cells = []

  def as_html(md_file):
    return md_file.replace(".md", "") + ".html"

  def about_feature(path_to_feature):
    with open(path_to_feature + '/about.md') as about_feature:
      feature_blurb, feature_metadata = templating.markdown(about_feature)
      feature_title = feature_metadata["feature_title"]
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
      if is_image(file):
        src = feature_path + '/' + file
        lazy_image_copy(src, os.path.join(output, src))
      elif file.endswith(".md") and file != "about.md":
        feature_md_files.append(file)

    feature_md_files.sort()
    for index, file in enumerate(feature_md_files):
      with open(feature_path + "/" + file) as feature_file:
        feature_html, feature_metadata = templating.markdown(feature_file)
        if feature_metadata["publish_time"] < render_at_time:
          soup = BeautifulSoup(feature_html, features="html.parser")

          # noinspection PyUnresolvedReferences
          feature_items.append({
            'html': feature_html,
            'url': as_html(file),
            'metadata': feature_metadata,
            'name': (str(index + 1) + ": " + soup.h3.text),
            'blurb': soup.p.text,
            'publish_time': feature_metadata["publish_time"],
            'updated_time': feature_metadata["updated_time"],
            'type': 'feature',
            'feature_path': feature,
            'feature_title': feature_title,
            'feature_item_path': file.replace(".md", ""),
            'feature_item_title': feature_metadata["title"]
          })

    for index, feature_item in enumerate(feature_items):
      nav = []
      if index > 0:
        previous_file = feature_md_files[index - 1]
        prev_file_link = as_html(previous_file)
        nav += "<a class='nav-previous' href='" + prev_file_link + "'>Previous</a>"
      if index + 1 < len(feature_items):
        next_file_link = as_html(feature_md_files[index + 1])
        nav += "<a class='nav-next' href='" + next_file_link + "'>Next</a>"
      content_nav = "".join(nav)
      full_page_html = templating.render_content_page(
        feature_item["metadata"],
        feature_item["html"],
        content_nav)

      out_path = os.path.join(output, feature_path + "/" + feature_item["url"])
      with open(out_path, "w+") as file_output:
        file_output.write(full_page_html)

    all_feature_items.extend(feature_items)

    feature_index_html = ""

    if len(feature_items) == 0:
      feature_index_html += templating.render_cell(
        "There's nothing here yet",
        "#",
        "But there will be soon :-)"
      )
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


def blog(
    templating: TemplateRenderer,
    render_at_time,
    output,
    blogs_with_blurb):
  def process_images(blog_name, soup):
    for img in soup.find_all('img'):
      if not img['src'].startswith('/') \
          and not img['src'].startswith('http'):
        img['src'] = blog_name + '/' + img['src']

  os.makedirs(os.path.join(output, "blog"), exist_ok=True)

  other_posts = []

  for blog_name in os.listdir("blog"):
    blog_output_dir = os.path.join(output, "blog", blog_name)
    os.makedirs(blog_output_dir, exist_ok=True)
    blog_input_dir = os.path.join("blog", blog_name)
    for filename in os.listdir(os.path.join("blog", blog_name)):
      if is_image(filename):
        lazy_image_copy(
          os.path.join(blog_input_dir, filename),
          os.path.join(blog_output_dir, filename))

    blog_markdown_path = os.path.join(blog_input_dir, blog_name + ".md")
    with open(blog_markdown_path) as blog_file:
      blog_html, metadata = templating.markdown(blog_file)
      if metadata["publish_time"] < render_at_time:
        soup = BeautifulSoup(blog_html, features="html.parser")
        process_images(blog_name, soup)

        blog_content_html = templating.render_content(metadata, blog_html)
        full_page_html = templating.render_page(blog_content_html)
        blog_index_html = templating.render_content(metadata, str(soup))

        # noinspection PyUnresolvedReferences
        post = {
          'name': blog_name,
          'blurb': soup.p.text,
          'publish_time': metadata["publish_time"],
          'updated_time': metadata["updated_time"],
          'type': 'blog',
          'blog_name': blog_name.replace("_", " "),
          'blog_path': blog_name,
          'title': metadata["title"],
          'html': blog_index_html
        }

        other_posts.append(post)

        blog_index_path = os.path.join(blog_output_dir, "index.html")
        with open(blog_index_path, "w+") as file_output:
          file_output.write(full_page_html)

  other_posts = sorted(
    other_posts,
    key=lambda item: item["publish_time"],
    reverse=True)

  all_posts = []
  all_posts.extend(other_posts)
  first = True

  if len(all_posts) > 10:
    raise Exception("Time to implement pagination, Jimbo")

  list_index_content = ""
  for blog in all_posts:
    if not first:
      list_index_content += "<hr/>"
    list_index_content += blog["html"]
    first = False

  with open(os.path.join(output, 'blog/index.html'), "w+") as list_index:
    list_index.write(templating.render_page(list_index_content))

  blogs_with_blurb["other_posts"] = other_posts


def sites(
    templating: TemplateRenderer,
    render_at_time,
    output,
    sites_with_blurb):
  os.makedirs(os.path.join(output, "sites"), exist_ok=True)

  sites_to_convert = []

  for filename in os.listdir("sites"):
    if filename.endswith(".md"):
      sites_to_convert.append((filename, filename.replace(".md", "")))
    elif is_image(filename):
      lazy_image_copy("sites/" + filename, os.path.join(output, "sites/" + filename))
  for (f, site_name) in sites_to_convert:
    with open(os.path.join("sites", f)) as site_file:
      site_html, metadata = templating.markdown(site_file)
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

        full_page_html = templating.render_content_page(metadata, site_html)
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


output = sys.argv[1]
if len(sys.argv) > 2:
  render_at_time = datetime.strptime(sys.argv[2], "%Y-%m-%dT%H:%M:%S.%fZ")
else:
  render_at_time = datetime.now()

create_website(output, render_at_time)