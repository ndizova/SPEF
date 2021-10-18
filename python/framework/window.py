
"""
-Window reprezentuje zobrazovane okno (view win) v obrazovke (screen)
-shift sluzi na zobrazenie spravnej casti obsahu do okna  

vyber riadku    buffer[self.row - win.begin_y]
koniec riadku   len(buffer[self.row - win.begin_y]) + win.begin_x   

"""

LEFT_EDGE = 2
RIGHT_EDGE = 2


import datetime
LOG_FILE = "/home/naty/Others/ncurses/python/framework/log"
def log(message):
    day = datetime.date.today()
    time = datetime.datetime.now().strftime("%X")
    with open(LOG_FILE, 'a') as f:
        f.write("{} {} | {}\n".format(day,time,message))


class Cursor:
    def __init__(self, row=0, col=0, col_last=None):
        self.row = row
        self._col = col
        self._col_last = col_last if col_last else col

    @property
    def col(self):
        return self._col

    @col.setter
    def col(self,col):
        self._col = col
        self._col_last = col

    def up(self, buffer, win, use_restrictions=True):
        if self.row > win.begin_y:
            self.row -= 1
            if use_restrictions:
                self._restrict_col(buffer, win)

    def down(self, buffer, win, use_restrictions=True):
        if self.row - win.begin_y < len(buffer) - 1:
            self.row += 1
            if use_restrictions:
                self._restrict_col(buffer, win)

    def left(self, buffer, win):
        if self.col > win.begin_x: # if not start of the line (if col > 0)
            self.col -= 1
        elif self.row > win.begin_y: # (if row > 0) move to the end of prev line if there is one
            self.row -= 1
            self.col = len(buffer[self.row - win.begin_y]) + win.begin_x

    def right(self, buffer, win):
        if self.col < len(buffer[self.row - win.begin_y]) + win.begin_x: # if its not end of the line
            self.col += 1
        elif self.row < len(buffer) - 1: # else go to the start of next line if there is one
            self.row += 1
            self.col = win.begin_x

    """ restrict the cursors column to be within the line we move to """
    def _restrict_col(self, buffer, win):
        end_of_line = len(buffer[self.row - win.begin_y])+win.begin_x
        self._col = min(self._col_last, end_of_line)


class Window:
    def __init__(self, height, width, begin_y, begin_x):
        """ position / location """
        self.begin_y = begin_y # height (max_rows = end_y - begin_y)
        self.begin_x = begin_x # width (max_cols = end_x - begin_x)
        self.end_y = begin_y + height - 1
        self.end_x = begin_x + width - 1

        """ shift position """
        self.row_shift = 0 # y
        self.col_shift = 0 # x

        """ cursor """
        self.cursor = Cursor(row=begin_y,col=begin_x)


    @property
    def bottom(self):
        return self.end_y + self.row_shift - 1

    def up(self, buffer, use_restrictions=True):
        self.cursor.up(buffer, self, use_restrictions)

        """ window shift """
        self.horizontal_shift()
        if (self.cursor.row - self.begin_y == self.row_shift - 1 ) and (self.row_shift > 0):
            self.row_shift -= 1


    def down(self, buffer, use_restrictions=True):
        self.cursor.down(buffer, self, use_restrictions)

        """ window shift """
        self.horizontal_shift()
        if (self.cursor.row == self.bottom) and (self.cursor.row - self.begin_y < len(buffer)):
            self.row_shift += 1


    def left(self, buffer):
        self.cursor.left(buffer, self)

        """ window shift """
        self.horizontal_shift()
        if (self.cursor.row == self.row_shift + 1) and (self.row_shift > 0):
            self.row_shift -= 1

        # _, col = self.get_cursor_position()
        # shift = self.end_x - self.begin_x - RIGHT_EDGE - LEFT_EDGE
        # if (col + 1 - LEFT_EDGE == self.begin_x) and (self.col_shift >= shift):
            # self.col_shift -= shift


    def right(self, buffer):
        self.cursor.right(buffer, self)

        """ window shift """
        self.horizontal_shift()
        if (self.cursor.row == self.bottom) and (self.cursor.row - self.begin_y < len(buffer)):
            self.row_shift += 1

        # _, col = self.get_cursor_position()
        # width = self.end_x - self.begin_x
        # if ((col - self.begin_x) // (width - RIGHT_EDGE)) > 0:
            # self.col_shift += width - RIGHT_EDGE - LEFT_EDGE


    def horizontal_shift(self):
        """ horizontal shift """
        width = self.end_x - self.begin_x
        shift = width - RIGHT_EDGE - LEFT_EDGE
        pages = (self.cursor.col - self.begin_x) // (width - RIGHT_EDGE)
        self.col_shift = pages * shift


    def get_cursor_position(self):
        new_col = self.cursor.col - self.col_shift - (1 if self.col_shift > 0 else 0)
        new_row = self.cursor.row - self.row_shift
        return new_row, new_col


    def set_cursor(self, begin_y, begin_x):
        self.cursor = Cursor(row=begin_y,col=begin_x)

    def reset_shifts(self):
        self.row_shift = 0
        self.col_shift = 0

    def reset_window(self):
        self.reset_shifts()
        self.set_cursor(self.begin_y, self.begin_x)

    def resize(self, width, height, begin_x, begin_y):
        self.begin_x = begin_x
        self.begin_y = begin_y
        self.end_x = begin_x + width
        self.end_y = begin_y + height

        self.cursor = Cursor(row=begin_y,col=begin_x)

        # check for shifts (row and col)
