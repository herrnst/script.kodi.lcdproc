'''
    Kodi LCDproc service

    Copyright (C) 2018 Team Kodi
    Copyright (C) 2018 Daniel 'herrnst' Scheller

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

import time
import json
import os
import threading

import xbmc
import xbmcaddon
import xbmcgui

sys.path.insert(0, xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")))

# imports from resources/lib
from common import *
from jrpchelper import *
from kodistate import *
from lcdprocglobals import *
from settings import *

def GlobalsInit():
  if not LCDprocGlobals.cSettings:
    LCDprocGlobals.cSettings = LCDprocSettings()

  if not LCDprocGlobals.cKodiState:
    LCDprocGlobals.cKodiState = CKodiState()

  LCDprocGlobals.cSettings.getSettings()

def registerNotification():
  jping = KodiJRPC_Get("JSONRPC.Ping", False)
  jperms = KodiJRPC_Get("JSONRPC.Permission", False)

def pymain():
  GlobalsInit()

  registerNotification()

  threadlist = []

  # run thread
  threadlist += [LCDprocGlobals.cKodiState]
  LCDprocGlobals.cKodiState.start()

  # run forever
  log(LOGNOTICE, "going to waitforabort")

  aborted = xbmc.Monitor().waitForAbort(-1)

  log(LOGNOTICE, "Unload request, flagging for stop")
  LCDprocGlobals.bUnloadRequested = True

  # signal cancel to all threads
  for thisthread in threadlist:
    thisthread.cancel()

  # wait for threads to join
  for thisthread in threadlist:
    thisthread.join()
    log(LOGDEBUG, "mainthread: stopped %s" % thisthread)

#########################################
# python entry point
pymain()
