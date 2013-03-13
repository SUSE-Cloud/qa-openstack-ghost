#!/usr/bin/python2

from unittest import TestCase
from ghost import Ghost as BaseGhost
from ghost.ghost import Logger
from time import sleep as system_sleep
import logging
import sys
import os
import subprocess
import re

def exit_error(msg=None):
	if msg:
		print >> sys.stderr, "ERROR: %s" % msg
	sys.exit(2)

def exit_skipped(msg=None):
	if msg:
		print >> sys.stderr, "SKIPPED: %s" % msg
	sys.exit(3)

def sleep(sec):
	msec = int(round(sec * 100))
	for i in range(1, msec):
		system_sleep(0.01)
		Ghost._app.processEvents()

# Read config

config = {}
config_file = os.path.join(os.path.dirname(sys.argv[0]), '..', 'config')
if not os.path.exists(config_file):
	exit_error("Can't find config in '%s'" % os.path.abspath(config_file))
command = ['bash', '-c', "source %s && env" % config_file]
proc = subprocess.Popen(command, stdout = subprocess.PIPE)
for line in proc.stdout:
	(key, _, value) = line.partition("=")
	config[key] = value.strip()
	if key in ['INSECURE', 'DEBUG', 'VIEW_DISPLAY']:
		config[key] = bool(int(config[key]))
	elif key in ['WAIT_TIMEOUT']:
		config[key] = int(config[key])
proc.communicate()

# Read config end


class Ghost(BaseGhost):
	def _on_manager_ssl_errors(self, reply, errors):
		url = unicode(reply.url().toString())
		if self.ignore_ssl_errors:
			Logger.log('Ignoring invalid SSL certificate: %s' % url, level='info')
			reply.ignoreSslErrors()
		else:
			exit_error('SSL certificate error: %s' % url)


class GhostTestCase(TestCase):
	display = config['VIEW_DISPLAY']
	wait_timeout = config['WAIT_TIMEOUT']
	viewport_size = (1024, 768)
	debug_screenshots = config['DEBUG']
	ignore_ssl_errors = config['INSECURE']

	log_level = logging.INFO
	testcase_name = os.path.basename(sys.argv[0]).replace('.py', '')

	def take_screenshot(self):
		out_file = os.path.join(
			os.path.dirname(sys.argv[0]),
			'..',
			'screenshots',
			'%s.png' % GhostTestCase.testcase_name
		)
		print >> sys.stderr, "---> Saving screenshot to '%s'" % os.path.abspath(out_file)
		self.ghost.capture_to(out_file)

	def __str__(self):
		return GhostTestCase.testcase_name

	def setUp(self):
		self.ghost = Ghost(
			display = GhostTestCase.display,
			wait_timeout = GhostTestCase.wait_timeout,
			viewport_size = GhostTestCase.viewport_size,
			ignore_ssl_errors = GhostTestCase.ignore_ssl_errors,
			log_level = GhostTestCase.log_level
		)

	def tearDown(self):
		self.do_finally()

	def runTest(self):
		try:
			try:
				self.do_testcase()
			finally:
				if GhostTestCase.display:
					# give the user some time to look
					sleep(1)
			if GhostTestCase.debug_screenshots:
				self.take_screenshot()
		except AssertionError:
			self.take_screenshot()
			raise
		except SystemExit as e:
			os._exit(e.message)

	def do_testcase(self):
		# to be overwritten
		pass

	def do_finally(self):
		# to be overwritten
		pass

	# helpers

	def help_open(self, path):
		self.ghost.open(config['DASHBOARD_NODE'] + path)

	def help_login(self, username='admin', password='crowbar'):
		self.ghost.delete_cookies()
		self.help_open('')
		assert 'Log In' in self.ghost.content
		result, resources = self.ghost.fill("form", {
			"username": username,
			"password": password
		})
		page, resources = self.ghost.fire_on("form", "submit", expect_loading=True)
		assert 'Logged in as: %s' % username in self.ghost.content
