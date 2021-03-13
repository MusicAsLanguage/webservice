from .auth import SignupApi, LoginApi
from .lessons import GetLessonsApi, CreateLessonsApi

def initialize_routes(api):    
    api.add_resource(SignupApi, '/api/auth/signup')
    api.add_resource(LoginApi, '/api/auth/login')
    api.add_resource(GetLessonsApi, '/api/lesson/getLessons')
    api.add_resource(CreateLessonsApi, '/api/lesson/createLessons')