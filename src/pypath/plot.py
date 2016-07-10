#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#
#  This file is part of the `pypath` python module
#
#  Copyright (c) 2014-2016 - EMBL-EBI
#
#  File author(s): Dénes Türei (denes@ebi.ac.uk)
#
#  Distributed under the GNU GPLv3 License.
#  See accompanying file LICENSE.txt or copy at
#      http://www.gnu.org/licenses/gpl-3.0.html
#
#  Website: http://www.ebi.ac.uk/~denes
#

from future.utils import iteritems
from past.builtins import xrange, range, reduce

import re
import sys
import os
import itertools
import imp

import math
import numpy as np
from numpy.random import randn
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.cluster.hierarchy as hc

try:
    import hcluster as hc2
except:
    sys.stdout.write('\t :: Module `hcluster` not available.\n')
import matplotlib.gridspec as gridspec
import matplotlib.backends.backend_pdf
from matplotlib import ticker
from scipy import stats

import pypath.common as common
import pypath.colorgen as colorgen

def is_opentype_cff_font(filename):
    """
    This is necessary to fix a bug in matplotlib:
    https://github.com/matplotlib/matplotlib/pull/6714
    Returns True if the given font is a Postscript Compact Font Format
    Font embedded in an OpenType wrapper.  Used by the PostScript and
    PDF backends that can not subset these fonts.
    """
    if os.path.splitext(filename)[1].lower() == '.otf':
        result = _is_opentype_cff_font_cache.get(filename)
        if result is None:
            with open(filename, 'rb') as fd:
                tag = fd.read(4)
            result = (tag == b'OTTO')
            _is_opentype_cff_font_cache[filename] = result
        return result
    return False

mpl.font_manager.is_opentype_cff_font = is_opentype_cff_font

if not 'next' in __builtins__:
    def next(gen):
        return gen.next()

# helper functions

def rotate_labels(angles = (0, -90, -135, -180, -270, -315)):
    i = 0
    while True:
        yield angles[i % len(angles)]
        i += 1

def move_labels(dist = (0, 10, 20, 30, 40, 50, 60, 70)):
    i = 0
    while True:
        yield dist[i % len(dist)] if i < 20 else 20
        i += 1

def overlap(bbox1, bbox2):
    return (bbox1._points[0][0] > bbox2._points[0][0] and \
        bbox1._points[0][0] < bbox2._points[1][0] or \
        bbox1._points[1][0] > bbox2._points[0][0] and \
        bbox1._points[1][0] < bbox2._points[1][0] or \
        bbox2._points[0][0] > bbox1._points[0][0] and \
        bbox2._points[0][0] < bbox1._points[1][0] or \
        bbox2._points[1][0] > bbox1._points[0][0] and \
        bbox2._points[1][0] < bbox1._points[1][0]) and \
        (bbox1._points[0][1] > bbox2._points[0][1] and \
        bbox1._points[0][1] < bbox2._points[1][1] or \
        bbox1._points[1][1] > bbox2._points[0][1] and \
        bbox1._points[1][1] < bbox2._points[1][1] or \
        bbox2._points[0][1] > bbox1._points[0][1] and \
        bbox2._points[0][1] < bbox1._points[1][1] or \
        bbox2._points[1][1] > bbox1._points[0][1] and \
        bbox2._points[1][1] < bbox1._points[1][1])

def get_moves(bbox1, bbox2):
    xmove = 0
    ymove = 0
    if bbox1._points[0][0] > bbox2._points[0][0] and \
        bbox1._points[0][0] < bbox2._points[1][0] or \
        bbox1._points[1][0] > bbox2._points[0][0] and \
        bbox1._points[1][0] < bbox2._points[1][0] or \
        bbox2._points[0][0] > bbox1._points[0][0] and \
        bbox2._points[0][0] < bbox1._points[1][0] or \
        bbox2._points[1][0] > bbox1._points[0][0] and \
        bbox2._points[1][0] < bbox1._points[1][0]:
        if (bbox1._points[0][0] + bbox1._points[1][0]) / 2.0 < \
            (bbox2._points[0][0] + bbox2._points[1][0]) / 2.0:
            xmove = bbox1._points[1][0] - bbox2._points[0][0]
        else:
            xmove = bbox1._points[0][0] - bbox2._points[1][0]
    if bbox1._points[0][1] > bbox2._points[0][1] and \
        bbox1._points[0][1] < bbox2._points[1][1] or \
        bbox1._points[1][1] > bbox2._points[0][1] and \
        bbox1._points[1][1] < bbox2._points[1][1] or \
        bbox2._points[0][1] > bbox1._points[0][1] and \
        bbox2._points[0][1] < bbox1._points[1][1] or \
        bbox2._points[1][1] > bbox1._points[0][1] and \
        bbox2._points[1][1] < bbox1._points[1][1]:
        if (bbox1._points[0][1] + bbox1._points[1][1]) / 2.0 < \
            (bbox2._points[0][1] + bbox2._points[1][1]) / 2.0:
            ymove = bbox1._points[1][1] - bbox2._points[0][1]
        else:
            ymove = bbox1._points[0][1] - bbox2._points[1][1]
    return (xmove, ymove)

class Plot(object):
    
    def __init__(self, fname = None, font_family = 'Helvetica Neue LT Std', 
        font_style = 'normal', font_weight = 'normal', font_variant = 'normal',
        font_stretch = 'normal',
        palette = None, context = 'poster', lab_size = (9, 9),
        axis_lab_size = 10.0, rc = {}):
        for k, v in iteritems(locals()):
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, v)
        if type(self.lab_size) is not tuple:
            self.lab_size = (self.lab_size, ) * 2
        if 'axes.labelsize' not in self.rc:
            self.rc['axes.labelsize'] = self.axis_lab_size
        if 'ytick.labelsize' not in self.rc:
            self.rc['ytick.labelsize'] = self.lab_size[0]
        if 'ytick.labelsize' not in self.rc:
            self.rc['ytick.labelsize'] = self.lab_size[1]
        self.rc['font.family'] = self.font_family
        self.rc['font.style'] = self.font_style
        self.rc['font.variant'] = self.font_variant
        self.rc['font.weight'] = self.font_weight
        self.rc['font.stretch'] = self.font_stretch
        self.palette = palette or self.embl_palette()
        self.fp = mpl.font_manager.FontProperties(family = self.font_family,
            style = self.font_style, variant = self.font_variant,
            weight = self.font_weight, stretch = self.font_stretch)
    
    def embl_palette(self, inFile = 'embl_colors'):
        cols = []
        inFile = os.path.join(common.ROOT, 'data', inFile)
        with open(inFile, 'r') as f:
            series = []
            for i, l in enumerate(f):
                l = [x.strip() for x in l.split(',')]
                series.append(colorgen.rgb2hex(tuple([256 * float(x) for x in l[0:3]])))
                if len(series) == 7:
                    cols.append(series)
                    series = []
        return cols
    
    def finish(self):
        '''
        Saves and closes a figure.
        '''
        self.fig.tight_layout()
        self.fig.savefig(self.fname)
        plt.close(self.fig)

class MultiBarplot(Plot):
    
    def __init__(self, x, y, categories = None, cat_names = None, cat_ordr = None,
        fname = None, figsize = (12, 4),
        xlab = '', ylab = '', title = '',
        lab_angle = 90, lab_size = (24, 24), color = '#007b7f',
        order = False, desc = True, legend = None, fin = True,
        rc = {}, palette = None, axis_lab_font = {},
        bar_args = {}, ticklabel_font = {}, title_font = {},
        title_halign = 'center', title_valign = 'top'):
        
        for k, v in iteritems(locals()):
            setattr(self, k, v)
        
        super(MultiBarplot, self).__init__()
        
        self.axes = {}
        
        self.bar_args_default = {
            'width': 0.8,
            'edgecolor': 'none',
            'linewidth': 0.0,
            'align': 'center'
        }
        self.axis_lab_font_default = {
            'family': ['Helvetica Neue LT Std'],
            'style': 'normal',
            'stretch': 'condensed',
            'weight': 'bold',
            'variant': 'normal',
            'size': 'x-large'
        }
        self.ticklabel_font_default = {
            'family': ['Helvetica Neue LT Std'],
            'style': 'normal',
            'stretch': 'condensed',
            'weight': 'roman',
            'variant': 'normal',
            'size': 'large'
        }
        self.title_font_default = {
            'family': ['Helvetica Neue LT Std'],
            'style': 'normal',
            'stretch': 'condensed',
            'weight': 'bold',
            'variant': 'normal',
            'size': 'xx-large'
        }
        
        self.bar_args = common.merge_dicts(bar_args, self.bar_args_default)
        self.axis_lab_font = common.merge_dicts(axis_lab_font,
                                                self.axis_lab_font_default)
        self.ticklabel_font = common.merge_dicts(ticklabel_font,
                                                 self.ticklabel_font_default)
        self.title_font = common.merge_dicts(title_font,
                                             self.title_font_default)
        self.fp_axis_lab = \
            mpl.font_manager.FontProperties(**self.axis_lab_font)
        self.fp_ticklabel = \
            mpl.font_manager.FontProperties(**self.ticklabel_font)
        self.fp_title = \
            mpl.font_manager.FontProperties(**self.title_font)
        
        self.x = np.array(self.x, dtype = np.object)
        self.y = np.array(self.y)
        
        self.plot()
    
    def reload(self):
        modname = self.__class__.__module__
        mod = __import__(modname, fromlist = [modname.split('.')[0]])
        imp.reload(mod)
        new = getattr(mod, self.__class__.__name__)
        setattr(self, '__class__', new)
    
    def plot(self):
        """
        The total workflow of this class.
        Calls all methods in the correct order.
        """
        self.pre_plot()
        self.do_plot()
        self.post_plot()
    
    def pre_plot(self):
        """
        Executes all necessary tasks before plotting in the correct order.
        """
        self.set_categories()
        self.plots_order()
        self.set_colors()
        self.sort()
        self.by_plot()
    
    def do_plot(self):
        """
        Calls the plotting methods in the correct order.
        """
        self.set_figsize()
        self.init_fig()
        self.set_grid()
        self.make_plots()
        self.set_title()
    
    def post_plot(self):
        """
        Saves the plot into file, and closes the figure.
        """
        self.finish()
    
    def set_categories(self):
        """
        Sets a list with category indices (integers) of length equal of x,
        and sets dicts to translate between category names and indices.
        """
        self.cnames = None
        if type(self.categories) is dict:
            # self.cnames: name -> number dict
            self.cnames = dict(map(reversed, enumerate(sorted(list(set(self.categories.values()))))))
            self.cats = list(map(lambda name: self.cnames[self.categories[name]], self.x))
        elif type(self.categories) is list:
            if type(self.categories[0]) is int:
                self.cats = self.categories
            else:
                self.cnames = dict(map(reversed, enumerate(sorted(list(set(self.categories))))))
            self.cats = list(map(lambda name: self.cnames[self.categories[name]], self.x))
        elif type(self.x[0]) is list:
            self.cats = []
            _x = []
            for i, c in enumerate(self.x):
                self.cats.extend([i] * len(c))
                _x.extend(c)
            self.x = _x
        else:
            self.cats = [0] * len(self.x)
        self.numof_cats = len(set(self.cats))
        if self.cnames is None:
            if self.cat_names is not None:
                self.cnames = dict(zip(self.cat_names, list(set(self.cats))))
            else:
                self.cnames = dict(map(lambda c: (c, '#%u'%c), self.cats))
        self.cnums = dict(map(reversed, iteritems(self.cnames)))
        self.cats = np.array(self.cats)
    
    def set_colors(self):
        """
        Compiles an array of colors equal length of x.
        """
        self.ccol = None
        if type(self.color) is str:
            self.ccol = dict(map(
                            lambda name:
                                (name, self.color),
                            self.cat_ordr)
                        )
        elif len(self.color) == len(self.cnames):
            if type(self.color[0]) is str:
                self.ccol = dict(map(
                                lambda c:
                                    (c[1], self.color[c[0]]),
                                enumerate(self.cat_ordr)
                            ))
            elif type(self.color[0]) is list:
                self.col = []
                for ccols in self.colors:
                    self.col.extend(ccols)
                self.col = np.array(self.col)
        if type(self.color) not in common.simpleTypes and \
            len(self.color) == len(self.x):
            self.col = np.array(self.color)
        elif self.ccol is not None:
            self.col = \
                np.array(list(map(
                    lambda cnum:
                        self.ccol[self.cnums[cnum]],
                    self.cats
                )))
    
    def plots_order(self):
        """
        Defines the order of the subplots.
        """
        if self.cat_ordr is None and self.cat_names is not None:
            self.cat_ordr = common.uniqOrdList(self.cat_names)
        elif self.cat_ordr is None:
            self.cat_ordr = common.uniqList(self.cnames.keys())
    
    def by_plot(self):
        """
        Sets list of lists with x and y values and colors by category.
        """
        for dim in ['x', 'y', 'col']:
            setattr(self, 'cat_%s' % dim,
                list(map(
                    lambda name:
                        list(map(
                            lambda n_lab:
                                n_lab[1],
                            filter(
                                lambda n_lab:
                                    n_lab[0] == self.cnames[name],
                                zip(self.cats, getattr(self, dim))
                            )
                        )),
                    self.cat_ordr
                ))
            )
    
    def sort(self):
        """
        Finds the defined or default order, and
        sorts the arrays x, y and col accordingly.
        """
        print(np.where(self.x == 'IntAct')[0][0])
        if type(self.order) is str:
            if self.order == 'x':
                self.ordr = np.array(self.x.argsort())
            elif self.order == 'y':
                self.ordr = np.array(self.y.argsort())
        elif hasattr(self.order, '__iter__') and \
            len(set(self.order) & set(self.x)) == len(self.x):
            self.ordr = np.array(list(map(
                            lambda i:
                                np.where(self.x == i)[0][0],
                            self.order
                        )))
        else:
            self.ordr = np.array(xrange(len(self.x)))
        if self.desc:
            self.ordr = self.ordr[::-1]
        print(self.ordr)
        self.x = self.x[self.ordr]
        self.y = self.y[self.ordr]
        self.col = self.col[self.ordr]
        self.cats = self.cats[self.ordr]
    
    def set_figsize(self):
        """
        Converts width and height to a tuple so can be used for figsize.
        """
        if hasattr(self, 'width') and hasattr(self, 'height'):
            self.figsize = (self.width, selg.height)
    
    def init_fig(self):
        """
        Creates a figure using the object oriented matplotlib interface.
        """
        self.pdf = mpl.backends.backend_pdf.PdfPages(self.fname)
        self.fig = mpl.figure.Figure(figsize = self.figsize)
        self.cvs = mpl.backends.backend_pdf.FigureCanvasPdf(self.fig)
    
    def set_grid(self):
        """
        Sets up a grid according to the number of subplots,
        with proportions according to the number of elements
        in each subplot.
        """
        self.gs = mpl.gridspec.GridSpec(2, self.numof_cats,
                height_ratios = [1, 0], width_ratios = list(map(len, self.cat_x)))
    
    def get_subplot(self, i, j = 0):
        self.axes[i] = self.fig.add_subplot(self.gs[j,i])
        self.ax = self.axes[i]
    
    def make_plots(self):
        for i, x in enumerate(self.cat_x):
            self.get_subplot(i)
            xcoo = np.arange(len(x)) - self.bar_args['width'] / 2.0
            xtlabs = np.array(list(map(lambda l: l[0] if type(l) is tuple else l, x)))
            self.ax.bar(left = xcoo,
                        height = self.cat_y[i],
                        color = self.cat_col[i],
                        tick_label = xtlabs,
                        **self.bar_args)
            self.labels()
            self.ax.xaxis.grid(False)
            self.ax.set_xlim([-1, max(xcoo) + 0.5])
            self.get_subplot(i, 1)
            self.ax.xaxis.set_ticklabels([])
            self.ax.yaxis.set_ticklabels([])
            self.ax.set_xlabel(self.cnums[i], fontproperties = self.fp_axis_lab)
            self.ax.xaxis.label.set_verticalalignment('bottom')
            # self.ax.xaxis._autolabelpos = False
    
    def labels(self):
        list(map(lambda tick:
                tick.label.set_fontproperties(self.fp_ticklabel) or \
                self.lab_angle == 0 or self.lab_angle == 90 or \
                    tick.label.set_rotation(self.lab_angle) or \
                    tick.label.set_horizontalalignment('right'),
            self.ax.xaxis.get_major_ticks()))
        list(map(lambda tick:
                tick.label.set_fontproperties(self.fp_ticklabel),
            self.ax.yaxis.get_major_ticks()))
        self.ax.set_ylabel(self.ylab, fontproperties = self.fp_axis_lab)
        #self.ax.yaxis.label.set_fontproperties(self)
    
    def set_title(self):
        self.title_text = self.fig.suptitle(self.title)
        self.title_text.set_fontproperties(self.fp_title)
        self.title_text.set_horizontalalignment(self.title_halign)
        self.title_text.set_verticalalignment(self.title_valign)
    
    def align_x_labels(self):
        self.lowest_ax = min(self.axes.values(), key = lambda ax: ax.xaxis.label.get_position()[1])
        self.minxlabcoo = self.lowest_ax.xaxis.label.get_position()[1]
        self.lowest_xlab_dcoo = self.lowest_ax.transData.transform(self.lowest_ax.xaxis.label.get_position())
        list(
            map(
                    lambda ax: \
                        ax.xaxis.set_label_coords(
                        self.fig.transFigure.inverted().transform(ax.transAxes.transform((0.5, 0.5)))[0],
                        self.fig.transFigure.inverted().transform(self.lowest_xlab_dcoo)[1],
                        transform = self.fig.transFigure
                        ),
                    self.axes.values()
                )
        )
        for ax in self.axes.values():
            ax.xaxis._autolabelpos = False
    
    def finish(self):
        self.fig.tight_layout()
        self.fig.subplots_adjust(top = 0.85)
        self.cvs.draw()
        self.cvs.print_figure(self.pdf)
        self.pdf.close()
        self.fig.clf()

class Barplot(Plot):
    
    def __init__(self, x, y, data = None, fname = None, font_family = 'Helvetica Neue LT Std',
        font_style = 'normal', font_weight = 'normal', font_variant = 'normal',
        font_stretch = 'normal',
        xlab = '', ylab = '', axis_lab_size = 10.0,
        lab_angle = 90, lab_size = (9, 9), color = '#007b7f',
        order = False, desc = True, legend = None, fin = True,
        y_break = None, rc = {}, palette = None, context = 'poster',
        do_plot = True, **kwargs):
        '''
        y_break : tuple
        If not None, the y-axis will have a break. 2 floats in the tuple, < 1.0, 
        mean the lower and upper proportion of the plot shown. The part between
        them will be hidden. E.g. y_break = (0.3, 0.1) shows the lower 30% and 
        upper 10%, but 60% in the middle will be cut out.
        '''
        for k, v in iteritems(locals()):
            setattr(self, k, v)
        self.sns = sns
        self.rc = self.rc or {'lines.linewidth': 1.0, 'patch.linewidth': 0.0,
            'grid.linewidth': 1.0}
        super(Barplot, self).__init__()
        self.color = self.color or self.palette[0][0]
        if type(self.color) is list:
            self.palette = sns.color_palette(self.color)
        elif self.color is not None:
            self.palette = sns.color_palette([self.color] * len(self.x))
        self.color = None
        if self.do_plot:
            self.plot(**kwargs)
    
    def plot(self, x = None, y = None, **kwargs):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if type(self.x) is list or type(self.x) is tuple:
            self.x = np.array(self.x)
        if type(self.y) is list or type(self.y) is tuple:
            self.y = np.array(self.y)
        self.seaborn_style()
        self.fig, self.ax = plt.subplots()
        self.sort()
        if self.y_break:
            self._break_y_gs()
        self.ax = sns.barplot(self.x, y = self.y, data = None, color = self.color,
            order = self.ordr, ax = self.ax, palette = self.palette,
            #fontproperties = self.fp,
            **kwargs)
        if self.y_break:
            self._break_y_axis(**kwargs)
        self.labels()
        if self.fin:
            self.finish()
    
    def sort(self):
        colcyc = itertools.cycle(list(self.palette))
        palcyc = [next(colcyc) for _ in xrange(len(self.x))]
        if self.order == 'x':
            self.ordr = np.array([self.x[i] for i in self.x.argsort()])
            self.palette = sns.color_palette([palcyc[i] for i in self.x.argsort()])
        elif self.order == 'y':
            self.ordr = np.array([self.x[i] for i in self.y.argsort()])
            self.palette = sns.color_palette([palcyc[i] for i in self.y.argsort()])
        elif len(set(self.order) & set(self.x)) == len(self.x):
            self.ordr = np.array(self.order)
            xl = list(self.x)
            self.palette = sns.color_palette([palcyc[xl.index(i)] for i in self.ordr])
        else:
            self.ordr = self.x
        if self.desc:
            self.ordr = self.ordr[::-1]
            self.palette = sns.color_palette(list(self.palette)[::-1])
    
    def _break_y_gs(self):
        self.gs = gridspec.GridSpec(2, 1,
            height_ratios = [self.y_break[1] / sum(self.y_break),
                self.y_break[0] / sum(self.y_break)])
        self.fig = plt.figure()
        self.ax2 = self.fig.add_subplot(self.gs[0])
        self.ax = self.fig.add_subplot(self.gs[1])
    
    def __break_y_axis(self, **kwargs):
        self.ax2 = self.sns.barplot(self.x, y = self.y, data = None, 
            color = self.color, order = self.ordr, ax = self.ax2, 
            palette = self.palette, **kwargs)
        self.ax2.yaxis.set_major_locator(
            ticker.MaxNLocator(nbins = int(9/sum(self.y_break) + 1), steps = [1, 2, 5, 10]))
        self._originalYticks = self.ax2.get_yticks()
        ymin, ymax = self.ax.get_ylim()
        ymax = min(ytick for ytick in self.ax.get_yticks() if ytick > max(self.y))
        self.ax.set_ylim((ymin, ymax * self.y_break[0]))
        self.ax2.set_ylim((ymax - ymax * self.y_break[1], ymax))
        self.lower_y_min, self.lower_y_max = self.ax.get_ylim()
        self.upper_y_min, self.upper_y_max = self.ax2.get_ylim()
        plt.subplots_adjust(hspace = 0.08)
        self.ax2.spines['bottom'].set_visible(False)
        plt.setp(self.ax2.xaxis.get_majorticklabels(), visible = False)
        self.ax.spines['top'].set_visible(False)
        self.ax.set_yticks([yt for yt in self._originalYticks \
            if yt >= self.lower_y_min and yt <= self.lower_y_max])
        self.ax2.set_yticks([yt for yt in self._originalYticks \
            if yt >= self.upper_y_min and yt <= self.upper_y_max])
    
    def _break_y_axis(self, **kwargs):
        self.ax2 = self.sns.barplot(self.x, y = self.y, data = None, 
            color = self.color, order = self.ordr, ax = self.ax2, 
            palette = self.palette, **kwargs)
        self.ax2.yaxis.set_major_locator(
            ticker.MaxNLocator(nbins = int(9/sum(self.y_break) + 1), steps = [1, 2, 5, 10]))
        self._originalYticks = self.ax2.get_yticks()
        ymin, ymax = self.ax.get_ylim()
        yticks = [ytick for ytick in self.ax.get_yticks() if ytick > max(self.y)]
        if len(yticks) > 0:
            ymax = min(yticks)
        else:
            ymax = max(self.ax.get_yticks())
        self.ax.set_ylim((ymin, ymax * self.y_break[0]))
        self.ax2.set_ylim((ymax - ymax * self.y_break[1], ymax))
        self.lower_y_min, self.lower_y_max = self.ax.get_ylim()
        self.upper_y_min, self.upper_y_max = self.ax2.get_ylim()
        plt.subplots_adjust(hspace = 0.08)
        self.ax2.spines['bottom'].set_visible(False)
        plt.setp(self.ax2.xaxis.get_majorticklabels(), visible = False)
        self.ax.spines['top'].set_visible(False)
        self.ax.set_yticks([yt for yt in self._originalYticks \
            if yt >= self.lower_y_min and yt <= self.lower_y_max])
        self.ax2.set_yticks([yt for yt in self._originalYticks \
            if yt >= self.upper_y_min and yt <= self.upper_y_max])
        # further adjusting of upper ylims:
        yticks = [yt for yt in self.ax2.get_yticks() if yt > max(self.y)]
        if len(yticks) > 0:
            ymax = min(yticks)
            self.ax.set_ylim((ymin, ymax * self.y_break[0]))
            self.ax2.set_ylim((ymax - ymax * self.y_break[1], ymax))
            self.lower_y_min, self.lower_y_max = self.ax.get_ylim()
            self.upper_y_min, self.upper_y_max = self.ax2.get_ylim()
            self.ax2.set_yticks([yt for yt in self._originalYticks \
                if yt >= self.upper_y_min and yt <= self.upper_y_max])
    
    def seaborn_style(self, context = None, rc = None):
        self.sns.set(font = self.font_family, rc = rc or self.rc)
        self.sns.set_context(context or self.context, rc = rc or self.rc)
    
    def labels(self):
        for tick in self.ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(self.lab_size[0])
        for tick in self.ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(self.lab_size[1])
        if self.y_break:
            for tick in self.ax2.yaxis.get_major_ticks():
                tick.label.set_fontsize(self.lab_size[1])
        self.ax.set_ylabel(self.ylab)
        self.ax.yaxis.get_label().set_fontproperties(self.fp)
        self.ax.yaxis.get_label().set_fontsize(self.axis_lab_size)
        self.ax.set_xlabel(self.xlab)
        self.ax.xaxis.get_label().set_fontproperties(self.fp)
        self.ax.xaxis.get_label().set_fontsize(self.axis_lab_size)
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation = self.lab_angle)
        if type(self.legend) is dict:
            legend_patches = [mpatches.Patch(color = col, label = lab) \
                for lab, col in iteritems(self.legend)]
            self.ax.legend(handles = legend_patches)

def boxplot(data, labels, xlab, ylab, fname, fontfamily = 'Helvetica Neue LT Std',
    textcol = 'black', violin = False):
    fig, ax = plt.subplots()
    sns.set(font = fontfamily)
    if violin:
        ax = sns.violinplot(data, names = labels, 
            color = embl_colors, linewidth = 0.1, saturation = 0.66)
    else:
        ax = sns.boxplot(data, names = labels, 
            color = embl_colors, linewidth = 0.1, saturation = 0.66)
    ax.set_xlabel(xlab, weight = 'light', fontsize = 12,
        variant = 'normal', color = textcol, stretch = 'normal')
    ax.set_ylabel(ylab, weight = 'light', fontsize = 12,
        variant = 'normal', color = textcol, stretch = 'normal')
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(8)
        tick.label.set_color(textcol)
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(11)
        tick.label.set_color(textcol)
    fig.savefig(fname)

def stacked_barplot(x, y, data, fname, names, font_family = 'Helvetica Neue LT Std', 
    xlab = '', ylab = '', lab_angle = 90, lab_size = (18, 21), axis_lab_size = 36, 
    legend = True, font_weight = None, leg_label_size = 18, 
    colors = ['#7AA0A1', '#C6909C', '#92C1D6', '#C5B26E', '#da0025'], 
    order = False, desc = True):
    plt.close('all')
    if type(x) is list or type(x) is tuple:
        x = np.array(x)
    for i, yi in enumerate(y):
        if type(yi) is list or type(yi) is tuple:
            y[i] = np.array(yi)
    total = np.array([sum([y[j][i] for j in xrange(len(y))]) for i in xrange(len(y[0]))])
    if order == 'x':
        ordr = np.array([x[i] for i in x.argsort()])
    elif order == 'y':
        ordr = np.array([x[i] for i in total.argsort()])
    elif type(order) is int:
        ordr = np.array([x[i] for i in y[order].argsort()])
    elif len(set(order) & set(x)) == len(x):
        ordr = order
    else:
        ordr = x
    if desc:
        ordr = ordr[::-1]
    fig, ax = plt.subplots()
    sns.set(font = font_family)
    sns.set_context('talk', rc={'lines.linewidth': 1.0, 'patch.linewidth': 0.0,
        'grid.linewidth': 1.0, 'axes.labelsize': axis_lab_size})
    for j in xrange(len(y), 0, -1):
        this_level = np.array([sum([y[jj][i] for jj in xrange(j)]) \
            for i in xrange(len(y[0]))])
        ax = sns.barplot(x, y = this_level, data = data, 
            color = colors[j-1], order = ordr)
    sns.set_context('talk', rc={'lines.linewidth': 1.0, 'patch.linewidth': 0.0,
        'grid.linewidth': 1.0, 'axes.labelsize': axis_lab_size})
    for tick in ax.xaxis.get_major_ticks():
        tick.label.set_fontsize(lab_size[0])
    for tick in ax.yaxis.get_major_ticks():
        tick.label.set_fontsize(lab_size[1])
    ax.set_ylabel(ylab)
    ax.set_xlabel(xlab)
    if font_weight is not None:
        ax.xaxis.label.set_fontweight(font_weight)
        ax.yaxis.label.set_fontweight(font_weight)
    ax.xaxis.get_label().set_fontsize(axis_lab_size)
    ax.yaxis.get_label().set_fontsize(axis_lab_size)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation = lab_angle)
    if legend:
        lhandles = [mpl.patches.Patch(color = colors[i], label = names[i]) for i in xrange(len(y))]
    leg = ax.legend(handles = lhandles)
    nul = [t.set_fontsize(leg_label_size) for t in leg.texts]
    fig.tight_layout()
    fig.savefig(fname)
    plt.close('all')

## ## ##

class ScatterPlus(Plot):
    
    def __init__(self, x, y, sizes = None, labels = None, data = None,
        xlog = False, ylog = False, xlim = None, ylim = None, 
        xtickscale = None, ytickscale = None, legscale = None, 
        fname = None, font_family = 'Helvetica Neue LT Std', 
        font_style = 'normal', font_weight = 'normal', font_variant = 'normal',
        font_stretch = 'normal', confi = True, 
        xlab = '', ylab = '', axis_lab_size = 10.0, 
        annotation_size = 9, size = 20.0, size_scaling = 0.8, 
        lab_angle = 90, lab_size = (9, 9), color = '#007b7f', 
        order = False, desc = True, legend = True, legtitle = None,
        legstrip = (None, None), legloc = 4, 
        size_to_value = lambda x: x,
        value_to_size = lambda x: x,
        fin = True, 
        rc = {}, palette = None, context = 'poster', **kwargs):
        '''
        y_break : tuple
        If not None, the y-axis will have a break. 2 floats in the tuple, < 1.0, 
        mean the lower and upper proportion of the plot shown. The part between
        them will be hidden. E.g. y_break = (0.3, 0.1) shows the lower 30% and 
        upper 10%, but 60% in the middle will be cut out.
        '''
        for k, v in iteritems(locals()):
            setattr(self, k, v)
        self.sns = sns
        self.rc = self.rc or {'lines.linewidth': 1.0, 'patch.linewidth': 0.0, 
            'grid.linewidth': 1.0}
        super(ScatterPlus, self).__init__(fname = fname, font_family = font_family, 
            font_style = font_style, font_weight = font_weight, 
            font_variant = font_variant, font_stretch = font_stretch,
            palette = palette, context = context, lab_size = self.lab_size, 
            axis_lab_size = self.axis_lab_size, rc = self.rc)
        self.color = self.color or self.palette[0][0]
        if type(self.color) is list:
            self.palette = sns.color_palette(self.color)
        elif self.color is not None:
            self.palette = sns.color_palette([self.color] * len(self.x))
        self.color = None
        self.plot(**kwargs)
    
    def scale(self, scale = None, q = 1):
        scale = [1, 2, 5] if scale is None else scale
        def _scaler(scale, q):
            while True:
                for i in scale:
                    yield i * q
                q *= 10.0
        _scale = _scaler(scale, q)
        return _scale
    
    def plot(self, x = None, y = None, sizes = None, size = None,
        labels = None, data = None, xlab = None, ylab = None, 
        legtitle = None, size_scaling = None, **kwargs):
        # optionally update the dataset at calling plot():
        for attr in ['x', 'y', 'sizes', 'size', 'labels', 'data', 
            'xlab', 'ylab', 'legtitle', 'size_scaling']:
            if locals()[attr] is not None:
                setattr(self, attr, locals()[attr])
        # if x, y or sizes are data frame colnames, attempt to 
        # get the variable labels by them:
        if type(self.x) in [str, unicode] and self.xlab is None:
            self.xlab = self.x.capitalize()
        if type(self.y) in [str, unicode] and self.ylab is None:
            self.ylab = self.y.capitalize()
        if type(self.sizes) in [str, unicode] and self.legtitle is None:
            self.legtitle = self.sizes.capitalize()
        # get the 
        if self.data is not None and type(self.x) in [str, unicode] \
            and self.x in self.data:
            self.x = list(self.data[self.x])
        if self.data is not None and type(self.y) in [str, unicode] \
            and self.y in self.data:
            self.y = list(self.data[self.y])
        if self.data is not None and type(self.sizes) in [str, unicode] \
            and self.sizes in self.data:
            self.sizes = list(self.data[self.sizes])
        if self.data is not None and type(self.labels) in [str, unicode] \
            and self.labels in self.data:
            self.labels = list(self.data[self.labels])
        if type(self.x) is list or type(self.x) is tuple:
            self.x = np.array(self.x)
        if type(self.y) is list or type(self.y) is tuple:
            self.y = np.array(self.y)
        if type(self.sizes) is list or type(self.sizes) is tuple:
            self.sizes = np.array(self.sizes)
        if type(self.labels) is list or type(self.labels) is tuple:
            self.labels = np.array(self.labels)
        self.seaborn_style()
        self.fig, self.ax = plt.subplots()
        if type(sizes) in [int, float]:
            self.sizes = sizes
        if self.sizes is not None and type(self.sizes) not in [int, float]:
            self.rads = self.size * (self.sizes / float(max(self.sizes)))**self.size_scaling
        if self.sizes is None:
            self.rads = np.array([self.size] * len(self.x))
        if self.ylog:
            self.ax.set_yscale('symlog' if self.ylog == 'symlog' else 'log')
        if self.xlog:
            self.ax.set_xscale('symlog' if self.xlog == 'symlog' else 'log')
        self.scatter = self.ax.scatter(self.x, self.y, \
            s = self.rads if self.sizes is None \
                else [np.pi * r**2 for r in self.rads], \
            c = '#6ea945', alpha = 0.5, \
            edgecolors = 'none')
        if self.confi:
            self._confidence_interval()
        self.axes_limits()
        self.set_ticklocs()
        self.annotations()
        self._legend()
        self.axes_labels()
        self.axes_limits()
        self.axes_ticklabels()
        self.axes_limits()
        self.fig.tight_layout()
        self.axes_limits()
        self.remove_annotation_overlaps()
        if self.fin:
            self.finish()
    
    def annotations(self):
        if self.labels is not None:
            self.annots = []
            dists = move_labels()
            for label, xx, yy, yf, o in \
                zip(self.labels, self.x, self.y, self.y_fit, self.rads):
                dst = dists.next()
                d = 1.0 if yy > 10**yf else -1.0
                coo = ((-7 - dst) * d / 3.0, (21 + dst) * d)
                self.annots.append(self.ax.annotate(
                    label, 
                    xy = (xx, yy), xytext = coo,
                    xycoords = 'data',
                    textcoords = 'offset points', ha = 'center', va = 'bottom', color = '#007B7F',
                    arrowprops = dict(arrowstyle = '-', connectionstyle = 'arc,rad=.0',
                        color = '#007B7F', edgecolor = '#007B7F', alpha = 1.0, 
                        visible = True, linewidth = 0.2), 
                ))
            for ann in self.annots:
                ann.set_fontsize(self.annotation_size)
    
    def set_ticklocs(self):
        if self.xlog:
            xscaler = self.scale(self.xtickscale)
            self.xtickloc = []
            while True:
                tickloc = xscaler.next()
                if tickloc >= self._xlim[0]:
                    self.xtickloc.append(tickloc)
                if tickloc > self._xlim[1]:
                    break
            self._xtickloc = self.ax.set_xticks(self.xtickloc)
        if self.ylog:
            yscaler = self.scale(self.ytickscale)
            self.ytickloc = []
            while True:
                tickloc = yscaler.next()
                if tickloc >= self._ylim[0]:
                    self.ytickloc.append(tickloc)
                if tickloc > self._ylim[1]:
                    break
            self._ytickloc = self.ax.set_yticks(self.ytickloc)
    
    def axes_limits(self, xlim = None, ylim = None):
        xlim = xlim if xlim is not None else self.xlim \
            if self.xlim is not None else self.ax.get_xlim()
        ylim = ylim if ylim is not None else self.ylim \
            if self.ylim is not None else self.ax.get_ylim()
        if xlim is not None:
            self._xlim = self.ax.set_xlim(xlim)
        if ylim is not None:
            self._ylim = self.ax.set_ylim(ylim)
    
    def seaborn_style(self, context = None, rc = None):
        self.sns.set(font = self.font_family, rc = rc or self.rc)
    
    def axes_ticklabels(self):
        if self.xlog:
            self.xticklabs = []
            for i, t in enumerate(list(self.ax.xaxis.get_major_locator().locs)):
                tlab = str(int(t)) if t - int(t) == 0 or t >= 10.0 else str(t)
                self.xticklabs.append(tlab[:-2] if tlab.endswith('.0') else tlab)
            self._xticklabels = self.ax.set_xticklabels(self.xticklabs)
        if self.ylog:
            self.yticklabs = []
            for i, t in enumerate(list(self.ax.yaxis.get_major_locator().locs)):
                tlab = str(int(t)) if t - int(t) == 0 or t >= 10.0 else str(t)
                self.yticklabs.append(tlab[:-2] if tlab.endswith('.0') else tlab)
            self._yticklabels = self.ax.set_yticklabels(self.yticklabs)
        for t in self.ax.xaxis.get_major_ticks():
            t.label.set_fontsize(self.lab_size[0])
        for t in self.ax.yaxis.get_major_ticks():
            t.label.set_fontsize(self.lab_size[1])
    
    def _confidence_interval(self):
        # the points:
        self._x = np.array([i if not np.isinf(i) else 0.0 \
                for i in np.log10(self.x)]) \
            if self.xlog else self.x
        self._y = np.array([i if not np.isinf(i) else 0.0 \
                for i in np.log10(self.y)]) \
            if self.ylog else self.y
        # (log)linear fit with confidence and prediction interval:
        (self.m, self.b), self.V = np.polyfit(self._x, self._y, 1, cov = True)
        self.n = self._x.size
        self.y_fit = np.polyval((self.m, self.b), self._x)
        self.df = self.n - 2
        self.t = stats.t.ppf(0.95, self.df)
        self.resid = self._y - self.y_fit
        self.chi2 = np.sum((self.resid / self.y_fit)**2)
        self.chi2_red = self.chi2 / self.df
        self.s_err = np.sqrt(np.sum(self.resid**2) / self.df)
        self.x2 = np.linspace(np.min(self._x), np.max(self._x), 100)
        self.y2 = np.linspace(np.min(self.y_fit), np.max(self.y_fit), 100)
        # confidence interval
        self.ci = self.t * self.s_err * np.sqrt(1 / self.n + \
            (self.x2 - np.mean(self._x))**2 / np.sum((self._x - np.mean(self._x))**2))
        # prediction interval
        self.pi = self.t * self.s_err * np.sqrt(1 + 1 / self.n + \
            (self.x2 - np.mean(self._x))**2 / np.sum((self._x - np.mean(self._x))**2))
        # regression line
        self.rline_x = [10**xx for xx in self._x] if self.xlog else self._x
        self.rline_y = [10**yy for yy in self.y_fit] if self.ylog else self.y_fit
        self.rline = self.ax.plot(self.rline_x, self.rline_y,
            '-', color = '#B6B7B9', alpha = 0.5)
        # confidence interval
        self.ci_rfill_x = [10**xx for xx in self.x2] if self.xlog else self.x2
        self.ci_rfill_y_upper = [10**yy for yy in (self.y2 + self.ci)] \
            if self.ylog else self.y2 + self.ci
        self.ci_rfill_y_lower = [10**yy for yy in (self.y2 - self.ci)] \
            if self.ylog else self.y2 - self.ci
        self.rfill = self.ax.fill_between(self.ci_rfill_x, 
            self.ci_rfill_y_upper, 
            self.ci_rfill_y_lower, 
            color = '#B6B7B9', edgecolor = '', alpha = 0.2)
        # prediction intreval
        self.pi_y_upper = [10**yy for yy in (self.y2 + self.pi)] \
            if self.ylog else self.y2 + self.pi
        self.pi_y_lower = [10**yy for yy in (self.y2 - self.pi)] \
            if self.ylog else self.y2 - self.pi
        self.pilowerline = self.ax.plot(self.ci_rfill_x, 
            self.pi_y_lower, 
            '--', color = '#B6B7B9', linewidth = 0.5)
        self.piupperline = self.ax.plot(self.ci_rfill_x, 
            self.pi_y_upper, 
            '--', color = '#B6B7B9', linewidth = 0.5)
    
    def _legend(self):
        if self.sizes is not None and self.legend:
            legtitle = '' if self.legtitle is None else self.legtitle
            self.lhandles = []
            self.llabels = []
            self.legvalues = [self.size_to_value(i) for i in self.sizes]
            self.leglower = 10**int(math.floor(math.log10(min(self.legvalues))))
            self.legscaler = self.scale(self.legscale, q = self.leglower)
            self.legsizes = []
            while True:
                legvalue = self.legscaler.next()
                self.legsizes.append(legvalue)
                if legvalue >= max(self.legvalues):
                    break
            self.legsizes = self.legsizes[self.legstrip[0]:\
                -self.legstrip[1] if self.legstrip[1] is not None else None]
            for s in self.legsizes:
                self.lhandles.append(mpl.legend.Line2D(range(1), range(1), 
                    color = 'none', marker = 'o', 
                    markersize = self.size * (self.value_to_size(s) / \
                        float(max(self.sizes)))**self.size_scaling, 
                    markerfacecolor = '#6ea945', markeredgecolor = 'none', alpha = .5, 
                    label = str(int(s)) if s - int(s) == 0 or s >= 10.0 else str(s)))
                self.llabels.append(str(int(s)) if s - int(s) == 0 or s >= 10.0 else str(s))
            self.leg = self.ax.legend(self.lhandles, self.llabels, 
                title = legtitle, labelspacing = .9,
                borderaxespad = .9, loc = self.legloc)
            self.leg.get_title().set_fontweight(self.font_weight)
    
    def axes_labels(self):
        if self.xlab is not None:
            self._xlab = self.ax.set_xlabel(self.xlab)
            self.ax.xaxis.label.set_fontweight(self.font_weight)
            self.ax.xaxis.label.set_size(self.axis_lab_size)
        if self.ylab is not None:
            self._ylab = self.ax.set_ylabel(self.ylab)
            self.ax.yaxis.label.set_fontweight(self.font_weight)
            self.ax.yaxis.label.set_size(self.axis_lab_size)
    
    def remove_annotation_overlaps(self):
        if self.labels is not None:
            self.fig.savefig(self.fname)
            # self.ax.figure.canvas.draw()
            steps = [0] * len(self.annots)
            for i, a2 in enumerate(self.annots):
                overlaps = False
                for z in xrange(100):
                    for a1 in self.annots[:i]:
                        if overlap(a1.get_window_extent(), a2.get_window_extent()):
                            # 'Overlapping labels: %s and %s' % (a1._text, a2._text)
                            mv = get_moves(a1.get_window_extent(), a2.get_window_extent())
                            if steps[i] % 2 == 0:
                                a2.xyann = (a2.xyann[0] + mv[0] * 1.1 * (z / 2 + 1), a2.xyann[1])
                            else:
                                a2.xyann = (a2.xyann[0], a2.xyann[1] + mv[1] * 1.1* (z / 2 + 1))
                            steps[i] += 1
                        else:
                            pass
                            # 'OK, these do not overlap: %s and %s' % (a1._text, a2._text)
                    if not overlaps:
                        break

class Histogram(Plot):
    
    def __init__(self, data, labels, fname, font_family = 'Helvetica Neue LT Std',
                font_style = 'normal', font_weight = 'normal',
                font_variant = 'normal', font_stretch = 'normal',
                xlab = '', ylab = '', title = '', axis_lab_size = 10.0,
                lab_angle = 90, lab_size = (9, 9), color = None,
                palette = None, rc = {}, context = 'poster',
                figsize = (5.0, 3.0), bins = None, nbins = None,
                x_log = False, y_log = False,
                tone = 2, alpha = 0.5,
                legend_size = 6, xlim = None,
                kde_base = 0.2, kde_perc = 12.0,
                **kwargs):
        self.data = data
        if type(self.data[0]) in common.numTypes:
            self.data = [data]
        for i, d in enumerate(self.data):
            if type(d) is list: self.data[i] = np.array(d)
        self.labels = labels
        if type(self.labels) in common.charTypes:
            self.labels = [labels]
        for k, v in iteritems(locals()):
            setattr(self, k, v)
        self.sns = sns
        self.rc = self.rc or {'lines.linewidth': 1.0, 'patch.linewidth': 0.0,
            'grid.linewidth': 1.0}
        super(Histogram, self).__init__(fname = fname, font_family = font_family,
            font_style = font_style, font_weight = font_weight,
            font_variant = font_variant, font_stretch = font_stretch,
            palette = palette, context = context, lab_size = self.lab_size,
            axis_lab_size = self.axis_lab_size, rc = self.rc)
        if self.color is None:
            self.set_palette()
        self.data_range()
        self.set_bins(bins)
        self.plot_args = kwargs
        self.plot(**kwargs)
    
    def reload(self):
        modname = self.__class__.__module__
        mod = __import__(modname, fromlist = [modname.split('.')[0]])
        imp.reload(mod)
        new = getattr(mod, self.__class__.__name__)
        setattr(self, '__class__', new)
    
    def set_bins(self, bins = None, nbins = None):
        self.bins = bins
        if self.bins is None:
            self.bins_default()
        self.nbins = nbins
        if self.nbins is None:
            self.nbins_default()
    
    def data_range(self):
        self.lowest = min(map(lambda d: np.nanmin(d[np.where(d != 0.0)]), self.data))
        self.highest = max(map(max, self.data))
    
    def nbins_default(self):
        self.nbins = min(
            map(
                lambda d:
                    len(d) / (150.0 + 3.0 * np.log10(len(d) / np.log10(len(d)))),
                self.data
            )
        )
    
    def bins_default(self):
        if self.x_log:
            self.bin_limits = sorted([
                np.log10(self.lowest) if self.lowest > 0.0 else np.log10(0.000001),
                np.log10(self.highest)
            ])
        else:
            self.bin_limits = [self.lowest, self.highest]
        self.bins = \
            np.logspace(self.bin_limits[0], self.bin_limits[1], self.nbins) \
            if self.x_log else \
            np.linspace(self.lowest, self.highest, self.nbins)
    
    def set_palette(self, palette = None):
        self.palette = self.palette if palette is None else palette
        self.colors = \
            map(
                lambda x:
                    x if len(x) < 100 else '%s%s' % (x, '%02x' % (self.alpha * 255.0)),
                map(
                    lambda i:
                        self.palette[i % len(self.palette)]\
                            [min(len(self.palette[i]) - 1, self.tone)],
                    xrange(len(self.data))
                )
            )
    
    def remove_borders(self):
        for patches in self.hist[2]:
            map(
                lambda p:
                    p.set_linewidth(0.0),
                patches
            )
    
    def set_labels(self):
        self.ax.set_ylabel(self.ylab)
        self.ax.set_xlabel(self.xlab)
        self.ax.set_title(self.title)
    
    def add_density_lines(self, **kwargs):
        for i, d in enumerate(self.data):
            self.kde_bandwidth = self.kde_base / d.std(ddof = 1)
            density = stats.gaussian_kde(d, bw_method = self.kde_bandwidth)
            x = np.arange(self.lowest, self.highest,
                          self.highest / len(self.hist[0][i]))
            y = np.array(density(x))
            limit = np.percentile(x, self.kde_perc)
            y = y[np.where(x < limit)]
            x = x[np.where(x < limit)]
            #y2 = mpl.mlab.normpdf(x, np.mean(d), np.std(d))
            ylim = self.ax.get_ylim()
            xlim = self.ax.get_xlim()
            self.ax.plot(x, y, ls = '--', lw = .5, c = self.palette[i][0],
                label = '%s, density' % self.labels[i])
            #self.ax.plot(x, y2, ls = ':', lw = .5, c = self.palette[i][0])
            self.ax.set_ylim(ylim)
            self.ax.set_xlim(xlim)
    
    def set_log(self):
        if self.y_log:
            self.ax.set_yscale('log')
        if self.x_log:
            self.ax.set_xscale('log')
    
    def set_ticklabels(self):
        #self.ax.yaxis.set_ticklabels(
            #map(
                #lambda x:
                    #'%.01f%%' % x if x >= 0.1 else '',
                #self.ax.get_yticks()
            #)
        #)
        self.ax.xaxis.set_ticklabels(
            map(
                lambda x:
                    '{:,g}'.format(x),
                self.ax.get_xticks()
            )
        )
    
    def set_xlim(self):
        if self.xlim is not None:
            self.ax.set_xlim(self.xlim)
    
    def add_legend(self):
        self.ax.legend(prop = {'size': self.legend_size})
    
    def plot(self, **kwargs):
        self.fig = mpl.figure.Figure(figsize = self.figsize)
        self.ax = self.fig.add_subplot(111)
        #for i, d in enumerate(self.data):
        #    sns.distplot(d, ax = self.ax,
        #                 axlabel = False, color = self.colors[i])
        self.hist = self.ax.hist(self.data, bins = self.bins,
                                label = self.labels, color = self.colors,
                                log = self.y_log, alpha = self.alpha,
                                **kwargs)
        self.remove_borders()
        self.set_labels()
        self.set_log()
        self.add_density_lines()
        self.set_xlim()
        self.set_ticklabels()
        self.add_legend()
