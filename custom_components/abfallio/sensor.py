import logging
import requests
import csv
from datetime import datetime
from datetime import timedelta
import voluptuous as vol
from pprint import pprint

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_RESOURCES)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(days=1)

SENSOR_PREFIX = 'Waste '

SENSOR_TYPES = {
    'hausmuell': ['Hausmüll', '', 'mdi:recycle'],
    'gelbersack': ['Gelber Sack', '', 'mdi:recycle'],
    'papiertonne': ['Papiertonne', '', 'mdi:recycle'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCES, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug("Setup Abfall API retriever")

    try:
        data = AbfallData()
    except requests.exceptions.HTTPError as error:
        _LOGGER.error(error)
        return False

    entities = []

    for resource in config[CONF_RESOURCES]:
        sensor_type = resource.lower()

        if sensor_type not in SENSOR_TYPES:
            SENSOR_TYPES[sensor_type] = [
                sensor_type.title(), '', 'mdi:flash']

        entities.append(AbfallSensor(data, sensor_type))

    add_entities(entities)


class AbfallData(object):

    def __init__(self):
        self.data = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Updating Abfall dates using remote API")
        try:
            payload = {
                "f_id_kommune": "1723",
                "f_id_bezirk": "6122,6123",
                "f_id_strasse": "7384",
                "f_id_abfalltyp_0": "18",
                "f_id_abfalltyp_1": "17",
                "f_id_abfalltyp_2": "86",
                "f_id_abfalltyp_3": "19",
                "f_id_abfalltyp_4": "87",
                "f_id_abfalltyp_5": "33",
                "f_abfallarten_index_max": "6",
                "f_abfallarten": "18,17,86,19,87,33",
                "f_zeitraum": "20190101-20301231"
            }

            j = requests.post(
                "http://api.abfall.io/?key=645adb3c27370a61f7eabbb2039de4f1&modus=d6c5855a62cf32a4dadbc2831f0f295f&waction=export_csv", data=payload, timeout=10)

            apiRequest = j.text.split('\n')
            reader = csv.reader(apiRequest, delimiter=";")
            rowCounter = 0
            columns = None
            gelberSack = []
            restMuell = []
            papierTonne = []

            for row in reader:
                if rowCounter == 0:
                    columns = {k:row.index(k) for k in row}
                    # _LOGGER.error(f"Kopfzeile: {row}")
                else:
                    if (row[columns["Gelber Sack"]] != ""):
                        gelberSack.append(datetime.strptime(row[columns["Gelber Sack"]], "%d.%m.%Y"))

                    if (row[columns["Hausmüll"]] != ""):
                        restMuell.append(datetime.strptime(row[columns["Hausmüll"]], "%d.%m.%Y"))

                    if (row[columns["Papiertonne"]] != ""):
                        papierTonne.append(datetime.strptime(row[columns["Papiertonne"]], "%d.%m.%Y"))

                rowCounter = rowCounter + 1

            gelberSack.sort(key=lambda date: date)
            restMuell.sort(key=lambda date: date)
            papierTonne.sort(key=lambda date: date)

            nextDates = {}

            for nextDate in gelberSack:
                if nextDate > datetime.now():
                    nextDates["gelberSack"] = nextDate
                    break

            for nextDate in restMuell:
                if nextDate > datetime.now():
                    nextDates["restMuell"] = nextDate
                    break

            for nextDate in papierTonne:
                if nextDate > datetime.now():
                    nextDates["papierTonne"] = nextDate
                    break

            self.data = nextDates

        except requests.exceptions.RequestException as exc:
            _LOGGER.error("Error occurred while fetching data: %r", exc)
            self.data = None
            return False


class AbfallSensor(Entity):

    def __init__(self, data, sensor_type):
        self.data = data
        self.type = sensor_type
        self._name = SENSOR_PREFIX + SENSOR_TYPES[self.type][0]
        self._unit = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_state_attributes(self):
        """Return attributes for the sensor."""
        return self._attributes

    def update(self):
        self.data.update()
        abfallData = self.data.data

        try:
            if self.type == 'gelbersack':
                self._state = abfallData.get("gelberSack")
            elif self.type == 'hausmuell':
                self._state = abfallData.get("restMuell")
            elif self.type == 'papiertonne':
                self._state = abfallData.get("papierTonne")

            if self._state is not None:
                weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                self._attributes['days'] = (self._state.date() - datetime.now().date()).days
                if self._attributes['days'] == 0:
                    printtext = "heute"
                elif self._attributes['days'] == 1:
                    printtext = "morgen"
                else:
                    printtext = 'in {} Tagen'.format(self._attributes['days'])
                self._attributes['display_text'] = self._state.strftime(
                    '{}, %d.%m.%Y ({})').format(weekdays[self._state.weekday()], printtext)

        except ValueError:
            self._state = None