"""
Reads data from the HVC afvalkalender REST API and adds pickup dates as sensors

For more details about this component, please refer to the documentation at
https://github.com/marius1/home-assistant-custom-components
"""
import logging
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_NAME
from homeassistant.util import Throttle
from datetime import date, datetime, timedelta

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'hvc'
DOMAIN = 'hvc'
ICON = 'mdi:delete-empty'
SENSOR_PREFIX = 'trash_'

GARBAGE_TYPES = {
	2: 'rest',
	3: 'papier',
	5: 'gft',
	6: 'plastic'
}

CONF_POSTALCODE = 'postalcode'
CONF_HOUSENUMBER = 'housenumber'

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=12)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
	vol.Required(CONF_POSTALCODE): cv.string,
	vol.Required(CONF_HOUSENUMBER): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
	postalcode = config.get(CONF_POSTALCODE)
	housenumber = config.get(CONF_HOUSENUMBER)

	addressUri = (f"https://apps.hvcgroep.nl/rest/adressen/{postalcode}-{housenumber}")
	_LOGGER.debug(f"Searching address {postalcode}-{housenumber} at: {addressUri}")

	response = requests.get(addressUri)
	addresses = response.json()
	
	if not addresses:
		_LOGGER.error(f"Could not find address {postalcode}-{housenumber}, check config")
		return
	
	bagId = addresses[0]['bagId']

	_LOGGER.debug(f"Found bagId {bagId}")

	schedule = (TrashCollectionSchedule(bagId, config))
	schedule.update()

	for trashType in schedule.data:
		add_devices([TrashCollectionSensor(trashType, schedule, config)])

class TrashCollectionSensor(Entity):
	"""Representation of a Sensor."""
	def __init__(self, afvalstroomId, schedule, config):
		"""Initialize the sensor."""
		self.config = config
		self._state = None
		self._name = GARBAGE_TYPES[afvalstroomId]
		self._afvalstroomId = afvalstroomId
		self.schedule = schedule

	@property
	def name(self):
		"""Return the name of the sensor."""
		return SENSOR_PREFIX + self._name

	@property
	def state(self):
		"""Return the state of the sensor."""
		return self._state

	@property
	def icon(self):
		"""Set the default sensor icon."""
		return ICON

	def update(self):
		_LOGGER.debug(f"Update: {self._name}")
		self.schedule.update()
		self._state = self.schedule.data[self._afvalstroomId]

class TrashCollectionSchedule(object):
	def __init__(self, bagId, config):
		"""Fetch vars."""
		self.bagId = bagId
		self.data = None
		self.config = config
		self.garbageTypes = None
	
	@Throttle(MIN_TIME_BETWEEN_UPDATES)
	def update(self):		
		year = date.today().year
		kalenderUrl = (f"https://apps.hvcgroep.nl/rest/adressen/{self.bagId}/kalender/{year}")
		_LOGGER.debug(f"Getting calendar data for {self.bagId} at: {kalenderUrl}")
		response = requests.get(kalenderUrl)
		data = response.json()

		if not data:
			_LOGGER.warning(f"Failed to get data at: {kalenderUrl}")
		
		self.data = {}
		for trashDay in data:
			afvalstroomId = trashDay['afvalstroom_id']
			pickupDate = datetime.strptime(trashDay['ophaaldatum'], '%Y-%m-%d')

			if afvalstroomId not in self.data and pickupDate > datetime.now():
				self.data[afvalstroomId] = pickupDate