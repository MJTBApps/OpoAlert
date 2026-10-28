"""Regresion v0.4.7. No hace peticiones al BOP: prueba el calendario y
la validacion AJAX del diagnostico 0.4.6 con datos sinteticos.
"""
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from history import (
    _month_number, _jsf_messages, _validation_error_text, _choose_calendar_day,
    _go_to_calendar_month, _visible_calendar_month, fill_date_range, CoverageError,
)

BAD_XML = '''<?xml version="1.0"?><partial-response><changes>
<update id="messages"><![CDATA[<div class="ui-messages-error">Des de: Validation Error: Value is not valid.</div>]]></update>
<update id="boletines3"><![CDATA[<div>Boletin 206</div>]]></update>
</changes></partial-response>'''
OK_XML = '''<?xml version="1.0"?><partial-response><changes>
<update id="messages"><![CDATA[<div></div>]]></update>
<update id="boletines3"><![CDATA[<div>Boletines 204-206</div>]]></update>
</changes></partial-response>'''

class Calendar047(unittest.TestCase):
    def test_month_names_and_picker_select_indices(self):
        self.assertEqual(_month_number('Setembre'), 9)
        self.assertEqual(_month_number('Septiembre'), 9)
        self.assertEqual(_month_number('October'), 10)
        self.assertEqual(_month_number('març'), 3)
        self.assertEqual(_month_number('9', is_select=True), 10)
        with self.assertRaises(CoverageError):
            _month_number('not-a-month')

    def test_parses_server_validation_in_diagnostic_046(self):
        self.assertIn('Value is not valid', _validation_error_text(BAD_XML))
        self.assertEqual(len(_jsf_messages(BAD_XML)), 1)
        self.assertIsNone(_validation_error_text(OK_XML))

    def test_parser_does_not_accept_stale_xml_as_validation(self):
        self.assertIsNone(_validation_error_text('HTTP 200 but not JSF'))

    def test_selects_final_date_before_initial_date(self):
        import history
        sequence = []
        orig_choose = history._choose_date
        orig_match = history._values_match
        try:
            history._choose_date = lambda page, key, day: sequence.append((key, day))
            history._values_match = lambda page, first, last: True
            fill_date_range(None, date(2026, 9, 28), date(2026, 10, 2))
        finally:
            history._choose_date = orig_choose
            history._values_match = orig_match
        self.assertEqual(sequence, [
            ('filtroCalendarioFin', date(2026, 10, 2)),
            ('filtroCalendarioIni', date(2026, 9, 28)),
        ])

    def test_rejects_date_change_during_selection(self):
        import history
        orig_choose = history._choose_date
        orig_match = history._values_match
        try:
            history._choose_date = lambda page, key, day: None
            history._values_match = lambda page, first, last: False
            with self.assertRaisesRegex(CoverageError, 'cambio una fecha'):
                fill_date_range(None, date(2026, 9, 28), date(2026, 10, 2))
        finally:
            history._choose_date = orig_choose
            history._values_match = orig_match

if __name__ == '__main__':
    unittest.main()
