#!/usr/bin/env python

import codecs
import datetime
import hashlib
import os
import re
import shutil
import subprocess

import cssmin
import jsmin


build_regex = re.compile(
    '(<\!--\s*build:(\w+)\s+([\w\$\-\./]*)\s*-->(.*?)<\!--\s*endbuild\s-->)',
    re.MULTILINE | re.DOTALL
)
src_regex = re.compile('src=["\']([^"\']+)["\']')
href_regex = re.compile('href=["\']([^"\']+)["\']')
html_comment_regex = re.compile('<\!--.*?-->', re.MULTILINE | re.DOTALL)

def _find_html_pages(source):
    paths = []
    for each in os.listdir(source):
        path = os.path.join(source, each)
        if os.path.isdir(path):
            paths.extend(_find_html_pages(path))
        elif os.path.isfile(path) and path.endswith('.html'):
            paths.append(path)
    return paths


def read(path):
    with codecs.open(path, 'r', 'utf-8') as f:
        return f.read()


def write(path, content):
    mkdir(os.path.dirname(path))
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(content)


def mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        return
    if os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired "
                      "dir, '%s', already exists." % newdir)
    head, tail = os.path.split(newdir)
    if head and not os.path.isdir(head):
        mkdir(head)
    if tail:
        os.mkdir(newdir)


def get_git_revision(short=False):
    sha = subprocess.check_output('git rev-parse HEAD'.split()).strip()
    if short:
        sha = sha[:10]
    return sha


def already_minified(filename):
    for part in ('-min-', '-min.', '.min.', '.minified.', '.pack.', '-jsmin.'):
        if part in filename:
            return True
    return False


def hash_all_css_images(css_code, rel_dir, source_dir, dest_dir):
    def replacer(match):
        filename = match.groups()[0]
        if (filename.startswith('"') and filename.endswith('"')) or \
          (filename.startswith("'") and filename.endswith("'")):
            filename = filename[1:-1]
        if 'data:image' in filename or filename.startswith('http://'):
            return 'url("%s")' % filename
        if filename == '.':
            # this is a known IE hack in CSS
            return 'url(".")'
        # It's really quite common that the CSS file refers to the file
        # that doesn't exist because if you refer to an image in CSS for
        # a selector you never use you simply don't suffer.
        # That's why we say not to warn on nonexisting files
        new_filename = filename
        full_path = os.path.abspath(os.path.join(rel_dir, filename))

        if os.path.isfile(full_path):
            hash = hashlib.md5(open(full_path, 'rb').read()).hexdigest()[:10]
            a, b = os.path.splitext(filename)
            new_filename = '%s-%s%s' % (a, hash, b)
            new_filename = os.path.basename(new_filename)
            new_filepath = os.path.abspath(os.path.join(dest_dir, new_filename))
            mkdir(os.path.dirname(new_filepath))
            shutil.copyfile(full_path, new_filepath)

        return match.group().replace(filename, new_filename)
    _regex = re.compile('url\(([^\)]+)\)')
    css_code = _regex.sub(replacer, css_code)

    return css_code


def minify_javascript(code):
    try:
        p = subprocess.Popen(
            ['uglifyjs'],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate(input=code)
        return stdout
    except OSError:
        return jsmin.jsmin(code)


class Page(object):

    def __init__(self, path, source_directory, output_directory,
                 compress_js=True, compress_css=True,
                 inline_js=False, inline_css=True,
                 remove_html_comments=False,
                 git_revision=None):
        self.path = path
        self.source_directory = source_directory
        if not output_directory.endswith('/'):
            output_directory += '/'
        self.output_directory = output_directory
        self.compress_js = compress_js
        self.compress_css = compress_css
        self.inline_js = inline_js
        self.inline_css = inline_css
        self.remove_html_comments = remove_html_comments
        self.processed_files = [path]
        self.git_revision = git_revision

    def _parse_html(self):
        content = read(self.path)
        for whole, type_, destination_name, bulk in build_regex.findall(content):

            if type_ == 'remove':
                content = content.replace(whole, '')
                continue
            else:
                output_directory = self.output_directory
                output_directory = os.path.join(
                    output_directory,
                    os.path.dirname(destination_name)
                )

            combined = []
            template = None
            if type_ == 'js':
                if self.inline_js:
                    output_directory = self.output_directory
                for src in src_regex.findall(bulk):
                    if src.startswith('/'):
                        path = self.source_directory + src
                    else:
                        path = os.path.join(self.source_directory, src)
                    this_content = read(path)
                    self.processed_files.append(path)
                    if not already_minified(os.path.basename(path)):
                        this_content = minify_javascript(this_content)
                    combined.append('/* %s */' % src)
                    combined.append(this_content.strip())
                if self.inline_js:
                    template = '<script>%s</script>'
                else:
                    tag_template = '<script src="%s"></script>'
            elif type_ == 'css':
                if self.inline_css:
                    output_directory = self.output_directory
                for href in href_regex.findall(bulk):
                    if href.startswith('/'):
                        path = self.source_directory + href
                    else:
                        path = os.path.join(self.source_directory, href)
                    this_content = read(path)
                    this_content = hash_all_css_images(
                        this_content,
                        os.path.dirname(path),
                        self.source_directory,
                        output_directory
                    )
                    self.processed_files.append(path)
                    if not already_minified(os.path.basename(path)):
                        this_content = cssmin.cssmin(this_content)
                    combined.append('/* %s */' % href)
                    combined.append(this_content.strip())
                if self.inline_css:
                    template = '<style>%s</style>'
                else:
                    tag_template = '<link rel="stylesheet" href="%s">'

            combined.append('')  # so it ends with a newline
            combined = '\n'.join(combined)
            if template:
                content = content.replace(
                    whole,
                    template % combined
                )
            else:
                if '$hash' in destination_name:
                    destination_name = destination_name.replace(
                        '$hash',
                        hashlib.md5(combined).hexdigest()[:7]
                    )
                if '$date' in destination_name:
                    destination_name = destination_name.replace(
                        '$date',
                        datetime.datetime.utcnow().strftime('%Y-%m-%d')
                    )

                if destination_name.startswith('/'):
                    destination_name = destination_name[1:]
                destination_path = os.path.join(
                    self.output_directory,
                    destination_name
                )

                write(destination_path, combined)
                remove = self.output_directory
                if remove.endswith('/'):
                    remove = remove[:-1]
                destination_path = destination_path.replace(remove, '')
                content = content.replace(
                    whole,
                    tag_template % destination_path
                )

        if self.remove_html_comments:
            def comment_replacer(match):
                group = match.group()
                beginning = group[len('<!--'):].strip()
                if beginning.startswith('!'):
                    return group.replace('<!--!', '<!--')
                return ''
            content = html_comment_regex.sub(comment_replacer, content)
        else:
            content = content.replace('<!--!', '<!--')

        if '$git_revision_short' in content:
            content = content.replace(
                '$git_revision_short',
                self.get_git_revision(short=True)
            )
        if '$git_revision' in content:
            content = content.replace(
                '$git_revision',
                self.get_git_revision()
            )

        return content

    def parse(self):
        new_content = self._parse_html()
        out_path = self.path.replace(
            self.source_directory,
            self.output_directory
        )
        write(out_path, new_content)

    def get_git_revision(self, short=False):
        if self.git_revision:
            if short:
                return self.git_revision[:10]
            else:
                return self.git_revision
        else:
            return get_git_revision(short=short)


def copy_files(source, dest, processed_files):
    for each in os.listdir(source):
        path = os.path.join(source, each)
        if os.path.isdir(path):
            copy_files(
                path,
                os.path.join(dest, each),
                processed_files
            )
        elif each.endswith('~'):
            pass
        elif path not in processed_files:
            mkdir(dest)
            shutil.copyfile(path, os.path.join(dest, each))


def run(
        source_directory,
        output_directory='./dist',
        wipe_first=False,
        inline_js=False,
        inline_css=False,
        remove_html_comments=False,
        git_revision=None,
    ):

    if wipe_first:
        assert output_directory not in source_directory
        if os.path.isdir(output_directory):
            shutil.rmtree(output_directory)

    processed_files = []
    if not source_directory:
        raise ValueError("no directory to read from set")
    if not os.path.isdir(source_directory):
        raise IOError('%s is not a directory' % source_directory)
    for html_file in _find_html_pages(source_directory):
        page = Page(
            html_file,
            source_directory,
            output_directory,
            inline_js=inline_js,
            inline_css=inline_css,
            remove_html_comments=remove_html_comments,
            git_revision=git_revision,
        )
        page.parse()
        processed_files.extend(page.processed_files)

    copy_files(source_directory, output_directory, processed_files)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'source_directory',
        help='Where the raw stuff is',
    )
    parser.add_argument(
        '-o',
        '--output-directory',
        help='Where the generated stuff goes (default ./dist)',
        default='./dist',
    )
    parser.add_argument(
        '-w',
        '--wipe-first',
        help='Clear output directory first',
        default=False,
        dest='wipe_first',
        action='store_true'
    )
    parser.add_argument(
        '--remove-html-comments',
        help='Removes all HTML comments',
        default=False,
        dest='remove_html_comments',
        action='store_true'
    )
    parser.add_argument(
        '--inline-css',
        help='Make all CSS inline',
        default=False,
        dest='inline_css',
        action='store_true'
    )
    parser.add_argument(
        '--inline-js',
        help='Make all JS inline',
        default=False,
        dest='inline_js',
        action='store_true'
    )
    parser.add_argument(
        '--git-revision',
        help='Known git revision sha to use',
        default='',
    )
    args = parser.parse_args()
    return run(
        source_directory=args.source_directory,
        output_directory=args.output_directory,
        wipe_first=args.wipe_first,
        inline_js=args.inline_js,
        inline_css=args.inline_css,
        remove_html_comments=args.remove_html_comments,
        git_revision=args.git_revision,
    )


if __name__ == '__main__':
    import sys
    sys.exit(main())
