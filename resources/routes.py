from .auth import SignupApi, LoginApi, TokenRefreshApi
from .lessons import GetLessonsApi, CreateLessonsApi, \
                    GetActivityStatusApi, UpdateActivityStatusApi, \
                    GetSongPlayingStatusApi, UpdateSongPlayingStatusApi
from .score import  GetUserScoreApi, UpdateUserScoreApi
from .reset_pwd import ForgotPassword, ResetPassword
from .message import SendMsgApi
from .user import DeleteUserAndDataApi
from .speech import SpeechScoreApi

def initialize_routes(api):    
    api.add_resource(SignupApi, '/api/auth/signup')
    api.add_resource(LoginApi, '/api/auth/login')
    api.add_resource(TokenRefreshApi, '/api/auth/tokenRefresh')
    api.add_resource(ForgotPassword, '/api/auth/forgotPwd')
    api.add_resource(ResetPassword, '/api/auth/resetPwd')
    api.add_resource(GetLessonsApi, '/api/lesson/getLessons')
    api.add_resource(CreateLessonsApi, '/api/lesson/createLessons')
    api.add_resource(GetActivityStatusApi, '/api/activity/getStatus')
    api.add_resource(UpdateActivityStatusApi, '/api/activity/updateStatus')
    api.add_resource(GetSongPlayingStatusApi, '/api/activity/getSongPlayingStatus')
    api.add_resource(UpdateSongPlayingStatusApi, '/api/activity/updateSongPlayingStatus')
    api.add_resource(GetUserScoreApi, '/api/user/getUserScore')
    api.add_resource(UpdateUserScoreApi, '/api/user/updateUserScore')
    api.add_resource(DeleteUserAndDataApi, '/api/user/deleteUserAndData')
    api.add_resource(SendMsgApi, '/api/msg/send')
    api.add_resource(SpeechScoreApi, '/api/user/speechScore')