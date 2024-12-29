import ltpa
import requests

ACORN_API_URL = 'https://acorn.utoronto.ca/sws/'

class ACORN:
    def __init__(self, utorid, password):
        self.utorid = utorid
        self.password = password
        self.session = requests.session()

        self.ltpa_token = None
        self.bypass_codes = []
    
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
