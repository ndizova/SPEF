
import curses
import curses.ascii
import yaml
import os
import traceback

from modules.buffer import Buffer, Report, Tags, Note

# from utils.printing import *
from utils.logger import *
from utils.match import *



""" **************** CONFIG **************** """
def load_config_from_file():
    utils_dir = os.path.dirname(__file__)
    src_dir = os.path.abspath(os.path.join(utils_dir, os.pardir))
    conf_file = os.path.join(src_dir, CONFIG_FILE)
    try:
        with open(conf_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as err:
        log("cannot load config file | "+str(err)+" | "+str(traceback.format_exc()))
        return None

def load_control_from_file():
    utils_dir = os.path.dirname(__file__)
    src_dir = os.path.abspath(os.path.join(utils_dir, os.pardir))
    control_file = os.path.join(src_dir, CONTROL_FILE)
    try:
        with open(control_file, 'r') as f:
            control = yaml.safe_load(f)
        return control
    except Exception as err:
        log("cannot load control file | "+str(err)+" | "+str(traceback.format_exc()))
        return None


""" **************** PROJECT **************** """
def load_proj_from_conf_file(path):
    # load data from yaml file
    project_file = os.path.join(path, PROJ_CONF_FILE)
    try:
        with open(project_file, 'r') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as err:
        log("cannot load project file | "+str(err)+" | "+str(traceback.format_exc()))
        return None

def save_proj_to_conf_file(path, data):
    project_file = os.path.join(path, PROJ_CONF_FILE)
    try:
        with open(project_file, 'w+', encoding='utf8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as err:
        log("cannot save project conf to file | "+str(err)+" | "+str(traceback.format_exc()))



""" ************* TYPICAL NOTES ************* """
def get_typical_notes_file_name():
    utils_dir = os.path.dirname(__file__)
    src_dir = os.path.abspath(os.path.join(utils_dir, os.pardir))
    notes_file = os.path.join(src_dir, TYPICAL_NOTES_FILE)
    return notes_file

def load_typical_notes_from_file():
    notes_file = get_typical_notes_file_name()
    notes = []
    try:
        with open(notes_file, 'r') as f:
            lines = f.read().splitlines()

        """ parse notes to list of Note objects """
        for line in lines:
            notes.append(Note(line))
    except FileNotFoundError:
        return []
    except Exception as err:
        log("cannot load file with typical notes | "+str(err)+" | "+str(traceback.format_exc()))

    return notes


def save_typical_notes_to_file(notes):
    """ save list of Note objects to file """
    if notes:
        lines = []
        for note in notes:
            lines.append(note.text)

        notes_file = get_typical_notes_file_name()
        with open(notes_file, 'w+') as f:
            lines = '\n'.join(lines)
            f.write(lines)




""" **************** REPORT **************** """
def get_report_file_name(path):
    file_name = os.path.splitext(path)[:-1]
    return str(os.path.join(*file_name))+REPORT_SUFFIX

def load_report_from_file(path, add_suffix=True, orig_file_name=None):
    report_file = get_report_file_name(path) if add_suffix else path
    report = Report(report_file, [])
    try:
        with open(report_file, 'r') as f: # first line is comment with file name
            first_line = f.readline()
            if first_line.startswith('#'):
                orig_file_name = first_line[1:]
        with open(report_file, 'r') as f:
            data = yaml.safe_load(f)
        notes = []
        """ parse notes from directory to list of Note objects """
        for row in data:
            for col in data[row]:
                for text in data[row][col]:
                    note = Note(text, row=row, col=col)
                    notes.append(note)
        report = Report(report_file, notes)
    except yaml.YAMLError as err:
        pass
    except FileNotFoundError:
        pass
    except Exception as err:
        log("load report | "+str(err)+" | "+str(traceback.format_exc()))
    finally:
        report.orig_file_name = orig_file_name
        return report


def save_report_to_file(report):
    """ parse notes list of Note objects to directory """
    notes = {}
    for note in report.data:
        if note.row is not None and note.col is not None:
            if note.row in notes:
                if note.col in notes[note.row]:
                    notes[note.row][note.col].append(note.text)
                else:
                    notes[note.row][note.col] = [note.text]
            else:
                notes[note.row] = {note.col: [note.text]}
        else:
            notes[0][0].append(note.text)

    """ save data to file """
    try:
        with open(report.path, 'w+', encoding='utf8') as f:
            if report.orig_file_name is not None:
                f.write(f"#{report.orig_file_name}\n")
        with open(report.path, 'a', encoding='utf8') as f:
            yaml.dump(notes, f, default_flow_style=False, allow_unicode=True)
        report.last_save = report.data.copy()
    except Exception as err:
        log("save report to file | "+str(err)+" | "+str(traceback.format_exc()))


""" **************** TAGS **************** """
def get_tags_file_name(path):
    file_name = os.path.splitext(path)[:-1]
    return str(os.path.join(*file_name))+TAGS_SUFFIX

# def load_tags_from_file(path):
def tmp(path):
    tags_file = get_tags_file_name(path)
    tags = None
    try:
        with open(tags_file, 'r') as f:
            data = yaml.safe_load(f)
        tags = Tags(tags_file, data)
    except yaml.YAMLError as err:
        tags = Tags(tags_file, {})
    except FileNotFoundError:
        tags = Tags(tags_file, {})
    except Exception as err:
        log("load tags | "+str(err)+" | "+str(traceback.format_exc()))
    return tags



def load_solution_tags(solution_dir):
    if os.path.exists(solution_dir):
        tags_file = os.path.join(solution_dir, SOLUTION_TAGS)
        return load_tags(tags_file)
    else:
        return None

def load_tests_tags(solution_tests_dir):
    if os.path.exists(solution_tests_dir):
        tags_file = os.path.join(solution_tests_dir, TESTS_TAGS)
        return load_tags(tags_file)
    else:
        return None

def load_testsuite_tags(proj_tests_dir):
    if os.path.exists(proj_tests_dir):
        tags_file = os.path.join(proj_tests_dir, TESTSUITE_TAGS)
        return load_tags(tags_file)
    else:
        return None

def load_testcase_tags(proj_testcase_dir):
    if os.path.exists(proj_tests_dir):
        tags_file = os.path.join(proj_testcase_dir, TESTCASE_TAGS)
        return load_tags(tags_file)
    else:
        return None


def load_tags(tags_file):
    if tags_file is None:
        return None
    tags = None
    try:
        with open(tags_file, 'r+') as f:
            data = yaml.safe_load(f)
        tags = Tags(tags_file, data)
    except yaml.YAMLError as err:
        tags = Tags(tags_file, {})
    except FileNotFoundError:
        tags = Tags(tags_file, {})
    except Exception as err:
        log("load tags | "+str(err)+" | "+str(traceback.format_exc()))
    finally:
        return tags



def load_tags_from_file(path):
    tags_file = get_tags_file(path)
    if tags_file is None:
        return None
    return load_tags(tags_file)


# in proj/solution/tests/   show "tests_tags.yaml"
# in proj/solution/         show "solution_tags.yaml"
# in proj/tests/testxx/     show "test_tags.yaml"
# in proj/tests/            show "testsuite_tags.yaml"
# else cant use tags
def get_tags_file(path, proj=None):
    if not os.path.exists(path):
        log(f"get tags file | path '{path}' doesnt exists ")
        return None

    if proj is not None:
        solution_id = proj.solution_id
    else:
        solution_id = None
        proj_path = get_proj_path(path)
        if proj_path is not None:
            proj_data = load_proj_from_conf_file(proj_path)
            if proj_data is not None:
                solution_id = proj_data['solution_id']

    if solution_id is not None:
        tags_file = None
        path_dir = path if os.path.isdir(path) else os.path.dirname(path)
        solution_root_dir = get_root_solution_dir(solution_id, path)
        tests_root_dir = get_root_tests_dir(path)
        if solution_root_dir is not None:
            if tests_root_dir is not None:
                tags_file = os.path.join(tests_root_dir, TESTS_TAGS)
            else:
                tags_file = os.path.join(solution_root_dir, SOLUTION_TAGS)
        elif tests_root_dir is not None:
            testcase_dir = get_root_testcase_dir(path)
            if testcase_dir is not None:
                tags_file = os.path.join(testcase_dir, TESTCASE_TAGS)
            else:
                tags_file = os.path.join(tests_root_dir, TESTSUITE_TAGS)
        return tags_file
    else:
        log(f"get tags file | path '{path}' is probably not in proj dir ")
    return None



def save_tags_to_file(tags):
    if tags is not None:
        with open(tags.path, 'w+', encoding='utf8') as f:
            yaml.dump(tags.data, f, default_flow_style=False, allow_unicode=True)


""" **************** BUFFER AND TAGS **************** """
def load_buffer_and_tags(env):
    """ try load file content to buffer """
    file_already_loaded = False
    if env.buffer and env.buffer.path == env.file_to_open:
        buffer = env.buffer
    else:
        try:
            with open(env.file_to_open, 'r') as f:
                lines = f.read().splitlines()
            buffer = Buffer(env.file_to_open, lines)
            env.buffer = buffer
        except UnicodeDecodeError as err:
            log("load file content ("+str(env.file_to_open)+") | "+str(err))
            return env, None, False
        except Exception as err:
            log("load file content ("+str(env.file_to_open)+") | "+str(err)+" | "+str(traceback.format_exc()))
            env.set_exit_mode()
            return env, None, False
    env = load_tags_if_changed(env)
    return env, buffer, True


def load_tags_if_changed(env, path=None):
    if path is None:
        path = env.file_to_open
    if path is not None and env.cwd.proj is not None:
        """ try load file tags to env """
        tags_file = get_tags_file(path, env.cwd.proj)
        if tags_file is not None:
            if not env.tags:
                env.tags = load_tags(tags_file)
            else:
                if env.tags.path != tags_file:
                    env.tags = load_tags(tags_file)
    return env


""" **************** SAVE BUFFER **************** """
def save_buffer(file_name, buffer, report=None):
    with open(file_name, 'w') as f:
        lines = '\n'.join(buffer.lines)
        f.write(lines)
    buffer.set_save_status(True)
    buffer.last_save = buffer.lines.copy()
    if report:
        save_report_to_file(report)

