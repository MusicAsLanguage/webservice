from .auth import SignupApi, LoginApi, TokenRefreshApi
from .lessons import GetLessonsApi, CreateLessonsApi, GetActivityStatusApi, UpdateActivityStatusApi

def initialize_routes(api):    
    api.add_resource(SignupApi, '/api/auth/signup')
    api.add_resource(LoginApi, '/api/auth/login')
    api.add_resource(TokenRefreshApi, '/api/auth/tokenRefresh')
    api.add_resource(GetLessonsApi, '/api/lesson/getLessons')
    api.add_resource(CreateLessonsApi, '/api/lesson/createLessons')
    api.add_resource(GetActivityStatusApi, '/api/activity/getStatus')
    api.add_resource(UpdateActivityStatusApi, '/api/activity/updateStatus')