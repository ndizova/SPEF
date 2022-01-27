import os
import glob
import fnmatch
import json
import re

from modules.buffer import Tags
from utils.loading import load_tags_from_file
from utils.logger import *



""" represents content of current working directory (cwd)"""
class Directory:
    def __init__(self, path, dirs=[], files=[]):
        self.path = path
        self.dirs = dirs
        self.files = files

    def __len__(self):
        return len(self.dirs) + len(self.files)

    def is_empty(self):
        return not (self.dirs or self.files)
 
    """ returns dirs and files currently displayed due to a shift in the browsing window"""
    def get_shifted_dirs_and_files(self, shift):
        if shift > 0:
            dirs_count = len(self.dirs)
            if shift == dirs_count:
                dirs = []
                files = self.files
            elif shift > dirs_count:
                dirs = []
                files = self.files[(shift-dirs_count):]
            else:
                dirs = self.dirs[shift:]
                files = self.files
            return dirs, files
        else:
            return self.dirs, self.files


    """ returns list of all items (directories and files) in current working directory"""
    def get_all_items(self):
        items = self.dirs.copy()
        items.extend(self.files)
        return items


""" class for currently set filters (by path, file content or tag) """
class Filter:
    def __init__(self, project):
        self.project = project # search for filtered files only in current project

        self.path = None
        self.content = None
        self.tag = None

        self.files = []

    def is_empty(self):
        return not (self.path or self.content or self.tag)

    """ add filter by path """
    def add_path(self, path):
        self.path = path

    """ add filter by file content """
    def add_content(self, content):
        self.content = content

    """ add filter by tag """
    def add_tag(self, tag):
        self.tag = tag


    """ search for files with match of all set filters in project directory """
    def find_files(self, conf):
        matches = []

        if self.path:
            matches = get_files_by_path(self.project, self.path)

        if self.content:
            # if some filtering has already been done, search for files only in its matches
            # else search all files in project directory
            files = matches if self.path else get_files_in_dir_recursive(self.project)
            matches = get_files_by_content(files, self.content)

        if self.tag:
            files = matches if (self.path or self.content) else get_files_in_dir_recursive(self.project)
            matches = get_files_by_tag(files, self.tag)

        filtered_files = []
        for file_path in matches:
            file_name = os.path.relpath(file_path, self.project)
            filtered_files.append(file_name)
        filtered_files.sort()
        self.files = filtered_files


    """ remove all filteres """
    def reset_all(self):
        self.path = None
        self.content = None
        self.tag = None


    """ remove filter according to current mode (ex: if broswing, remove filter by path) """
    def reset_by_current_mode(self, conf):
        if conf.is_brows_mode():
            self.path = None
        if conf.is_view_mode():
            self.content = None
        if conf.is_tag_mode():
            self.tag = None


    """ set filter according to current mode """
    def add_by_current_mode(self, conf, text):
        if conf.is_brows_mode():
            self.path = text
        if conf.is_view_mode():
            self.content = text
        if conf.is_tag_mode():
            self.tag = text



""" returns list of all files in directory (recursive) """
def get_files_in_dir_recursive(dir_path):
    files = []
    for root, dirnames, filenames in os.walk(dir_path):
        files.extend(os.path.join(root, filename) for filename in filenames)
    return files


""" 
src: source directory path
dest: destination path to match
"""
def get_files_by_path(src, dest):
    try:
        path_matches = []
        dest_path = os.path.join(src, "**", dest)
        for file_path in glob.glob(dest_path, recursive=True):
            if os.path.isfile(file_path):
                path_matches.append(file_path)
        return path_matches
    except Exception as err:
        log("Filter by path | "+str(err))
        return []


""" 
files: files to filter
content: content to match
"""
def get_files_by_content(files, content):
    try:
        content_matches = []
        for file_path in files:
            with open(file_path) as f:
                if content in f.read():
                    content_matches.append(file_path)
        return content_matches
    except Exception as err:
        log("Filter by content | "+str(err))
        # if there is some exception, dont apply filter, just ignore it and return all files
        return files


""" 
files: files to filter
tag: tag to match, ex: "#test1(0,.*,2,[0-5],5)"
"""
def get_files_by_tag(files, tag):
    try:
        tag_matches = []

        """ parse tag """
        tag_parsing_ok = False
        if re.match('#\w(...)', tag):
            components = re.split('[#()]', tag)
            log(components)
            if components[0]=='' and components[-1]=='': # there is nothing before and after the tag
                components = components[1:-1]
                if len(components)==2: # there is only tag name and tag arguments, nothing else
                    tag_name, args = components
                    compare_args = list(map(str, args.split(',')))
                    tag_parsing_ok = True

        if not tag_parsing_ok:
            user_input = UserInput()
            user_input.text = "invalid input for tag filter... press F1 to see how to use tag filter "
            max_cols = conf.right_down_win.end_x - conf.right_down_win.begin_x
            max_rows = conf.right_down_win.end_y - conf.right_down_win.begin_y - 1
            show_filter(conf.right_down_screen, user_input, max_rows, max_cols, conf)
        else:
            for file_path in files:
                tags = load_tags_from_file(file_path)
                if tags and len(tags)>0:
                    if tags.find(tag_name, compare_args):
                        tag_matches.append(file_path)
            return tag_matches
    except Exception as err:
        log("Filter by tag | "+str(err))
        return files
