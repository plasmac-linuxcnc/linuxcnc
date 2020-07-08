#!/usr/bin/env python

'''
w_sector.py

Copyright (C) 2019, 2020  Phillip A Carter

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
import gtk
import time
import math
import linuxcnc
import shutil
import hal
from subprocess import Popen,PIPE

class sector:

    def __init__(self):
        self.i = linuxcnc.ini(os.environ['INI_FILE_NAME'])
        self.c = linuxcnc.command()
        self.s = linuxcnc.stat()
        self.gui = self.i.find('DISPLAY', 'DISPLAY').lower()
        self.configFile = '{}_wizards.cfg'.format(self.i.find('EMC', 'MACHINE').lower())

    def dialog_error(self, error):
        md = gtk.MessageDialog(self.W, 
            gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
            gtk.BUTTONS_CLOSE, error)
        md.run()
        md.destroy()

    def load_file(self, fName):
        if self.gui == 'axis':
            Popen('axis-remote {}'.format(fName), stdout = PIPE, shell = True)
        elif self.gui == 'gmoccapy':
            self.c = linuxcnc.command()
            self.c.program_open('./plasmac/blank.ngc')
            self.c.program_open(fName)
        else:
            print('Unknown GUI in .ini file')

    def end_this_shape(self, event):
        if os.path.exists(self.fWizard):
            outWiz = open(self.fWizard, 'a+')
            post = False
            for line in outWiz:
                if '(postamble)' in line:
                    post = True
            if not post:
                outWiz.write('\n(postamble)\n')
                outWiz.write('{}\n'.format(self.postamble))
                outWiz.write('m30\n')
            outWiz.close()
            self.load_file(self.fWizard)
        self.W.destroy()
        return None

    def add_shape_to_file(self, event):
        if os.path.exists(self.fWizard):
            path = os.path.dirname(os.path.abspath(self.fWizard))
            tmp = ('{}/tmp'.format(path))
            shutil.copyfile(self.fWizard, tmp)
            inWiz = open(tmp, 'r')
            outWiz = open(self.fWizard, 'w')
            for line in inWiz:
                if '(postamble)' in line:
                    break
                outWiz.write(line)
            inWiz.close()
            outWiz.close()
            os.remove(tmp)
            inTmp = open(self.fTmp, 'r')
            outWiz = open(self.fWizard, 'a')
            for line in inTmp:
                outWiz.write(line)
        else:
            inTmp = open(self.fTmp, 'r')
            outWiz = open(self.fWizard, 'w')
            outWiz.write('(preamble)\n')
            outWiz.write('{}\n'.format(self.preamble))
            outWiz.write('f#<_hal[plasmac.cut-feed-rate]>\n')
            for line in inTmp:
                outWiz.write(line)
        inTmp.close()
        outWiz.close()
        self.add.set_sensitive(False)

    def send_preview(self, event):
# validate entries
        try:
            leadInOffset = math.sin(math.radians(45)) * float(self.liEntry.get_text())
            leadOutOffset = math.sin(math.radians(45)) * float(self.loEntry.get_text())
            radius = float(self.rEntry.get_text())
            sAngle = math.radians(float(self.sEntry.get_text()))
#            angle = math.radians(float(self.aEntry.get_text()) + 270)
            angle = math.radians(float(self.aEntry.get_text()))
        except:
            msg  = 'Valid numerical entries required for:\n\n'
            msg += 'Lead In\n'
            msg += 'Lead Out\n'
            msg += 'Radius\n'
            msg += 'Sector Angle\n'
            msg += 'Angle\n'
            self.dialog_error(msg)
            return
        if radius == 0 or sAngle == 0:
            msg  = 'Valid numerical entries required for:\n\n'
            msg += 'Radius\n'
            msg += 'Sector Angle\n'
            self.dialog_error(msg)
            return
        if self.offset.get_active() and leadInOffset <= 0:
            msg  = 'A Lead In is required if\n\n'
            msg += 'kerf width offset is enabled\n'
            self.dialog_error(msg)
            return
        self.s.poll()
# get current x/y position
        xPos = self.s.actual_position[0] - self.s.g5x_offset[0] - self.s.g92_offset[0]
        yPos = self.s.actual_position[1] - self.s.g5x_offset[1] - self.s.g92_offset[1]
# set origin position
        if self.xSEntry.get_text():
            xO = float(self.xSEntry.get_text())
        else:
            xO = xPos
        if self.ySEntry.get_text():
            yO = float(self.ySEntry.get_text())
        else:
            yO = yPos
# set start point
        xS = xO + (radius * 0.75) * math.cos(angle)
        yS = yO + (radius * 0.75) * math.sin(angle)
# set bottom point
        xB = xO + radius * math.cos(angle)
        yB = yO + radius * math.sin(angle)
# set top point
        xT = xO + radius * math.cos(angle + sAngle)
        yT = yO + radius * math.sin(angle + sAngle)
# set directions
        right = math.radians(0)
        up = math.radians(90)
        left = math.radians(180)
        down = math.radians(270)
        if self.outside.get_active():
            dir = [down, right, left, up]
        else:
            dir = [up, left, right, down]
# set leadin and leadout points
        xIC = xS + (leadInOffset * math.cos(angle + dir[0]))
        yIC = yS + (leadInOffset * math.sin(angle + dir[0]))
        xIS = xIC + (leadInOffset * math.cos(angle + dir[1]))
        yIS = yIC + (leadInOffset * math.sin(angle + dir[1]))
        xOC = xS + (leadOutOffset * math.cos(angle + dir[0]))
        yOC = yS + (leadOutOffset * math.sin(angle + dir[0]))
        xOE = xOC + (leadOutOffset * math.cos(angle + dir[2]))
        yOE = yOC + (leadOutOffset * math.sin(angle + dir[2]))

# setup files and write g-code
        self.fTmp = '{}/shape.tmp'.format(self.tmpDir)
        self.fNgc = '{}/shape.ngc'.format(self.tmpDir)
        outTmp = open(self.fTmp, 'w')
        outNgc = open(self.fNgc, 'w')
        if os.path.exists(self.fWizard):
            inWiz = open(self.fWizard, 'r')
            for line in inWiz:
                if '(postamble)' in line:
                    break
                outNgc.write(line)
        else:
            outNgc.write('(preamble)\n')
            outNgc.write('{}\n'.format(self.preamble))
            outNgc.write('f#<_hal[plasmac.cut-feed-rate]>\n')
        outTmp.write('\n(wizard sector)\n')

        outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xIS, yIS))
        outTmp.write('m3 $0 s1\n')
        if self.offset.get_active():
            outTmp.write('g41.1 d#<_hal[plasmac_run.kerf-width-f]>\n')
        if leadInOffset:
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xS, yS, xIC - xIS, yIC - yIS))
        if self.outside.get_active():
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xO, yO))
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xT, yT))
            outTmp.write('g2 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xB, yB, xO - xT, yO - yT))
        else:
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xB, yB))
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xT, yT, xO - xB, yO - yB))
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xO, yO))
        outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xS, yS))
        if leadOutOffset:
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xOE, yOE, xOC - xS, yOC - yS))
        if self.offset.get_active():
            outTmp.write('g40\n')
        outTmp.write('m5\n')
        outTmp.close()
        outTmp = open(self.fTmp, 'r')
        for line in outTmp:
            outNgc.write(line)
        outTmp.close()
        outNgc.write('\n(postamble)\n')
        outNgc.write('{}\n'.format(self.postamble))
        outNgc.write('m30\n')
        outNgc.close()
        self.load_file(self.fNgc)
        self.add.set_sensitive(True)
        hal.set_p('plasmac_run.preview-tab', '1')

    def do_sector(self, fWizard, tmpDir):
        self.tmpDir = tmpDir
        self.fWizard = fWizard
        self.sRadius = 0.0
        self.hSpeed = 100
        self.W = gtk.Dialog('Sector',
                       None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons = None)
        self.W.set_keep_above(True)
        self.W.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.W.set_default_size(250, 200)
        t = gtk.Table(1, 1, True)
        t.set_row_spacings(6)
        self.W.vbox.add(t)
        cutLabel = gtk.Label('Cut Type')
        cutLabel.set_alignment(0.95, 0.5)
        cutLabel.set_width_chars(10)
        t.attach(cutLabel, 0, 1, 0, 1)
        self.outside = gtk.RadioButton(None, 'Outside')
        t.attach(self.outside, 1, 2, 0, 1)
        inside = gtk.RadioButton(self.outside, 'Inside')
        t.attach(inside, 2, 3, 0, 1)
        offsetLabel = gtk.Label('Offset')
        offsetLabel.set_alignment(0.95, 0.5)
        offsetLabel.set_width_chars(10)
        t.attach(offsetLabel, 3, 4, 0, 1)
        self.offset = gtk.CheckButton('Kerf Width')
        t.attach(self.offset, 4, 5, 0, 1)
        lLabel = gtk.Label('Lead In')
        lLabel.set_alignment(0.95, 0.5)
        lLabel.set_width_chars(10)
        t.attach(lLabel, 0, 1, 1, 2)
        self.liEntry = gtk.Entry()
        self.liEntry.set_width_chars(10)
        t.attach(self.liEntry, 1, 2, 1, 2)
        loLabel = gtk.Label('Lead Out')
        loLabel.set_alignment(0.95, 0.5)
        loLabel.set_width_chars(10)
        t.attach(loLabel, 0, 1, 2, 3)
        self.loEntry = gtk.Entry()
        self.loEntry.set_width_chars(10)
        t.attach(self.loEntry, 1, 2, 2, 3)
        xSLabel = gtk.Label('X start')
        xSLabel.set_alignment(0.95, 0.5)
        xSLabel.set_width_chars(10)
        t.attach(xSLabel, 0, 1, 3, 4)
        self.xSEntry = gtk.Entry()
        self.xSEntry.set_width_chars(10)
        t.attach(self.xSEntry, 1, 2, 3, 4)
        ySLabel = gtk.Label('Y start')
        ySLabel.set_alignment(0.95, 0.5)
        ySLabel.set_width_chars(10)
        t.attach(ySLabel, 0, 1, 4, 5)
        self.ySEntry = gtk.Entry()
        self.ySEntry.set_width_chars(10)
        t.attach(self.ySEntry, 1, 2, 4, 5)
        rLabel = gtk.Label('Radius')
        rLabel.set_alignment(0.95, 0.5)
        rLabel.set_width_chars(10)
        t.attach(rLabel, 0, 1, 5, 6)
        self.rEntry = gtk.Entry()
        self.rEntry.set_width_chars(10)
        t.attach(self.rEntry, 1, 2, 5, 6)
        sLabel = gtk.Label('Sector Angle')
        sLabel.set_alignment(0.95, 0.5)
        sLabel.set_width_chars(10)
        t.attach(sLabel, 0, 1, 6, 7)
        self.sEntry = gtk.Entry()
        self.sEntry.set_width_chars(10)
        t.attach(self.sEntry, 1, 2, 6, 7)
        aLabel = gtk.Label('Angle')
        aLabel.set_alignment(0.95, 0.5)
        aLabel.set_width_chars(10)
        t.attach(aLabel, 0, 1, 7, 8)
        self.aEntry = gtk.Entry()
        self.aEntry.set_width_chars(10)
        self.aEntry.set_text('0')
        t.attach(self.aEntry, 1, 2, 7, 8)
        preview = gtk.Button('Preview')
        preview.connect('pressed', self.send_preview)
        t.attach(preview, 0, 1, 9, 10)
        self.add = gtk.Button('Add')
        self.add.set_sensitive(False)
        self.add.connect('pressed', self.add_shape_to_file)
        t.attach(self.add, 2, 3, 9, 10)
        end = gtk.Button('Return')
        end.connect('pressed', self.end_this_shape)
        t.attach(end, 4, 5, 9, 10)
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                filename='./plasmac/wizards/images/sector.png', 
                width=240, 
                height=240)
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        t.attach(image, 2, 5, 1, 9)
        self.xSEntry.grab_focus()
        self.W.show_all()
        if os.path.exists(self.configFile):
            f_in = open(self.configFile, 'r')
            for line in f_in:
                if line.startswith('preamble'):
                    self.preamble = line.strip().split('=')[1]
                elif line.startswith('postamble'):
                    self.postamble = line.strip().split('=')[1]
                elif line.startswith('lead-in'):
                    self.liEntry.set_text(line.strip().split('=')[1])
                elif line.startswith('lead-out'):
                    self.loEntry.set_text(line.strip().split('=')[1])
        response = self.W.run()
