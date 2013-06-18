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

logger = logging.getLogger('test')
class Logger(logging.Logger):
	pass
log = Logger(logger)
frm = logging.Formatter("%(levelname)s:test:%(module)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(frm)
log.addHandler(handler)

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
	elif key in ['WAIT_TIMEOUT', 'MULTI_INST_COUNT', 'CYCLE_COUNT']:
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

	if re.match(r"[A-Z]*", config['LOG_LEVEL']):
		log_level = eval("logging.%s" % config['LOG_LEVEL'])
	else:
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
		log.setLevel(GhostTestCase.log_level)

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
		self.help_open('/')
		assert 'Log In' in self.ghost.content
		result, resources = self.ghost.fill("form", {
			"username": username,
			"password": password
		})
		page, resources = self.ghost.fire_on("form", "submit", expect_loading=True)
		assert 'Logged in as: %s' % username in self.ghost.content
		log.info("Login succeeded with %s/%s" % (username, password))

	def help_select_project(self, project='openstack'):
		if not "<h3>openstack</h3>" in self.ghost.content:
			tenant_id = re.search(r"switch/(\w*)/[^\"]*\">openstack<", self.ghost.content, re.M).group(1)
			self.ghost.click("a[href*='switch/%s']" % tenant_id, expect_loading=True)
		assert "<h3>openstack</h3>" in self.ghost.content

	def help_wait_instance_active(self, instance_id, timeout=60):
		log.info("Waiting for instance %s to become active" % instance_id)
		timeout /= 2
		instance_status = None
		for i in range(0, timeout):
			if self.ghost.exists("tr#instances__row__%s td.status_up" % instance_id):
				instance_status = self.ghost.evaluate('document.querySelector("tr#instances__row__%s td.status_up").innerHTML;' % instance_id)[0]
			else:
				instance_status = None
			if instance_status == 'Active':
				break
			sleep(2)
		self.assertEqual(instance_status, 'Active')

	def help_wait_instance_gone(self, instance_id, timeout=60):
		log.info("Waiting for instance %s to disappear" % instance_id)
		timeout /= 2
		for i in range(0, timeout):
			self.ghost.click("a[href*='instances']", expect_loading=True)
			if not instance_id in self.ghost.content:
				break
			sleep(2)
		assert not instance_id in self.ghost.content

# openstack api

def get_api_auth(username='admin', password='crowbar', tenant_name='openstack', tenant_id=None, service_type='image'):
	from keystoneclient.v2_0 import client as ksclient
	_ksclient = ksclient.Client(
		username=username,
		password=password,
		tenant_id=tenant_id,
		tenant_name=tenant_name,
		auth_url=config['AUTH_URL'],
		insecure=config['INSECURE'])
	token = _ksclient.auth_token
	endpoint = _ksclient.service_catalog.url_for(
		service_type=service_type,
		endpoint_type='publicURL')

	# Get rid of trailing '/' if present
	if endpoint.endswith('/'):
		endpoint = endpoint[:-1]
	url_bits = endpoint.split('/')
	# regex to match 'v1' or 'v2.0' etc
	if re.match('v\d+\.?\d*', url_bits[-1]):
		endpoint = '/'.join(url_bits[:-1])
	return token, endpoint

def get_glance_api(token, endpoint):
	from glanceclient import Client
	glance = Client('1', endpoint=endpoint, token=token)
	return glance

def get_glance_image_properties():
	if config['VIRT'] == 'xen-hvm':
		return {'vm_mode': 'hvm'}
	elif config['VIRT'] == 'xen-pv':
		return {'vm_mode': 'xen'}
	else:
		return {}
