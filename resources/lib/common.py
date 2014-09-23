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

######
# imports

import xbmc

######
# defines/pseudo-constants

# addon strings
KODI_SCRIPT_ID = "script.kodi.lcdproc"
KODI_SCRIPT_NAME = "Kodi LCDproc"

# shortened log severities
LOGDEBUG   = xbmc.LOGDEBUG
LOGERROR   = xbmc.LOGERROR
LOGFATAL   = xbmc.LOGFATAL
LOGINFO    = xbmc.LOGINFO
LOGNONE    = xbmc.LOGNONE
LOGNOTICE  = xbmc.LOGNOTICE
LOGSEVERE  = xbmc.LOGSEVERE
LOGWARNING = xbmc.LOGWARNING

# interesting XBMC GUI Window IDs (no defines seem to exist for this)
class WINDOW_IDS:
  WINDOW_WEATHER               = 12600
  WINDOW_PVR                   = 10601
  WINDOW_PVR_MAX               = 10699
  WINDOW_VIDEOS                = 10006
  WINDOW_VIDEO_FILES           = 10024
  WINDOW_VIDEO_NAV             = 10025
  WINDOW_VIDEO_PLAYLIST        = 10028
  WINDOW_MUSIC                 = 10005
  WINDOW_MUSIC_PLAYLIST        = 10500
  WINDOW_MUSIC_FILES           = 10501
  WINDOW_MUSIC_NAV             = 10502
  WINDOW_MUSIC_PLAYLIST_EDITOR = 10503
  WINDOW_PICTURES              = 10002
  WINDOW_DIALOG_VOLUME_BAR     = 10104
  WINDOW_DIALOG_KAI_TOAST      = 10107

######
# common functions/helpers

######
# enum snippet from http://stackoverflow.com/a/1695250 - thanks!
def enum(*sequential, **named):
  enums = dict(zip(sequential, range(len(sequential))), **named)
  return type('Enum', (), enums)

######
# log() - wrapper for proper kodi.log output
def log(loglevel, msg):
  xbmc.log("### [%s] - %s" % (KODI_SCRIPT_ID, msg), level=loglevel)

def timestrtoseconds(timestr):
  # initialise return
  currentsecs = 0

  timearray = timestr.split(":")

  if timearray[0] == "":
    return currentsecs

  arraylen = len(timearray)
  if arraylen == 1:
    currentsecs = int(timearray[0])
  elif arraylen == 2:
    currentsecs = int(timearray[0]) * 60 + int(timearray[1])
  elif arraylen == 3:
    currentsecs = int(timearray[0]) * 60 * 60 + int(timearray[1]) * 60 + int(timearray[2])

  return currentsecs
