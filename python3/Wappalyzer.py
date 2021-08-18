import aiohttp
from typing import Callable, Dict, Iterable, List, Mapping, Any, Set
import json
import logging
import pkg_resources
import re
import os
import pathlib
import requests
from datetime import datetime, timedelta

from bs4 import BeautifulSoup # type: ignore
from typing import Union, Optional

logger = logging.getLogger(name="python-Wappalyzer")


class WappalyzerError(Exception):
    """
    Raised for fatal Wappalyzer errors.
    """
    pass


class WebPage:
    """
    Simple representation of a web page, decoupled
    from any particular HTTP library's API.

    Well, except for the class methods that use `requests`
    or `aiohttp` to create the WebPage.

    This object is designed to be created for each website scanned
    by python-Wappalyzer. 
    It will parse the HTML with BeautifulSoup to find <script> and <meta> tags.

    You can create it from manually from HTML with the `WebPage()` method
    or from the class methods. 

    """

    def __init__(self, url:str, html:str, headers:Mapping[str, Any]):
        """
        Initialize a new WebPage object manually.  

        >>> from Wappalyzer import WebPage
        >>> w = WebPage('exemple.com',  html='<strong>Hello World</strong>', headers={'Server': 'Apache', })

        :param url: The web page URL.
        :param html: The web page content (HTML)
        :param headers: The HTTP response headers
        """
        self.url = url
        self.html = html
        self.headers = headers
        self.scripts :List[str] = []

        try:
            list(self.headers.keys())
        except AttributeError:
            raise ValueError("Headers must be a dictionary-like object")

        self._parse_html()

    def _parse_html(self):
        """
        Parse the HTML with BeautifulSoup to find <script> and <meta> tags.
        """
        self.parsed_html = soup = BeautifulSoup(self.html, 'lxml')
        self.scripts.extend(script['src'] for script in
                        soup.findAll('script', src=True))
        self.meta = {
            meta['name'].lower():
                meta['content'] for meta in soup.findAll(
                    'meta', attrs=dict(name=True, content=True))
        }

    @classmethod
    def new_from_url(cls, url: str, **kwargs:Any) -> 'WebPage':
        """
        Constructs a new WebPage object for the URL,
        using the `requests` module to fetch the HTML.

        >>> from Wappalyzer import WebPage
        >>> page = WebPage.new_from_url('exemple.com', timeout=5)

        :param url: URL 
        :param headers: (optional) Dictionary of HTTP Headers to send.
        :param cookies: (optional) Dict or CookieJar object to send.
        :param timeout: (optional) How many seconds to wait for the server to send data before giving up. 
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param verify: (optional) Boolean, it controls whether we verify the SSL certificate validity. 
        :param \*\*kwargs: Any other arguments are passed to `requests.get` method as well. 
        """
        response = requests.get(url, **kwargs)
        return cls.new_from_response(response)

    @classmethod
    def new_from_response(cls, response:requests.Response) -> 'WebPage':
        """
        Constructs a new WebPage object for the response,
        using the `BeautifulSoup` module to parse the HTML.

        :param response: `requests.Response` object
        """
        return cls(response.url, html=response.text, headers=response.headers)


    @classmethod
    async def new_from_url_async(cls, url: str, verify: bool = True,
                                 aiohttp_client_session: aiohttp.ClientSession = None, **kwargs:Any) -> 'WebPage':
        """
        Same as new_from_url only Async.

        Constructs a new WebPage object for the URL,
        using the `aiohttp` module to fetch the HTML.

        >>> from Wappalyzer import WebPage
        >>> from aiohttp import ClientSession
        >>> async with ClientSession() as session:
        ...     page = await WebPage.new_from_url_async(aiohttp_client_session=session)
        
        :param url: URL
        :param aiohttp_client_session: `aiohttp.ClientSession` instance to use, optional.
        :param verify: (optional) Boolean, it controls whether we verify the SSL certificate validity. 
        :param headers: Dict. HTTP Headers to send with the request (optional).
        :param cookies: Dict. HTTP Cookies to send with the request (optional).
        :param timeout: Int. override the session's timeout (optional)
        :param proxy: Proxy URL, `str` or `yarl.URL` (optional).
        :param \*\*kwargs: Any other arguments are passed to `aiohttp.ClientSession.get` method as well. 

        """

        if not aiohttp_client_session:
            connector = aiohttp.TCPConnector(ssl=verify)
            aiohttp_client_session = aiohttp.ClientSession(connector=connector)

        async with aiohttp_client_session.get(url, **kwargs) as response:
            return await cls.new_from_response_async(response)

    @classmethod
    async def new_from_response_async(cls, response:aiohttp.ClientResponse) -> 'WebPage':
        """
        Constructs a new WebPage object for the response,
        using the `BeautifulSoup` module to parse the HTML.

        >>> from aiohttp import ClientSession
        >>> wappalyzer = Wappalyzer.latest()
        >>> async with ClientSession() as session:
        ...     page = await session.get("http://example.com")
        ...
        >>> webpage = await WebPage.new_from_response_async(page)

        :param response: `aiohttp.ClientResponse` object
        """
        html = await response.text()
        return cls(str(response.url), html=html, headers=response.headers)


class Wappalyzer:
    """
    Python Wappalyzer driver.

    Consider the following exemples.
    
    Here is how you can use the latest technologies file from AliasIO/wappalyzer repository. 
    
    .. python::

        from Wappalyzer import Wappalyzer
        wappalyzer=Wappalyzer.latest(update=True)
        # Create webpage
        webpage=WebPage.new_from_url('http://example.com')
        # analyze
        results = wappalyzer.analyze_with_categories(webpage)


    Here is how you can custom request and headers arguments:
    
    .. python::

        import requests
        from Wappalyzer import Wappalyzer, WebPage
        wappalyzer = Wappalyzer.latest()
        webpage = WebPage.new_from_url('http://exemple.com', headers={'User-Agent': 'Custom user agent'})
        wappalyzer.analyze_with_categories(webpage)

    """

    def __init__(self, categories:Dict[str, Any], technologies:Dict[str, Any]):
        """
        Manually initialize a new Wappalyzer instance. 
        
        You might want to use the factory method: `latest`

        :param categories: Map of category ids to names, as in ``technologies.json``.
        :param technologies: Map of technology names to technology dicts, as in ``technologies.json``.
        """
        self.categories = categories
        self.technologies = technologies
        self._confidence_regexp = re.compile(r"(.+)\\;confidence:(\d+)")

        # TODO
        for name, technology in list(self.technologies.items()):
            self._prepare_technology(technology)

    @classmethod
    def latest(cls, technologies_file:str=None, update:bool=False) -> 'Wappalyzer':
        """
        Construct a Wappalyzer instance.
        
        Use ``update=True`` to download the very latest file from internet. 
        Do not update if the file has already been updated in the last 24 hours. 
        *New in version 0.4.0*

        Use ``technologies_file=/some/path/technologies.json`` to load a 
        custom technologies file. 
        
        If no arguments is passed, load the default ``data/technologies.json`` file
        inside the package ressource.

        :param technologies_file: File path
        :param update: Download and use the latest ``technologies.json`` file 
            from `AliasIO/wappalyzer <https://github.com/AliasIO/wappalyzer>`_ repository.  
        
        """
        default=pkg_resources.resource_string(__name__, "technologies.json")
        defaultobj = json.loads(default)

        if technologies_file:
            with open(technologies_file, 'r', encoding='utf-8') as fd:
                obj = json.load(fd)
        elif update:
            should_update = True
            _technologies_file: pathlib.Path
            _files = cls._find_files(['HOME', 'APPDATA',], ['.python-Wappalyzer/technologies.json'])
            if _files:
                _technologies_file = pathlib.Path(_files[0])
                last_modification_time = datetime.fromtimestamp(_technologies_file.stat().st_mtime)
                if datetime.now() - last_modification_time < timedelta(hours=24):
                    should_update = False

            # Get the lastest file
            if should_update:
                try:
                    lastest_technologies_file=requests.get('https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json')
                    obj = lastest_technologies_file.json()
                    _technologies_file = pathlib.Path(cls._find_files(
                        ['HOME', 'APPDATA',],
                        ['.python-Wappalyzer/technologies.json'],
                        create = True
                        ).pop())

                    if obj != defaultobj:
                        with _technologies_file.open('w', encoding='utf-8') as tfile:
                            tfile.write(lastest_technologies_file.text)
                        logger.info("python-Wappalyzer technologies.json file updated")

                except Exception as err: # Or loads default
                    logger.error("Could not download latest Wappalyzer technologies.json file because of error : '{}'. Using default. ".format(err))
                    obj = defaultobj
            else:
                logger.debug("python-Wappalyzer technologies.json file not updated because already updated in the last 24h")
                with _technologies_file.open('r', encoding='utf-8') as tfile:
                    obj = json.load(tfile)

            logger.info("Using technologies.json file at {}".format(_technologies_file.as_posix()))
        else:
            obj = defaultobj

        
        return cls(categories=obj['categories'], technologies=obj['technologies'])

    @staticmethod
    def _find_files(
        env_location: List[str],
        potential_files: List[str],
        default_content: str = "",
        create: bool = False,
    ) -> List[str]:
        """Find existent files based on folders name and file names.
        Arguments:
        - `env_location`: list of environment variable to use as a base path. Exemple: ['HOME', 'XDG_CONFIG_HOME', 'APPDATA', 'PWD']
        - `potential_files`: list of filenames. Exemple: ['.myapp/conf.ini',]
        - `default_content`: Write default content if the file does not exist
        - `create`: Create the file in the first existing env_location with default content if the file does not exist
        """
        potential_paths = []
        existent_files = []

        env_loc_exists = False
        # build potential_paths of config file
        for env_var in env_location:
            if env_var in os.environ:
                env_loc_exists = True
                for file_path in potential_files:
                    potential_paths.append(os.path.join(os.environ[env_var], file_path))
        if not env_loc_exists and create:
            raise RuntimeError(f"Cannot find any of the env locations {env_location}. ")
        # If file exist, add to list
        for p in potential_paths:
            if os.path.isfile(p):
                existent_files.append(p)
        # If no file foud and create=True, init new file
        if len(existent_files) == 0 and create:
            os.makedirs(os.path.dirname(potential_paths[0]), exist_ok=True)
            with open(potential_paths[0], "w", encoding='utf-8') as config_file:
                config_file.write(default_content)
            existent_files.append(potential_paths[0])
        return existent_files

    def _prepare_technology(self, technology: Dict[str, Any]) -> None:
        """
        Normalize technology data, preparing it for the detection phase.
        """
        # Ensure these keys' values are lists
        for key in ['url', 'html', 'scripts', 'implies']:
            try:
                value = technology[key]
            except KeyError:
                technology[key] = []
            else:
                if not isinstance(value, list):
                    technology[key] = [value]

        # Ensure these keys exist
        for key in ['headers', 'meta']:
            try:
                value = technology[key]
            except KeyError:
                technology[key] = {}

        # Ensure the 'meta' key is a dict
        obj = technology['meta']
        if not isinstance(obj, dict):
            technology['meta'] = {'generator': obj}

        # Ensure keys are lowercase
        for key in ['headers', 'meta']:
            obj = technology[key]
            technology[key] = {k.lower(): v for k, v in list(obj.items())}

        # Prepare regular expression patterns
        for key in ['url', 'html', 'scripts']:
            patterns = []
            for pattern in technology[key]:
                patterns.extend(self._prepare_pattern(pattern))
            technology[key] = patterns

        for key in ['headers', 'meta']:
            obj = technology[key]
            for name, pattern in list(obj.items()):
                obj[name] = self._prepare_pattern(obj[name])

    def _prepare_pattern(self, pattern:Union[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Strip out key:value pairs from the pattern and compile the regular
        expression.
        """
        prep_patterns = []
        if isinstance(pattern, list):
            for p in pattern:
                prep_patterns.extend(self._prepare_pattern(p))
        else:
            attrs = {}
            patterns = pattern.split('\\;')
            for index, expression in enumerate(patterns):
                if index == 0:
                    attrs['string'] = expression
                    try:
                        attrs['regex'] = re.compile(expression, re.I) # type: ignore
                    except re.error as err:
                        # Wappalyzer is a JavaScript application therefore some of the regex wont compile in Python.
                        logger.debug(
                            "Caught '{error}' compiling regex: {regex}".format(
                                error=err, regex=patterns)
                        )
                        # regex that never matches:
                        # http://stackoverflow.com/a/1845097/413622
                        attrs['regex'] = re.compile(r'(?!x)x') # type: ignore
                else:
                    attr = expression.split(':')
                    if len(attr) > 1:
                        key = attr.pop(0)
                        attrs[str(key)] = ':'.join(attr)
            prep_patterns.append(attrs)

        return prep_patterns

    def _has_technology(self, technology: Dict[str, Any], webpage: WebPage) -> bool:
        """
        Determine whether the web page matches the technology signature.
        """
        app = technology

        has_app = False
        # Search the easiest things first and save the full-text search of the
        # HTML for last

        for pattern in app['url']:
            if pattern['regex'].search(webpage.url):
                self._set_detected_app(app, 'url', pattern, webpage.url)

        for name, patterns in list(app['headers'].items()):
            if name in webpage.headers:
                content = webpage.headers[name]
                for pattern in patterns:
                    if pattern['regex'].search(content):
                        self._set_detected_app(app, 'headers', pattern, content, name)
                        has_app = True

        for pattern in technology['scripts']:
            for script in webpage.scripts:
                if pattern['regex'].search(script):
                    self._set_detected_app(app, 'scripts', pattern, script)
                    has_app = True

        for name, patterns in list(technology['meta'].items()):
            if name in webpage.meta:
                content = webpage.meta[name]
                for pattern in patterns:
                    if pattern['regex'].search(content):
                        self._set_detected_app(app, 'meta', pattern, content, name)
                        has_app = True

        for pattern in app['html']:
            if pattern['regex'].search(webpage.html):
                self._set_detected_app(app, 'html', pattern, webpage.html)
                has_app = True

        # Set total confidence
        if has_app:
            total = 0
            for index in app['confidence']:
                total += app['confidence'][index]
            app['confidenceTotal'] = total

        return has_app

    def _set_detected_app(self, app: Dict[str, Any], app_type:str, pattern: Dict[str, Any], value:str, key='') -> None:
        """
        Store detected app.
        """
        app['detected'] = True

        # Set confidence level
        if key != '':
            key += ' '
        if 'confidence' not in app:
            app['confidence'] = {}
        if 'confidence' not in pattern:
            pattern['confidence'] = 100
        else:
            # Convert to int for easy adding later
            pattern['confidence'] = int(pattern['confidence'])
        app['confidence'][app_type + ' ' + key + pattern['string']] = pattern['confidence']

        # Dectect version number
        if 'version' in pattern:
            allmatches = re.findall(pattern['regex'], value)
            for i, matches in enumerate(allmatches):
                version = pattern['version']

                # Check for a string to avoid enumerating the string
                if isinstance(matches, str):
                    matches = [(matches)]
                for index, match in enumerate(matches):
                    # Parse ternary operator
                    ternary = re.search(re.compile('\\\\' + str(index + 1) + '\\?([^:]+):(.*)$', re.I), version)
                    if ternary and len(ternary.groups()) == 2 and ternary.group(1) is not None and ternary.group(2) is not None:
                        version = version.replace(ternary.group(0), ternary.group(1) if match != ''
                                                  else ternary.group(2))

                    # Replace back references
                    version = version.replace('\\' + str(index + 1), match)
                if version != '':
                    if 'versions' not in app:
                        app['versions'] = [version]
                    elif version not in app['versions']:
                        app['versions'].append(version)
            self._set_app_version(app)

    def _set_app_version(self, app: Dict[str, Any]) -> None:
        """
        Resolve version number (find the longest version number that *is supposed to* contains all shorter detected version numbers).

        TODO: think if it's the right wat to handled version detection.
        """
        if 'versions' not in app:
            return

        app['versions'] = sorted(app['versions'], key=self._cmp_to_key(self._sort_app_versions))

    def _get_implied_technologies(self, detected_technologies:Iterable[str]) -> Iterable[str]:
        """
        Get the set of technologies implied by `detected_technologies`.
        """
        def __get_implied_technologies(technologies:Iterable[str]) -> Iterable[str] :
            _implied_technologies = set()
            for tech in technologies:
                try:
                    for implie in self.technologies[tech]['implies']:
                        # If we have no doubts just add technology
                        if 'confidence' not in implie:
                            _implied_technologies.add(implie)

                        # Case when we have "confidence" (some doubts)
                        else:
                            try:
                                # Use more strict regexp (cause we have already checked the entry of "confidence")
                                # Also, better way to compile regexp one time, instead of every time
                                app_name, confidence = self._confidence_regexp.search(implie).groups() # type: ignore
                                if int(confidence) >= 50:
                                    _implied_technologies.add(app_name)
                            except (ValueError, AttributeError):
                                pass
                except KeyError:
                    pass
            return _implied_technologies

        implied_technologies = __get_implied_technologies(detected_technologies)
        all_implied_technologies : Set[str] = set()

        # Descend recursively until we've found all implied technologies
        while not all_implied_technologies.issuperset(implied_technologies):
            all_implied_technologies.update(implied_technologies)
            implied_technologies = __get_implied_technologies(all_implied_technologies)

        return all_implied_technologies

    def get_categories(self, tech_name:str) -> List[str]:
        """
        Returns a list of the categories for an technology name.

        :param tech_name: Tech name
        """
        cat_nums = self.technologies.get(tech_name, {}).get("cats", [])
        cat_names = [self.categories.get(str(cat_num), "").get("name", "")
                     for cat_num in cat_nums]

        return cat_names

    def get_versions(self, app_name:str) -> List[str]:
        """
        Retuns a list of the discovered versions for an app name.

        :param app_name: App name
        """
        return [] if 'versions' not in self.technologies[app_name] else self.technologies[app_name]['versions']

    def get_confidence(self, app_name:str) -> Optional[int]:
        """
        Returns the total confidence for an app name.

        :param app_name: App name
        """
        return None if 'confidenceTotal' not in self.technologies[app_name] else self.technologies[app_name]['confidenceTotal']

    def analyze(self, webpage:WebPage) -> Set[str]:
        """
        Return a set of technology that can be detected on the web page.

        :param webpage: The Webpage to analyze
        """
        detected_technologies = set()

        for tech_name, technology in list(self.technologies.items()):
            if self._has_technology(technology, webpage):
                detected_technologies.add(tech_name)

        detected_technologies.update(self._get_implied_technologies(detected_technologies))

        return detected_technologies

    def analyze_with_versions(self, webpage:WebPage) -> Dict[str, Dict[str, Any]]:
        """
        Return a dict of applications and versions that can be detected on the web page.

        :param webpage: The Webpage to analyze
        """
        detected_apps = self.analyze(webpage)
        versioned_apps = {}

        for app_name in detected_apps:
            versions = self.get_versions(app_name)
            versioned_apps[app_name] = {"versions": versions}

        return versioned_apps

    def analyze_with_categories(self, webpage:WebPage) -> Dict[str, Dict[str, Any]]:
        """
        Return a dict of technologies and categories that can be detected on the web page.

        :param webpage: The Webpage to analyze

        >>> wappalyzer.analyze_with_categories(webpage)
        {'Amazon ECS': {'categories': ['IaaS']},
        'Amazon Web Services': {'categories': ['PaaS']},
        'Azure CDN': {'categories': ['CDN']},
        'Docker': {'categories': ['Containers']}}

        """
        detected_technologies = self.analyze(webpage)
        categorised_technologies = {}

        for tech_name in detected_technologies:
            cat_names = self.get_categories(tech_name)
            categorised_technologies[tech_name] = {"categories": cat_names}

        return categorised_technologies

    def analyze_with_versions_and_categories(self, webpage:WebPage) -> Dict[str, Dict[str, Any]]:
        """
        Return a dict of applications and versions and categories that can be detected on the web page.

        :param webpage: The Webpage to analyze

        >>> wappalyzer.analyze_with_versions_and_categories(webpage)
        {'Font Awesome': {'categories': ['Font scripts'], 'versions': ['5.4.2']},
        'Google Font API': {'categories': ['Font scripts'], 'versions': []},
        'MySQL': {'categories': ['Databases'], 'versions': []},
        'Nginx': {'categories': ['Web servers', 'Reverse proxies'], 'versions': []},
        'PHP': {'categories': ['Programming languages'], 'versions': ['5.6.40']},
        'WordPress': {'categories': ['CMS', 'Blogs'], 'versions': ['5.4.2']},
        'Yoast SEO': {'categories': ['SEO'], 'versions': ['14.6.1']}}

        """
        versioned_apps = self.analyze_with_versions(webpage)
        versioned_and_categorised_apps = versioned_apps

        for app_name in versioned_apps:
            cat_names = self.get_categories(app_name)
            versioned_and_categorised_apps[app_name]["categories"] = cat_names

        return versioned_and_categorised_apps

    def _sort_app_versions(self, version_a: str, version_b: str) -> int:
        return len(version_a) - len(version_b)

    def _cmp_to_key(self, mycmp: Callable[..., Any]):
        """
        Convert a cmp= function into a key= function
        """

        # https://docs.python.org/3/howto/sorting.html
        class CmpToKey:
            def __init__(self, obj, *args):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0

        return CmpToKey

def analyze(url:str, 
            update:bool=False, 
            useragent:str=None,
            timeout:int=10,
            verify:bool=True) -> Dict[str, Dict[str, Any]]:
    """
    Quick utility method to analyze a website with minimal configurable options. 

    :See: `WebPage` and `Wappalyzer`. 

    :Parameters:
        - `url`: URL
        - `update`: Update the technologies file from the internet
        - `useragent`: Request user agent
        - `timeout`: Request timeout
        - `verify`: SSL cert verify
    
    :Return: 
        `dict`. Just as `Wappalyzer.analyze_with_versions_and_categories`. 
    :Note: More information might be added to the returned values in the future
    """
    # Create Wappalyzer
    wappalyzer=Wappalyzer.latest(update=update)
    # Create WebPage
    headers={}
    if useragent:
        headers['User-Agent'] = useragent
    webpage=WebPage.new_from_url(url, 
        headers=headers, 
        timeout=timeout, 
        verify=verify)
    # Analyze
    results = wappalyzer.analyze_with_versions_and_categories(webpage)
    return results
