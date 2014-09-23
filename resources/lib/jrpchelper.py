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

import xbmc
import xbmcaddon

sys.path.insert(0, xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")))

# imports from resources/lib
from common import *

def KodiJRPC_Get(method, params):
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

    rpcreply = xbmc.executeJSONRPC(rpccmd)    
    if jsondebug: log(LOGNOTICE, "JSONRPC in: " + rpcreply)

    if jsondebug: log(LOGNOTICE, "==== JSONRPC debug end ====")

    rpcdata = json.loads(rpcreply)

    if rpcdata["id"] == method and rpcdata.has_key("result"):
      return rpcdata["result"]
  except:
    log(LOGERROR, "Caught exception in JSON-RPC helper")

  return False
