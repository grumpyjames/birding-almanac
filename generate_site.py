import os

from datetime import datetime
import markdown
import pystache
import shutil
import sys
import time
from bs4 import BeautifulSoup


class TemplateRenderer:
  # Golly, this might be better modelled as a dict?
  def __init__(
      self,
      page_template,
      archive_template,
      content_template,
      content2_template,
      cell_template,
      fpi_template,
      fc_template,
  ):
    self.page_template = page_template
    self.archive_template = archive_template
    self.content_template = content_template
    self.content2_template = content2_template
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

  def render_content2_page(
      self,
      content_html,
      published_at,
      previously,
      nextUp):
    date = datetime.strftime(published_at, "%B %-d, %Y")
    time = datetime.strftime(published_at, "%H:%M")
    content = pystache.render(
      self.content2_template,
      {
        'main-content': content_html,
        'published-at-date': date,
        'published-at-time': time,
        'previously': previously,
        'next': nextUp
      }
    )
    return self.render_page(content)

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

  def render_each_with_nav(self, posts, write_item):
    for index, post in enumerate(posts):
      last = index == len(posts) - 1
      def maybe_url(p, default):
        if p is None:
          return default
        else:
          return f"<a href='{p['item-url']}'>{p['item-title']}</a>"

      prev_post = None if index - 1 < 0 else posts[index - 1]
      next_post = None if index + 1 >= len(posts) else posts[index + 1]

      full_page_html = self.render_content2_page(
        post["html"],
        post["publish_time"],
        maybe_url(prev_post, "This is the latest item"),
        maybe_url(next_post, "This is the first item")
      )

      write_item(post, last, full_page_html)

  def render_archive(self, views):
    content = pystache.render(
      self.archive_template,
      {
        "archive-months": views
      }
    )
    return self.render_page(content)


def create_website(output, render_at_time):
  with \
      open("page.mustache") as f, \
      open("archive.mustache") as a, \
      open("content.mustache") as c, \
      open("content2.mustache") as c2, \
      open("front_page_item.mustache") as fpi, \
      open("feature_cell.mustache") as fc, \
      open('by_name_cell.mustache') as cell:
    templating = TemplateRenderer(
      f.read(),
      a.read(),
      c.read(),
      c2.read(),
      cell.read(),
      fpi.read(),
      fc.read()
    )

  os.makedirs(output, exist_ok=True)
  copy_images(output)
  about_page(templating, output)
  sites_with_blurb = []
  sites(templating, render_at_time, output, sites_with_blurb)
  blog_posts = blog(templating, render_at_time, output)
  all_feature_items = []
  features(templating, render_at_time, output, all_feature_items)

  all_items = []
  all_items.extend(all_feature_items)
  all_items.extend(sites_with_blurb)
  all_items.extend(blog_posts)
  all_items = sorted(
    all_items,
    key=lambda item: item["publish_time"],
    reverse=True)

  front_page(templating, all_items, output)
  archive_page(templating, all_items, output)


# copy only if different, to preserve timestamps and prevent resync.
def lazy_image_copy(src, target):
  if not os.path.exists(target):
    shutil.copyfile(src, target)
  src_modify_time = os.stat(src).st_mtime
  tgt_modify_time = os.stat(target).st_mtime
  if src_modify_time > tgt_modify_time:
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

def front_page(templating, all_items, output):
  def convert(idx, item):
    even = idx % 2 != 0
    attrs = {
      'row-class': ('left' if even else 'right'),
      'img-class': ('float-right' if even else 'float-left'),
      'date': datetime.strftime(item["publish_time"], "%B %-d, %Y"),
      'time': datetime.strftime(item["publish_time"], "%H:%M"),
      'blurb': item["blurb"],
    }

    for attr in [
      "index-url",
      "index-title",
      "item-image",
      "item-url",
      "item-title"]:
      attrs[attr] = item[attr]
    return attrs

  home_items = ""
  first = True

  for (index, f) in enumerate(all_items[:10]):
    if not first:
      home_items += "<hr/>"
    first = False
    front_page_item = convert(index + 1, f)
    home_items += templating.render_front_page_item(front_page_item)

  home_items += """
    <hr>
    <div class="row">
      <div class="cell col-md-12 text-center">      
      Older content can be found in the <a href="/archive.html">Archive</a>    
    </div>
    </div>
  """

  index_html = templating.render_page(home_items)

  with open(os.path.join(output, "index.html"), "+w") as index_file:
    index_file.write(index_html)

def archive_page(templating: TemplateRenderer, all_items, output):
  by_month = {}
  for item in all_items:
    key = item["publish_time"].strftime("%B, %Y")
    if key not in by_month:
      by_month[key] = [item]
    else:
      by_month[key].append(item)

  views = []
  for k in by_month:
    def to_post(post):
      attrs = {}
      for attr in ["index-url", "index-title", "item-url", "item-title"]:
        attrs[attr] = post[attr]

      attrs['date'] = datetime.strftime(post["publish_time"], "%B %-d, %Y")
      attrs['time'] = datetime.strftime(post["publish_time"], "%H:%M")
      return attrs

    views.append({
      "key": k,
      "posts": [to_post(p) for p in by_month[k]]
    })

  with open(os.path.join(output, "archive.html"), "+w") as archive_file:
    archive_file.write(templating.render_archive(views))


def features(
    templating: TemplateRenderer,
    render_at_time,
    output,
    all_feature_items):

  feature_cells = []

  def as_html(md_file):
    return md_file.replace(".md", "") + ".html"

  def about_feature(path_to_feature):
    with open(path_to_feature + '/about.md') as about_feature_md:
      feature_blurb, about_metadata = templating.markdown(about_feature_md)
      feature_cells.append(templating.render_feature(
        about_metadata["feature_title"],
        "/" + path_to_feature,
        feature_blurb
      ))
    return about_metadata["feature_title"]

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
            'item-image': feature_path + '/' + file.replace(".md", "") + '-thumb.png',
            'item-url': '/' + feature_path + "/" + as_html(file),
            'item-title': feature_metadata["title"],
            'index-url': '/' + feature_path,
            'index-title': feature_title
          })

    def write_item(feature_item, _, full_page_html):
      out_path = os.path.join(output, feature_path + "/" + feature_item["url"])
      with open(out_path, "w+") as file_output:
        file_output.write(full_page_html)

    templating.render_each_with_nav(feature_items, write_item)

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
    output):
  def process_images(post_path, post_soup):
    def absolute(tag):
      for t in post_soup.find_all(tag):
        if not t['src'].startswith('/') \
            and not t['src'].startswith('http'):
          t['src'] = '/blog/' + post_path + '/' + t['src']
    absolute('img')
    absolute('source')

  os.makedirs(os.path.join(output, "blog"), exist_ok=True)

  posts = []

  for post_name in os.listdir("blog"):
    post_output_dir = os.path.join(output, "blog", post_name)
    os.makedirs(post_output_dir, exist_ok=True)
    post_input_dir = os.path.join("blog", post_name)
    for filename in os.listdir(os.path.join("blog", post_name)):
      if is_image(filename):
        lazy_image_copy(
          os.path.join(post_input_dir, filename),
          os.path.join(post_output_dir, filename))

    post_markdown_path = os.path.join(post_input_dir, post_name + ".md")
    with open(post_markdown_path) as blog_file:
      blog_html, metadata = templating.markdown(blog_file)
      if metadata["publish_time"] < render_at_time:
        soup = BeautifulSoup(blog_html, features="html.parser")
        process_images(post_name, soup)

        # noinspection PyUnresolvedReferences
        post = {
          'blurb': soup.p.text,
          'publish_time': metadata["publish_time"],
          'updated_time': metadata["updated_time"],
          'html': str(soup),
          'output_directory': post_output_dir,
          'item-image': '/blog/' + post_name + '/' + post_name + '-thumb.png',
          'item-url': '/blog/' + post_name + '/index.html',
          'item-title': metadata["title"],
          'index-url': "/blog/index.html",
          'index-title': "Blog"
        }

        posts.append(post)

  posts = sorted(
    posts,
    key=lambda item: item["publish_time"],
    reverse=True)

  def write_item(item, last, full_page_html):
    blog_index_path = os.path.join(item["output_directory"], "index.html")
    with open(blog_index_path, "w+") as file_output:
      file_output.write(full_page_html)

    if last:
      with open(os.path.join(output, 'blog/index.html'), "w+") as list_index:
        list_index.write(full_page_html)

  posts = sorted(
    posts,
    key=lambda item: item["publish_time"],
    reverse=False)
  templating.render_each_with_nav(posts, write_item)

  posts = sorted(
    posts,
    key=lambda item: item["publish_time"],
    reverse=True)
  return posts


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
          'item-image': f"/sites/{site_name}-thumb.png",
          'item-url': f"/sites/{site_name}.html",
          'item-title': site_name.replace("_", " "),
          'index-url': "/sites/index.html",
          'index-title': "Site Guides",
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

start = time.monotonic_ns()

output_directory = sys.argv[1]
if len(sys.argv) > 2:
  time_of_render = datetime.strptime(sys.argv[2], "%Y-%m-%dT%H:%M:%S.%fZ")
else:
  time_of_render = datetime.now()

create_website(output_directory, time_of_render)

end = time.monotonic_ns()

taken_nanos = end - start
print(f"Generated site in {taken_nanos / 1_000_000_000}s")