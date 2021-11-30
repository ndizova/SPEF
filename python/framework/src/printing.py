import curses
import os
import re

from loading import save_buffer
from buffer import UserInput
from logger import *
from coloring import *

ESC = 27


"""
    CTRL + Q    delete filter

    CTRL + L    hard reload (from original buff)
    CTRL + H    enable/disable note highlight

    CTRL + D    show notes detail
    CTRL + R    remove note
    CTRL + E    edit note
    CTRL + Down next note
    CTRL + Up   prev note

    CTRL + N    show/hide line numbers
"""


def print_hint(conf, filter_mode=False):
    screen = conf.down_screen
    screen.erase()
    screen.border(0)
    size = screen.getmaxyx()

    view_switch = "off" if conf.quick_view else "on"
    B_HELP = {"F1":"help", "F2":"menu", "F3":f"view {view_switch}","F4":"edit", "F5":"copy",
                "F6":"rename", "F8":"delete", "F9":"filter", "F10":"exit"}
    E_HELP = {"F1":"help", "F2":"save", "F3":"view/tag", "F4":"note", "F5":"goto",
                "F8":"reload", "F9":"filter", "F10":"exit"}
    V_HELP = {"F1":"help", "F4":"edit file", "F5":"goto", "F9":"filter", "F10":"exit"}
    T_HELP = {"F1":"help", "F4":"edit tags", "F9":"filter", "F10":"exit"}

    if filter_mode:
        if conf.is_brows_mode(): filter_type = "path"
        elif conf.is_view_mode(): filter_type = "content"
        elif conf.is_tag_mode(): filter_type = "tag"
        else: filter_type = None

        if not filter_type:
            help_dict = {}
        else:
            help_dict = {"F1":"help", "ESC":"exit filter mode", 
                        "F8":"remove all filters", "F9":f"edit {filter_type} filter"}
    elif conf.is_brows_mode():
        help_dict = B_HELP
    elif conf.is_view_mode():
        help_dict = E_HELP if conf.edit_allowed else V_HELP
    elif conf.is_tag_mode():
        help_dict = T_HELP
    else:
        help_dict = {}


    string = ""
    for key in help_dict:
        hint = " | " + str(key) + ":" + str(help_dict[key])
        if len(string) + len(hint) <= size[1]:
            string += hint
    screen.addstr(1, 1, string[2:])
    screen.refresh()



def print_help(screen, max_cols, max_rows, conf, filter_mode=False):
    screen.erase()
    screen.border(0)
    mode = ""
    if filter_mode:
        mode = "FILTER MANAGEMENT"
        actions = {"ESC, F10": "exit filter management",
        "F8": "delete/remove all filters",
        "F1": "show this user help",
        "Arrows": "move cursor in user input",
        "Delete, Backspace": "delete symbol in user input",
        "Ascii character": "insert symbol in user input",
        "Enter": "set filter and exit filter management"}

    elif conf.is_brows_mode():
        mode = "DIRECTORY BROWSING"
        actions = {"F10": "exit program",
        "F9": "set filter by path",
        "F7": "show/hide project info",
        "F6": "show/hide cached files (tags, report)",
        "F4": "opent file for edit",
        "F3": "set quick view mode on/off",
        "F2": "open menu with other functions",
        "F1": "show this user help",
        "TAB": "change focus to file view or edit",
        "Arrows": "brows between files and dirs"}
    elif conf.is_view_mode():
        if conf.edit_allowed:
            mode = "FILE EDIT"
            actions = {"F10": "exit program",
            "F9": "set filter by content",
            "F8": "reload file content from last save",
            "F6": "show/hide note highlight",
            "F5": "show/hide line numbers",
            "F4": "open note management",
            "F3": "change to file view/tag mode",
            "F2": "save file changes",
            "F1": "show this user help",
            "TAB": "change focus to directory browsing or note management",
            "Arrows": "move cursor in file content",
            "Delete, Backspace": "delete symbol in file on current cursor position",
            "Ascii character": "insert symbol in file on current cursor position",
            "Enter": "insert new line in file on current cursor position",
            "CTRL + Up/Down": "jump to prev/next line with note in file",
            "CTRL + L": "reload file content from original buffer",
            "CTRL + R": "remove all notes on current line"}
        else:
            mode = "FILE VIEW"
            actions = {"F10": "exit program",
            "F9": "set filter by content",
            "F6": "show/hide note highlight",
            "F5": "show/hide line numbers",
            "F4": "change to file edit mode",
            "F1": "show this user help",
            "TAB": "change focus to tag management",
            "Arrows": "move cursor in file content"}
    elif conf.is_tag_mode():
        mode = "TAG MANAGEMENT"
        actions = {"F10": "exit program",
        "F9": "set filter by tag",
        "F8": "delete current tag",
        "F4": "open file with tags for edit",
        "F3": "create new tag",
        "F2": "edit current tag",
        "F1": "show this user help",
        "TAB": "change focus to directory browsing",
        "Arrows": "brows between tags"}
    if mode and actions:
        exit_message = "Press ESC or F1 to hide user help."
        message = f"*** USER HELP FOR {mode} ***"
        if len(message) > max_cols or len(exit_message) > max_cols:
            return
        screen.addstr(1, 1, exit_message, curses.color_pair(HELP))
        screen.addstr(2, int(max_cols/2-len(message)/2), message, curses.A_NORMAL)
        line = 3
        for key in actions:
            action = actions[key]
            if line < max_rows:
                if len(key)+2 > max_cols:
                    break
                screen.addstr(line, 1, str(key), curses.color_pair(HELP))
                # if it doesnt fit to windows weight
                free_space = max_cols-len(key)-3
                if len(action) > free_space:
                    words = action.split()
                    while words:
                        if line > max_rows:
                            break
                        part = ""
                        word = words[0]
                        while len(part)+len(word)+1 < free_space:
                            part += " "+word
                            del words[0]
                            if not words:
                                break
                            word = words[0]
                        screen.addstr(line, 3+len(key), str(part), curses.A_NORMAL)
                        line +=1
                else:
                    screen.addstr(line, 3+len(key), str(action), curses.A_NORMAL)
                    line += 1
        screen.refresh()



EXIT_WITHOUT_SAVING_MESSAGE = """WARNING: Exit without saving.\n\
    Press F2 to save and exit.\n\
    Press {} to force exiting without saving.\n\
    Press any other key to continue editing your file."""

RELOAD_FILE_WITHOUT_SAVING = """WARNING: Reload file will discard changes.\n\
    Press F2 to save changes.\n\
    Press {} or Enter to reload file and discard all changes.\n\
    Press any other key to continue editing your file."""

""" check if file changes are saved or user want to save or discard them """
def show_unsaved_changes_warning(stdscr, conf, warning=None, exit_key=None):
    if conf.buffer:
        if (conf.buffer.is_saved) or (conf.buffer.original_buff == conf.buffer.lines):
            return True
        else:
            curses_key, str_key = exit_key if exit_key else (ESC, "ESC")
            message = warning if warning else EXIT_WITHOUT_SAVING_MESSAGE
            """ print warning message """
            screen = conf.right_screen
            screen.erase()
            screen.addstr(1, 1, str(message.format(str_key)), curses.A_BOLD)
            screen.border(0)
            screen.refresh()

            key = stdscr.getch()
            if key == curses_key: # force exit without saving
                return True
            elif key == curses.KEY_F2: # save and exit
                save_buffer(conf.file_to_open, conf.buffer, conf.report)
                return True
            else:
                return False
    else:
        return True



""" show file name/path of currently opened file/directory """
def show_path(screen, path, max_cols):
    while len(path) > max_cols-2:
        path = path.split(os.sep)[1:]
        path = "/".join(path)
    dir_name = str(path)
    screen.addstr(0, int(max_cols/2-len(dir_name)/2), dir_name)
    screen.refresh()


def show_user_input(screen, user_input, max_rows, max_cols, conf, color=None, title=None):
    screen.erase()
    screen.border(0)

    row = 1
    if title:
        screen.addstr(row, 1, title[:max_cols-1], color if color else curses.A_NORMAL)
        row += 1

    last_row = row
    last_col = 1
    if user_input:
        max_cols -= 1
        user_input_str = ''.join(user_input.text)
        # if len(user_input_str) > max_cols:
        words = re.split(r'(\S+)',user_input_str) # split string into list of words and spaces
        split_words = []
        for word in words:
            # if any word is longer than window, split it
            if len(word) >= max_cols:
                while len(word) >= max_cols:
                    part = word[:max_cols-1]
                    log(part)
                    split_words.append(part)
                    word = word[max_cols-1:]
            split_words.append(word)

        words = split_words
        while words:
            if row > max_rows:
                break
            part = ""
            word = words[0]
            while len(part)+len(word) < max_cols:
                part += word
                del words[0]
                if not words:
                    break
                word = words[0]
            log(part)
            screen.addstr(row, 1, str(part), curses.A_NORMAL)
            last_col = 1+len(part)
            last_row = row
            row +=1

    screen.refresh()
    return last_row, last_col


def show_filter(screen, user_input, max_rows, max_cols, conf, color=None):
    if user_input:
        user_input_str = ''.join(user_input.text)

        if user_input.col_shift > 0 and len(user_input_str) > user_input.col_shift:
            user_input_str = user_input_str[user_input.col_shift + 1:]

    if not user_input.text:
        empty_message = ""
        if conf.is_brows_mode(): empty_message = "add path filter... ex: test1/unit_*.* "
        elif conf.is_view_mode(): empty_message = "add content filter... ex: def test1 "
        elif conf.is_tag_mode(): empty_message = "add tag filter... ex: #plagiat(.*) "
        empty_message += " "*(max_cols-1-len(empty_message))
        screen.addstr(max_rows, 1, empty_message[:max_cols-1], curses.color_pair(FILTER) | curses.A_ITALIC)
    else:
        user_input_str += " "*(max_cols-1-len(user_input_str))
        screen.addstr(max_rows, 1, user_input_str[:max_cols-1], color if color else curses.color_pair(FILTER))
    screen.refresh()


def show_directory_content(screen, win, cwd, conf):
    screen.erase()
    screen.border(0)

    print_hint(conf)

    dirs, files = cwd.get_shifted_dirs_and_files(win.row_shift)
    max_cols = win.end_x - win.begin_x
    max_rows = win.end_y - win.begin_y - 1
    # last_row = win.last_row
    try:
        """ show dir content """
        if cwd.is_empty():
            if conf.filter_not_empty():
                screen.addstr(1, 1, "* No file matches with current filter *", curses.A_NORMAL | curses.A_BOLD)
            else:
                screen.addstr(1, 1, "* This directory is empty *", curses.A_NORMAL | curses.A_BOLD)
        else:
            i=1
            for dir_name in dirs:
                if i > max_rows:
                    break
                elif i == max_rows and conf.filter:
                    if conf.filter.path:
                        break
                coloring = (curses.color_pair(SELECT) if i+win.row_shift == win.cursor.row+1 else curses.A_NORMAL)
                screen.addstr(i, 1, "/"+str(dir_name[:max_cols-2]), coloring | curses.A_BOLD)
                i+=1
            for file_name in files:
                if i > max_rows:
                    break
                elif i == max_rows and conf.filter:
                    if conf.filter.path:
                        break
                coloring = curses.color_pair(SELECT) if i+win.row_shift == win.cursor.row+1 else curses.A_NORMAL
                screen.addstr(i, 1, str(file_name[:max_cols-1]), coloring)
                i+=1

        """ show path filter if there is one """
        if conf.filter:
            if conf.filter.path:
                user_input = UserInput()
                user_input.text = conf.filter.path
                show_filter(screen, user_input, max_rows, max_cols, conf)

        """ show dir name """
        show_path(screen, cwd.path, max_cols)

    except Exception as err:
        log("show directory | "+str(err))
    finally:
        screen.refresh()



def show_file_content(screen, win, buffer, report, conf, user_input=None):
    screen.erase()
    screen.border(0)

    print_hint(conf)

    max_cols = win.end_x - win.begin_x
    max_rows = win.end_y - win.begin_y - 1
    # last_row = win.last_row

    if buffer is None:
        screen.refresh()
        return

    """ highlight lines with notes """
    colored_lines = []
    if conf.note_highlight and report:
        for key in report.code_review:
            colored_lines.append(int(key))


    shift = len(conf.line_numbers)+1 if conf.line_numbers else 0
    try:
        """ show file content """
        if buffer:
            for row, line in enumerate(buffer[win.row_shift : max_rows + win.row_shift]):
                if (user_input is not None) and (row == max_rows-1):
                    break
                if (row + win.begin_y == win.cursor.row - win.row_shift) and (win.col_shift > 0):
                    line = line[win.col_shift + 1:]
                if len(line) > max_cols - 1 - shift:
                    line = line[:max_cols - 1 - shift]
                color = curses.color_pair(NOTE_HIGHLIGHT) if (row+1+win.row_shift in colored_lines) else curses.A_NORMAL
                if conf.line_numbers:
                    screen.addstr(row+1, 1, str(row+win.row_shift), curses.color_pair(LINE_NUM))
                screen.addstr(row+1, 1+shift, line, color)

        """ show user input from note entering """
        if user_input:
            color=curses.color_pair(NOTE_MGMT)
            show_filter(screen, user_input, max_rows, max_cols, conf, color=color)
        elif conf.filter:
            if conf.filter.content:
                user_input = UserInput()
                user_input.text = conf.filter.content
                show_filter(screen, user_input, max_rows, max_cols, conf)

        """ show file name """
        show_path(screen, buffer.path, max_cols+(shift if conf.line_numbers else 1))

    except Exception as err:
        log("show file | "+str(err))
    finally:
        screen.refresh()



def show_tags(screen, win, tags, conf, user_input=None):
    screen.erase()
    screen.border(0)

    if tags is None:
        screen.refresh()
        return

    max_cols = win.end_x - win.begin_x
    max_rows = win.end_y - win.begin_y - 1
    # last_row = win.last_row
    try:
        """ show tags """
        if tags.data:
            for row, name in enumerate(tags.data):
                if row > max_rows or (row == max_rows and conf.tag_filter_on()):
                    break
                if row+win.row_shift == win.cursor.row and conf.is_tag_mode():
                    coloring = curses.color_pair(SELECT)
                else:
                    coloring = curses.A_NORMAL

                params = tags.data[name]
                str_params = "(" + ",".join(map(str,params)) + ")"
                line = "#"+str(name)+str_params
                if len(line) > max_cols -1:
                    line = line[:max_cols - 1]
                screen.addstr(row+1, 1, line, coloring)


        """ show tag filter if there is one """
        if conf.tag_filter_on():
            user_input = UserInput()
            user_input.text = conf.filter.tag
            show_filter(screen, user_input, max_rows, max_cols, conf)

        """ show file name """
        show_path(screen, tags.path, max_cols)

    except Exception as err:
        log("show tags | "+str(err))
    finally:
        screen.refresh()