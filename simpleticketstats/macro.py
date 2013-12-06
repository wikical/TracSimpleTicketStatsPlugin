# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Ivan F. Villanueva B <ivan@wikical.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from datetime import timedelta
import datetime
import json
import math
import random
import re
import string

from trac.core import *
from trac.perm import IPermissionRequestor
from trac.util.datefmt import utc
from trac.util.html import Markup
from trac.web.chrome import Chrome, ITemplateProvider, add_javascript
from trac.wiki.macros import WikiMacroBase, parse_args

from localtimezone import LocalTimeZone
try:
    from trac.util.datefmt import to_utimestamp as to_timestamp
except ImportError:
    from trac.util.datefmt import to_timestamp


def _get_config_variable(env, variable_name, default_value):
    return env.config.get('simpleticketstats', variable_name, default_value)


def _get_args_defaults(env, args):
    """
    Fill the args dict with the default values for the keys that don't exist
    """
    defaults = {
        'title': 
            _get_config_variable(env, 'default_title', 'Tickets statistics'),
        'days': _get_config_variable(env, 'default_days', '60'),
        'width': _get_config_variable(env, 'default_width', '600'),
        'height': _get_config_variable(env, 'default_height', '400'),
        'timezone': _get_config_variable(env, 'default_timezone', 'local')}
    defaults.update(args)
    return defaults

class SimpleTicketStatsMacro(WikiMacroBase):

    implements(ITemplateProvider, IPermissionRequestor)


    # IPermissionRequestor method
    def get_permission_actions(self):
        return ['SIMPLE_TICKET_STATS']


    # ITemplateProvider method
    # Used to add the plugin's template
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]


    # ITemplateProvider method
    # Used to add the plugin's htdocs (static files)
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        # NOTE: if you change the namespace below (stsm), you also need to
        # change it when using add_javascript
        return [('stsm', resource_filename(__name__, 'htdocs'))]


    # main method
    def expand_macro(self, formatter, name, args):
        args = parse_args(args)
        # args is a tuple with a list of unnamed parameters (which is empty as
        # we don't support them), and a dictionary (named parameters)
        args = _get_args_defaults(formatter.env, args[1])
        timezone = args.pop('timezone')
        if timezone == 'utc' :
            timezone = utc 
        elif timezone == 'local':
            timezone = LocalTimeZone()
        else:
            raise Exception('parameter "timezone" was either "utc" nor '
                    '"local", it was: %s' % timezone)
        title = args.pop('title')
        days = int(args.pop('days'))
        width = int(args.pop('width'))
        height = int(args.pop('height'))
        today = datetime.datetime.combine(
                datetime.date.today(),
                # last microsecond :-) of today
                datetime.time(23, 59, 59, 999999, tzinfo=timezone))
        ts_start = to_timestamp(today - timedelta(days=days))
        ts_end = to_timestamp(today)

        # values for the template:
        data = {}
        data['title'] = title
        data['width'] = width
        data['height'] = height
        data['id'] = ''.join(random.choice(string.lowercase) for i in range(10)) 

        # calculate db extra restrictions from extra parameters
        extra_parameters = []
        extra_sql = ''
        if args:
            extra_sql_constraints = []
            not_allowed = re.compile(r'[^a-zA-Z0-9]')
            for key, value in args.items():
                if not_allowed.search(key):
                    raise Exception('a paramter contained not allowed characters')
                if value[0] == '!':
                    extra_sql_constraints.append("{0} <> %s".format(key))
                    extra_parameters.append(value[1:])
                else:
                    extra_sql_constraints.append("{0} = %s".format(key))
                    extra_parameters.append(value)
            extra_sql = u' AND '.join(extra_sql_constraints)

        if hasattr(self.env, 'get_read_db'):
            db = self.env.get_read_db()
        else:
            db = self.env.get_db_cnx()
        cursor = db.cursor()

        series = {
            'openedTickets': {},
            'closedTickets': {},
            'reopenedTickets': {},
            'openTickets': {}
        }

        # NOTE on casting times: in the sql statements below, we use:
        #            CAST((time / 86400) AS int) * 86400 AS date
        # which homogenize all times during a day to the same day. Example:
        # The following two values will have the same value
        # 1386280739  (2013-12-05 22:58:59)  ->  2013-12-05 00:00:00
        # 1386270739  (2013-12-05 20:12:19)  ->  2013-12-05 00:00:00

        # number of created tickets for the time period, grouped by day
        # a day has 86400 seconds
        sql = 'SELECT COUNT(DISTINCT id), ' \
                     'CAST((time / 86400) AS int) * 86400 AS date ' \
              'FROM ticket WHERE {0} {1} time BETWEEN %s AND %s ' \
              'GROUP BY date ORDER BY date ASC'.format(
                    extra_sql, ' AND ' if extra_sql else '')
        cursor.execute(sql, tuple(extra_parameters) + (ts_start, ts_end))
        for count, timestamp in cursor:
            # flot needs the time in milliseconds, not seconds, see
            # https://github.com/flot/flot/blob/master/API.md#time-series-data
            series['openedTickets'][timestamp*1000] = float(count)

        # number of reopened tickets for the time period, grouped by day
        # a day has 86400 seconds
        cursor.execute("SELECT COUNT(DISTINCT tc.ticket), "
                            "CAST((tc.time / 86400) AS int) * 86400 as date "
                       "FROM ticket_change tc JOIN ticket t ON t.id = tc.ticket "
                       "WHERE {0} {1} field = 'status' AND newvalue = 'reopened' "
                       "AND tc.time BETWEEN %s AND %s "
                       "GROUP BY date ORDER BY date ASC".format(
                           extra_sql, ' AND ' if extra_sql else ''),
                       tuple(extra_parameters) + (ts_start, ts_end))
        for count, timestamp in cursor:
            # flot needs the time in milliseconds, not seconds, see
            # https://github.com/flot/flot/blob/master/API.md#time-series-data
            series['reopenedTickets'][float(timestamp*1000)] = float(count)

        # number of closed tickets for the time period, grouped by day (ms)
        cursor.execute("SELECT COUNT(DISTINCT ticket), "
                            "CAST((tc.time / 86400) AS int) * 86400 AS date "
                       "FROM ticket_change tc JOIN ticket t ON t.id = tc.ticket "
                       "WHERE {0} {1} tc.field = 'status' AND tc.newvalue = 'closed' "
                       "AND tc.time BETWEEN %s AND %s " \
                       "GROUP BY date ORDER BY date ASC".format(
                           extra_sql, ' AND ' if extra_sql else ''),
                       tuple(extra_parameters) + (ts_start, ts_end))
        for count, timestamp in cursor:
            # flot needs the time in milliseconds, not seconds, see
            # https://github.com/flot/flot/blob/master/API.md#time-series-data
            series['closedTickets'][float(timestamp*1000)] = float(count)

        # calculate number of open tickets for each day
        
        # number of open tickets up to now
        cursor.execute(
            "SELECT COUNT(*) FROM ticket "
            "WHERE {0} {1} status <> 'closed'".format(
                extra_sql, ' AND ' if extra_sql else ''),
            tuple(extra_parameters))
        open_tickets = cursor.fetchone()[0]
        series['openTickets'][ts_end * 1000] = open_tickets

        for day_ms in range(math.floor(ts_end / 86400.0) * 86400000, ts_start * 1000, -86400000):
            open_tickets += series['closedTickets'].get(day_ms, 0)
            open_tickets -= series['openedTickets'].get(day_ms, 0)
            open_tickets -= series['reopenedTickets'].get(day_ms, 0)
            series['openTickets'][day_ms] = open_tickets

        # sort all series and put them in data
        for i in series:
            keys = series[i].keys()
            keys.sort()
            data[i] = json.dumps([(k, series[i][k]) for k in keys])

        # generate output
        # NOTE: if you change the namespace below, you also need to change it
        # when using in get_htdocs_dirs
        add_javascript(formatter.req, 'stsm/js/excanvas.min.js')
        add_javascript(formatter.req, 'stsm/js/jquery.flot.min.js')
        add_javascript(formatter.req, 'stsm/js/jquery.flot.stack.min.js')
        add_javascript(formatter.req, 'stsm/js/simpleticketstats.js')
        template = Chrome(self.env).load_template(
                'simpleticketstats_macro.html', method='text')
        return Markup(template.generate(**data))
