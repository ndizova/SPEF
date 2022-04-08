import os
import glob
import fnmatch
import json
import re
import traceback
import datetime

from modules.buffer import Tags, UserInput

from utils.loading import *
from utils.logger import *
from utils.match import *


""" represents content of current working directory (cwd)"""
class Directory:
    def __init__(self, path, dirs=None, files=None):
        self.path = path
        self.dirs = [] if dirs is None else dirs
        self.files = [] if files is None else files

        self.proj = None # None or project object (if its project subdirectory)


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

    def get_proj_conf(self):
        try:
            proj_path = get_proj_path(self.path)
            if proj_path is not None:
                proj_data = load_proj_from_conf_file(proj_path)
                # create Project obj from proj data
                self.proj = Project(proj_path)
                self.proj.set_values_from_conf(proj_data)
        except Exception as err:
            log("get proj conf | "+str(err)+" | "+str(traceback.format_exc()))



class Project:
    def __init__(self, path):
        self.path = path
        self.created = None
        self.tests_dir = None
        self.solution_id = None

        self.sut_required = ""
        self.sut_ext_variants = []

        self.description = ""
        self.test_timeout = 0
        self.solutions_dir = None
        self.solution_quick_view = None
        self.solution_test_quick_view = None

    def set_values_from_conf(self, data):
        try:
            self.created = data['created']
            self.tests_dir = data['tests_dir']
            self.solution_id = data['solution_id']
            self.sut_required = data['sut_required']
            self.sut_ext_variants = data['sut_ext_variants']
        except:
            log("wrong data for proj")


    def set_default_values(self):
        self.created = datetime.date.today() # date of creation
        self.tests_dir = "tests"
        self.solution_id =  "x[a-z]{5}[0-9]{2}" # default solution identifier: xlogin00
        self.sut_required = "sut" # default file name of project solution is "sut" (system under test)
        self.sut_ext_variants = ["*sut*", "sut.sh", "sut.bash"]


        self.test_timeout = 5
        self.solutions_dir = "solutions"
        self.solution_quick_view = "auto_report"
        self.solution_test_quick_view = "stdout"


    """
    solution info = informacie ktore sa zobrazia pre xlogin00 dir
    * informacie sa zarovnaju vpravo
    * informacie su oddelene medzerou
    * ak informacia nematchne ani jeden predikat -- nema sa zobrazit, zostane namiesto nej prazdne miesto

    * identifier = id informacie (int)
                -- urcuje poradie v akom sa informacie zobrazuju zprava
                -- ak sa do okna nezmestia vsetky info, ako prve sa schovaju tie s najvacsim identifier
    * visualization = ako sa ma informacia zobrazit
                -- idealne pouzit len jeden znak
                -- cim menej miesta to zaberie, tym viac roznych info viem zobrazit
                -- mozno pouzit aj priamo hodnotu parametra nejakeho tagu --- POZOR !!!
                    -- mozu sa pouzivat len hodnoty z jedno-parametrovych tagov
                    -- musi byt dodrzany striktny format zadavania: param FROM #tag_name(param)
                    -- napr: datetime FROM #last_testing(datetime)
                    -- napr: body FROM #scoring(body)
                    -- zobrazenie hodnoty mozu byt rozne pre kazde riesenie
                        -- to moze viest k tomu ze sa zobrazovane informacie rozsynchronizuju
                        -- vizualne to teda nemusi vyzerat dobre (ked sa ostatne info posunu lebo je tento parameter dlhy)
                        -- odporuca sa preto definovat hodnotu length (vid dalej)
    * length = (optional) urcuje maximalnu dlzku informacie pre vizualizaciu
                -- tato hodnota nemusi byt definovana
                -- je vhodne definovat ak sa pri vizualizacii pouziva parameter tagu (hodnota ktora moze byt premenna pre rozne riesenia)
                -- napr. ak viem ze vizualizujem celkove skore riesenia
                    -- viem ze nebude viac ako 100, teda viem ze bude max dvojciferne
                    -- chcem ho teda zarovnat na dva znaky --> length=2
                    -- ak pre dane riesenie nenajdem #scoring tak bude namiesto cisla zobrazena medzera o velkosti 2
    * description = strucny popis informacie
                -- lubovolny retazec (idealne nie moc dlhy)
                -- zobrazi sa v nahlade informacii (po zadani "show details about project solution informations" v menu)
    * predicates = zoznam predikatov
                -- urcuju za akych podniemok sa informacia zobrazi a s akou farbou
                -- na zobrazenie informacie sa musi aspon jedna podniemka z predikatov [...] vyhodnotit ako True
                -- ak su splnene viacere podmienky predikatov, pouzije sa farba z prveho, ktory sa matchne
                * predicate = podmienka zobrazenia informacie
                        -- pracuje s tagmi (funguje rovnako ako filter podla tagov)
                        -- u tagov sa skuma:
                            -- existencia = odkazuje na vsoebecnu existenciu tagu bez ohladu na parameter,  napr: plag
                            -- zhoda = odkazuje na zhodu tagu aj parametru podla regex,                     napr: scoring(^[0-5])
                            -- porovnanie = odkazuje na porovnanie tagu s niecim,                           napr: body FROM #scoring(body) > 0
                * color = farba zobrazenia informacie
                        -- ak sa podmienka v danom predikate vyhodnoti na True
                        -- potom sa pouzije tato definovana farba na vyzobrazenie informacie
                        -- ak farba nie je definovana, pouzije sa Normal (biela)
                        -- farba sa zadava pomocou
                                ??? preddefinovanych hodnot: white, red, green, blue  (gray, cyan, yellow, orange, pink)
                                ??? GRB hodnot
                                ??? #hex hodnot
    -- tagy mozno pouzit u visualization a predicate
    -- ak ma nejake info rovnaky indentifier, porovnaju sa jeho predikaty...
        -- ak je splneny predikat len jednej z info --> zobrazi sa
        -- ak nie je splneny predikat ziadnej       --> nezobrazi sa ziadna
        -- ak je splneny predikat oboch             --> zobrazi sa prva v poradi v zozname

    POSTUP PRI ZOBRAZOVANI:
    1. get solution_info from proj conf
    2. zoradir solution_info podla identifier (od najmensieho po najvacsie)
    3. for info in solution_info -- citam zprava a pridavam zlava
    a) if visualization je hodnota parametru tagu
        1. zisti tuto hodnotu
        2. ak taky tag neexistuje --> nezobrazuj info a chod dalej
        3. pozri ci je definovana length
        4. ak neni, by default daj length = 1 medzera
    b) else
        1. pozri ci je definovana length
        2. ak neni, by default daj length = len(visualization)
    c) for predicate in predicates -- resp while predicate not matches
        1. spracuj predicate
        2. vyhodnot predicate
        3. ak matchol, konci a vrat farbu ak je definovana, inak vrat Normal farbu
        4. ak nematchol pokracuj v cykle
        5. ak uz nie su dalsie predicates --> nezobrazuj info a chod dalej
    d) ak mas co zobrazit, pridaj zlava hodnotu v danej farbe + 1 medzeru
    e) ak nemas co zobrazit, pridaj zlava medzeru*length + 1 medzeru

    """

    def get_solution_info(self):
        # sorting by id: [... 3 2 1]

        # default info
        date = {
            'identifier': 1,
            'visualization': 'datetime FROM #last_testing(datetime)', # vypise sa ak existuje tag #last_testing
            'length': 12, #10-12 15:30
            'description': 'datetime of last test',
            'predicates': []
        }
        status = {
            'identifier': 2,
            'visualization': 'T',
            'description': 'was tested',
            'predicates': [
                {'predicate': 'testsuite_done', 'color': ''} # tag: testsuite_done sa prida na konci testsuite.sh
            ]
        }
        group = {
            'identifier': 3,
            'visualization': 'G',
            'desrcription': "is group project",
            'predicates': [
                {'predicate': 'group', 'color': ''}
            ]
        }
        plagiat = {
            'identifier': 4,
            'visualization': '!',
            'description': 'is plagiat',
            'predicates': [
                {'predicate': 'plag', 'color': 'red'}
            ]
        }

        # test results
        """
        test1 = {
            'identifier': 8,
            'visualization': '.',
            'description': 'test1 result',
            'predicates': [
                {'predicate': 'test1_fail', 'color': 'red'},
                {'predicate': 'test1_ok', 'color': 'green'}
            ]
        }
        test2 = {
            'identifier': 7,
            'visualization': '.',
            'description': 'test2 result',
            'predicates': [
                {'predicate': 'test2_fail', 'color': 'red'},
                {'predicate': 'test2_ok', 'color': 'green'}
            ]
        }
        """

        solution_info = [date, status, group, plagiat, test1, test2, test3, test4]
        return solution_info

    def to_dict(self):
        
        solution_info = self.get_solution_info()
        return {
            'created': self.created,
            'tests_dir': self.tests_dir,
            'solution_id': self.solution_id,
            'sut_required': self.sut_required,
            'sut_ext_variants': self.sut_ext_variants,
            'solution_info': solution_info
        }
        #     'tests_dir': self.tests_dir
        #     'test_timeout': self.test_timeout
        #     'solutions_dir': self.solutions_dir
        #     'solution_id': self.solution_id
        #     'solution_quick_view': self.solution_quick_view
        #     'solution_test_quick_view': self.solution_test_quick_view
        # }



""" class for currently set filters (by path, file content or tag) """
class Filter:
    def __init__(self, root):
        self.root = root # root path

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


    """ search for files with match of all set filters in root directory """
    def find_files(self, env):
        matches = []

        if self.path:
            matches = self.get_files_by_path(self.root, self.path)

        if self.content:
            # if some filtering has already been done, search for files only in its matches
            # else search all files in root directory
            files = matches if self.path else self.get_files_in_dir_recursive(self.root)
            matches = self.get_files_by_content(files)

        if self.tag:
            files = matches if (self.path or self.content) else self.get_files_in_dir_recursive(self.root)
            matches = self.get_files_by_tag(env, files)

        filtered_files = []
        for file_path in matches:
            file_name = os.path.relpath(file_path, self.root)
            filtered_files.append(file_name)
        filtered_files.sort()
        self.files = filtered_files


    """ remove all filteres """
    def reset_all(self):
        self.path = None
        self.content = None
        self.tag = None


    """ remove filter according to current mode (ex: if broswing, remove filter by path) """
    def reset_by_current_mode(self, env):
        if env.is_brows_mode():
            self.path = None
        if env.is_view_mode():
            self.content = None
        if env.is_tag_mode():
            self.tag = None


    """ set filter according to current mode """
    def add_by_current_mode(self, env, text):
        if env.is_brows_mode():
            self.path = text
        if env.is_view_mode():
            self.content = text
        if env.is_tag_mode():
            self.tag = text



    """ returns list of all files in directory (recursive) """
    def get_files_in_dir_recursive(self, dir_path):
        files = []
        for root, dirnames, filenames in os.walk(dir_path):
            files.extend(os.path.join(root, filename) for filename in filenames)
        return files


    """ 
    src: source directory path
    dest: destination path to match
    """
    def get_files_by_path(self, src, dest):
        try:
            path_matches = []
            dest_path = os.path.join(src, "**", dest+"*")
            for file_path in glob.glob(dest_path, recursive=True):
                if os.path.isfile(file_path):
                    path_matches.append(file_path)
            return path_matches
        except Exception as err:
            log("Filter by path | "+str(err)+" | "+str(traceback.format_exc()))
            return []


    """ 
    files: files to filter
    content: content to match
    """
    def get_files_by_content(self, files):
        try:
            content_matches = []
            for file_path in files:
                with open(file_path) as f:
                    if self.content in f.read():
                        content_matches.append(file_path)
            return content_matches
        except Exception as err:
            log("Filter by content | "+str(err)+" | "+str(traceback.format_exc()))
            # if there is some exception, dont apply filter, just ignore it and return all files
            return files


    """
    files: files to filter
    tag: tag to match, ex: "test1(0,.*,2,[0-5],5)"
    """
    def get_files_by_tag(self, env, files):
        return files
        # TODO !!!!!!!!!
        # if len(files) > 10:
        #     upozornenie_moze_to_dlho_trvat
        #     chces_naozaj_pokracovat??
        #     if no:
        #         return files


        if not is_in_project_dir(self.root):
            log("filter by tag | there is no tags (bcs you are not in proj dir)")
            return files

        try:
            tag_matches = set()

            """ parse tag """
            tag_parsing_ok = False
            if re.match('\w(...)', self.tag):
                components = re.split('[()]', self.tag)
                # log(components)
                if len(components)>0:
                    # search only for tag name
                    tag_name = components[0]
                    compare_args = None
                    tag_parsing_ok = True
                    if len(components)>1 and components[1]!="":
                        compare_args = list(map(str, components[1].split(',')))

            if not tag_parsing_ok:
                log("invalid input for tag filter")
                return files
            else:
                for file_path in files:
                    tags = load_tags_from_file(file_path)
                    if tags and len(tags)>0:
                        if tags.find(tag_name, compare_args):
                            tag_matches.add(file_path)
                return tag_matches
        except Exception as err:
            log("Filter by tag | "+str(err)+" | "+str(traceback.format_exc()))
            return files
