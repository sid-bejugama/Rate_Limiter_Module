from werkzeug.wrappers import Request, Response, ResponseStream
from rateLimiter import *
class RateLimitMiddleWare:
    def __init__(self, app, conn, cur):
        self.app = app
        self.conn = conn
        self.cur = cur

    def __call__(self, env, start_response):
        req = Request(env)
        if req.environ.get('HTTP_X_FORWARDED_FOR') is None:
            ip_address = req.environ['REMOTE_ADDR']
        else:
            ip_address = request.environ['HTTP_X_FORWARDED_FOR']
        user_id = req.args.get('userID', None)
    
        APILimit = track_api_usage(ip_address, self.cur, self.conn, user_id)
            
        if APILimit: return self.app(env, start_response)

        res = Response("Too many requests", status=429)

        return res(env, start_response)