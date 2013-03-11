#!/usr/bin/python2

from unittest import TestCase
from ghost import Ghost
import logging
import sys
import os

class GhostTestCase(TestCase):
	display = False
	wait_timeout = 8
	viewport_size = (800, 600)
	debug_screenshots = False

	log_level = logging.INFO
	testcase_name = os.path.basename(sys.argv[0]).replace('.py', '')

	def take_screenshot(self):
		out_file = os.path.join(
			os.path.dirname(sys.argv[0]),
			'..',
			'screenshots',
			'%s.png' % GhostTestCase.testcase_name
		)
		print >> sys.stderr, "Saving screenshot to '%s'" % os.path.abspath(out_file)
		self.ghost.capture_to(out_file)

	def __str__(self):
		return GhostTestCase.testcase_name

	def setUp(self):
		self.ghost = Ghost(
			display = GhostTestCase.display,
			wait_timeout = GhostTestCase.wait_timeout,
			viewport_size = GhostTestCase.viewport_size,
			log_level = GhostTestCase.log_level
		)

	def tearDown(self):
		self.do_finally()

	def runTest(self):
		try:
			self.do_testcase()
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

def exit_error(msg=None):
	if msg:
		print >> sys.stderr, "ERROR: %s" % msg
	sys.exit(2)

def exit_skipped(msg=None):
	if msg:
		print >> sys.stderr, "SKIPPED: %s" % msg
	sys.exit(3)
