#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        try:
            # Handle the request
            msg = conn.recv(1024).decode()
            req.prepare(msg, routes)
            
            # Check if request parsing failed
            if req.method is None or req.path is None:
                print("[HttpAdapter] Invalid request received, closing connection")
                conn.close()
                return

            # Task 1A: Handle /login POST with authentication (Multi-user support)
            if req.method == 'POST' and req.path == '/login':
                # Parse form data from body
                username = None
                password = None
                if req.body:
                    for param in req.body.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            if key == 'username':
                                username = value
                            elif key == 'password':
                                password = value
                
                # Load users from database
                import json
                import os
                try:
                    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'users.json')
                    with open(db_path, 'r') as f:
                        db = json.load(f)
                        users = db.get('users', [])
                except:
                    # Fallback to hardcoded admin
                    users = [{'username': 'admin', 'password': 'password', 'role': 'user'}]
                
                # Validate credentials against database
                user_found = None
                for user in users:
                    if user['username'] == username and user['password'] == password:
                        user_found = user
                        break
                
                if user_found:
                    print("[HttpAdapter] Login successful for user: {} (role: {})".format(username, user_found.get('role', 'user')))
                    # Set cookies for successful login
                    resp.cookies['auth'] = 'true'
                    resp.cookies['username'] = username
                    resp.cookies['role'] = user_found.get('role', 'user')
                    # Serve index page
                    req.path = '/index.html'
                    response = resp.build_response(req)
                else:
                    print("[HttpAdapter] Login failed for user: {}".format(username))
                    # Return 401 Unauthorized
                    body_content = "<html><body><h1>401 Unauthorized</h1><p>Invalid credentials. <a href='/login.html'>Try again</a> or <a href='/register.html'>Register</a></p></body></html>"
                    response = (
                        "HTTP/1.1 401 Unauthorized\r\n"
                        "Content-Type: text/html\r\n"
                        "Content-Length: {}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "{}"
                    ).format(len(body_content), body_content).encode('utf-8')
            
            # NEW: Handle /register POST - User registration
            elif req.method == 'POST' and req.path == '/register':
                # Parse form data
                username = None
                password = None
                if req.body:
                    for param in req.body.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            if key == 'username':
                                username = value
                            elif key == 'password':
                                password = value
                
                if not username or not password:
                    body_content = "<html><body><h1>Error</h1><p>Username and password required. <a href='/register.html'>Try again</a></p></body></html>"
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/html\r\n"
                        "Content-Length: {}\r\n"
                        "\r\n"
                        "{}"
                    ).format(len(body_content), body_content).encode('utf-8')
                else:
                    # Load and update users database
                    import json
                    import os
                    from datetime import datetime
                    
                    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'users.json')
                    try:
                        with open(db_path, 'r') as f:
                            db = json.load(f)
                    except:
                        db = {'users': []}
                    
                    # Check if username already exists
                    username_exists = any(u['username'] == username for u in db.get('users', []))
                    
                    if username_exists:
                        body_content = "<html><body><h1>Error</h1><p>Username already exists. <a href='/register.html'>Try again</a></p></body></html>"
                        response = (
                            "HTTP/1.1 409 Conflict\r\n"
                            "Content-Type: text/html\r\n"
                            "Content-Length: {}\r\n"
                            "\r\n"
                            "{}"
                        ).format(len(body_content), body_content).encode('utf-8')
                    else:
                        # Add new user
                        new_user = {
                            'username': username,
                            'password': password,
                            'role': 'user',
                            'created_at': datetime.now().isoformat()
                        }
                        db['users'].append(new_user)
                        
                        # Save to database
                        with open(db_path, 'w') as f:
                            json.dump(db, f, indent=2)
                        
                        print("[HttpAdapter] New user registered: {}".format(username))
                        
                        # Auto-login after registration
                        resp.cookies['auth'] = 'true'
                        resp.cookies['username'] = username
                        resp.cookies['role'] = 'user'
                        req.path = '/index.html'
                        response = resp.build_response(req)
            
            # Task 1B: Cookie-based access control for GET /index.html
            elif req.method == 'GET' and req.path == '/index.html':
                # Check for auth cookie
                auth_cookie = req.cookies.get('auth', '')
                if auth_cookie == 'true':
                    print("[HttpAdapter] Authorized access to index page")
                    response = resp.build_response(req)
                else:
                    print("[HttpAdapter] Unauthorized access attempt to index page")
                    # Return 401 Unauthorized
                    body_content = "<html><body><h1>401 Unauthorized</h1><p>Please <a href='/login.html'>login</a> first.</p></body></html>"
                    response = (
                        "HTTP/1.1 401 Unauthorized\r\n"
                        "Content-Type: text/html\r\n"
                        "Content-Length: {}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "{}"
                    ).format(len(body_content), body_content).encode('utf-8')
            
            # Cookie-based access control for GET /chat_discord.html (ADDED)
            elif req.method == 'GET' and req.path == '/chat_discord.html':
                # Check for auth cookie
                auth_cookie = req.cookies.get('auth', '')
                print("[HttpAdapter] Chat access attempt - Cookie value: '{}'".format(auth_cookie))
                if auth_cookie == 'true':
                    print("[HttpAdapter] Authorized access to chat page")
                    response = resp.build_response(req)
                else:
                    print("[HttpAdapter] Unauthorized access attempt to chat page - redirecting to login")
                    # Redirect to login page
                    body_content = "<html><body><h1>401 Unauthorized</h1><p>Please <a href='/login.html'>login</a> first.</p><script>window.location.href='/login.html';</script></body></html>"
                    response = (
                        "HTTP/1.1 401 Unauthorized\r\n"
                        "Content-Type: text/html\r\n"
                        "Content-Length: {}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "{}"
                    ).format(len(body_content), body_content).encode('utf-8')
            
            # Handle request hook for RESTful routes
            elif req.hook:
                print("[HttpAdapter] hook in route-path METHOD {} PATH {}".format(req.hook._route_path,req.hook._route_methods))
                # Call the route handler with headers and body
                result = req.hook(headers=req.headers, body=req.body)
                
                # Convert result to JSON response
                import json
                if isinstance(result, dict):
                    json_body = json.dumps(result)
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
                        "Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
                        "Content-Length: {}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        "{}"
                    ).format(len(json_body), json_body).encode('utf-8')
                else:
                    # Build normal response if not dict
                    response = resp.build_response(req)
            
            else:
                # Build normal response for all other requests (including /login.html)
                response = resp.build_response(req)

            #print(response)
            conn.sendall(response)
            conn.close()
        
        except Exception as e:
            print("[HttpAdapter] Exception in handle_client: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            try:
                conn.close()
            except:
                pass

    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        headers = req.headers
        for header_name, header_value in headers.items():
            if header_name.lower() == "cookie":
                cookie_str = header_value.strip()
                for pair in cookie_str.split(";"):
                    if '=' in pair:
                        key, value = pair.strip().split("=", 1)
                        cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding - simple default
        response.encoding = 'utf-8'
        response.raw = resp
        response.reason = getattr(response.raw, 'reason', 'OK')

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = self.extract_cookies(req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers