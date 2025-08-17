import ltpa
import requests
import json
import os

from contextlib import contextmanager
from functools import cached_property

class APIResponseError(Exception):
     response: requests.Response
     
     def __init__(self, response, *args, **kwargs):
         super(*args, **kwargs)
         self.response = response

ACORN_API_URL = 'https://acorn.utoronto.ca/sws/rest'
DEFAULT_CACHE_PATH = os.path.join(os.getenv('HOME'), '.acorn', 'bypass_codes')

class ACORN:
    def __init__(self, utorid, password, bypass_codes=None):
        self.utorid = utorid
        self.password = password
        self.session = requests.session()

        self.ltpa_token = None
        self.bypass_codes = [] if bypass_codes is None else bypass_codes
    
    def authorize(self):
        if self.bypass_codes:
            self.__refresh_ltpa()
        else:
            self.__refresh_bypass()

    def isAuthorized(self):
        return 'weblogin idpz' not in self.session.get(ACORN_API_URL).text

    def authorizeIfNeeded(self):
        if self.isAuthorized():
            return
        self.authorize()

    def __refresh_bypass(self):
        self.ltpa_token, self.bypass_codes = ltpa.get_LTPA_and_bypass_codes(self.utorid, self.password)
        self.__set_session_ltpa()

    def __refresh_ltpa(self):
        bypass_code = self.bypass_codes.pop()
        driver = ltpa.make_driver()
        self.ltpa_token = ltpa.get_LTPA_token(driver, self.utorid, self.password, bypass_code)
        self.__set_session_ltpa()
        driver.close()

    def __set_session_ltpa(self):
        self.session.cookies.set(ltpa.LTPA_COOKIE_NAME, self.ltpa_token, domain="acorn.utoronto.ca")

    # ----- actual api stuff -----

    def get_json(self, endpoint, params=None):
        self.authorizeIfNeeded()
        params = {} if params is None else params
        response = self.session.get(f'{ACORN_API_URL}{endpoint}', params=params)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return APIResponseError(response)

    @cached_property
    def eligible_registrations(self):
        return self.get_json('/enrolment/eligible-registrations')
    
    @cached_property
    def program_progress(self):
        return self.get_json('/dashboard/programProgress')
    
    @cached_property
    def student_no(self):
        return self.program_progress['studentID']

    def search_courses(self, course_prefix, student_campus, sessions, registration_params=None):
        """
        course_prefix: search term
        student_campus: ERIN/SCA/STG
        sessions: list of session codes to search for
        """
        if registration_params is None:
            registration_params = self.eligible_registrations[0]['registrationParams']
        return self.get_json(
            '/enrolment/course/matching-courses',
            params=registration_params | {
                'coursePrefix': course_prefix,
                'studentCampus': student_campus,
                'sessions': sessions,
            }
        )

    def course_registration_info(self, course_code, section_code, course_session_code, registration_params=None):
        """
        course_code: department, course number, credit weight, campus
                     e.g MAT102H5, CSC463H1
                     does NOT contain F/S at the end
        section_code: F/S
        course_session_code: YYYY(1/5/9) (e.g 20249, 20251)
        """
        if registration_params is None:
            registration_params = self.eligible_registrations[0]['registrationParams']
        return self.get_json(
            '/enrolment/course/view',
            params=registration_params | {
                'courseCode': course_code,
                'courseSessionCode': course_session_code,
                'sectionCode': section_code,
                'sessionCode': course_session_code,
            }
        )

    def recent_academic_history(self):
        return self.get_json('/history/academic/recent')

    def timetable(self):
        return self.get_json('/timetable')

    def exams(self):
        return self.get_json('/timetable/exams')

    def invoice(self, session_code=""):
        return self.get_json('/invoice/', params={'sessionCode': session_code})

    def transaction_history(self):
        return self.get_json('/financial-account/transactionHistory')
        

@contextmanager
def ACORN_cached(utorid, password, bypass_codes_path=DEFAULT_CACHE_PATH):
    bypass_codes = []
    if os.path.exists(bypass_codes_path):
       with open(bypass_codes_path, 'r') as file:
           bypass_codes = [l.strip() for l in file]
    acorn = ACORN(utorid, password, bypass_codes=bypass_codes)
    try:
        yield acorn
    finally:
        os.makedirs(os.path.dirname(bypass_codes_path), exist_ok=True)
        with open(bypass_codes_path, 'w') as file:
            file.write('\n'.join(acorn.bypass_codes))
