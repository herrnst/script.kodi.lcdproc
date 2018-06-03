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

import json
import os
import sys
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

sys.path.insert(0, xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")))

# imports from resources/lib
from common import *
from lcdthread import *
from lcdprocglobals import *
from jrpchelper import *
from settings import *

PLAYSTATE = enum(
  'STOP',
  'PLAY',
  'PAUSE',
  'FFWD',
  'RWD'
)

REPEATMODE = enum(
  'OFF',
  'ALL',
  'ONE'
)

ACTIVEPLAYER = enum(
  'NONE',
  'AUDIO',
  'VIDEO'
)

DISPLAYMODE = enum(
  'GENERAL',
  'MUSIC',
  'VIDEO',
  'TVSHOW',
  'PVRTV',
  'PVRRADIO',
  'MUSICVIDEO',
  'NAVIGATION',
  'SCREENSAVER'
)

class CKodiState(CLCDThread, xbmc.Monitor):

  ######
  # constructor, init vars and sync state
  def __init__(self):
    # init base classes
    CLCDThread.__init__(self)
    xbmc.Monitor.__init__(self)

    # prepare infobool strings to save some cpu ticks later
    self.const_sKaiToastActive = "Window.IsActive(" + str(WINDOW_IDS.WINDOW_DIALOG_KAI_TOAST) + ")"
    self.const_sVolumeBarActive = "Window.IsActive(" + str(WINDOW_IDS.WINDOW_DIALOG_VOLUME_BAR) + ")"

    # lock object
    self.m_jrpclock = threading.Lock()
    self.m_bDeferredSync = False

    # initialise state
    self.m_eActivePlayer = ACTIVEPLAYER.NONE
    self.m_ePlayState = PLAYSTATE.STOP
    self.m_eDisplayMode = DISPLAYMODE.GENERAL

    self.m_sSysCurrentWindow = ""
    self.m_sSysCurrentControl = ""
    self.m_iActiveWindowID = 0
    self.m_bKaiToastActive = False
    self.m_bVolumeBarActive = False
    self.m_bScreenSaverActive = False
    self.m_bNavigationActive = False
    self.m_bDPMSActive = False
    self.m_iScreenRes = 0
    self.m_sSystemTime = ""
    self.m_ePlaySpeed = 0
    self.m_iAudioChannels = 0
    self.m_bPVRIsRecording = False
    self.m_bPlayerIsMuted = False
    self.m_bPlayerAudioPassthrough = False
    self.m_bSysHasDisc = False

    self.m_fAppVolumePercent = 0.0
    self.m_iSecondsPlayerTime = 0
    self.m_iSecondsPlayerDuration = 0
    self.m_fPlayerProgressPercent = 0.0
    self.m_iLastNavTime = 0

    # clear/init other vars and resync all states with Kodi
    self.m_jrpclock.acquire()

    self.clearPlayerVars()
    self.syncStateOnInit()
    self.forceResync()

    self.m_jrpclock.release()

  def jsonrpc_get(self, method, params):
    jsondebug = False

    jsondata = {
      "jsonrpc": "2.0",
      "method": method,
      "id": method}

    if params:
      jsondata["params"] = params

    try:
      if jsondebug: log(LOGNOTICE, "==== JSONRPC debug begin ====")

      rpccmd = json.dumps(jsondata)
      if jsondebug: log(LOGNOTICE, "JSONRPC out: " + rpccmd)

      if self.m_cancel:
        log(LOGNOTICE, "in abort state")
        return False

      rpcreply = xbmc.executeJSONRPC(rpccmd)

      if jsondebug: log(LOGNOTICE, "JSONRPC in: " + rpcreply)

      if jsondebug: log(LOGNOTICE, "==== JSONRPC debug end ====")

      rpcdata = json.loads(rpcreply)

      if rpcdata["id"] == method and rpcdata.has_key("result"):
        return rpcdata["result"]
    except:
      log(LOGERROR, "Caught exception in JSON-RPC helper")

    return False

  ######
  # run() - main thread loop doing background state inquiry for
  # things we don't get notified of (like player progress)
  def run(self):

    # take note of threadid and debug to application log
    self.m_threadid = str(threading.current_thread())
    log(LOGDEBUG, "Starting worker thread '%s'" % self.m_threadid)

    # do work unless being told otherwise
    while not self.m_cancel:
      # sleep for refreshrate time or until application wants to get rid of us
      abrtreq = self.waitForAbort(LCDprocGlobals.fRefreshDelay)
      if abrtreq:
        log(LOGDEBUG, "abortRequested")
        self.cancel()
        continue

      # take lock so notifications won't interfere
      self.m_jrpclock.acquire()

      # if something requested a deferred resync, do so now
      if self.m_bDeferredSync:
        log(LOGDEBUG, "Handling deferred resync")
        self.forceResync()
        self.m_bDeferredSync = False
      # else (nothing special) just do normal status inquiry
      else:
        self.syncStatePeriodic()

      # done doing stuff, release lock
      self.m_jrpclock.release()

      ##FIXME## debug dummy output (get rid of when done)
      log(LOGDEBUG, "state: %i / mode: %i / iRefreshRate: %i / vcodec: %s / acodec: %s / progress: %f" % (self.m_ePlayState, self.getRealDisplayMode(), LCDprocGlobals.iRefreshRate, self.m_sVideoCodec, self.m_sAudioCodec, self.m_fPlayerProgressPercent))

    # leave stop note
    log(LOGDEBUG, "%s stopping" % self.m_threadid)

  ######
  # clearPlayerVars() cleans up state vars on stop, init etc.
  def clearPlayerVars(self):
    self.m_sVideoCodec = ""
    self.m_sAudioCodec = ""
    self.m_iVideoRes = 0
    self.m_sPlayFileName = ""
    self.m_bFileIsInternetStream = False
    self.m_bRepeatMode = REPEATMODE.OFF
    self.m_bShuffle = False

    self.m_sPlayerTime = ""
    self.m_sPlayerDuration = ""

  ######
  # getRealDisplayMode(self) evaluates any override flags and returns
  # the "real" mode that's at least recommended to display
  def getRealDisplayMode(self):

    # first priority: navigation
    if self.m_bNavigationActive:
      return DISPLAYMODE.NAVIGATION
    # second priority: screensaver
    if self.m_bScreenSaverActive:
      return DISPLAYMODE.SCREENSAVER

    # any other case (no overrides): whatever is running
    return self.m_eDisplayMode

  ######
  # forceResync() syncs Kodi's state with CKodiState
  def forceResync(self):

    # check if any player is active
    players = self.jsonrpc_get("Player.GetActivePlayers", False)

    # if any player is active, retrieve more data
    if players and len(players) > 0:

      # sanity check/user notification
      if len(players) > 1:
        log(LOGNOTICE, "Kodi reported more than one active players, querying first player to determine state")

      # take note of first playerid
      playerid = players[0]["playerid"]

      # retrieve some data using JSONRPC
      playitem = self.jsonrpc_get("Player.GetItem", {"playerid": playerid})
      playprops = self.jsonrpc_get("Player.GetProperties", {"playerid": playerid, "properties": ["type", "speed", "repeat", "shuffled"]})
      pvrprops = self.jsonrpc_get("PVR.GetProperties", {"properties": ["recording"]})

      # take note of type of played item
      playtype = playitem["item"]["type"]

      # take note of channel id in case of PVR
      if playtype == "channel":
        channelid = playitem["item"]["id"]

      # evaluate playback state/speed and playback type/mode
      self.setPlayStateBySpeed(playprops["speed"])
      self.setActiveStateByTypes(playtype, playprops["type"])

    # acquire one-time and periodic state information
    self.syncStateOnNotify()
    self.syncStatePeriodic()

  ######
  # syncStateOnInit() is called on class init to retrieve
  # various data from application which later will be updated
  # using notifications
  def syncStateOnInit(self):

    # retrieve volume from app properties (note we get an int here,
    # further notification will yield floats)
    props = self.jsonrpc_get("Application.GetProperties", {"properties": ["volume", "muted"]})
    self.m_fAppVolumePercent = float(props["volume"])
    self.m_bPlayerIsMuted = props["muted"]

    # additional list of interesting InfoBools
    bools = self.jsonrpc_get("XBMC.GetInfoBooleans", {
      "booleans": [
        "System.ScreenSaverActive",
        "System.DPMSActive"
        ]})

    # those two should be false on regular startup, but who knows...
    self.m_bScreenSaverActive = bools["System.ScreenSaverActive"]
    self.m_bDPMSActive = bools["System.DPMSActive"]


  ######
  # syncStateOnNotify() should be called on any player notifications
  # to get additional data about the playing item (codec names etc)
  def syncStateOnNotify(self):

    # list of InfoLabels to load
    labels = self.jsonrpc_get("XBMC.GetInfoLabels", {
      "labels": [
        "MusicPlayer.Codec",
        "Player.Filenameandpath",
        "VideoPlayer.AudioCodec",
        "VideoPlayer.VideoCodec",
        "VideoPlayer.VideoResolution"
        ]})

    # list of InfoBools (aka. CondVisibility)
    bools = self.jsonrpc_get("XBMC.GetInfoBooleans", {
      "booleans": [
        "Player.IsInternetStream",
        "Playlist.IsRandom",
        "Playlist.IsRepeat",
        "Playlist.IsRepeatOne"
        ]})

    # evaluate label data
    if labels:
      self.m_sPlayFileName = labels["Player.Filenameandpath"]
      self.m_sVideoCodec = labels["VideoPlayer.VideoCodec"]

      if self.m_eActivePlayer == ACTIVEPLAYER.AUDIO:
        self.m_sAudioCodec = labels["MusicPlayer.Codec"]
        self.m_iVideoRes = 0
      elif self.m_eActivePlayer == ACTIVEPLAYER.VIDEO:
        self.m_sAudioCodec = labels["VideoPlayer.AudioCodec"]
        try: self.m_iVideoRes = int(labels["VideoPlayer.VideoResolution"])
        except: self.m_iVideoRes = 0
      else:
        self.m_sAudioCodec = ""
        self.m_iVideoRes = 0

    # evaluate infobool data
    if bools:
      self.m_bFileIsInternetStream = bools["Player.IsInternetStream"]
      self.m_bShuffle = bools["Playlist.IsRandom"]

      if bools["Playlist.IsRepeat"] or bools["Playlist.IsRepeatOne"]:
        if bools["Playlist.IsRepeatOne"]:
          self.m_bRepeatMode = REPEATMODE.ONE
        else:
          self.m_bRepeatMode = REPEATMODE.ALL
      else:
        self.m_bRepeatMode = REPEATMODE.OFF

  ######
  # syncStatePeriodic() gets all constantly changing data that
  # application doesn't tell us about (like player time), also
  # evaluates "advanced" things like player duration
  def syncStatePeriodic(self):

    # init local vars
    oldwindow = ""
    oldcontrol = ""
    tstamp = time.time()

    # list of InfoLabels to load
    labels = self.jsonrpc_get("XBMC.GetInfoLabels", {
      "labels": [
        "MusicPlayer.Channels",
        "Player.Duration",
        "Player.Time",
        "System.CurrentWindow",
        "System.CurrentControl",
        "System.ScreenHeight",
        "System.Time(hh:mm:ss)",
        "VideoPlayer.AudioChannels",
        ]})

    # list of InfoBools (aka. CondVisibility)
    bools = self.jsonrpc_get("XBMC.GetInfoBooleans", {
      "booleans": [
        "PVR.IsRecording",
        "Player.Passthrough",
        self.const_sKaiToastActive,
        self.const_sVolumeBarActive
        ]})

    # take note of active window id (accessible via xbmcgui)
    self.m_iActiveWindowID = int(xbmcgui.getCurrentWindowId())

    # special case: codec data absent yet, player not fully in effect? whatever, do sync
    if self.m_eActivePlayer != ACTIVEPLAYER.NONE and self.m_sVideoCodec == "" and self.m_sAudioCodec == "":
      log(LOGDEBUG, "No codec info available yet, refetching information")
      self.syncStateOnNotify()

    # only act if application returned something to work with
    if labels:
      self.m_sSystemTime = labels["System.Time(hh:mm:ss)"]
      self.m_sPlayerTime = labels["Player.Time"]
      self.m_sPlayerDuration = labels["Player.Duration"]

      oldwindow = self.m_sSysCurrentWindow
      oldcontrol = self.m_sSysCurrentControl
      self.m_sSysCurrentWindow = labels["System.CurrentWindow"]
      self.m_sSysCurrentControl = labels["System.CurrentControl"]

      self.m_iScreenRes = int(labels["System.ScreenHeight"])

      if self.m_eActivePlayer == ACTIVEPLAYER.AUDIO:
        try: self.m_iAudioChannels = int(labels["MusicPlayer.Channels"])
        except: self.m_iAudioChannels = 0
      elif self.m_eActivePlayer == ACTIVEPLAYER.VIDEO:
        try: self.m_iAudioChannels = int(labels["VideoPlayer.AudioChannels"])
        except: self.m_iAudioChannels = 0
      else:
        self.m_iAudioChannels = 0

      if self.m_eActivePlayer != ACTIVEPLAYER.NONE:
        self.m_iSecondsPlayerTime = timestrtoseconds(self.m_sPlayerTime)
        self.m_iSecondsPlayerDuration = timestrtoseconds(self.m_sPlayerDuration)
        if self.m_iSecondsPlayerDuration == 0:
          self.m_fPlayerProgressPercent = 0.0
        else:
          self.m_fPlayerProgressPercent = float(self.m_iSecondsPlayerTime) / float(self.m_iSecondsPlayerDuration)
      else:
        self.m_iSecondsPlayerTime = 0
        self.m_iSecondsPlayerDuration = 0
        self.m_fPlayerProgressPercent = 0.0

    # same for the bools, only act if there's something
    if bools:
      self.m_bPVRIsRecording = bools["PVR.IsRecording"]
      self.m_bPlayerAudioPassthrough = bools["Player.Passthrough"]
      self.m_bKaiToastActive = bools[self.const_sKaiToastActive]
      self.m_bVolumeBarActive = bools[self.const_sVolumeBarActive]

    # evaluate some vars for state updates

    # update last nav timestamp when window or control changed
    # (equals: navigation active)
    if self.m_sSysCurrentWindow != oldwindow or self.m_sSysCurrentControl != oldcontrol:
      self.m_iLastNavTime = tstamp

    # update state if lastnav time+timeout is larger than timestamp
    if (self.m_iLastNavTime + LCDprocGlobals.iOverlayTimeout) > tstamp:
      self.m_bNavigationActive = True
    # lastnav+timeout is old, conditionally reset and restore overrides
    else:
      self.m_bNavigationActive = False

  def onNotification(self, sender, method, data):
    if False:
      log(LOGNOTICE, "CXBMCMonitor::onNotification() - dumping")
      log(LOGNOTICE, "CXBMCMonitor::onNotification() - sender: %s" % sender)
      log(LOGNOTICE, "CXBMCMonitor::onNotification() - method: %s" % method)
      log(LOGNOTICE, "CXBMCMonitor::onNotification() - data: %s" % data)

    log(LOGDEBUG, "onNotification(): acquire m_jrpclock")
    self.m_jrpclock.acquire()

    jsondata = json.loads(data)

    if method == "Player.OnPlay":
      self.notifyPlayerOnPlay(jsondata)
    elif method == "Player.OnPause":
      self.notifyPlayerOnPause(jsondata)
    elif method == "Player.OnSpeedChanged":
      self.notifyPlayerOnSpeedChanged(jsondata)
    elif method == "Player.OnStop":
      self.notifyPlayerOnStop(jsondata)
    elif method == "Player.OnPropertyChanged":
      self.notifyPlayerOnPropertyChanged(jsondata)
    elif method == "Application.OnVolumeChanged":
      self.notifyApplicationVolumeChanged(jsondata)
    elif method == "GUI.OnScreenSaverActivated":
      self.notifyGUIOnScreenSaver(True)
    elif method == "GUI.OnScreensaverDeactivated":
      self.notifyGUIOnScreenSaver(False)
    elif method == "GUI.OnDPMSActivated":
      self.notifyGUIOnDPMS(True)
    elif method == "GUI.OnDPMSDeactivated":
      self.notifyGUIOnDPMS(False)

    log(LOGDEBUG, "onNotification(): release m_jrpclock")
    self.m_jrpclock.release()

  def onSettingsChanged(self):
    LCDprocGlobals.cSettings.getSettings()

  # action handler for JSON-RPC Player.onPlay notification
  def notifyPlayerOnPlay(self, jsondata):

    # receiving calls also on unpause, but only care on play start
    if self.m_ePlayState != PLAYSTATE.PAUSE:

      # take note of received item type
      itemtype = jsondata["item"]["type"]

      # if itemtype is "unknown", inspect further (happens for paplayer and dsdiff audio)
      if itemtype == "unknown":

        # trigger deferred resync
        log(LOGDEBUG, "Got type 'unknown' for playerid %i from application (notification too early?), triggering deferred resync" % jsondata["player"]["playerid"])
        self.m_bDeferredSync = True

      # got usable type, proceed
      else:

        # type is channel, move on with channeltype as subtype (pvrtv vs. pvrradio)
        if itemtype == "channel":
          self.setActiveStateByTypes(itemtype, jsondata["item"]["channeltype"])

        # all else should be clear, evaluate without subtype
        else:
          self.setActiveStateByTypes(itemtype, False)

        # sync state details
        self.syncStateOnNotify()

    # update local state to playing
    self.m_ePlayState = PLAYSTATE.PLAY

  def notifyPlayerOnPause(self, jsondata):
    self.m_ePlayState = PLAYSTATE.PAUSE

  def notifyPlayerOnSpeedChanged(self, jsondata):
    self.setPlayStateBySpeed(jsondata["player"]["speed"])

  def notifyPlayerOnStop(self, jsondata):
    self.m_ePlayState = PLAYSTATE.STOP
    self.m_eDisplayMode = DISPLAYMODE.GENERAL
    self.m_eActivePlayer = ACTIVEPLAYER.NONE
    self.clearPlayerVars()

  # handle Player.OnPropertyChanged notification
  def notifyPlayerOnPropertyChanged(self, jsondata):

    # act only if property key exists in dict
    if jsondata.has_key("property"):

      # act on shuffled state if given
      if jsondata["property"].has_key("shuffled"):
        self.m_bShuffle = jsondata["property"]["shuffled"]

      # act on repeat mode if given
      if jsondata["property"].has_key("repeat"):
        if jsondata["property"]["repeat"] == "all":
          self.m_bRepeatMode = REPEATMODE.ALL
        elif jsondata["property"]["repeat"] == "one":
          self.m_bRepeatMode = REPEATMODE.ONE
        else:
          self.m_bRepeatMode = REPEATMODE.OFF

  # handle Application.OnVolumeChanged notification
  def notifyApplicationVolumeChanged(self, jsondata):

    # take volume if key is present
    if jsondata.has_key("volume"):
      self.m_fAppVolumePercent = jsondata["volume"]

    # take mute flag if key is present
    if jsondata.has_key("muted"):
      self.m_bPlayerIsMuted = jsondata["muted"]

  # handle screensaver (de)activation notifications
  def notifyGUIOnScreenSaver(self, state):

    # copy state
    self.m_bScreenSaverActive = state

  # handle dpms (de)activation notifications
  def notifyGUIOnDPMS(self, state):

    # copy state
    self.m_bDPMSActive = state

  def setPlayStateBySpeed(self, playspeed):
    if playspeed < 0:
      self.m_ePlayState = PLAYSTATE.RWD
    elif playspeed > 1:
      self.m_ePlayState = PLAYSTATE.FFWD
    else:
      self.m_ePlayState = PLAYSTATE.PLAY

  def setActiveStateByTypes(self, playtype, proptype):
    if playtype == "movie":
      self.m_eDisplayMode = DISPLAYMODE.VIDEO
      self.m_eActivePlayer = ACTIVEPLAYER.VIDEO
    elif playtype == "episode":
      self.m_eDisplayMode = DISPLAYMODE.TVSHOW
      self.m_eActivePlayer = ACTIVEPLAYER.VIDEO
    elif playtype == "song":
      self.m_eDisplayMode = DISPLAYMODE.MUSIC
      self.m_eActivePlayer = ACTIVEPLAYER.AUDIO
    elif playtype == "musicvideo":
      self.m_eDisplayMode = DISPLAYMODE.MUSICVIDEO
      self.m_eActivePlayer = ACTIVEPLAYER.VIDEO
    elif playtype == "channel":
      if proptype == "tv" or proptype == "video":
        self.m_eDisplayMode = DISPLAYMODE.PVRTV
        self.m_eActivePlayer = ACTIVEPLAYER.VIDEO
      elif proptype == "radio" or proptype == "audio":
        self.m_eDisplayMode = DISPLAYMODE.PVRRADIO
        self.m_eActivePlayer = ACTIVEPLAYER.AUDIO
    elif playtype == "unknown":
      if proptype == "video":
        self.m_eDisplayMode = DISPLAYMODE.VIDEO
        self.m_eActivePlayer = ACTIVEPLAYER.VIDEO
      elif proptype == "audio":
        self.m_eDisplayMode = DISPLAYMODE.MUSIC
        self.m_eActivePlayer = ACTIVEPLAYER.AUDIO
      else:
        self.m_eDisplayMode = DISPLAYMODE.GENERAL
        self.m_eActivePlayer = ACTIVEPLAYER.NONE
    else:
      self.m_eDisplayMode = DISPLAYMODE.GENERAL
      self.m_eActivePlayer = ACTIVEPLAYER.NONE
