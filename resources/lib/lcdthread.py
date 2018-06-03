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

import os
import sys
import threading
import time

import xbmc
import xbmcaddon

sys.path.insert(0, xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib")))

from common import *

class CLCDThread(threading.Thread):

	######
	# constructor, init vars and sync state
	def __init__(self):
		# init base classes
		super(CLCDThread, self).__init__(self)

		# instance vars
		self.m_threadlock = threading.Lock()
		self.m_cancel = False
		self.m_type = self.__class__.__name__
		self.m_threadid = None

	def cancel(self):
		log(LOGDEBUG, "Cancelling worker thread %s" % self.m_threadid)
		self.m_threadlock.acquire()
		self.m_cancel = True
		self.m_threadlock.release()
