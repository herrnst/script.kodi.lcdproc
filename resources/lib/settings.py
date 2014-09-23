'''
    Kodi LCDproc Python addon
    Copyright (C) 2014 Team Kodi
    Copyright (C) 2014 Daniel 'herrnst' Scheller
    
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
    
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import string
import sys

import xbmc
import xbmcaddon

sys.path.insert(0, xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")))

# imports from resources/lib
from lcdprocglobals import *
from common import *

class LCDprocSettings():

  def __init__(self):
    self.m_cAddon = xbmcaddon.Addon(id=KODI_SCRIPT_ID)

  def getSettings(self):
    if not self.m_cAddon:
      log(LOGWARNING, "getSettings(): xbmcaddon not instanciated, expect problems.")
    else:
      log(LOGDEBUG, "getSettings(): Reading GUI settings")

      # load GUI settings into local vars for further processing
      overlaytimeout = int(float(string.replace(self.m_cAddon.getSetting("overlaytimeout"), ",", ".")))
      refreshrate = int(float(string.replace(self.m_cAddon.getSetting("refreshrate"), ",", ".")))

      if LCDprocGlobals.iRefreshRate != refreshrate:
        LCDprocGlobals.iRefreshRate = refreshrate

        if refreshrate < 1:
          LCDprocGlobals.iRefreshRate = 1

        if refreshrate > 20:
          LCDprocGlobals.iRefreshRate = 20
        
        LCDprocGlobals.fRefreshDelay = 1.0 / float(LCDprocGlobals.iRefreshRate)

      if LCDprocGlobals.iOverlayTimeout != overlaytimeout:
        LCDprocGlobals.iOverlayTimeout = overlaytimeout

        if overlaytimeout < 1:
          LCDprocGlobals.iOverlayTimeout = 1

        if overlaytimeout > 10:
          LCDprocGlobals.iOverlayTimeout = 10
